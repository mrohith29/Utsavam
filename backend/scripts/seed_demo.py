# backend/scripts/seed_demo.py
"""
Usage:
  # ensure DATABASE_URL and REDIS_URL env vars are set (or use .env)
  python backend/scripts/seed_demo.py
This script will:
 - create 3 sample users
 - create 3 sample events
 - initialize Redis token keys for each event
"""
import asyncio
import os
import sys
from datetime import datetime

# Add the project root to Python path for imports
# The script is in backend/scripts/, so go up two levels to reach project root
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Also add the backend directory to the path for app imports
BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from sqlalchemy import select
from app.db import AsyncSessionLocal
from app.models import User, Event
from app.redis_tools import init_tokens_for_event


async def seed():
    async with AsyncSessionLocal() as session:
        async with session.begin():
            # create users if not existing
            emails = ["alice@example.com", "bob@example.com", "carol@example.com"]
            created_users = []
            for email in emails:
                res = await session.execute(select(User).where(User.email == email))
                u = res.scalars().first()
                if not u:
                    u = User(email=email, name=email.split("@")[0].title())
                    session.add(u)
                    created_users.append(email)

            # create events (small capacities to test concurrency)
            now = datetime.utcnow()
            demo_events = [
                {"name": "Indie Concert", "venue": "Stadium A", "start_at": now, "capacity": 5},
                {"name": "Tech Talk", "venue": "Hall B", "start_at": now, "capacity": 50},
                {"name": "Art Expo", "venue": "Gallery C", "start_at": now, "capacity": 100},
            ]
            created_events = []
            for ev in demo_events:
                res = await session.execute(select(Event).where(Event.name == ev["name"]))
                existing = res.scalars().first()
                if existing:
                    created_events.append(existing)
                    continue
                e = Event(
                    name=ev["name"],
                    venue=ev["venue"],
                    start_at=ev["start_at"],
                    capacity=ev["capacity"],
                    seats_available=ev["capacity"],
                    version=0,
                )
                session.add(e)
                created_events.append(e)

        # after commit, initialize redis tokens
        # note: events have ids after flush/commit
        for e in created_events:
            try:
                await init_tokens_for_event(e.id, e.seats_available)
            except Exception as exc:
                print(f"warning: failed to init redis tokens for event {e.id}: {exc}")

    print("Seed complete.")
    print("Users created:", created_users)
    print("Events created or existing:", [e.name for e in created_events])


if __name__ == "__main__":
    asyncio.run(seed())
