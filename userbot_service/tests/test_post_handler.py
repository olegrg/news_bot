import datetime

from handlers.post_handler import _group_messages, _aggregate_group, score


class DummyReplies:
    def __init__(self, replies):
        self.replies = replies


class DummyReaction:
    def __init__(self, count):
        self.count = count


class DummyReactions:
    def __init__(self, counts):
        self.results = [DummyReaction(c) for c in counts]


class DummyMessage:
    def __init__(
        self,
        msg_id,
        grouped_id=None,
        message=None,
        date=None,
        views=None,
        forwards=None,
        replies=None,
        reactions=None,
    ):
        self.id = msg_id
        self.grouped_id = grouped_id
        self.message = message
        self.date = date or datetime.datetime(2025, 1, 1)
        self.views = views
        self.forwards = forwards
        self.replies = replies
        self.reactions = reactions


def test_group_messages_groups_albums():
    messages = [
        DummyMessage(1, grouped_id=10),
        DummyMessage(2, grouped_id=10),
        DummyMessage(3),
    ]

    groups = _group_messages(messages)
    assert len(groups) == 2
    assert [msg.id for msg in groups[0]] == [1, 2]
    assert [msg.id for msg in groups[1]] == [3]


def test_aggregate_group_combines_fields():
    group = [
        DummyMessage(
            1,
            grouped_id=10,
            message='first',
            date=datetime.datetime(2025, 1, 1),
            views=100,
            forwards=1,
            replies=DummyReplies(2),
            reactions=DummyReactions([1, 2]),
        ),
        DummyMessage(
            2,
            grouped_id=10,
            message='',
            date=datetime.datetime(2025, 1, 2),
            views=120,
            forwards=2,
            replies=DummyReplies(3),
            reactions=DummyReactions([3]),
        ),
    ]

    content, published_at, views, forwards, reactions_cnt, comments_cnt = _aggregate_group(group)
    assert content == 'first'
    assert published_at == datetime.datetime(2025, 1, 1)
    assert views == 120
    assert forwards == 3
    assert reactions_cnt == 6
    assert comments_cnt == 5


def test_score_handles_zero_views():
    assert score(0, 1, 1, 1) == 0.0
    assert score(None, 1, 1, 1) == 0.0
