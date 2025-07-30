from api_client import get_offsets, create_post, get_top_posts
from telethon.tl.types import PeerChannel
import json

def score(views, forwards, reactions, comments):
    return ((reactions * 1) + (comments * 2) + (comments * 3) + (forwards * 2)) / views

async def handle_post_command(event, client):
    sender = await event.get_sender()
    telegram_id = sender.id

    print(f"Fetching offsets for user {telegram_id}")
    try:
        offsets = await get_offsets(telegram_id)
    except Exception as e:
        await event.respond("Не удалось получить подписки: " + str(e))
        return

    for entry in offsets.get("offsets", []):
        channel_id = entry["channel_id"]
        offset_id = entry["offset_message_id"]
        channel_link = entry["link"]
        print(f"Processing channel {channel_id} with offset {offset_id}")
        try:
            input_channel = await client.get_entity(channel_link)
            messages = await client.get_messages(input_channel, limit=50)

            new_messages = [msg for msg in messages if msg.id > offset_id]

            for msg in reversed(new_messages):
                if msg.id <= 30:
                    continue
                comments_cnt = 0
                reactions_cnt = 0
                if msg.replies is not None:
                    comments_cnt = msg.replies.replies
                if msg.reactions is not None:
                    for reaction in msg.reactions.results:
                        reactions_cnt += reaction.count
                post_data = {
                    "channel_id": channel_id,
                    "message_id": msg.id,
                    "published_at": msg.date.isoformat(),
                    "content": msg.message or "",
                    "views": msg.views or 0,
                    "forwards": msg.forwards or 0,
                    "reactions": reactions_cnt,
                    "comments": comments_cnt,
                    "score": score(msg.views, msg.forwards, reactions_cnt, comments_cnt),
                }
                print(json.dumps(post_data, indent=2))
                await create_post(post_data)

        except Exception as e:
            print(f"Failed to process channel {channel_id}: {e}")

    try:
        top_posts = await get_top_posts(telegram_id)
    except Exception as e:
        await event.respond("Ошибка при получении постов: " + str(e))
        return

    posts = top_posts.get("posts", [])

    if not posts:
        await event.respond("Нет новых интересных постов 🤷‍♂️")
        return

    for post_batch in posts:
        channel = await client.get_entity(post_batch["link"])

        try:
            await client.forward_messages(entity=event.chat_id, messages=post_batch["message_ids"], from_peer=channel)
        except Exception as e:
            print(f"Failed to send post {post_batch}: {e}")
