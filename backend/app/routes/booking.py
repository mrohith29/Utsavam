from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_session
from app.services.booking import create_booking, cancel_booking


router = APIRouter()


class BookingRequest(BaseModel):
    user_id: int
    event_id: int
    seats: int = 1
    idempotency_key: str | None = None


@router.post("/bookings", status_code=status.HTTP_201_CREATED)
async def post_booking(req: BookingRequest, session: AsyncSession = Depends(get_session)):
    booking = await create_booking(
    session=session,
    user_id=req.user_id,
    event_id=req.event_id,
    seats=req.seats,
    idempotency_key=req.idempotency_key,
    )
    # return a lightweight response
    return {
    "booking_id": booking.id,
    "status": booking.status,
    "user_id": booking.user_id,
    "event_id": booking.event_id,
    "seats": booking.seats,
    }


@router.delete("/bookings/{booking_id}")
async def delete_booking(booking_id: int, session: AsyncSession = Depends(get_session)):
    booking = await cancel_booking(session=session, booking_id=booking_id)
    return {"booking_id": booking.id, "status": booking.status}