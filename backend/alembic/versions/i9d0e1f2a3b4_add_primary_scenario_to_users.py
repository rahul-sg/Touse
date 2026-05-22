"""add primary_scenario_id to users

Lets a user nominate one scenario as their "primary" — the one the dashboard
headlines and the one the map / ZIP forecast default to.

Revision ID: i9d0e1f2a3b4
Revises: h8c9d0e1f2a3
Create Date: 2026-05-21 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'i9d0e1f2a3b4'
down_revision = 'h8c9d0e1f2a3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('primary_scenario_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_users_primary_scenario',
        'users', 'scenarios',
        ['primary_scenario_id'], ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint('fk_users_primary_scenario', 'users', type_='foreignkey')
    op.drop_column('users', 'primary_scenario_id')
