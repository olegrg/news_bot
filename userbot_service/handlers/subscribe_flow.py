from telethon.tl.types import PeerChannel

import json

from api_client import subscribe_user, get_subscriptions, delete_subscription
from handlers.subscribe_handler import (
    _build_channel_payload,
    DEFAULT_TOP_N,
    DEFAULT_SEND_IMMEDIATELY,
    format_policy_human,
)
from handlers.immediate_handler import refresh_immediate_subscriptions
from handlers.post_handler import handle_post_command
from llm_intent import parse_intent_with_llm, parse_intent_fallback

STATE = {}

STEP_MODE = "awaiting_mode"
STEP_CHANNEL = "awaiting_channel"
STEP_IMMEDIATE = "awaiting_immediate"

HELP_TEXT = (
    "Я умею работать с подписками на каналы.\n"
    "Вы можете просто писать обычным языком: например, "
    "\"отпиши меня от подписки 4\" или "
    "\"сделай, чтобы из канала 5 посты приходили сразу\".\n"
    "Также можно переслать пост из канала, чтобы подписаться и настроить параметры.\n\n"
    "Важно: я работаю только с подписками и только с открытыми каналами."
)

OFF_TOPIC_TEXT = (
    "Я работаю только с подписками на каналы.\n"
    "По другим темам не отвечаю."
)


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


def _parse_yes_no(text):
    low = (text or "").strip().lower()
    if not low:
        return None

    positive = ("да", "ага", "угу", "конечно", "yes", "yep", "ok", "ок", "sure")
    negative = ("нет", "неа", "не", "no", "nope", "off", "выключ", "отключ")

    if low in ("y", "1", "true", "on"):
        return True
    if low in ("n", "0", "false"):
        return False

    if any(low.startswith(p) for p in positive):
        return True
    if any(low.startswith(n) for n in negative):
        return False

    if "да" in low and "нет" not in low:
        return True
    if "нет" in low or " не " in f" {low} ":
        return False

    return None


async def show_main_menu(event):
    await event.respond(HELP_TEXT)


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
        handled = await _handle_free_text(event, client, event.raw_text or "")
        if not handled:
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
        handled = await _handle_free_text(event, client, text)
        if not handled:
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
            await refresh_immediate_subscriptions()
            _clear_state(user_id)
            await event.respond(f"Подписка удалена: {channel_entity.title}")
            return
        await _start_flow_with_channel(event, client, channel_entity, state.get("mode", "subscribe"))
        return

    if step == STEP_IMMEDIATE:
        send_immediately = _parse_yes_no(event.raw_text or "")
        if send_immediately is None:
            await event.respond("Ответьте: да / нет")
            return
        state["send_immediately"] = send_immediately
        _set_state(user_id, **state)
        await _finalize_subscription(event, client, user_id, DEFAULT_TOP_N)
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
            f"Политика обновлена: {channel['title']}\n"
            f"{format_policy_human(policy)}"
        )
    else:
        await event.respond(
            f"Подписка создана: {channel['title']}\n"
            f"{format_policy_human(policy)}"
        )


async def _handle_list_subscriptions(event):
    sender = await event.get_sender()
    try:
        data = await get_subscriptions(sender.id)
    except Exception:
        await event.respond("Не удалось получить подписки. Попробуйте чуть позже.")
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


async def _handle_free_text(event, client, text):
    sender = await event.get_sender()
    try:
        subscriptions_data = await get_subscriptions(sender.id)
    except Exception:
        subscriptions_data = {"subscriptions": []}
    subscriptions = subscriptions_data.get("subscriptions", []) if subscriptions_data else []

    intent_data = await parse_intent_with_llm(text, subscriptions)
    if intent_data is None:
        intent_data = parse_intent_fallback(text)

    intent = intent_data.get("intent")
    index = intent_data.get("index")
    value = intent_data.get("value")

    if intent == "help" or intent == "unknown":
        if intent == "unknown":
            await event.respond(f"{OFF_TOPIC_TEXT}\n\n{HELP_TEXT}")
        else:
            await show_main_menu(event)
        return True

    if intent == "list":
        await _handle_list_subscriptions(event)
        return True

    if intent == "fetch_posts":
        await handle_post_command(event, client)
        return True

    if intent in ("unsubscribe_by_index", "set_send_immediately"):
        if index is None:
            await event.respond("Не вижу номер канала. Напишите, например: 'отпиши от канала 2'")
            return True
        if index < 1 or index > len(subscriptions):
            await event.respond(f"Неверный номер канала: {index}. Введите /subscriptions, чтобы увидеть список.")
            return True

        sub = subscriptions[index - 1]
        channel_tg = sub.get("channel_telegram_id")
        title = sub.get("title") or sub.get("link") or f"канал #{index}"
        if not channel_tg:
            await event.respond("Не удалось определить канал в подписке.")
            return True

        if intent == "unsubscribe_by_index":
            await delete_subscription(sender.id, int(channel_tg))
            await refresh_immediate_subscriptions()
            await event.respond(f"Готово. Отписал от: {title}")
            return True

        if intent == "set_send_immediately":
            if value is None:
                await event.respond("Не понял, включить или выключить отправку сразу.")
                return True

            policy = {"send_immediately": bool(value)}
            channel = {
                "telegram_id": int(channel_tg),
                "link": sub.get("link") or "",
                "title": sub.get("title") or "",
                "is_private": not bool(sub.get("link")),
            }
            user = {
                "username": sender.username or "",
                "first_name": sender.first_name or "",
                "last_name": sender.last_name or "",
                "telegram_id": sender.id,
            }
            await subscribe_user(user, channel, policy)
            await refresh_immediate_subscriptions()
            await event.respond(
                f"Готово. Канал: {title}\n"
                f"{format_policy_human({'send_immediately': bool(value)})}"
            )
            return True

    return False
