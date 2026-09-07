"""Add dashboard users and seed the default administrator.

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-07
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from homelab_monitor.auth.passwords import hash_password

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
    )
    users = sa.table(
        "users",
        sa.column("id", sa.String),
        sa.column("username", sa.String),
        sa.column("password_hash", sa.String),
        sa.column("full_name", sa.String),
        sa.column("role", sa.String),
        sa.column("is_active", sa.Boolean),
    )
    op.bulk_insert(
        users,
        [
            {
                "id": str(uuid.uuid4()),
                "username": "admin",
                "password_hash": hash_password("admin123"),
                "full_name": "Administrator",
                "role": "admin",
                "is_active": True,
            }
        ],
    )


def downgrade() -> None:
    op.drop_table("users")
