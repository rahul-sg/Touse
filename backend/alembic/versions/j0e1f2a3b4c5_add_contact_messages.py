"""add contact_messages table

Stores messages submitted through the public contact form.

Revision ID: j0e1f2a3b4c5
Revises: i9d0e1f2a3b4
Create Date: 2026-05-21 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'j0e1f2a3b4c5'
down_revision = 'i9d0e1f2a3b4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'contact_messages',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(120), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('contact_messages')
