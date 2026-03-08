import asyncio
import logging
import os
import time

from telethon.errors import FloodWaitError
from telethon.tl.types import PeerChannel

from metrics import inc

logger = logging.getLogger(__name__)

_rate_lock = asyncio.Lock()
_last_send_ts = 0.0
_recipient_cache = {}
_self_id = None


async def _resolve_recipient(client, user_id):
    global _self_id
    if _self_id is None:
        me = await client.get_me()
        _self_id = me.id

    if user_id == _self_id:
        return "me"

    if user_id in _recipient_cache:
        return _recipient_cache[user_id]

    entity = await client.get_entity(user_id)
    _recipient_cache[user_id] = entity
    return entity


async def _rate_limit_sleep():
    global _last_send_ts
    min_interval = float(os.getenv("DELIVERY_MIN_INTERVAL_SEC", "0.35"))
    async with _rate_lock:
        now = time.monotonic()
        sleep_for = (_last_send_ts + min_interval) - now
        if sleep_for > 0:
            await asyncio.sleep(sleep_for)
        _last_send_ts = time.monotonic()


async def _handle_task(queue, client, task):
    channel_id = int(task["channel_id"])
    message_ids = task["message_ids"]
    user_ids = [int(uid) for uid in task.get("user_ids", [])]
    attempt = int(task.get("attempt", 0))

    if not user_ids:
        return

    try:
        channel_entity = await client.get_entity(PeerChannel(channel_id=channel_id))
    except Exception as exc:
        inc("delivery_channel_resolve_error")
        logger.exception("delivery channel resolve failed channel=%s err=%s", channel_id, exc)
        return

    for idx, user_id in enumerate(user_ids):
        try:
            recipient = await _resolve_recipient(client, user_id)
            await _rate_limit_sleep()
            await client.forward_messages(entity=recipient, messages=message_ids, from_peer=channel_entity)
            inc("delivery_forwarded")
            logger.info(
                "delivery forwarded channel=%s user=%s messages=%s attempt=%s",
                channel_id,
                user_id,
                message_ids,
                attempt,
            )
        except FloodWaitError as exc:
            remaining = user_ids[idx:]
            delay = int(exc.seconds) + 1
            retry_task = {
                "channel_id": channel_id,
                "message_ids": message_ids,
                "user_ids": remaining,
                "attempt": attempt + 1,
                "reason": "flood_wait",
            }
            await queue.requeue_with_delay(retry_task, delay_sec=delay)
            inc("delivery_floodwait")
            logger.warning(
                "delivery floodwait channel=%s wait_sec=%s remaining_users=%s",
                channel_id,
                exc.seconds,
                len(remaining),
            )
            return
        except Exception as exc:
            inc("delivery_forward_error")
            logger.exception(
                "delivery forward failed channel=%s user=%s messages=%s err=%s",
                channel_id,
                user_id,
                message_ids,
                exc,
            )


async def worker_loop(worker_id, queue, client):
    logger.info("delivery worker started id=%s redis=%s", worker_id, queue.is_redis_enabled)
    while True:
        task = await queue.pop(timeout_sec=5)
        if not task:
            continue
        inc("delivery_dequeued")
        await _handle_task(queue, client, task)


async def start_workers(queue, client):
    workers_count = int(os.getenv("DELIVERY_WORKERS", "1"))
    tasks = []
    for idx in range(workers_count):
        tasks.append(asyncio.create_task(worker_loop(idx + 1, queue, client)))
    return tasks
