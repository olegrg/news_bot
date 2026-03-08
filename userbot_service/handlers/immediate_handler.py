import asyncio
import logging
from collections import defaultdict

from api_client import get_immediate_subscriptions
from metrics import inc
from telethon.tl.types import PeerChannel

IMMEDIATE_REFRESH_SEC = 60
ALBUM_FLUSH_DELAY = 1.5
IMMEDIATE_POLL_SEC = 10

_immediate_map = defaultdict(list)
_album_buffers = {}
_last_polled_message_id = {}
_delivery_queue = None
logger = logging.getLogger(__name__)


def set_delivery_queue(queue):
    global _delivery_queue
    _delivery_queue = queue

async def refresh_immediate_subscriptions():
    try:
        data = await get_immediate_subscriptions()
    except Exception as exc:
        logger.exception("Failed to load immediate subscriptions from API: %s", exc)
        return
    if not data or not isinstance(data, dict):
        return

    subscriptions = data.get("subscriptions")
    if not subscriptions or not isinstance(subscriptions, list):
        return

    new_map = defaultdict(list)
    for entry in subscriptions:
        channel_id = entry.get("channel_telegram_id")
        user_id = entry.get("user_telegram_id")
        if channel_id and user_id:
            new_map[int(channel_id)].append(int(user_id))

    _immediate_map.clear()
    _immediate_map.update(new_map)
    inc("immediate_subscriptions_refreshed")
    logger.info("Immediate subscriptions refreshed: channels=%d", len(_immediate_map))

async def periodic_refresh():
    while True:
        try:
            await refresh_immediate_subscriptions()
        except Exception as exc:
            logger.exception("Failed to refresh immediate subscriptions: %s", exc)
            inc("immediate_refresh_error")
        await asyncio.sleep(IMMEDIATE_REFRESH_SEC)

async def _enqueue_delivery(channel_id, message_ids, user_ids, source):
    if not _delivery_queue:
        logger.warning("delivery queue is not set, dropping task channel=%s messages=%s", channel_id, message_ids)
        inc("delivery_queue_missing")
        return
    if not user_ids:
        return
    task = {
        "channel_id": int(channel_id),
        "message_ids": [int(mid) for mid in sorted(message_ids)],
        "user_ids": [int(uid) for uid in sorted(set(user_ids))],
        "attempt": 0,
        "source": source,
    }
    await _delivery_queue.enqueue(task)
    inc("delivery_enqueued")
    logger.info(
        "delivery enqueued source=%s channel=%s users=%s messages=%s",
        source,
        channel_id,
        len(task["user_ids"]),
        task["message_ids"],
    )


async def _flush_album(key):
    await asyncio.sleep(ALBUM_FLUSH_DELAY)
    payload = _album_buffers.pop(key, None)
    if not payload:
        return

    await _enqueue_delivery(
        channel_id=key[0],
        message_ids=payload["message_ids"],
        user_ids=list(payload["user_ids"]),
        source="event_album",
    )


def _group_by_album(messages):
    groups = {}
    order = []
    for msg in messages:
        group_id = msg.grouped_id if msg.grouped_id else msg.id
        if group_id not in groups:
            groups[group_id] = []
            order.append(group_id)
        groups[group_id].append(msg)
    return [groups[group_id] for group_id in order]

async def handle_immediate_message(event, client):
    if not event.is_channel:
        return

    channel_id = None
    if event.message and event.message.peer_id and hasattr(event.message.peer_id, "channel_id"):
        channel_id = event.message.peer_id.channel_id

    if not channel_id:
        return

    user_ids = _immediate_map.get(channel_id)
    if not user_ids:
        return

    message = event.message
    _last_polled_message_id[channel_id] = max(_last_polled_message_id.get(channel_id, 0), message.id)
    inc("immediate_event_seen")
    logger.info(
        "Immediate message candidate: channel=%s message_id=%s grouped_id=%s recipients=%d",
        channel_id,
        getattr(message, "id", None),
        getattr(message, "grouped_id", None),
        len(user_ids),
    )

    if message.grouped_id:
        key = (channel_id, message.grouped_id)
        payload = _album_buffers.get(key)
        if not payload:
            payload = {"message_ids": [], "user_ids": set()}
            _album_buffers[key] = payload
            asyncio.create_task(_flush_album(key))
        payload["message_ids"].append(message.id)
        payload["user_ids"].update(user_ids)
        return

    await _enqueue_delivery(
        channel_id=channel_id,
        message_ids=[message.id],
        user_ids=user_ids,
        source="event_single",
    )


async def poll_immediate_messages(client):
    for channel_id, user_ids in list(_immediate_map.items()):
        if not user_ids:
            continue
        try:
            channel_entity = await client.get_entity(PeerChannel(channel_id=channel_id))
        except Exception as exc:
            logger.exception("Immediate poll: cannot resolve channel %s: %s", channel_id, exc)
            inc("immediate_poll_channel_resolve_error")
            continue

        last_seen = _last_polled_message_id.get(channel_id)
        if last_seen is None:
            try:
                latest = await client.get_messages(channel_entity, limit=1)
                if latest:
                    _last_polled_message_id[channel_id] = latest[0].id
            except Exception as exc:
                logger.exception("Immediate poll: cannot get latest message for channel %s: %s", channel_id, exc)
                inc("immediate_poll_bootstrap_error")
            continue

        try:
            messages = await client.get_messages(channel_entity, limit=20, min_id=last_seen)
        except Exception as exc:
            logger.exception("Immediate poll: fetch failed for channel %s: %s", channel_id, exc)
            inc("immediate_poll_fetch_error")
            continue

        if not messages:
            continue

        messages = sorted(messages, key=lambda m: m.id)
        max_id = max(m.id for m in messages)
        _last_polled_message_id[channel_id] = max(last_seen, max_id)
        logger.info(
            "Immediate poll found new messages: channel=%s count=%d from_id>%d",
            channel_id,
            len(messages),
            last_seen,
        )
        inc("immediate_poll_new_messages", len(messages))

        for group in _group_by_album(messages):
            if not group:
                continue
            if group[0].grouped_id:
                await _enqueue_delivery(
                    channel_id=channel_id,
                    message_ids=[m.id for m in group],
                    user_ids=user_ids,
                    source="poll_album",
                )
            else:
                await _enqueue_delivery(
                    channel_id=channel_id,
                    message_ids=[group[0].id],
                    user_ids=user_ids,
                    source="poll_single",
                )


async def periodic_poll(client):
    while True:
        try:
            await poll_immediate_messages(client)
        except Exception as exc:
            logger.exception("Immediate periodic poll failed: %s", exc)
            inc("immediate_poll_error")
        await asyncio.sleep(IMMEDIATE_POLL_SEC)
