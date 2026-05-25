# Touse

A USA housing tool that shows you **what you can afford, where you can afford it, and where prices are heading** — built on live market data, not a bank's optimistic ceiling.

---

## What it does

- **Affordability engine** — your real max home price across 6 loan types (conventional, FHA, VA, USDA, ARM 5/1, jumbo), using the **live 30-year mortgage rate** from Freddie Mac's weekly survey.
- **Scenarios** — save, edit, and compare multiple buy/rent situations; star one as your **primary scenario**, which drives the dashboard headline, the map, and the forecast.
- **Readiness score** — a 0–100 score with a concrete action plan. Buy scenarios are scored on 5 forward-looking dimensions (DTI *including the projected mortgage*, down payment, credit, cushion, market fit); rent scenarios use a 4-dimension model (DTI, rent burden, credit, cushion).
- **Interactive map** — real listings filtered to your budget, geocoded to their true locations, centered on your primary scenario's area; click a listing card to fly to it. Filter by property type, beds/baths, square footage, year built, and lot size.
- **ZIP price forecast** — a 12-month projection with an 80% confidence band: a global **LightGBM panel model** (lagged prices + US macro + metro supply/rent + election cycle) sets the endpoint, and a per-ZIP **Prophet** model shapes the path. **Type-aware** — switch between all-homes, single-family, and condo forecasts. **Rate-scenario overlays** (rates ±1 point) stress-test sensitivity.
- **Market context** — live mortgage rate, CPI inflation, US unemployment, and your state's GDP growth.
- **Now-vs-wait** — models how *X* more months of saving (across three rate scenarios) changes your budget.
- **Accounts** — email-or-username login, a profile page to manage details and password, and email verification (via Resend).
- **Public calculator** — try affordability anonymously right on the landing page, no signup required.

---

## Architecture

Touse is a small monolith split into four cooperating processes — a Vite SPA, a FastAPI backend, a Celery worker, and a Celery Beat scheduler — backed by PostgreSQL and Redis. Market data is collected by Celery on a public-source cadence, written to Postgres, and served read-mostly by FastAPI. The forecast pipeline is two-stage: a global LightGBM panel sets each ZIP × home-type's 12-month endpoint offline, and a per-`(zip, home_type)` Prophet model shapes the monthly path on demand.

```mermaid
flowchart TB
    UI["Browser — React + Vite SPA<br/>(JWT in localStorage · TanStack Query cache)"]

    subgraph api[FastAPI backend]
        direction TB
        AUTH["Auth + profile<br/>(JWT mint · ownership checks)"]
        AFFORD["Affordability + readiness<br/>(28/36 rule · 6 loan types · DTI scoring)"]
        FORECAST["ZIP forecast API<br/>/lookup · /forecast · /projection · /market-context"]
        LISTINGS["Listings API<br/>(RapidAPI proxy → cache → geocoder)"]
        PROJ["zip_projection service<br/>Prophet path + LightGBM endpoint anchor<br/>(trained on demand · cached per zip × home_type)"]
    end

    subgraph jobs[Celery]
        direction TB
        BEAT["Beat — cron scheduler"]
        ETLW["Worker — ETL tasks<br/>(Zillow ZHVI · Zillow metro · FRED · Freddie · BEA)"]
        MLW["Worker — ML tasks<br/>(train_global_lgbm · refresh_zip_forecasts)"]
    end

    DB[("PostgreSQL<br/>15.8M price rows · macro · listings · users")]
    REDIS[("Redis<br/>Celery broker + result backend<br/>(optional rate-limit store)")]

    subgraph ext[External services]
        ZILLOW["Zillow Research<br/>(ZHVI CSVs · metro supply)"]
        FRED["FRED · Freddie Mac · BEA"]
        RAPID["RapidAPI realty-us"]
        CENSUS["US Census geocoder"]
        RESEND["Resend (transactional email)"]
    end

    UI -->|"REST + Bearer JWT"| AUTH
    UI --> AFFORD
    UI --> FORECAST
    UI --> LISTINGS

    AUTH <--> DB
    AFFORD <--> DB
    FORECAST --> PROJ
    PROJ <--> DB
    LISTINGS <--> DB
    LISTINGS -->|cache miss| RAPID
    LISTINGS -->|geocode| CENSUS
    AUTH -->|verification| RESEND
    api -. slowapi rate limit .-> REDIS

    BEAT --> REDIS
    REDIS --> ETLW
    REDIS --> MLW
    ETLW --> ZILLOW
    ETLW --> FRED
    ETLW --> DB
    MLW <--> DB
```

