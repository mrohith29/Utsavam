"""create core tables

Revision ID: 0001_create_tables
Revises:
Create Date: 2025-09-08 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0001_create_tables"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False, unique=True),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("venue", sa.String(length=255), nullable=True),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("seats_available", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "bookings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_id", sa.Integer(), sa.ForeignKey("events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("seats", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="CONFIRMED"),
        sa.Column("idempotency_key", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_index("ix_events_start_at", "events", ["start_at"])
    op.create_index("ix_bookings_event_id", "bookings", ["event_id"])
    op.create_index("ix_bookings_user_id", "bookings", ["user_id"])


def downgrade():
    op.drop_index("ix_bookings_user_id", table_name="bookings")
    op.drop_index("ix_bookings_event_id", table_name="bookings")
    op.drop_index("ix_events_start_at", table_name="events")
    op.drop_table("bookings")
    op.drop_table("events")
    op.drop_table("users")
