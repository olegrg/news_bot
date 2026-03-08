from handlers.subscribe_handler import _parse_top_n, _extract_channel_ref, _parse_send_immediately


def test_parse_top_n():
    assert _parse_top_n('/subscribe @chan top_n=5') == 5
    assert _parse_top_n('/subscribe @chan n=7') == 7
    assert _parse_top_n('/subscribe @chan 4') == 4
    assert _parse_top_n('/subscribe @chan') is None


def test_extract_channel_ref():
    assert _extract_channel_ref('/subscribe @test') == '@test'
    assert _extract_channel_ref('/policy https://t.me/test') == 'https://t.me/test'
    assert _extract_channel_ref('/subscribe') is None


def test_parse_send_immediately():
    assert _parse_send_immediately('/subscribe @chan send_immediately=true') is True
    assert _parse_send_immediately('/subscribe @chan immediate=1') is True
    assert _parse_send_immediately('/subscribe @chan immediate') is True
    assert _parse_send_immediately('/subscribe @chan send_immediately=false') is False
    assert _parse_send_immediately('/subscribe @chan') is None
