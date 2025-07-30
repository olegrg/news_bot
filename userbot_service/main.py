import asyncio
import os
from telethon import TelegramClient, events
from dotenv import load_dotenv

from handlers.subscribe_handler import handle_new_message
from handlers.post_handler import handle_post_command

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
PHONE_NUMBER = os.getenv("PHONE_NUMBER")

client = TelegramClient("userbot_session", API_ID, API_HASH)

@client.on(events.NewMessage)
async def on_message(event):
    await handle_new_message(event, client)

@client.on(events.NewMessage(pattern='/post'))
async def on_post(event):
    await handle_post_command(event, client)

async def main():
    await client.start(PHONE_NUMBER)
    print("Userbot started.")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
