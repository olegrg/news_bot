import re

from telethon.tl.types import PeerChannel

import json

from api_client import subscribe_user, get_subscriptions, delete_subscription
from handlers.subscribe_handler import _build_channel_payload, DEFAULT_TOP_N, DEFAULT_SEND_IMMEDIATELY
from handlers.immediate_handler import refresh_immediate_subscriptions

STATE = {}

STEP_MODE = "awaiting_mode"
STEP_CHANNEL = "awaiting_channel"
STEP_IMMEDIATE = "awaiting_immediate"
STEP_TOP_N = "awaiting_top_n"


def _set_state(user_id, **kwargs):
    STATE[user_id] = kwargs


def _get_state(user_id):
    return STATE.get(user_id)


def _clear_state(user_id):
    STATE.pop(user_id, None)


def _looks_like_command(text):
    return bool(text) and text.strip().startswith("/")


def _extract_channel_ref(text):
    if not text:
        return None
    tokens = text.strip().split()
    if not tokens:
        return None
    return tokens[0]


async def show_main_menu(event):
    await event.respond(
        "Что хотите сделать? Лучше всего переслать пост из канала.\n"
        "1. Подписаться на канал\n"
        "2. Настроить политику\n"
        "3. Показать подписки\n"
        "4. Удалить подписку\n"
        "Ответьте цифрой."
    )


async def _start_flow_with_channel(event, client, channel_entity, mode):
    sender = await event.get_sender()
    user_id = sender.id
    _set_state(user_id, step=STEP_IMMEDIATE, mode=mode, channel_entity=channel_entity)
    await event.respond("Отправлять новые посты сразу? Ответьте: да / нет")


async def handle_message(event, client):
    if not event.is_private:
        return

    sender = await event.get_sender()
    user_id = sender.id
    state = _get_state(user_id)

    if not state:
        if event.fwd_from and isinstance(event.fwd_from.from_id, PeerChannel):
            channel_id = event.fwd_from.from_id.channel_id
            channel_entity = await client.get_entity(PeerChannel(channel_id=channel_id))
            await _start_flow_with_channel(event, client, channel_entity, "subscribe")
            return
        if _looks_like_command(event.raw_text):
            return
        _set_state(user_id, step=STEP_MODE)
        await show_main_menu(event)
        return

    step = state.get("step")
    if step is None:
        _clear_state(user_id)
        return

    if step == STEP_MODE:
        text = (event.raw_text or "").strip()
        if text in ("1", "подписаться", "subscribe"):
            _set_state(user_id, step=STEP_CHANNEL, mode="subscribe")
            await event.respond("Отправьте @канал, ссылку t.me или перешлите сообщение из канала.")
            return
        if text in ("2", "политика", "policy"):
            _set_state(user_id, step=STEP_CHANNEL, mode="policy")
            await event.respond("Отправьте @канал, ссылку t.me или перешлите сообщение из канала.")
            return
        if text in ("3", "подписки", "list"):
            await _handle_list_subscriptions(event)
            _clear_state(user_id)
            return
        if text in ("4", "удалить", "delete"):
            _set_state(user_id, step=STEP_CHANNEL, mode="delete")
            await event.respond("Отправьте @канал или перешлите сообщение из канала для удаления подписки.")
            return
        await show_main_menu(event)
        return

    if step == STEP_CHANNEL:
        channel_entity = None
        if event.fwd_from and isinstance(event.fwd_from.from_id, PeerChannel):
            channel_id = event.fwd_from.from_id.channel_id
            channel_entity = await client.get_entity(PeerChannel(channel_id=channel_id))
        else:
            channel_ref = _extract_channel_ref(event.raw_text)
            if channel_ref:
                channel_entity = await client.get_entity(channel_ref)
        if not channel_entity:
            await event.respond("Лучше всего переслать пост из канала. Не удалось найти канал, попробуйте снова.")
            return
        if state.get("mode") == "delete":
            sender = await event.get_sender()
            await delete_subscription(sender.id, channel_entity.id)
            _clear_state(user_id)
            await event.respond(f"Подписка удалена: {channel_entity.title}")
            return
        await _start_flow_with_channel(event, client, channel_entity, state.get("mode", "subscribe"))
        return

    if step == STEP_IMMEDIATE:
        text = (event.raw_text or "").strip().lower()
        if text in ("да", "yes", "y", "1", "true", "on"):
            send_immediately = True
        elif text in ("нет", "no", "n", "0", "false", "off"):
            send_immediately = False
        else:
            await event.respond("Ответьте: да / нет")
            return
        state["send_immediately"] = send_immediately
        state["step"] = STEP_TOP_N
        _set_state(user_id, **state)
        await event.respond(
            "Сколько постов показывать в подборке? Ответьте числом (например 3)."
        )
        return

    if step == STEP_TOP_N:
        text = event.raw_text or ""
        match = re.search(r"\d+", text)
        if not match:
            await event.respond("Нужно число. Пример: 3")
            return
        top_n = int(match.group(0))
        await _finalize_subscription(event, client, user_id, top_n)
        return



async def _finalize_subscription(event, client, user_id, top_n):
    state = _get_state(user_id)
    if not state or "channel_entity" not in state:
        _clear_state(user_id)
        await event.respond("Сессия устарела. Начните заново.")
        return

    channel_entity = state["channel_entity"]
    send_immediately = state.get("send_immediately", DEFAULT_SEND_IMMEDIATELY)
    mode = state.get("mode", "subscribe")

    sender = await event.get_sender()
    user = {
        "username": sender.username or "",
        "first_name": sender.first_name or "",
        "last_name": sender.last_name or "",
        "telegram_id": sender.id,
    }

    channel = _build_channel_payload(channel_entity)
    policy = {
        "top_n": top_n if top_n is not None else DEFAULT_TOP_N,
        "send_immediately": send_immediately,
    }

    await subscribe_user(user, channel, policy)
    await refresh_immediate_subscriptions()
    _clear_state(user_id)

    if mode == "policy":
        await event.respond(
            f"Политика обновлена: {channel['title']} (top_n={policy['top_n']}, send_immediately={policy['send_immediately']})"
        )
    else:
        await event.respond(
            f"Подписка создана: {channel['title']} (top_n={policy['top_n']}, send_immediately={policy['send_immediately']})"
        )


async def _handle_list_subscriptions(event):
    sender = await event.get_sender()
    data = await get_subscriptions(sender.id)
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
        parts = []
        if top_n is not None:
            parts.append(f"top_n={top_n}")
        if send_immediately is not None:
            parts.append(f"send_immediately={send_immediately}")
        policy_text = ", ".join(parts) if parts else "без политики"
        lines.append(f"{idx}. {title} ({policy_text})")

    await event.respond("\n".join(lines))