### Request lifecycle — the headline path

A logged-in user opening their dashboard fans out into three independent reads, all carrying the JWT:

1. **`GET /scenarios/user/{id}`** → `scenarios` table → the SPA renders the primary scenario card.
2. **`POST /readiness`** with the primary scenario → `readiness_service` blends affordability math + DTI + market fit → 0–100 score and action plan.
3. **`GET /api/v1/zip/projection?zip=...&home_type=...`** → `zip_projection.get_or_train()`:
   - Hits `zip_forecast_results` for a cached projection. If found, returned immediately.
   - On miss, pulls all monthly history for `(zip, home_type)` from `zip_price_history`, looks up the LightGBM 12-month endpoint anchor in `zip_lgbm_predictions`, fits Prophet (~1–2 s) anchored to that endpoint, caches the result, returns it.

TanStack Query keeps everything cached client-side; revisits are instant.

### Forecast pipeline (two-stage, offline + on-demand)

```
                 ┌─────────────────── offline (monthly, Celery) ──────────────────┐
                 │                                                                │
ZHVI CSVs ─┐     │   build_panel()                                                │
metro CSVs ┼──→ Postgres ──→  zip × home_type × month                             │
FRED feed ─┘                  + lagged prices + growth rates                      │
                              + US macro + metro supply + rent + election cycle   │
                              → LightGBM panel (n_estimators=250, subsample=0.7,  │
                                 zip_code + home_type as categoricals)            │
                                            ↓                                     │
                              zip_lgbm_predictions ← endpoint anchor per (z, ht)  │
                 │                                                                │
                 └────────────────────────────────────────────────────────────────┘
                                            ↓
                            on demand (first request per z × ht)
                                            ↓
                  Prophet(yearly_seasonality=True) on (z, ht) history
                              ↓
                  blend toward LightGBM endpoint + long-run CAGR
                              ↓
                  zip_forecast_results ←  12 monthly points + 80% band
```

Cached forecasts live in Postgres so a restart loses nothing. Celery refreshes the cache the day after the LightGBM panel retrains, so served forecasts always reflect the newest macro snapshot.

### Refresh cadence (Celery Beat)

All times UTC. Cadence matches each source's actual publication schedule (see `backend/tasks/celery_app.py`).

| When | Task | Why |
|------|------|-----|
| Friday 09:00 | `run_freddie_mac_etl` | PMMS publishes every Thursday |
| Monday 02:00 | `run_fred_etl` | Weekly pass picks up monthly + back-revisions |
| 15th 03:00 | `run_zillow_zip_etl` | Zillow ZHVI publishes mid-month (3 home types) |
| 15th 03:30 | `run_zillow_metro_etl` | Metro supply panel publishes alongside |
| Quarterly | `run_bea_etl` | State GDP is annual; quarterly pass is plenty |
| 16th 02:00 | `train_global_lgbm` | Day after fresh Zillow data — retrain the panel |
| 16th 04:00 | `refresh_zip_forecasts` | Re-fit Prophet caches against new anchors |
| Daily 05:00 | `realize_forecasts` | Backfill `actual_price` for served forecasts whose horizon arrived |

### Forecasting in depth

**Target.** For each `(zip, home_type, month)` panel row, the LightGBM target is the
12-month-forward growth: `target_t = price_{t+12} / price_t − 1`. Rows without a known 12-month-forward
price are excluded from training but kept for prediction at serving time.

**Features** (currently 37, in `backend/app/ml/train_lgbm.py::build_panel`):

- **Local price history** — `price_lag_{1,3,6,12,24}m`, `growth_{1,3,6,12}m`, plus 3- and
  12-month rolling means of monthly growth. Lag features are computed *within* each
  `(zip_code, home_type)` group so a condo's history can never leak into a single-family lag
  for the same ZIP.
