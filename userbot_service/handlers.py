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
    subscribe_user(user, channel, policy)


@client.on(events.NewMessage(pattern='/post'))
async def handle_post_command(event):
    sender = await event.get_sender()
    telegram_id = sender.id

    print(f"Fetching offsets for user {telegram_id}")
    offsets = get_offsets(telegram_id)

    for entry in offsets.get("offsets", []):
        channel_id = entry["telegram_id"]
        offset_id = entry["offset_message_id"]

        try:
            input_channel = await client.get_entity(PeerChannel(channel_id=channel_id))
            messages = await client.get_messages(input_channel, limit=50)

            new_messages = [msg for msg in messages if msg.id > offset_id]

            for msg in reversed(new_messages):  # по возрастанию id
                post_data = {
                    "channel_id": channel_id,
                    "message_id": msg.id,
                    "published_at": msg.date.isoformat(),
                    "content": msg.message or "",
                    "views": msg.views or 0,
                    "forwards": msg.forwards or 0,
                    "score": 0  # допустим, ты пока его не считаешь тут
                }
                create_post(post_data)

        except Exception as e:
            print(f"Failed to process channel {channel_id}: {e}")

    top_posts = get_top_posts(telegram_id)
    posts = top_posts.get("posts", [])

    if not posts:
        await event.respond("Нет новых интересных постов 🤷‍♂️")
        return

    for post in posts:
        try:
            await event.respond(f"https://t.me/c/{post['channel_id']}/{post['message_id']}")
        except Exception as e:
            print(f"Failed to send post {post}: {e}")