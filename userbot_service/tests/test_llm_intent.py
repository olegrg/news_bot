from llm_intent import parse_intent_fallback, _extract_json, _normalize_intent, _extract_index


def test_fallback_help():
    assert parse_intent_fallback("привет")["intent"] == "help"
    assert parse_intent_fallback("помощь")["intent"] == "help"
    assert parse_intent_fallback("")["intent"] == "help"
    assert parse_intent_fallback("что ты умеешь?")["intent"] == "help"
    assert parse_intent_fallback("начать")["intent"] == "help"


def test_fallback_list():
    assert parse_intent_fallback("мои подписки")["intent"] == "list"
    assert parse_intent_fallback("список каналов")["intent"] == "list"
    assert parse_intent_fallback("на что я подписан")["intent"] == "list"


def test_fallback_fetch_posts():
    assert parse_intent_fallback("посты")["intent"] == "fetch_posts"
    assert parse_intent_fallback("что нового")["intent"] == "fetch_posts"
    assert parse_intent_fallback("покажи новости")["intent"] == "fetch_posts"
    assert parse_intent_fallback("дальше")["intent"] == "fetch_posts"
    assert parse_intent_fallback("еще")["intent"] == "fetch_posts"
    assert parse_intent_fallback("ещё посты")["intent"] == "fetch_posts"
    assert parse_intent_fallback("топ постов")["intent"] == "fetch_posts"
    assert parse_intent_fallback("что интересного")["intent"] == "fetch_posts"
    assert parse_intent_fallback("покажи лучшее")["intent"] == "fetch_posts"


def test_fallback_unsubscribe():
    result = parse_intent_fallback("отпиши от канала 3")
    assert result["intent"] == "unsubscribe_by_index"
    assert result["index"] == 3

    result = parse_intent_fallback("отписаться от 2")
    assert result["intent"] == "unsubscribe_by_index"
    assert result["index"] == 2

    result = parse_intent_fallback("убери канал 1")
    assert result["intent"] == "unsubscribe_by_index"
    assert result["index"] == 1

    result = parse_intent_fallback("удали 5")
    assert result["intent"] == "unsubscribe_by_index"
    assert result["index"] == 5

    result = parse_intent_fallback("убрать третий")
    assert result["intent"] == "unsubscribe_by_index"
    # "третий" is a word, not a digit — fallback can't extract it, LLM handles this
    assert result["index"] is None


def test_fallback_set_immediately():
    result = parse_intent_fallback("присылай из канала 2 сразу")
    assert result["intent"] == "set_send_immediately"
    assert result["index"] == 2
    assert result["value"] is True

    result = parse_intent_fallback("отключи немедленную из 1")
    assert result["intent"] == "set_send_immediately"
    assert result["index"] == 1
    assert result["value"] is False

    result = parse_intent_fallback("не присылай сразу 3")
    assert result["intent"] == "set_send_immediately"
    assert result["value"] is False


def test_fallback_subscribe():
    assert parse_intent_fallback("хочу подписаться")["intent"] == "subscribe"
    assert parse_intent_fallback("добавь канал")["intent"] == "subscribe"
    assert parse_intent_fallback("хочу читать канал")["intent"] == "subscribe"


def test_fallback_unknown():
    assert parse_intent_fallback("расскажи анекдот")["intent"] == "unknown"
    assert parse_intent_fallback("какая погода")["intent"] == "unknown"


def test_extract_json():
    assert _extract_json('{"intent":"help"}') == {"intent": "help"}
    assert _extract_json('```json\n{"intent":"list"}\n```') == {"intent": "list"}
    assert _extract_json("no json here") is None
    assert _extract_json("") is None
    assert _extract_json(None) is None


def test_normalize_intent():
    assert _normalize_intent({"intent": "help"}) == {"intent": "help", "index": None, "value": None}
    assert _normalize_intent({"intent": "subscribe"}) == {"intent": "subscribe", "index": None, "value": None}
    assert _normalize_intent({"intent": "invalid"}) is None
    result = _normalize_intent({"intent": "set_send_immediately", "index": 2, "value": True})
    assert result["value"] is True
    assert result["index"] == 2


def test_extract_index():
    assert _extract_index("канал 3") == 3
    assert _extract_index("no number") is None
    assert _extract_index("5 канал") == 5
