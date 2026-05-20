"""add_scenarios

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-05-20 11:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "scenarios",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("scenario_type", sa.String(10), nullable=False, server_default="buy"),
        sa.Column("annual_income", sa.Float(), nullable=True),
        sa.Column("savings", sa.Float(), nullable=True),
        sa.Column("down_payment", sa.Float(), nullable=True),
        sa.Column("credit_score", sa.Integer(), nullable=True),
        sa.Column("monthly_debt_car", sa.Float(), nullable=False, server_default="0"),
        sa.Column("monthly_debt_student", sa.Float(), nullable=False, server_default="0"),
        sa.Column("monthly_debt_credit", sa.Float(), nullable=False, server_default="0"),
        sa.Column("monthly_debt_other", sa.Float(), nullable=False, server_default="0"),
        sa.Column("zip_code", sa.String(20), nullable=True),
        sa.Column("cached_max_price", sa.Float(), nullable=True),
        sa.Column("cached_monthly_payment", sa.Float(), nullable=True),
        sa.Column("cached_rate_used", sa.Float(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_scenarios_user_id", "scenarios", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_scenarios_user_id", table_name="scenarios")
    op.drop_table("scenarios")
