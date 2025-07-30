from api_client import subscribe_user
from telethon.tl.types import PeerChannel

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

    channel = {
        "telegram_id": input_channel.id,
        "link": f"https://t.me/{input_channel.username}" if input_channel.username else "",
        "title": input_channel.title,
        "is_private": input_channel.username is None,
    }

    policy = {
        "top_n": 3
    }

    print(f"Subscribing user {user['telegram_id']} to channel {channel['telegram_id']}")
    await subscribe_user(user, channel, policy)
