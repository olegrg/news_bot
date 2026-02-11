import asyncio
import logging
import os
from telethon import TelegramClient, events
from dotenv import load_dotenv

from delivery_queue import DeliveryQueue
from delivery_worker import start_workers
from handlers.subscribe_handler import handle_subscribe_command, handle_policy_command, handle_list_command, handle_unsubscribe_command
from handlers.immediate_handler import handle_immediate_message, periodic_refresh, refresh_immediate_subscriptions, periodic_poll, set_delivery_queue
from handlers.post_handler import handle_post_command
from handlers.subscribe_flow import handle_message
from metrics import periodic_metrics_log

load_dotenv()
logging.basicConfig(level=logging.INFO)

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
PHONE_NUMBER = os.getenv("PHONE_NUMBER")

client = TelegramClient("userbot_session", API_ID, API_HASH)

@client.on(events.NewMessage(pattern='/post'))
async def on_post(event):
    await handle_post_command(event, client)

@client.on(events.NewMessage(pattern='/posts'))
async def on_posts(event):
    await handle_post_command(event, client)

@client.on(events.NewMessage(pattern=r'^/subscribe'))
async def on_subscribe(event):
    await handle_subscribe_command(event, client)

@client.on(events.NewMessage(pattern=r'^/policy'))
async def on_policy(event):
    await handle_policy_command(event, client)

@client.on(events.NewMessage(pattern=r'^/subscriptions'))
async def on_subscriptions(event):
    await handle_list_command(event, client)

@client.on(events.NewMessage(pattern=r'^/unsubscribe'))
async def on_unsubscribe(event):
    await handle_unsubscribe_command(event, client)

@client.on(events.NewMessage)
async def on_immediate(event):
    await handle_immediate_message(event, client)

@client.on(events.NewMessage)
async def on_flow_message(event):
    await handle_message(event, client)

async def main():
    await client.start(PHONE_NUMBER)
    print("Userbot started.")
    delivery_queue = DeliveryQueue()
    await delivery_queue.connect()
    set_delivery_queue(delivery_queue)
    await start_workers(delivery_queue, client)
    await refresh_immediate_subscriptions()
    asyncio.create_task(periodic_refresh())
    asyncio.create_task(periodic_poll(client))
    asyncio.create_task(periodic_metrics_log())
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
