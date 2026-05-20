"""initial_schema

Revision ID: c11ee415d25a
Revises: 
Create Date: 2026-05-19 13:52:03.765443

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c11ee415d25a'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "regions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("metro_id", sa.String(64), nullable=False),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("state", sa.String(2), nullable=False),
        sa.Column("state_name", sa.String(64), nullable=True),
        sa.Column("zip_codes", sa.ARRAY(sa.String(10)), nullable=True),
        sa.Column("zillow_region_id", sa.String(32), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("metro_id"),
    )
    op.create_index("ix_regions_metro_id", "regions", ["metro_id"])
    op.create_index("ix_regions_state", "regions", ["state"])
    op.create_index("ix_regions_zillow_region_id", "regions", ["zillow_region_id"])

    op.create_table(
        "metro_price_history",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("metro_id", sa.String(64), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("median_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("zillow_region_id", sa.String(32), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("metro_id", "date", name="uq_metro_date"),
    )
    op.create_index("ix_metro_price_history_metro_id", "metro_price_history", ["metro_id"])
    op.create_index("ix_metro_price_history_date", "metro_price_history", ["date"])

    op.create_table(
        "macro_indicators",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("series_name", sa.String(64), nullable=False),
        sa.Column("geo_id", sa.String(16), nullable=False, server_default="US"),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("value", sa.Numeric(14, 6), nullable=False),
        sa.Column("source", sa.String(16), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("series_name", "geo_id", "date", name="uq_series_geo_date"),
    )
    op.create_index("ix_macro_indicators_series_name", "macro_indicators", ["series_name"])
    op.create_index("ix_macro_indicators_geo_id", "macro_indicators", ["geo_id"])
    op.create_index("ix_macro_indicators_date", "macro_indicators", ["date"])

    op.create_table(
        "policy_flags",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("state", sa.String(2), nullable=False),
        sa.Column("year", sa.SmallInteger(), nullable=False),
        sa.Column("zoning_reform_score", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("first_time_buyer_credit_active", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("state_housing_bond_passed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("election_year", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("notes", sa.String(512), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("state", "year", name="uq_state_year"),
    )
    op.create_index("ix_policy_flags_state", "policy_flags", ["state"])

    op.create_table(
        "forecast_results",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("metro_id", sa.String(64), nullable=False),
        sa.Column("model_version", sa.String(32), nullable=False),
        sa.Column("trained_at", sa.DateTime(), nullable=False),
        sa.Column("trend_3m", sa.Numeric(8, 4), nullable=True),
        sa.Column("trend_12m", sa.Numeric(8, 4), nullable=True),
        sa.Column("forecast_12m", sa.JSON(), nullable=True),
        sa.Column("top_drivers", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("metro_id", "model_version", name="uq_metro_model"),
    )
    op.create_index("ix_forecast_results_metro_id", "forecast_results", ["metro_id"])

    op.create_table(
        "listings_cache",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("external_id", sa.String(128), nullable=False),
        sa.Column("source", sa.String(32), nullable=False, server_default="rapidapi"),
        sa.Column("address", sa.String(512), nullable=False),
        sa.Column("price", sa.Numeric(12, 2), nullable=False),
        sa.Column("beds", sa.SmallInteger(), nullable=True),
        sa.Column("baths", sa.Numeric(4, 1), nullable=True),
        sa.Column("lat", sa.Numeric(10, 7), nullable=False),
        sa.Column("lng", sa.Numeric(10, 7), nullable=False),
        sa.Column("zip_code", sa.String(10), nullable=True),
        sa.Column("listing_url", sa.String(1024), nullable=True),
        sa.Column("fetched_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_id", "source", name="uq_listing_source"),
    )
    op.create_index("ix_listings_cache_zip_code", "listings_cache", ["zip_code"])


def downgrade() -> None:
    op.drop_table("listings_cache")
    op.drop_table("forecast_results")
    op.drop_table("policy_flags")
    op.drop_table("macro_indicators")
    op.drop_table("metro_price_history")
    op.drop_table("regions")
