import os
from celery import Celery
from celery.schedules import crontab

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

app = Celery("touse", broker=REDIS_URL, backend=REDIS_URL)

app.conf.beat_schedule = {
    # Zillow publishes new data mid-month — run on the 15th
    "etl-zillow-monthly": {
        "task": "tasks.etl_tasks.run_zillow_etl",
        "schedule": crontab(day_of_month="15", hour="3", minute="0"),
    },
    # FRED updates weekly for most series
    "etl-fred-weekly": {
        "task": "tasks.etl_tasks.run_fred_etl",
        "schedule": crontab(day_of_week="monday", hour="2", minute="0"),
    },
    # BLS publishes monthly
    "etl-bls-monthly": {
        "task": "tasks.etl_tasks.run_bls_etl",
        "schedule": crontab(day_of_month="5", hour="2", minute="30"),
    },
    # BEA publishes quarterly
    "etl-bea-quarterly": {
        "task": "tasks.etl_tasks.run_bea_etl",
        "schedule": crontab(month_of_year="1,4,7,10", day_of_month="1", hour="4", minute="0"),
    },
    # Policy flags updated annually after election cycle
    "etl-policy-annual": {
        "task": "tasks.etl_tasks.run_policy_etl",
        "schedule": crontab(month_of_year="1", day_of_month="1", hour="5", minute="0"),
    },
    # Retrain Prophet models after Zillow data lands (16th of each month)
    "ml-retrain-prophet-monthly": {
        "task": "tasks.ml_tasks.retrain_prophet_all",
        "schedule": crontab(day_of_month="16", hour="4", minute="0"),
    },
    # Retrain LightGBM after Prophet (17th — uses fresh price history + macro)
    "ml-retrain-lightgbm-monthly": {
        "task": "tasks.ml_tasks.retrain_lightgbm",
        "schedule": crontab(day_of_month="17", hour="4", minute="0"),
    },
}

app.conf.timezone = "UTC"
