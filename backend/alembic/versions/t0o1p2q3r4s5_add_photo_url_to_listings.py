"""add photo_url to listings_cache

This column was in the ORM model from day one but no migration ever added
it, so any fresh deployment is missing it. Local dev databases ran the
schema directly from the model (create_all) so the bug was invisible until
the first production deploy.

Revision ID: t0o1p2q3r4s5
Revises: s9n0o1p2q3r4
Create Date: 2026-05-27 17:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 't0o1p2q3r4s5'
down_revision = 's9n0o1p2q3r4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # IF NOT EXISTS guard: local dev DBs may already have this column via
    # SQLAlchemy create_all; production never had it.
    conn = op.get_bind()
    has_column = conn.execute(sa.text(
        "SELECT EXISTS (SELECT 1 FROM information_schema.columns "
        "WHERE table_name='listings_cache' AND column_name='photo_url')"
    )).scalar()
    if not has_column:
        op.add_column('listings_cache', sa.Column('photo_url', sa.String(1024), nullable=True))


def downgrade() -> None:
    op.drop_column('listings_cache', 'photo_url')