- **US macro (FRED + Freddie Mac)** — `mortgage_rate_30y` plus 3-month / 12-month lags and the
  3-month change; `cpi_yoy` (derived from the raw CPI index); `unemployment`; `fed_funds_rate`
  with 3-month and 12-month deltas; `housing_starts`; `consumer_sentiment` (UMich);
  `new_home_sales`. Macros are pivoted wide and joined as-of, backward (only values published
  at or before t are visible at training time t).
- **Metro supply &amp; rent (Zillow Research)** — `invt_fs` (for-sale inventory), `new_listings`,
  `mean_doz_pending` (days-on-market), `perc_price_cut`, `median_list_price`, `median_rent`,
  `invt_fs_yoy`, `new_listings_yoy`, `rent_yoy`, `rent_to_price_ratio`. Joined same-month by
  normalized metro name; same-month join is not leakage because supply at t and price-growth
  from t→t+12 are contemporaneous → future as far as the target is concerned.
- **Cycle &amp; seasonality** — `is_election_year` (presidential + midterm cycles correlate with
  policy uncertainty); `month_sin` and `month_cos` for yearly periodicity.
- **Identity (categoricals)** — `zip_code` and `home_type`. Both are passed to LightGBM as
  categorical features so the model can learn neighborhood- and type-specific effects without
  blowing up the feature space.

**Model hyperparameters** (production, in `train_and_save_predictions`):

```python
LGBMRegressor(
    n_estimators=250,         # reduced from 500 because the typed panel is ~3× larger
    learning_rate=0.05,
    num_leaves=63,
    min_child_samples=100,    # higher than default — guards against tiny-ZIP overfit
    reg_lambda=0.1,
    subsample=0.7,            # row bagging for speed + variance reduction
    subsample_freq=1,
    feature_fraction=0.9,     # column bagging
)
```

**The two-stage serving pipeline** (in `backend/app/services/zip_projection.py`):

1. **Endpoint anchor.** Look up the latest `zip_lgbm_predictions` row for `(zip, home_type)`.
   If present, its `predicted_endpoint_price` becomes the 12-month anchor. If absent
   (cold-start: ZIP without sufficient history for the LightGBM panel to learn from), fall
   back to a clamped 20-year CAGR derived from that ZIP's own series.
2. **Monthly path.** Fit Prophet on the (ZIP, home_type) history with `yearly_seasonality=True`,
   `changepoint_prior_scale=0.03` (low — home values move slowly). Rescale its in-sample
   prediction so the trajectory starts from the current actual price (preventing visible
   jumps), then blend toward the anchor path at each future month — weight starts at 0.30
   near-term and decays to 0.15 at month 12, so the anchor dominates the level throughout.
3. **Confidence band.** Preserve Prophet's relative band width (in % terms) and recenter it
   on the blended value. The 80% interval is Prophet's; conformal calibration is on the
   roadmap.

**Why this design.** Two failure modes deserve two tools. The *endpoint* (where will prices
be in 12 months) is structural — it benefits from seeing every ZIP at once: rate regimes,
supply dynamics, regional momentum. The *path* (how does it get there month by month) is
local — it benefits from a model fit to just that ZIP's own seasonality and noise. Anchoring
heavily toward the LightGBM endpoint stops Prophet's known failure mode (linear extrapolation
of recent slope after a boom).

**Caching.** Forecast results are cached in `zip_forecast_results` keyed by `(zip, home_type)`,
stamped with `model_version` and `trained_at`. The cache is treated as stale if either the
model version changes or the row is older than 30 days. Celery refreshes the cache the day
after the LightGBM panel retrains so served forecasts always reflect the newest anchor.

**Audit trail.** Every production training run inserts a row into `model_runs` capturing
`(version, trained_at, panel_rows, train_rows, feature_count, zips_predicted, train_seconds)`
and optional backtest metrics (`mape_all`, `bias_all`, `per_type` JSON, `seeds` JSON). The
`/api/v1/methodology/summary` endpoint reads the most recent row and the `/about` page links
to a public methodology view that surfaces it to users.

