"""
Celery tasks for scheduled data ingestion.

Each task wraps an ETL module's entry point and retries on transient failure.
The cron schedule that drives them lives in tasks/celery_app.py.
"""
from tasks.celery_app import app


@app.task(name="tasks.etl_tasks.run_freddie_mac_etl", bind=True, max_retries=3)
def run_freddie_mac_etl(self):
    """Refresh 30/15-year mortgage rates from Freddie Mac PMMS (publishes weekly)."""
    try:
        from etl.freddie_mac import run
        run()
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60 * 5)


@app.task(name="tasks.etl_tasks.run_fred_etl", bind=True, max_retries=3)
def run_fred_etl(self):
    """Refresh CPI, fed funds rate, housing starts and unemployment from FRED."""
    try:
        from etl.fred import run_all
        run_all()
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60 * 5)


@app.task(name="tasks.etl_tasks.run_zillow_zip_etl", bind=True, max_retries=3)
def run_zillow_zip_etl(self):
    """Refresh ZIP-level home value history from Zillow Research."""
    try:
        from etl.zillow_zip import load_zip_prices
        load_zip_prices()
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60 * 10)


@app.task(name="tasks.etl_tasks.run_zillow_metro_etl", bind=True, max_retries=3)
def run_zillow_metro_etl(self):
    """Refresh metro-level supply/demand indicators from Zillow Research."""
    try:
        from etl.zillow_metro import run
        run()
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60 * 10)


@app.task(name="tasks.etl_tasks.run_bea_etl", bind=True, max_retries=3)
def run_bea_etl(self):
    """Refresh state-level GDP growth from the BEA."""
    try:
        from etl.bea import fetch_state_gdp, load_to_db
        load_to_db(fetch_state_gdp())
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60 * 5)
