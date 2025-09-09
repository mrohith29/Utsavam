# backend/app/main.py
import os
import sys
from typing import List, Optional

# Add the backend directory to Python path for imports
BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from fastapi import FastAPI, APIRouter, Depends, HTTPException, Header, status
from pydantic import BaseModel, Field
from datetime import datetime

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.routes.booking import router as bookings_router
from app.models import Event, User, Booking
from app.redis_tools import init_tokens_for_event
from app.db import engine
from app.models import Base

ADMIN_KEY = os.getenv("ADMIN_KEY", "change_me_admin_key")

app = FastAPI(title="Utsavam - Backend")

# include bookings router (handles /bookings)
app.include_router(bookings_router)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.on_event("startup")
async def startup_create_tables():
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception:
        pass


# Simple events read endpoints
class EventOut(BaseModel):
    id: int
    name: str
    venue: Optional[str]
    start_at: datetime
    capacity: int
    seats_available: int

    class Config:
        orm_mode = True


@app.get("/events", response_model=List[EventOut])
async def list_events(limit: int = 50, upcoming_only: bool = True, session: AsyncSession = Depends(get_session)):
    q = select(Event)
    if upcoming_only:
        q = q.where(Event.start_at >= func.now())
    q = q.order_by(Event.start_at).limit(limit)
    res = await session.execute(q)
    events = res.scalars().all()
    return events


@app.get("/events/{event_id}", response_model=EventOut)
async def get_event(event_id: int, session: AsyncSession = Depends(get_session)):
    res = await session.execute(select(Event).where(Event.id == event_id))
    ev = res.scalars().first()
    if not ev:
        raise HTTPException(status_code=404, detail="event not found")
    return ev


# Admin routes
admin_router = APIRouter(prefix="/admin")


class EventCreate(BaseModel):
    name: str = Field(..., min_length=1)
    venue: Optional[str]
    start_at: datetime
    capacity: int = Field(..., ge=0)


class EventUpdate(BaseModel):
    name: Optional[str]
    venue: Optional[str]
    start_at: Optional[datetime]
    capacity: Optional[int] = Field(None, ge=0)


def require_admin(x_admin_key: Optional[str] = Header(None)):
    if x_admin_key is None or x_admin_key != ADMIN_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="admin auth required")


@admin_router.post("/events", response_model=EventOut, status_code=status.HTTP_201_CREATED)
async def create_event(payload: EventCreate, session: AsyncSession = Depends(get_session), _=Depends(require_admin)):
    async with session.begin():
        event = Event(
            name=payload.name,
            venue=payload.venue,
            start_at=payload.start_at,
            capacity=payload.capacity,
            seats_available=payload.capacity,
            version=0,
        )
        session.add(event)
        await session.flush()  # ensure event.id exists
        # initialize redis tokens (best-effort)
        try:
            await init_tokens_for_event(event.id, event.seats_available)
        except Exception:
            # init tokens is best-effort: don't fail the request if Redis is down
            pass
        return event


@admin_router.put("/events/{event_id}", response_model=EventOut)
async def update_event(event_id: int, payload: EventUpdate, session: AsyncSession = Depends(get_session), _=Depends(require_admin)):
    async with session.begin():
        res = await session.execute(select(Event).where(Event.id == event_id).with_for_update())
        event = res.scalars().first()
        if not event:
            raise HTTPException(status_code=404, detail="event not found")

        # If capacity is being reduced, ensure no confirmed bookings exceed new capacity
        if payload.capacity is not None and payload.capacity < event.capacity:
            res2 = await session.execute(
                select(func.coalesce(func.sum(Booking.seats), 0)).where(Booking.event_id == event_id, Booking.status == "CONFIRMED")
            )
            total_confirmed = res2.scalar_one() or 0
            if payload.capacity < total_confirmed:
                raise HTTPException(status_code=400, detail=f"capacity {payload.capacity} less than confirmed seats {total_confirmed}")

            # adjust seats_available to reflect new free seats
            event.seats_available = payload.capacity - total_confirmed
            event.capacity = payload.capacity
        else:
            # capacity increasing or unchanged
            if payload.capacity is not None:
                delta = payload.capacity - event.capacity
                event.capacity = payload.capacity
                event.seats_available = max(0, (event.seats_available or 0) + delta)

        if payload.name is not None:
            event.name = payload.name
        if payload.venue is not None:
            event.venue = payload.venue
        if payload.start_at is not None:
            event.start_at = payload.start_at

        # update redis token count to match seats_available
        try:
            await init_tokens_for_event(event.id, event.seats_available)
        except Exception:
            pass

        await session.flush()
        return event


