from tasks.celery_app import app


@app.task(name="tasks.etl_tasks.run_zillow_etl", bind=True, max_retries=3)
def run_zillow_etl(self):
    try:
        from etl.zillow import fetch_metro_prices, load_to_db
        df = fetch_metro_prices()
        load_to_db(df)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60 * 10)


@app.task(name="tasks.etl_tasks.run_fred_etl", bind=True, max_retries=3)
def run_fred_etl(self):
    try:
        from etl.fred import run_all
        run_all()
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60 * 5)


@app.task(name="tasks.etl_tasks.run_bls_etl", bind=True, max_retries=3)
def run_bls_etl(self):
    try:
        from etl.bls import run_all
        run_all()
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60 * 5)


@app.task(name="tasks.etl_tasks.run_bea_etl", bind=True, max_retries=3)
def run_bea_etl(self):
    try:
        from etl.bea import fetch_state_gdp, load_to_db
        df = fetch_state_gdp()
        load_to_db(df)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60 * 5)


@app.task(name="tasks.etl_tasks.run_policy_etl", bind=True, max_retries=3)
def run_policy_etl(self):
    try:
        from etl.policy import load_to_db
        load_to_db()
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60 * 5)
