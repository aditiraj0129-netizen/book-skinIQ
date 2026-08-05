"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-08-04

"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

appointment_status = sa.Enum(
    "confirmed", "cancelled", "completed", "no_show", name="appointmentstatus"
)


def upgrade() -> None:
    op.create_table(
        "services",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False, unique=True),
        sa.Column("description", sa.Text(), server_default=""),
        sa.Column("duration_minutes", sa.Integer(), server_default="30"),
        sa.Column("price", sa.Numeric(10, 2), server_default="0"),
        sa.Column("active", sa.Boolean(), server_default=sa.true()),
    )

    op.create_table(
        "customers",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(30), server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("email", name="uq_customer_email"),
    )

    op.create_table(
        "appointments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("customer_id", sa.String(36), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("service_id", sa.String(36), sa.ForeignKey("services.id"), nullable=False),
        sa.Column("start_time", sa.DateTime(), nullable=False),
        sa.Column("end_time", sa.DateTime(), nullable=False),
        sa.Column("status", appointment_status, nullable=False, server_default="confirmed"),
        sa.Column("notes", sa.Text(), server_default=""),
        sa.Column("created_via", sa.String(20), server_default="chat"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_appointments_start_time", "appointments", ["start_time"])
    op.create_index("ix_appointments_end_time", "appointments", ["end_time"])
    op.create_index("ix_appointments_status", "appointments", ["status"])

    op.create_table(
        "admin_users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("username", sa.String(80), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
    )

    op.create_table(
        "chat_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("customer_id", sa.String(36), sa.ForeignKey("customers.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("context", sa.JSON(), server_default="{}"),
    )

    op.create_table(
        "chat_messages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("session_id", sa.String(36), sa.ForeignKey("chat_sessions.id"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), server_default=""),
        sa.Column("tool_calls", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("chat_messages")
    op.drop_table("chat_sessions")
    op.drop_table("admin_users")
    op.drop_table("appointments")
    op.drop_table("customers")
    op.drop_table("services")
    appointment_status.drop(op.get_bind(), checkfirst=True)
