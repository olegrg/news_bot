import json
import os
import re
from typing import Any, Dict, List, Optional

import httpx


async def parse_intent_with_llm(text: str, subscriptions: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    api_key = os.getenv("LLM_API_KEY")
    if not api_key:
        return None

    api_base = os.getenv("LLM_API_BASE", "https://api.openai.com/v1").rstrip("/")
    model = os.getenv("LLM_MODEL", "gpt-4o-mini")

    subscriptions_brief = []
    for idx, sub in enumerate(subscriptions, start=1):
        title = sub.get("title") or sub.get("link") or "unknown"
        subscriptions_brief.append(f"{idx}. {title}")

    system_prompt = (
        "You are intent parser for Telegram assistant. "
        "Return strict JSON only with schema: "
        "{\"intent\":\"help|list|fetch_posts|subscribe|unsubscribe_by_index|set_send_immediately|unknown\","
        "\"index\":number|null,\"value\":true|false|null}.\n"
        "subscribe = user wants to add a new channel subscription.\n"
        "fetch_posts = user wants to see new/interesting/top posts."
    )

    user_prompt = (
        "User text:\n"
        f"{text}\n\n"
        "Current subscriptions:\n"
        f"{chr(10).join(subscriptions_brief) if subscriptions_brief else 'no subscriptions'}\n\n"
        "Interpret user's intent. If user asks to disable immediate sending, set value=false."
    )

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=12) as client:
            resp = await client.post(f"{api_base}/chat/completions", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        return None

    content = (
        data.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
    )
    parsed = _extract_json(content)
    if not parsed:
        return None

    return _normalize_intent(parsed)


def parse_intent_fallback(text: str) -> Dict[str, Any]:
    low = (text or "").strip().lower()

    if not low:
        return {"intent": "help", "index": None, "value": None}

    if any(token in low for token in ["привет", "help", "помощ", "умеешь", "команд", "старт", "начат"]):
        return {"intent": "help", "index": None, "value": None}

    idx = _extract_index(low)

    # unsubscribe — check before "list" because "подписк" appears in both
    if any(token in low for token in ["отпиш", "отпис", "отподпис", "убери", "убрать", "удали"]):
        return {"intent": "unsubscribe_by_index", "index": idx, "value": None}

    # immediate delivery
    if any(token in low for token in ["сразу", "немед", "мгнов", "immediate"]):
        disable_markers = ["не ", "отключ", "выключ", "убери", "false", "нет", "без"]
        value = not any(marker in low for marker in disable_markers)
        return {"intent": "set_send_immediately", "index": idx, "value": value}

    # fetch posts — check before "list" because "покажи посты" should be fetch, not list
    if any(token in low for token in [
        "пост", "новости", "новое", "что нового", "дальше",
        "следующ", "еще", "ещё", "интересн", "лучш", "топ",
    ]):
        return {"intent": "fetch_posts", "index": None, "value": None}

    # list subscriptions — "подписки" and "подписан" mean list, not subscribe
    if any(token in low for token in ["список", "подписки", "подписан", "каналы", "мои канал"]):
        return {"intent": "list", "index": None, "value": None}

    # user wants to subscribe but didn't forward a post
    if any(token in low for token in ["подпис", "добавь", "добавить", "хочу читать"]):
        return {"intent": "subscribe", "index": None, "value": None}

    return {"intent": "unknown", "index": None, "value": None}


def _extract_index(text: str) -> Optional[int]:
    match = re.search(r"\d+", text)
    if not match:
        return None
    try:
        return int(match.group(0))
    except Exception:
        return None


def _extract_json(raw: str) -> Optional[Dict[str, Any]]:
    if not raw:
        return None

    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw.replace("json", "", 1).strip()

    try:
        return json.loads(raw)
    except Exception:
        pass

    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None

    try:
        return json.loads(raw[start : end + 1])
    except Exception:
        return None


def _normalize_intent(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    intent = data.get("intent")
    if intent not in {
        "help",
        "list",
        "fetch_posts",
        "subscribe",
        "unsubscribe_by_index",
        "set_send_immediately",
        "unknown",
    }:
        return None

    index = data.get("index")
    if index is not None:
        try:
            index = int(index)
        except Exception:
            index = None

    value = data.get("value")
    if intent == "set_send_immediately":
        if isinstance(value, bool):
            pass
        elif isinstance(value, str):
            value = value.strip().lower() in {"1", "true", "yes", "on", "да"}
        else:
            value = None

    return {"intent": intent, "index": index, "value": value}
