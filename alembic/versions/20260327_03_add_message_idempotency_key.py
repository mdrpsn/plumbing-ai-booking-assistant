"""add message idempotency key

Revision ID: 20260327_03
Revises: 20260327_02
Create Date: 2026-03-27 22:55:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260327_03"
down_revision = "20260327_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("messages", schema=None) as batch_op:
        batch_op.add_column(sa.Column("idempotency_key", sa.String(length=120), nullable=True))
        batch_op.create_index(batch_op.f("ix_messages_idempotency_key"), ["idempotency_key"], unique=True)


def downgrade() -> None:
    with op.batch_alter_table("messages", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_messages_idempotency_key"))
        batch_op.drop_column("idempotency_key")
