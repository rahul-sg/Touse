#!/usr/bin/env bash
# seed.sh — load all ETL data and train models for local testing
# Run from the project root: ./seed.sh
#
# Expects .env to exist with real API keys filled in.
# Postgres + Redis must be running (docker compose up -d postgres redis)

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$SCRIPT_DIR/backend"
PYTHON="$BACKEND/.venv/bin/python"

# Load .env into shell
set -a
source "$SCRIPT_DIR/.env"
set +a

# Use psycopg2 URL for sync ETL scripts
export DATABASE_URL="${DATABASE_URL/postgresql+asyncpg/postgresql+psycopg2}"

check_key() {
    local name="$1" val="$2"
    if [[ -z "$val" || "$val" == PASTE* ]]; then
        echo "  [skip] $name not set"
        return 1
    fi
    return 0
}

echo ""
echo "══════════════════════════════════════════"
echo "  Touse data seed"
echo "══════════════════════════════════════════"

# ── 1. Zillow (no key needed) ─────────────────────────────────
echo ""
echo "▶ [1/6] Zillow price history (free CSV, no key needed)…"
(cd "$BACKEND" && $PYTHON -m etl.zillow)
echo "  ✓ Zillow done"

# ── 2. FRED ───────────────────────────────────────────────────
echo ""
echo "▶ [2/6] FRED macro indicators (rates, CPI, housing starts)…"
if check_key "FRED_API_KEY" "${FRED_API_KEY:-}"; then
    (cd "$BACKEND" && $PYTHON -m etl.fred)
    echo "  ✓ FRED done"
fi

# ── 3. BEA ────────────────────────────────────────────────────
echo ""
echo "▶ [3/6] BEA state GDP growth…"
if check_key "BEA_API_KEY" "${BEA_API_KEY:-}"; then
    (cd "$BACKEND" && $PYTHON -m etl.bea)
    echo "  ✓ BEA done"
fi

# ── 4. Policy flags (no key — seeded from hardcoded data) ─────
echo ""
echo "▶ [4/6] Policy flags (zoning reform, buyer credit, bonds)…"
(cd "$BACKEND" && $PYTHON -m etl.policy)
echo "  ✓ Policy done"

# ── 5. Prophet model training ─────────────────────────────────
echo ""
echo "▶ [5/6] Training Prophet forecast models (per-metro)…"
echo "  This takes 2–5 min depending on how many metros loaded."
(cd "$BACKEND" && $PYTHON -m app.ml.train_prophet)
echo "  ✓ Prophet done"

# ── 6. LightGBM model training ────────────────────────────────
echo ""
echo "▶ [6/6] Training LightGBM global model (macro + policy)…"
echo "  This takes 1–3 min."
(cd "$BACKEND" && $PYTHON -m app.ml.train_lightgbm)
echo "  ✓ LightGBM done"

echo ""
echo "══════════════════════════════════════════"
echo "  Seed complete. Visit http://localhost:3000"
echo "══════════════════════════════════════════"
echo ""
