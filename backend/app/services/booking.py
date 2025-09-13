# booking.py
import asyncio
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from app.models import Event, Booking, User
from app.redis_tools import try_acquire_tokens, try_refund_tokens  # optional token-bucket

MAX_RETRIES = 5

async def create_booking(session: AsyncSession, user_id: int, event_id: int,
                         seats: int = 1, idempotency_key: str | None = None,
                         use_redis_token_bucket: bool = True):
    if seats <= 0:
        raise HTTPException(status_code=400, detail="seats must be > 0")

    # Idempotency check first (fast)
    if idempotency_key:
        q = select(Booking).where(Booking.idempotency_key == idempotency_key)
        res = await session.execute(q)
        existing = res.scalars().first()
        if existing:
            # Ensure we are not leaving an implicit transaction open
            try:
                await session.rollback()
            except Exception:
                pass
            raise HTTPException(status_code=409, detail="Booking with this idempotency key already exists, Please change the `idempotency_key` value")

    # Optionally attempt Redis token bucket fast path.
    # None -> missing key or error; fall back to DB.
    reserved_in_redis = False
    if use_redis_token_bucket:
        redis_result = await try_acquire_tokens(event_id=event_id, tokens=seats)
        if redis_result is True:
            reserved_in_redis = True
        elif redis_result is False:
            # definitely insufficient tokens
            raise HTTPException(status_code=409, detail="Not enough seats")
        else:
            # None: no key/error; proceed to DB check
            pass

    # End any implicit transaction before starting explicit one
    try:
        await session.rollback()
    except Exception:
        pass

    # Pessimistic locking approach inside transaction
    for attempt in range(MAX_RETRIES):
        try:
            async with session.begin():  # transaction
                res = await session.execute(
                    select(Event).where(Event.id == event_id).with_for_update()
                )
                event = res.scalars().first()
                if not event:
                    if reserved_in_redis:
                        await try_refund_tokens(event_id, seats)
                    raise HTTPException(status_code=404, detail="event not found")

                # Ensure user exists to avoid FK violation
                res_user = await session.execute(select(User).where(User.id == user_id))
                user_obj = res_user.scalars().first()
                if not user_obj:
                    if reserved_in_redis:
                        await try_refund_tokens(event_id, seats)
                    raise HTTPException(status_code=404, detail="user not found")
                if event.seats_available < seats:
                    if reserved_in_redis:
                        await try_refund_tokens(event_id, seats)
                    raise HTTPException(status_code=409, detail="Not enough seats")
                # update seats and persist booking
                event.seats_available -= seats
                event.version = event.version + 1
                booking = Booking(user_id=user_id, event_id=event_id, seats=seats,
                                  status="CONFIRMED", idempotency_key=idempotency_key)
                session.add(booking)
                await session.flush()  # ensure booking.id populated
                return booking
        except Exception as e:
            # Detect serialization/lock failures and retry; re-raise others
            # For SQLAlchemy async exceptions inspect DB error codes as needed.
            # Simple exponential backoff
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(0.02 * (attempt + 1))
                continue
            raise

async def cancel_booking(session: AsyncSession, booking_id: int):
    async with session.begin():
        res = await session.execute(select(Booking).where(Booking.id == booking_id))
        booking = res.scalars().first()
        if not booking:
            raise HTTPException(404, "booking not found")
        if booking.status == "CANCELLED":
            return booking
        # lock event, restore seats
        res2 = await session.execute(select(Event).where(Event.id == booking.event_id).with_for_update())
        event = res2.scalars().first()
        event.seats_available += booking.seats
        booking.status = "CANCELLED"
        # also refund redis tokens if using bucket
        await try_refund_tokens(event.id, booking.seats)
        await session.flush()
        return booking

