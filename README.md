# Touse

A USA housing market tool that shows you what you can afford, where you can afford it, and where the market is heading.

**Features:**
- Affordability calculator (income, debt, credit score, down payment)
- Interactive map with listings filtered to your budget
- Market trend indicators per metro (3m / 12m price change)
- ML-driven 12-month price forecast with confidence intervals
- Economic + political signal integration (mortgage rates, CPI, unemployment, zoning reform, buyer credits)

## Stack

| Layer | Tech |
|-------|------|
| Frontend | React 18 + Vite + TypeScript |
| Routing | React Router v6 |
| Data fetching | TanStack Query v5 |
| Charts | Recharts |
| Map | Mapbox GL JS + react-map-gl |
| Backend | FastAPI + Python 3.11 |
| Database | PostgreSQL 16 |
| Cache / Queue | Redis 7 + Celery |
| ML | Prophet → LightGBM |
| Reverse proxy | Caddy |
| Deployment | Docker Compose + AWS EC2 |

## Data Sources

- [Zillow Research](https://www.zillow.com/research/data/) — historical median prices
- [FRED](https://fred.stlouisfed.org/) — mortgage rates, CPI, housing starts
- [BLS](https://www.bls.gov/developers/) — metro unemployment
- [BEA](https://apps.bea.gov/API/) — state GDP
- [Census ACS](https://www.census.gov/data/developers/) — income + population by ZIP
- [HUD](https://www.huduser.gov/portal/datasets/) — fair market rents + policy
- [MIT Election Lab](https://electionlab.mit.edu/) — ballot results
- [Congress.gov API](https://api.congress.gov/) — federal housing legislation

## Getting Started

```bash
cp .env.example .env
# Fill in API keys in .env

docker compose up --build
```

Frontend: http://localhost:3000  
API docs: http://localhost:8000/docs

## Project Structure

```
Touse/
├── frontend/       # React + Vite
├── backend/        # FastAPI + ETL pipelines + ML
├── docker-compose.yml
├── Caddyfile
└── .env.example
```
