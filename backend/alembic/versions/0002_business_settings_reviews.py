"""business settings and reviews

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-05

"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "business_settings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("business_name", sa.String(120), server_default="Bright Studio"),
        sa.Column("tagline", sa.String(200), server_default=""),
        sa.Column("description", sa.Text(), server_default=""),
        sa.Column("address", sa.String(255), server_default=""),
        sa.Column("phone", sa.String(30), server_default=""),
        sa.Column("open_hour", sa.Integer(), server_default="9"),
        sa.Column("close_hour", sa.Integer(), server_default="18"),
        sa.Column("open_days", sa.JSON(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "reviews",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("customer_name", sa.String(120), nullable=False),
        sa.Column("service_id", sa.String(36), sa.ForeignKey("services.id"), nullable=True),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("comment", sa.Text(), server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("reviews")
    op.drop_table("business_settings")
