from datetime import date, datetime
from sqlalchemy import String, Float, Date, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class ZipLgbmPrediction(Base):
    """Latest global-model 12-month price-growth prediction per (ZIP, home_type).

    Written by the periodic `train_global_lgbm` Celery task — one row per
    (zip, home_type). The projection service reads this to anchor the Prophet
    forecast endpoint for the requested home type.
    """
    __tablename__ = "zip_lgbm_predictions"

    zip_code: Mapped[str] = mapped_column(String(10), primary_key=True)
    home_type: Mapped[str] = mapped_column(String(20), primary_key=True, default="all", server_default="all")
    model_version: Mapped[str] = mapped_column(String(32), nullable=False)
    trained_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    reference_month: Mapped[date] = mapped_column(Date, nullable=False)
    reference_price: Mapped[float] = mapped_column(Float, nullable=False)
    predicted_growth_12m: Mapped[float] = mapped_column(Float, nullable=False)
    predicted_endpoint_price: Mapped[float] = mapped_column(Float, nullable=False)
    data_points_used: Mapped[int] = mapped_column(Integer, default=0)
