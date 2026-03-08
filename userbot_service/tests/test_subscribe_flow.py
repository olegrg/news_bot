from handlers.subscribe_flow import _parse_yes_no, _looks_like_command, _extract_channel_ref, HELP_TEXT


def test_parse_yes_no_positive():
    assert _parse_yes_no("да") is True
    assert _parse_yes_no("Да") is True
    assert _parse_yes_no("ага") is True
    assert _parse_yes_no("yes") is True
    assert _parse_yes_no("y") is True
    assert _parse_yes_no("1") is True
    assert _parse_yes_no("true") is True
    assert _parse_yes_no("конечно") is True


def test_parse_yes_no_negative():
    assert _parse_yes_no("нет") is False
    assert _parse_yes_no("no") is False
    assert _parse_yes_no("n") is False
    assert _parse_yes_no("0") is False
    assert _parse_yes_no("false") is False
    assert _parse_yes_no("неа") is False


def test_parse_yes_no_none():
    assert _parse_yes_no("") is None
    assert _parse_yes_no(None) is None
    assert _parse_yes_no("что-то непонятное") is None


def test_looks_like_command():
    assert _looks_like_command("/start") is True
    assert _looks_like_command("/subscribe @chan") is True
    assert _looks_like_command("hello") is False
    assert _looks_like_command("") is False
    assert _looks_like_command(None) is False


def test_extract_channel_ref():
    assert _extract_channel_ref("@testchannel") == "@testchannel"
    assert _extract_channel_ref("https://t.me/test extra") == "https://t.me/test"
    assert _extract_channel_ref("") is None
    assert _extract_channel_ref(None) is None


def test_help_text_is_conversational():
    # No slash commands in help text — it's a userbot, not a bot
    assert "/posts" not in HELP_TEXT
    assert "/subscriptions" not in HELP_TEXT
    assert "/unsubscribe" not in HELP_TEXT
    # Has conversational guidance
    assert "перешли" in HELP_TEXT.lower()
    assert "посты" in HELP_TEXT.lower()
    assert "подписки" in HELP_TEXT.lower()
