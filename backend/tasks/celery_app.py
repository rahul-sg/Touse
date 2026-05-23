import os
from celery import Celery
from celery.schedules import crontab

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

app = Celery("touse", broker=REDIS_URL, backend=REDIS_URL)

# Ensure the worker imports the task modules on startup.
app.conf.imports = ("tasks.etl_tasks", "tasks.ml_tasks")
app.conf.timezone = "UTC"

# All times UTC. Cadence is matched to how often each source actually publishes.
app.conf.beat_schedule = {
    # Freddie Mac PMMS publishes every Thursday — refresh Friday morning.
    "etl-freddie-mac-weekly": {
        "task": "tasks.etl_tasks.run_freddie_mac_etl",
        "schedule": crontab(day_of_week="friday", hour="9", minute="0"),
    },
    # FRED series (CPI, fed funds, housing starts, unemployment) update monthly;
    # a weekly pass also picks up back-revisions.
    "etl-fred-weekly": {
        "task": "tasks.etl_tasks.run_fred_etl",
        "schedule": crontab(day_of_week="monday", hour="2", minute="0"),
    },
    # Zillow ZIP home values publish mid-month.
    "etl-zillow-zip-monthly": {
        "task": "tasks.etl_tasks.run_zillow_zip_etl",
        "schedule": crontab(day_of_month="15", hour="3", minute="0"),
    },
    # BEA state GDP is annual — a quarterly pass is plenty.
    "etl-bea-quarterly": {
        "task": "tasks.etl_tasks.run_bea_etl",
        "schedule": crontab(month_of_year="1,4,7,10", day_of_month="1", hour="4", minute="0"),
    },
    # Day after fresh Zillow data lands: train the global LightGBM panel +
    # write per-ZIP 12-month endpoint predictions...
    "ml-train-global-lgbm-monthly": {
        "task": "tasks.ml_tasks.train_global_lgbm",
        "schedule": crontab(day_of_month="16", hour="2", minute="0"),
    },
    # ...then re-train cached Prophet trajectories so they use the new anchors.
    "ml-refresh-zip-forecasts-monthly": {
        "task": "tasks.ml_tasks.refresh_zip_forecasts",
        "schedule": crontab(day_of_month="16", hour="4", minute="0"),
    },
}
