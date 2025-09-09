from __future__ import annotations
from sqlalchemy.orm import declarative_base, Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, DateTime, func, ForeignKey, Text


Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())


    def __repr__(self):
        return f"<User id={self.id} email={self.email}>"


class Event(Base):
    __tablename__ = "events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    venue: Mapped[str] = mapped_column(String(255), nullable=True)
    start_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    seats_available: Mapped[int] = mapped_column(Integer, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


    bookings = relationship("Booking", back_populates="event")


    def __repr__(self):
        return f"<Event id={self.id} name={self.name} seats_available={self.seats_available}>"


class Booking(Base):
    __tablename__ = "bookings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    event_id: Mapped[int] = mapped_column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    seats: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="CONFIRMED")
    idempotency_key: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


    event = relationship("Event", back_populates="bookings")


    def __repr__(self):
        return f"<Booking id={self.id} user_id={self.user_id} event_id={self.event_id} seats={self.seats} status={self.status}>"