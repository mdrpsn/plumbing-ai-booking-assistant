"""add customer normalized phone

Revision ID: 20260327_02
Revises: 20260327_01
Create Date: 2026-03-27 22:35:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260327_02"
down_revision = "20260327_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("customers", schema=None) as batch_op:
        batch_op.add_column(sa.Column("normalized_phone", sa.String(length=20), nullable=True))

    customers = sa.table(
        "customers",
        sa.column("id", sa.Integer()),
        sa.column("phone", sa.String(length=50)),
        sa.column("normalized_phone", sa.String(length=20)),
    )

    bind = op.get_bind()
    rows = bind.execute(sa.select(customers.c.id, customers.c.phone)).fetchall()
    for row in rows:
        bind.execute(
            customers.update()
            .where(customers.c.id == row.id)
            .values(normalized_phone=_normalize_phone(row.phone))
        )

    with op.batch_alter_table("customers", schema=None) as batch_op:
        batch_op.alter_column("normalized_phone", existing_type=sa.String(length=20), nullable=False)
        batch_op.create_index(batch_op.f("ix_customers_normalized_phone"), ["normalized_phone"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("customers", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_customers_normalized_phone"))
        batch_op.drop_column("normalized_phone")


def _normalize_phone(phone: str) -> str:
    digits = "".join(character for character in phone if character.isdigit())
    if len(digits) == 10:
        digits = f"1{digits}"
    return f"+{digits}"
