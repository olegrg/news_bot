from telethon import TelegramClient
import logging
import os
from dotenv import load_dotenv

load_dotenv()

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
PHONE_NUMBER = os.getenv("PHONE_NUMBER")

logging.basicConfig(level=logging.INFO)

client = TelegramClient('news_bot_session', API_ID, API_HASH)

async def fetch_messages(channel_link=None, message_count=10):
    channel = await client.get_entity(channel_link)

    messages = await client.get_messages(channel, limit=message_count)
    
    print(f"Получено {len(messages)} сообщений из канала {channel_link}")
    for msg in messages:
        print(f"Дата: {msg.date}, Id: {msg.id}, Chat: {msg.chat_id}")
    #for msg in messages:
    #    print(f"Дата: {msg.date}, Сообщение: {msg.text}")
        # if msg.media:
        #     print(f"Содержит медиа: {msg.media}")

async def main():
    await client.start(PHONE_NUMBER)
    await fetch_messages('t.me/svtvnews', 10)

if __name__ == "__main__":
    with client:
        client.loop.run_until_complete(main())
