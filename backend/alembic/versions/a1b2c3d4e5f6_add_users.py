"""add_users

Revision ID: a1b2c3d4e5f6
Revises: c11ee415d25a
Create Date: 2026-05-20 10:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'c11ee415d25a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("username", sa.String(50), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("annual_income", sa.Float(), nullable=True),
        sa.Column("savings", sa.Float(), nullable=True),
        sa.Column("down_payment", sa.Float(), nullable=True),
        sa.Column("credit_score", sa.Integer(), nullable=True),
        sa.Column("monthly_debt_car", sa.Float(), nullable=False, server_default="0"),
        sa.Column("monthly_debt_student", sa.Float(), nullable=False, server_default="0"),
        sa.Column("monthly_debt_credit", sa.Float(), nullable=False, server_default="0"),
        sa.Column("monthly_debt_other", sa.Float(), nullable=False, server_default="0"),
        sa.Column("zip_code", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_username", "users", ["username"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")
