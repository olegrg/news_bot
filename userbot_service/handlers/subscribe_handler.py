import re

import json

from api_client import subscribe_user, get_subscriptions, delete_subscription
from handlers.immediate_handler import refresh_immediate_subscriptions
from telethon.tl.types import PeerChannel

DEFAULT_TOP_N = 3
DEFAULT_SEND_IMMEDIATELY = False


def _bool_ru(value):
    return "да" if bool(value) else "нет"


def format_policy_human(policy):
    parts = []
    if "top_n" in policy and policy["top_n"] is not None:
        parts.append(f"Максимум постов за раз: {policy['top_n']}")
    if "send_immediately" in policy and policy["send_immediately"] is not None:
        parts.append(f"Присылать новые посты сразу: {_bool_ru(policy['send_immediately'])}")
    if not parts:
        return "Без настроек"
    return "; ".join(parts)

def _parse_top_n(text):
    if not text:
        return None
    match = re.search(r"(?:top_n|topn|n)\s*=\s*(\d+)", text, re.IGNORECASE)
    if match:
        return int(match.group(1))
    tokens = text.strip().split()
    if tokens:
        tail = tokens[-1]
        if tail.isdigit():
            return int(tail)
    return None

def _parse_send_immediately(text):
    if not text:
        return None
    match = re.search(r"(?:send_immediately|immediate)\s*=\s*(\w+)", text, re.IGNORECASE)
    if match:
        value = match.group(1).lower()
        if value in ("1", "true", "yes", "on"):
            return True
        if value in ("0", "false", "no", "off"):
            return False
    if re.search(r"\b(send_immediately|immediate)\b", text, re.IGNORECASE):
        return True
    return None

def _extract_channel_ref(text):
    if not text:
        return None
    tokens = text.strip().split()
    if len(tokens) < 2:
        return None
    return tokens[1]

def _build_channel_payload(input_channel):
    if input_channel.username:
        link = f"https://t.me/{input_channel.username}"
    else:
        link = f"tg://channel?id={input_channel.id}"
    return {
        "telegram_id": input_channel.id,
        "link": link,
        "title": input_channel.title,
        "is_private": input_channel.username is None,
    }

async def handle_new_message(event, client):
    if not event.is_private or not event.fwd_from:
        return

    sender = await event.get_sender()
    from_id = event.fwd_from.from_id

    if not isinstance(from_id, PeerChannel):
        return

    channel_id = from_id.channel_id
    input_channel = await client.get_entity(PeerChannel(channel_id=channel_id))

    user = {
        "username": sender.username or "",
        "first_name": sender.first_name or "",
        "last_name": sender.last_name or "",
        "telegram_id": sender.id,
    }

    channel = _build_channel_payload(input_channel)
    policy = {
        "top_n": DEFAULT_TOP_N,
        "send_immediately": DEFAULT_SEND_IMMEDIATELY,
    }

    print(f"Subscribing user {user['telegram_id']} to channel {channel['telegram_id']}")
    await subscribe_user(user, channel, policy)
    await refresh_immediate_subscriptions()

async def handle_subscribe_command(event, client):
    if not event.is_private:
        return

    text = event.raw_text or ""
    channel_ref = _extract_channel_ref(text)
    if not channel_ref:
        await event.respond("Использование: /subscribe <канал> [top_n=3]")
        return

    top_n = _parse_top_n(text) or DEFAULT_TOP_N
    send_immediately = _parse_send_immediately(text)
    if send_immediately is None:
        send_immediately = DEFAULT_SEND_IMMEDIATELY
    sender = await event.get_sender()

    try:
        input_channel = await client.get_entity(channel_ref)
    except Exception as exc:
        await event.respond(f"Не удалось найти канал: {exc}")
        return

    user = {
        "username": sender.username or "",
        "first_name": sender.first_name or "",
        "last_name": sender.last_name or "",
        "telegram_id": sender.id,
    }
    channel = _build_channel_payload(input_channel)
    policy = {"top_n": top_n, "send_immediately": send_immediately}

    print(f"Subscribing user {user['telegram_id']} to channel {channel['telegram_id']}")
    await subscribe_user(user, channel, policy)
    await refresh_immediate_subscriptions()
    await event.respond(
        f"Подписка создана: {channel['title']}\n"
        f"{format_policy_human(policy)}"
    )

async def handle_policy_command(event, client):
    if not event.is_private:
        return

    text = event.raw_text or ""
    channel_ref = _extract_channel_ref(text)
    if not channel_ref:
        await event.respond("Использование: /policy <канал> top_n=<N>")
        return

    top_n = _parse_top_n(text)
    send_immediately = _parse_send_immediately(text)
    if top_n is None and send_immediately is None:
        await event.respond("Нужен параметр top_n или send_immediately, пример: /policy @channel top_n=5")
        return

    sender = await event.get_sender()

    try:
        input_channel = await client.get_entity(channel_ref)
    except Exception as exc:
        await event.respond(f"Не удалось найти канал: {exc}")
        return

    user = {
        "username": sender.username or "",
        "first_name": sender.first_name or "",
        "last_name": sender.last_name or "",
        "telegram_id": sender.id,
    }
    channel = _build_channel_payload(input_channel)
    policy = {}
    if top_n is not None:
        policy["top_n"] = top_n
    if send_immediately is not None:
        policy["send_immediately"] = send_immediately

    print(f"Updating policy for user {user['telegram_id']} and channel {channel['telegram_id']}")
    await subscribe_user(user, channel, policy)
    await refresh_immediate_subscriptions()
    await event.respond(
        f"Политика обновлена: {channel['title']}\n"
        f"{format_policy_human(policy)}"
    )


async def handle_list_command(event, client):
    if not event.is_private:
        return

    sender = await event.get_sender()
    try:
        data = await get_subscriptions(sender.id)
    except Exception as exc:
        await event.respond(f"Не удалось получить подписки. Попробуйте позже.\nДетали: {exc}")
        return
    subs = data.get("subscriptions", [])
    if not subs:
        await event.respond("У вас нет подписок.")
        return

    lines = ["Ваши подписки:"]
    for idx, sub in enumerate(subs, start=1):
        title = sub.get("title") or sub.get("link") or "Без названия"
        policy_raw = sub.get("policy") or {}
        if isinstance(policy_raw, str):
            try:
                policy_raw = json.loads(policy_raw)
            except Exception:
                policy_raw = {}
        top_n = policy_raw.get("top_n")
        send_immediately = policy_raw.get("send_immediately")
        policy_text = format_policy_human({
            "top_n": top_n,
            "send_immediately": send_immediately,
        })
        lines.append(f"{idx}. {title} ({policy_text})")

    await event.respond("\n".join(lines))


async def handle_unsubscribe_command(event, client):
    if not event.is_private:
        return

    channel_entity = None
    if event.fwd_from and isinstance(event.fwd_from.from_id, PeerChannel):
        channel_id = event.fwd_from.from_id.channel_id
        channel_entity = await client.get_entity(PeerChannel(channel_id=channel_id))
    else:
        text = event.raw_text or ""
        channel_ref = _extract_channel_ref(text)
        if channel_ref:
            channel_entity = await client.get_entity(channel_ref)

    if not channel_entity:
        await event.respond("Использование: /unsubscribe <канал> или перешлите пост из канала.")
        return

    sender = await event.get_sender()
    await delete_subscription(sender.id, channel_entity.id)
    await refresh_immediate_subscriptions()
    await event.respond(f"Подписка удалена: {channel_entity.title}")
