import os
import httpx

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8080")

async def subscribe_user(user, channel, policy=None):
    payload = {"user": user, "channel": channel, "policy": policy}
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{API_BASE}/subscribe", json=payload)
        resp.raise_for_status()
        return resp.json()

async def create_post(post_data):
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{API_BASE}/posts", json=post_data)
        resp.raise_for_status()
        return resp.json()

async def get_top_posts(telegram_id):
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{API_BASE}/top-posts", params={"telegram_id": telegram_id})
        resp.raise_for_status()
        return resp.json()

async def get_offsets(telegram_id):
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{API_BASE}/offsets", params={"telegram_id": telegram_id})
        resp.raise_for_status()
        return resp.json()
