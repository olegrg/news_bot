from api_client import get_offsets, create_post, get_top_posts
from telethon.tl.types import PeerChannel
import json

def score(views, forwards, reactions, comments):
    if not views or views <= 0:
        return 0.0
    weighted = (reactions * 1) + (comments * 3) + (forwards * 2)
    return weighted / views

def _group_messages(messages):
    groups = {}
    order = []
    for msg in messages:
        group_id = msg.grouped_id if msg.grouped_id else msg.id
        if group_id not in groups:
            groups[group_id] = []
            order.append(group_id)
        groups[group_id].append(msg)
    return [groups[group_id] for group_id in order]

def _aggregate_group(group):
    content = ""
    published_at = None
    views = 0
    forwards = 0
    reactions_cnt = 0
    comments_cnt = 0

    for msg in group:
        if not content and msg.message:
            content = msg.message
        if published_at is None or msg.date < published_at:
            published_at = msg.date
        if msg.views is not None:
            views = max(views, msg.views)
        forwards += msg.forwards or 0
        if msg.replies is not None:
            comments_cnt += msg.replies.replies or 0
        if msg.reactions is not None:
            for reaction in msg.reactions.results:
                reactions_cnt += reaction.count

    return content, published_at, views, forwards, reactions_cnt, comments_cnt

async def handle_post_command(event, client):
    sender = await event.get_sender()
    telegram_id = sender.id

    print(f"Fetching offsets for user {telegram_id}")
    try:
        offsets = await get_offsets(telegram_id)
    except Exception as e:
        await event.respond(
            "Не удалось получить подписки.\n"
            "Перешлите пост из канала, чтобы подписаться."
        )
        return

    for entry in offsets.get("offsets", []):
        channel_id = entry["channel_id"]
        offset_id = entry["offset_message_id"]
        telegram_channel_id = entry.get("telegram_id")
        channel_link = entry.get("link")
        print(f"Processing channel {channel_id} with offset {offset_id}")
        try:
            if telegram_channel_id:
                input_channel = await client.get_entity(PeerChannel(channel_id=telegram_channel_id))
            else:
                input_channel = await client.get_entity(channel_link)
            messages = await client.get_messages(input_channel, limit=50)

            new_messages = [msg for msg in messages if msg.id > offset_id]

            for group in _group_messages(reversed(new_messages)):
                if not group:
                    continue
                content, published_at, views, forwards, reactions_cnt, comments_cnt = _aggregate_group(group)
                group_score = score(views, forwards, reactions_cnt, comments_cnt)

                for msg in group:
                    post_data = {
                        "channel_id": channel_id,
                        "message_id": msg.id,
                        "grouped_id": msg.grouped_id,
                        "published_at": published_at.isoformat(),
                        "content": content,
                        "views": views,
                        "forwards": forwards,
                        "reactions": reactions_cnt,
                        "comments": comments_cnt,
                        "score": group_score,
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
        await event.respond(
            "Нет новых интересных постов.\n"
            "Перешлите пост из канала, чтобы добавить подписку."
        )
        return

    for post_batch in posts:
        channel = None
        if post_batch.get("telegram_id"):
            channel = await client.get_entity(PeerChannel(channel_id=post_batch["telegram_id"]))
        else:
            channel = await client.get_entity(post_batch["link"])

        try:
            await client.forward_messages(entity=event.chat_id, messages=post_batch["message_ids"], from_peer=channel)
        except Exception as e:
            print(f"Failed to send post {post_batch}: {e}")
            for msg_id in post_batch["message_ids"]:
                try:
                    await client.forward_messages(entity=event.chat_id, messages=msg_id, from_peer=channel)
                except Exception as e:
                    print(f"Failed to send message {msg_id} from channel {channel.id}: {e}")
