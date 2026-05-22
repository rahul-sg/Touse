"""add public_id to scenarios

Adds a non-enumerable base62 identifier for scenarios so URLs and the API no
longer expose the sequential integer primary key.

Revision ID: h8c9d0e1f2a3
Revises: g7b8c9d0e1f2
Create Date: 2026-05-21 00:00:00.000000
"""
import secrets
import string

from alembic import op
import sqlalchemy as sa

revision = 'h8c9d0e1f2a3'
down_revision = 'g7b8c9d0e1f2'
branch_labels = None
depends_on = None

_ALPHABET = string.ascii_letters + string.digits


def _token(length: int = 10) -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(length))


def upgrade() -> None:
    # 1. Add the column nullable so existing rows can be backfilled.
    op.add_column('scenarios', sa.Column('public_id', sa.String(16), nullable=True))

    # 2. Backfill existing rows with unique tokens.
    conn = op.get_bind()
    ids = [r[0] for r in conn.execute(
        sa.text("SELECT id FROM scenarios WHERE public_id IS NULL")
    ).fetchall()]
    used: set[str] = set()
    for sid in ids:
        token = _token()
        while token in used:
            token = _token()
        used.add(token)
        conn.execute(
            sa.text("UPDATE scenarios SET public_id = :p WHERE id = :i"),
            {"p": token, "i": sid},
        )

    # 3. Enforce NOT NULL + uniqueness.
    op.alter_column('scenarios', 'public_id', nullable=False)
    op.create_index('ix_scenarios_public_id', 'scenarios', ['public_id'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_scenarios_public_id', table_name='scenarios')
    op.drop_column('scenarios', 'public_id')
