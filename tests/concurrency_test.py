import asyncio, httpx, os
from datetime import datetime, timedelta, timezone

BASE = os.getenv("BASE", "http://localhost:8000")
CONCURRENCY = 172
SEATS_PER_REQ = 1

async def ensure_event_id(client: httpx.AsyncClient) -> int:
    # Try to seed demo data (idempotent)
    try:
        await client.post(f"{BASE}/admin/seed_demo_data", headers={"X-Admin-Key": "change_me_admin_key"})
    except Exception:
        pass

    # Fetch events
    r = await client.get(f"{BASE}/events")
    r.raise_for_status()
    try:
        evs = r.json() or []
    except Exception:
        evs = []
    if evs:
        return evs[0]["id"]

    # No events returned: create a temporary one
    start_at = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    payload = {
        "name": "Concurrency Test Event",
        "venue": "Test Hall",
        "start_at": start_at,
        "capacity": 10,
    }
    r = await client.post(
        f"{BASE}/admin/events",
        json=payload,
        headers={"X-Admin-Key": "change_me_admin_key"},
    )
    r.raise_for_status()
    try:
        created = r.json()
    except Exception:
        # If server didn't return JSON, fail clearly
        raise RuntimeError(f"Failed to create event, non-JSON response: {r.text}")
    return created["id"]

async def main():
    async with httpx.AsyncClient(timeout=30) as client:
        event_id = await ensure_event_id(client)

        async def try_book(i):
            try:
                r = await client.post(
                    f"{BASE}/bookings",
                    json={
                        "user_id": [1, 2][i % 2],
                        "event_id": 4,
                        "seats": SEATS_PER_REQ,
                        "idempotency_key": str(i),
                    },
                )
                # Prefer JSON, but fall back to text to avoid decode crashes
                try:
                    body = r.json() if r.content else None
                except Exception:
                    body = r.text
                return r.status_code, body
            except Exception as e:
                return "err", str(e)

        results = await asyncio.gather(*[try_book(i) for i in range(CONCURRENCY)])
        success = sum(1 for st, _ in results if st == 201)
        conflict = sum(1 for st, _ in results if st == 409)
        print("total:", len(results), "success:", success, "conflict:", conflict)
        print(results)

if __name__ == "__main__":
    asyncio.run(main())