**Realized-accuracy tracking.** Every served forecast inserts a placeholder row into
`forecast_realizations` (predicted endpoint, horizon end, current price at serve time). A
daily Celery task (`tasks.ml_tasks.realize_forecasts`) backfills `actual_price` once the
12-month horizon arrives — looking up the matching ZHVI value in `zip_price_history` for
the `(zip, home_type, horizon_end)` triple — and computes the absolute and signed percentage
error. The Forecast page surfaces a per-ZIP track-record badge once at least one realized
prediction exists ("our forecasts in this ZIP have averaged X% MAPE across N realized
predictions"). Idempotent: re-runs of the task skip already-filled rows.

### ETL pipelines

Each ETL is a `python -m etl.<name>` entry point under `backend/etl/`. They are idempotent:
all writes use `INSERT ... ON CONFLICT DO UPDATE` on the appropriate composite key.

| Module | Source | Cadence | Notes |
|--------|--------|---------|-------|
| `etl.zip_centroids` | Public ZIP centroid CSV | one-time | 41k rows; rerun only when the ZIP list changes |
| `etl.zillow_zip` | Zillow ZHVI CSVs (3 home types) | monthly | ~15.8M rows; iterates all 3 series and upserts on `(zip, home_type, date)` |
| `etl.zillow_metro` | Zillow Research metro panel | monthly | Inventory, new listings, days-on-market, price cuts, rent |
| `etl.freddie_mac` | Freddie Mac PMMS | weekly | Weekly 30- and 15-year fixed rates |
| `etl.fred` | FRED API | weekly | CPI, fed funds, unemployment, housing starts, sentiment, new-home sales |
| `etl.bea` | BEA API | quarterly | State GDP growth |
| `etl.geocode_listings` | US Census geocoder | on-demand | Backfills `listings_cache.lat/lng` for previously cached rows |

The Celery Beat schedule in `backend/tasks/celery_app.py` matches each source's actual
publication schedule, so what you see is never more than one publication cycle behind. ML
retraining (`tasks.ml_tasks.train_global_lgbm`) runs the day after the monthly Zillow drop;
`tasks.ml_tasks.refresh_zip_forecasts` runs two hours later to re-fit cached Prophet
trajectories against the new anchors.

### Trust boundaries

- **ETL workers are the only writers of market data.** API routes never write `zip_price_history`, `macro_indicators`, etc. — this keeps the read path simple and prevents user input from corrupting market state.
- **Every user-data endpoint requires a JWT and verifies ownership.** A user can only read/write their own profile and scenarios; the `public_id` on scenarios is a non-enumerable opaque token so shared/scenario URLs can't be guessed.
- **Listings flow is RapidAPI → Census geocoder → 6-hour cache.** Addresses the geocoder can't match (≈25%) fall back to the ZIP centroid; the rest land on real coordinates.
- **Rate limiting is per-IP via slowapi** — in-memory by default, switchable to Redis via `RATELIMIT_STORAGE_URI` so the limit holds across multiple backend instances behind a load balancer.

### Key database tables

| Table | Holds |
|-------|-------|
| `users`, `scenarios` | Accounts and saved buy/rent scenarios (scenarios keyed by a non-enumerable `public_id`; each scenario carries a `home_type`) |
| `zip_price_history` | ~15.8M monthly Zillow ZHVI values by (ZIP, `home_type`: all / single_family / condo) |
| `zip_centroids` | ~41k ZIP → lat/lng/city/state |
| `zip_forecast_results` | Cached 12-month projections, keyed by (zip, home_type), stamped with `model_version` |
| `zip_lgbm_predictions` | Endpoint anchors from the global LightGBM panel, per (zip, home_type) |
| `model_runs` | Audit trail for every production training run — version, panel size, train time, optional backtest metrics |
| `forecast_realizations` | One row per served forecast (predicted endpoint, horizon end). A daily Celery task fills `actual_price` once the horizon arrives; powers the per-ZIP track-record badge |
| `macro_indicators` | Mortgage rates, CPI, fed funds, housing starts, unemployment, consumer sentiment, new-home sales, state GDP |
| `metro_supply_history` | Zillow Research metro supply + rent panel (inventory, new listings, days-on-market, price cuts, median rent) |
| `listings_cache` | Geocoded listing snapshots (6h TTL) with property type, sqft, year built, lot size |
| `contact_messages` | Submissions from the contact form |

**Migrations** live in `backend/alembic/versions/` and run in a single linear chain
(`alembic upgrade head`). Schema changes are additive wherever possible — adding `home_type` to
`zip_price_history` backfilled all 6.3M existing rows to `'all'` so prior consumers kept working
without code changes. The `zip_lgbm_predictions` table's primary key was migrated from
`(zip_code)` to `(zip_code, home_type)` to support per-type endpoint storage.

### API surface

All routes live under `/api/v1/*` unless noted. Auth-required endpoints expect a
`Authorization: Bearer <jwt>` header.

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/health` | — | Liveness probe (cheap, no DB) |
| GET | `/healthz` | — | Readiness probe — DB reachability + freshness of price + mortgage rate data |
| POST | `/api/v1/affordability` | — | Public affordability calculator (used by the landing page) |
| POST | `/api/v1/rental-affordability` | — | Rent-side companion calculator |
| POST | `/api/v1/readiness` | — | 0–100 readiness score + action plan |
| POST | `/api/v1/compare/now-vs-wait` | — | Three rate scenarios × N months of additional saving |
| POST | `/api/v1/register` · `/login` · `/verify-email` | — | Account flow (JWT-issuing) |
| GET / PATCH | `/api/v1/me/{user_id}` · `/account/{user_id}` · `/profile/{user_id}` · `/target-zip/{user_id}` | ✓ | User-self CRUD |
| POST | `/api/v1/change-password/{user_id}` · `/resend-verification/{user_id}` | ✓ | Sensitive account actions |
| GET / POST | `/api/v1/scenarios/user/{user_id}` | ✓ | List / create scenarios for a user |
| PUT / DELETE / PATCH | `/api/v1/scenarios/{public_id}` · `/.../primary` | ✓ | Mutate / delete / star a scenario (ownership-checked) |
| GET | `/api/v1/zip/lookup?zip=...` | — | ZIP → lat/lng + city/state |
| GET | `/api/v1/zip/nearest?lat=&lng=` | — | Reverse-lookup: nearest ZIP centroid |
| GET | `/api/v1/zip/forecast?zip=&home_type=` | — | Price trend indicators (3/6/12-month % + direction) |
| GET | `/api/v1/zip/projection?zip=&home_type=` | — | 12-month forecast (Prophet path + LightGBM anchor) |
| GET | `/api/v1/zip/forecast-accuracy?zip=&home_type=` | — | Realized MAPE / bias for past forecasts on this ZIP (returns `samples: 0` if no track record yet) |
| GET | `/api/v1/zip/market-context?zip=` | — | Live macro snapshot for the ZIP's state |
| GET | `/api/v1/listings?lat=&lng=&radius_miles=&max_price=...` | — | Live for-sale listings (RapidAPI proxy + geocoded cache) |
| GET | `/api/v1/regions/search?q=` · `/regions/nearest?lat=&lng=` | — | Region search / reverse lookup |
| POST | `/api/v1/contact` | — | Contact-form submission |
| GET | `/api/v1/methodology/summary` | — | Model card for the live LightGBM panel — version, training stats, coverage, backtest metrics |

**Rate limits** (per IP, via slowapi): cheap endpoints 60/min, lookup 120/min,
projection 20/min, contact 5/min. The store defaults to in-memory and can be
swapped to Redis via `RATELIMIT_STORAGE_URI` for multi-instance deployments.

---

## Stack

| Layer | Tech |
|-------|------|
| Frontend | React 18 + Vite + TypeScript |
| Routing / data | React Router v6 · TanStack Query v5 |
| Charts / map | Recharts · MapLibre GL + react-map-gl (OpenFreeMap tiles — no API key) |
| Backend | FastAPI + Python 3.11 · SQLAlchemy (async) |
| Auth | JWT (python-jose) + bcrypt |
| Database | PostgreSQL · Alembic migrations |
| Forecasting | LightGBM panel (global, retrained monthly) + Prophet (per-ZIP × home_type, trained on demand) |
| Background jobs | Celery + Redis (Beat schedule for ETL & retraining) |
| Email | Resend (transactional) |
| Deployment | Docker Compose |

---

## Data sources

| Source | Used for | API key |
|--------|----------|---------|
| [Zillow Research](https://www.zillow.com/research/data/) | Monthly ZHVI by ZIP × home type (all / SFR / condo); metro supply + rent panel | none (CSV) |
| [Freddie Mac PMMS](https://www.freddiemac.com/pmms) | Weekly 30/15-yr mortgage rates | **none** |
| [FRED](https://fred.stlouisfed.org/) | CPI, fed funds, housing starts, unemployment, UMich consumer sentiment, new-home sales | `FRED_API_KEY` |
| [BEA](https://apps.bea.gov/API/) | State GDP growth | `BEA_API_KEY` |
| [US Census Geocoder](https://geocoding.geo.census.gov/) | Real listing coordinates | **none** |
| [RapidAPI realty-us](https://rapidapi.com/) | Live for-sale listings | `RAPIDAPI_KEY` |
| [Resend](https://resend.com/) | Account verification emails | `RESEND_API_KEY` |

Metro-level forecasting from the original design was retired in favour of the ZIP-native pipeline. Without `RESEND_API_KEY` the app still runs — verification emails are logged instead of sent.

---

## Routes

| Path | Page |
|------|------|
| `/` | Marketing landing + public affordability calculator |
| `/onboarding` | Two-step signup + financial profile |
| `/login` | Sign in (email or username) |
| `/verify-email` | Email-verification landing |
| `/dashboard` | Headline (primary scenario), readiness score, scenarios |
| `/profile` | Manage account details and password |
| `/map` | Interactive listings map |
| `/forecast/:zip` | ZIP price forecast + market context (with `?type=single_family\|condo`) |
| `/scenarios/:publicId` | Scenario detail |
| `/about` | What Touse does, math, data sources, contact form (links into Methodology) |
| `/methodology` | Deep-dive: live model card, backtest metrics, features, pipeline math (linked from About) |

---

## Getting started (local dev)

**Prerequisites:** Python 3.11, Node 18+, PostgreSQL, a C++ toolchain (for Prophet/Stan).

```bash
# 1. Config — fill in API keys (FRED, BEA, RapidAPI at minimum)
cp .env.example .env

# 2. Database — start PostgreSQL (the default DATABASE_URL expects localhost:5433)
docker compose up -d postgres redis

# 3. Backend
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/setup_prophet.py          # REQUIRED — fixes Prophet's broken bundled Stan
.venv/bin/uvicorn app.main:app --reload --port 8000

# 4. Load data (one-time, from backend/)
.venv/bin/python -m etl.zip_centroids       # ZIP → lat/lng
.venv/bin/python -m etl.zillow_zip          # ZIP price history (all / single_family / condo)
.venv/bin/python -m etl.zillow_metro        # metro supply + rent panel
.venv/bin/python -m etl.freddie_mac         # mortgage rates
.venv/bin/python -m etl.fred                # CPI, fed funds, unemployment, housing starts, sentiment
.venv/bin/python -m etl.bea                 # state GDP
.venv/bin/python -m etl.geocode_listings    # backfill real listing coordinates (optional)

# 4b. Train the LightGBM endpoint model (one-time; Celery retrains it monthly)
.venv/bin/python -m app.ml.train_lgbm --save-predictions

# 5. Frontend
cd ../frontend
npm install
npm run dev
```

- Frontend (dev): http://localhost:5173
- API + interactive docs: http://localhost:8000/docs

> **Prophet note:** Prophet 1.1.x ships a broken bundled Stan backend. `scripts/setup_prophet.py` installs a real cmdstan and disables the broken one. It is idempotent — **re-run it after any `pip install` that reinstalls Prophet.**

The whole stack also runs via `docker compose up --build`.

---

## Project structure

```
Touse/
├── frontend/
│   └── src/
│       ├── pages/         # Landing, Dashboard, MapView, Forecast, ScenarioDetail, ...
│       ├── components/    # TouseMap, ScenarioForm, ForecastChart, ZipForecastPanel, ...
│       ├── hooks/         # TanStack Query hooks
│       ├── context/       # AuthContext
│       └── utils/         # api.ts (axios + JWT interceptors)
├── backend/
│   ├── app/
│   │   ├── api/           # Route handlers
│   │   ├── models/        # SQLAlchemy ORM models
│   │   ├── services/      # Affordability, readiness, listings, zip_projection, geocoding
│   │   ├── ml/            # train_lgbm.py — global panel model + backtest
│   │   ├── security.py    # JWT minting + auth dependency
│   │   └── main.py
│   ├── etl/               # Data ingestion scripts (Zillow ZIP × type, metro supply, FRED, BEA, ...)
│   ├── scripts/           # setup_prophet.py
│   └── alembic/           # Migrations
├── docker-compose.yml
└── .env.example
```

---

## Operations

### Health checks

- **`GET /health`** — cheap liveness probe (no DB). Use for load balancer health checks.
- **`GET /healthz`** — readiness probe; verifies the DB is reachable and reports the most
  recent `zip_price_history.date` and `mortgage_rate_30y` observation date. Returns
  `status: "degraded"` if either feed has never been ingested.

### Retraining the LightGBM panel

The Celery Beat schedule retrains automatically on the 16th of each month. To trigger manually:

```bash
cd backend && source .venv/bin/activate
DATABASE_URL='postgresql+asyncpg://touse:touse@localhost:5433/touse' \
  python -u -m app.ml.train_lgbm --save-predictions
```

The script builds the full panel (~25 min on a laptop), trains LightGBM (~3 min with current
hyperparams), upserts predictions per `(zip, home_type)` (~10 sec), and records a row in
`model_runs`. Cached Prophet forecasts older than 30 days or stamped with the prior model
version are automatically re-fit on next request.

### Running a backtest

```bash
cd backend && source .venv/bin/activate
python -u -m app.ml.train_lgbm --seeds 42,7,100,2024,1337
```

Output reports MAPE / sMAPE / bias for the home_type=`all` slice (baseline-comparable to
prior single-type models) plus a per-home-type breakdown (apples-to-apples within the same
eval ZIPs).

### Common ops queries

```sql
-- Most recent model run
SELECT model_version, trained_at, panel_rows, train_rows, zips_predicted, train_seconds
FROM model_runs ORDER BY trained_at DESC LIMIT 1;

-- Coverage of typed predictions
SELECT home_type, COUNT(*) FROM zip_lgbm_predictions GROUP BY home_type;

-- Forecast cache health (model version drift)
SELECT model_version, home_type, COUNT(*)
FROM zip_forecast_results GROUP BY model_version, home_type
ORDER BY 1, 2;

-- Stale forecasts that next request will retrain
SELECT zip_code, home_type, trained_at FROM zip_forecast_results
WHERE trained_at < NOW() - INTERVAL '30 days' LIMIT 20;
```

### Invalidating cached forecasts

A new model version invalidates the cache automatically (mismatch on `model_version`).
To force-invalidate without bumping the version (e.g. after a hand-edit to an anchor):

```sql
DELETE FROM zip_forecast_results WHERE home_type = 'condo';  -- or specific zip
```

The next request for that `(zip, home_type)` will re-train Prophet and re-cache.

---

## Notes & limitations

- **Forecasts** are 12-month projections: a global LightGBM panel (lagged prices + US macro + metro supply/rent + election cycle) sets the endpoint, and a per-ZIP × home-type Prophet model shapes the monthly path. Honest confidence ranges, not guarantees. The model can't anticipate rate surprises or policy shocks, so the forecast page offers illustrative rate-scenario overlays.
- **Type-aware:** condo and single-family forecasts are served only for ZIPs where Zillow publishes a separate series; otherwise switch the toggle to "All homes."
- **Listing coordinates** come from the US Census geocoder. Addresses it can't match (≈25%) fall back to the ZIP centroid.
- **Market data freshness** is kept current by a Celery Beat schedule (`backend/tasks/celery_app.py`): Freddie Mac mortgage rates weekly, FRED weekly, Zillow ZIP values + metro supply + LightGBM panel retraining monthly, BEA quarterly. The `celery` and `celery-beat` services are included in `docker compose`; the worker image installs cmdstan at build time so Prophet retraining works in-container.
- **No financial advice.** Touse is a planning tool. Confirm with a licensed lender before any major decision.
