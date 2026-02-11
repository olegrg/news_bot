import asyncio
import json
import logging
import os
import time

try:
    import redis.asyncio as redis
except Exception:  # pragma: no cover
    redis = None

logger = logging.getLogger(__name__)


class DeliveryQueue:
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.queue_key = os.getenv("DELIVERY_QUEUE_KEY", "news_bot:delivery:queue")
        self.delayed_key = os.getenv("DELIVERY_DELAYED_KEY", "news_bot:delivery:delayed")
        self._redis_client = None
        self._local_queue = asyncio.Queue()

    @property
    def is_redis_enabled(self):
        return self._redis_client is not None

    async def connect(self):
        if redis is None:
            logger.warning("redis package unavailable, falling back to local in-memory queue")
            return
        try:
            self._redis_client = redis.from_url(self.redis_url, decode_responses=True)
            await self._redis_client.ping()
            logger.info("delivery queue connected to redis url=%s", self.redis_url)
        except Exception as exc:
            self._redis_client = None
            logger.exception("failed to connect redis, fallback to in-memory queue err=%s", exc)

    async def enqueue(self, task):
        payload = json.dumps(task, separators=(",", ":"))
        if self._redis_client:
            await self._redis_client.rpush(self.queue_key, payload)
            return
        await self._local_queue.put(payload)

    async def requeue_with_delay(self, task, delay_sec):
        payload = json.dumps(task, separators=(",", ":"))
        if self._redis_client:
            score = time.time() + max(0, delay_sec)
            await self._redis_client.zadd(self.delayed_key, {payload: score})
            return

        async def _delayed_put():
            await asyncio.sleep(max(0, delay_sec))
            await self._local_queue.put(payload)

        asyncio.create_task(_delayed_put())

    async def _promote_due_tasks(self):
        if not self._redis_client:
            return
        now = time.time()
        due_payloads = await self._redis_client.zrangebyscore(self.delayed_key, min="-inf", max=now)
        if not due_payloads:
            return
        async with self._redis_client.pipeline(transaction=True) as pipe:
            for payload in due_payloads:
                pipe.zrem(self.delayed_key, payload)
                pipe.rpush(self.queue_key, payload)
            await pipe.execute()

    async def pop(self, timeout_sec=5):
        if self._redis_client:
            await self._promote_due_tasks()
            item = await self._redis_client.blpop(self.queue_key, timeout=timeout_sec)
            if not item:
                return None
            _, payload = item
            return json.loads(payload)

        try:
            payload = await asyncio.wait_for(self._local_queue.get(), timeout=timeout_sec)
        except asyncio.TimeoutError:
            return None
        return json.loads(payload)