@admin_router.post("/seed_demo_data", status_code=status.HTTP_201_CREATED)
async def seed_demo(session: AsyncSession = Depends(get_session), _=Depends(require_admin)):
    """
    Idempotent seed endpoint for demos.
    - Creates demo users and events only if they don't already exist.
    - Initializes Redis token keys for events (best-effort).
    """
    from app.redis_tools import init_tokens_for_event
    from sqlalchemy import select
    from sqlalchemy.exc import IntegrityError

    demo_users = [("alice@example.com", "Alice"), ("bob@example.com", "Bob"), ("carol@example.com", "Carol")]
    now = datetime.utcnow()
    demo_events = [
        {"name": "Indie Concert", "venue": "Stadium A", "start_at": now, "capacity": 5},
        {"name": "Tech Talk", "venue": "Hall B", "start_at": now, "capacity": 50},
        {"name": "Art Expo", "venue": "Gallery C", "start_at": now, "capacity": 100},
    ]

    created_users = []
    created_events = []

    try:
        # Create missing users
        async with session.begin():
            for email, name in demo_users:
                q = select(User).where(User.email == email)
                res = await session.execute(q)
                existing = res.scalars().first()
                if not existing:
                    u = User(email=email, name=name)
                    session.add(u)
                    created_users.append(email)
            await session.flush()

            # Create missing events
            for ev in demo_events:
                q = select(Event).where(Event.name == ev["name"])
                res = await session.execute(q)
                existing = res.scalars().first()
                if not existing:
                    e = Event(
                        name=ev["name"],
                        venue=ev["venue"],
                        start_at=ev["start_at"],
                        capacity=ev["capacity"],
                        seats_available=ev["capacity"],
                        version=0,
                    )
                    session.add(e)
                    created_events.append(ev["name"])
            await session.flush()
    except IntegrityError:
        # Race or duplicate insertion — rollback and re-query to build response
        await session.rollback()
        # re-query current DB state for users/events
        created_users = []
        created_events = []
        for email, _ in demo_users:
            res = await session.execute(select(User).where(User.email == email))
            if res.scalars().first():
                created_users.append(email)
        for ev in demo_events:
            res = await session.execute(select(Event).where(Event.name == ev["name"]))
            if res.scalars().first():
                created_events.append(ev["name"])

    # Initialize redis tokens for events that exist (best-effort)
    # We query events by name so we have the DB ids.
    for ev in demo_events:
        res = await session.execute(select(Event).where(Event.name == ev["name"]))
        e_obj = res.scalars().first()
        if not e_obj:
            continue
        try:
            # init_tokens_for_event overwrites or sets the key to seats_available
            await init_tokens_for_event(e_obj.id, e_obj.seats_available)
        except Exception:
            # best-effort: do not fail seed because Redis is down
            pass

    return {"users_present_or_created": created_users, "events_present_or_created": created_events}


## moved to bottom after admin routes are defined


# Admin: List bookings for an event with user details (newest first)
class AdminEventBookingOut(BaseModel):
    booking_id: int
    user_id: int
    user_email: Optional[str]
    user_name: Optional[str]
    seats: int
    status: str
    created_at: datetime

    class Config:
        orm_mode = True


@admin_router.get("/events/{event_id}/bookings", response_model=List[AdminEventBookingOut])
async def admin_list_event_bookings(event_id: int, session: AsyncSession = Depends(get_session), _=Depends(require_admin)):
    from sqlalchemy.orm import joinedload

    res = await session.execute(
        select(Booking)
        .options(joinedload(Booking.event))
        .where(Booking.event_id == event_id)
        .order_by(Booking.created_at.desc())
    )
    bookings = res.scalars().all()

    # Shape the response with user details via separate query to keep code simple
    # (Alternatively, define relationship and joinedload for User.)
    user_ids = list({b.user_id for b in bookings})
    users_map = {}
    if user_ids:
        res_u = await session.execute(select(User).where(User.id.in_(user_ids)))
        for u in res_u.scalars().all():
            users_map[u.id] = u

    out: list[AdminEventBookingOut] = []
    for b in bookings:
        u = users_map.get(b.user_id)
        out.append(
            AdminEventBookingOut(
                booking_id=b.id,
                user_id=b.user_id,
                user_email=(u.email if u else None),
                user_name=(u.name if u else None),
                seats=b.seats,
                status=b.status,
                created_at=b.created_at,
            )
        )
    return out


# User booking history
class BookingOut(BaseModel):
    id: int
    event_id: int
    seats: int
    status: str
    created_at: datetime

    class Config:
        orm_mode = True


@app.get("/users/{user_id}/bookings", response_model=List[BookingOut])
async def user_booking_history(user_id: int, session: AsyncSession = Depends(get_session)):
    res = await session.execute(
        select(Booking).where(Booking.user_id == user_id).order_by(Booking.created_at.desc())
    )
    return res.scalars().all()


# Admin analytics
class EventAnalytics(BaseModel):
    event_id: int
    name: str
    total_confirmed_bookings: int
    capacity: int
    seats_available: int
    capacity_utilization_pct: float


@admin_router.get("/analytics")
async def analytics(session: AsyncSession = Depends(get_session), _=Depends(require_admin)):
    total_res = await session.execute(
        select(func.count()).select_from(Booking).where(Booking.status == "CONFIRMED")
    )
    total_bookings = int(total_res.scalar() or 0)

    res = await session.execute(
        select(
            Event.id,
            Event.name,
            Event.capacity,
            Event.seats_available,
            func.coalesce(func.sum(Booking.seats), 0),
        )
        .join(Booking, Booking.event_id == Event.id, isouter=True)
        .where((Booking.status == "CONFIRMED") | (Booking.id == None))
        .group_by(Event.id, Event.name, Event.capacity, Event.seats_available)
        .order_by(func.coalesce(func.sum(Booking.seats), 0).desc())
    )

    rows = res.all()
    events: list[EventAnalytics] = []
    for (eid, name, cap, seats_avail, confirmed_sum) in rows:
        cap = int(cap or 0)
        seats_avail = int(seats_avail or 0)
        confirmed = int(confirmed_sum or 0)
        utilized = 0.0
        if cap > 0:
            utilized = round(100.0 * (cap - seats_avail) / cap, 2)
        events.append(
            EventAnalytics(
                event_id=eid,
                name=name,
                total_confirmed_bookings=confirmed,
                capacity=cap,
                seats_available=seats_avail,
                capacity_utilization_pct=utilized,
            )
        )

    return {"total_confirmed_bookings": total_bookings, "events": events}


# Register admin routes after all admin endpoints are defined
app.include_router(admin_router)
