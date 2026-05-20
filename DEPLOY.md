# Touse — EC2 Deployment Runbook

## Prerequisites

| Tool | Version |
|------|---------|
| AWS CLI | v2 |
| Docker + Compose v2 | latest |
| Git | any |

You'll need an EC2 key pair (.pem file) and the public IP/hostname of your instance.

---

## 1. Provision EC2

1. **Launch instance** — `t3.small` (2 vCPU, 2 GB RAM) running Ubuntu 24.04 LTS.
2. **Security group** — inbound rules:

   | Port | Source | Purpose |
   |------|--------|---------|
   | 22 | Your IP | SSH |
   | 80 | 0.0.0.0/0 | HTTP (Caddy redirects to HTTPS) |
   | 443 | 0.0.0.0/0 | HTTPS |

3. **Elastic IP** — allocate and associate so the address doesn't change on reboot.
4. **DNS** — point `touse.app` (A record) and `www.touse.app` (CNAME) to the Elastic IP.

---

## 2. Bootstrap the server (one-time)

SSH in and run:

```bash
ssh -i ~/.ssh/touse-key.pem ubuntu@<your-ec2-host>

# Install Docker
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker ubuntu
newgrp docker

# Install Git
sudo apt-get install -y git

# Clone repo
sudo mkdir -p /opt/touse
sudo chown ubuntu:ubuntu /opt/touse
git clone https://github.com/rahul-sg/touse.git /opt/touse
cd /opt/touse

# Create .env from example
cp .env.example .env
nano .env   # fill in all values — especially DB_PASSWORD and API keys
```

---

## 3. First deploy

```bash
cd /opt/touse

# Copy production Caddyfile
cp Caddyfile.prod Caddyfile

# Build and start all services
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# Run DB migrations
docker compose -f docker-compose.yml -f docker-compose.prod.yml run --rm backend \
    python -m alembic upgrade head

# Seed initial data (one-time)
docker compose -f docker-compose.yml -f docker-compose.prod.yml run --rm backend \
    python -m etl.zillow

docker compose -f docker-compose.yml -f docker-compose.prod.yml run --rm backend \
    python -m etl.fred

docker compose -f docker-compose.yml -f docker-compose.prod.yml run --rm backend \
    python -m etl.bea

docker compose -f docker-compose.yml -f docker-compose.prod.yml run --rm backend \
    python -m etl.policy

# Train initial models
docker compose -f docker-compose.yml -f docker-compose.prod.yml run --rm backend \
    python -m app.ml.train_prophet

docker compose -f docker-compose.yml -f docker-compose.prod.yml run --rm backend \
    python -m app.ml.train_lightgbm
```

Wait ~60 seconds for Caddy to obtain TLS certificates, then visit `https://touse.app`.

---

## 4. Subsequent deploys

From your **local machine**:

```bash
./deploy.sh <ec2-host> ~/.ssh/touse-key.pem
```

The script will:
1. `git pull` on the server
2. Rebuild Docker images
3. Run any new Alembic migrations
4. Restart services with zero-downtime replacement
5. Prune old images
6. Run a health check

---

## 5. Useful commands (run on EC2)

```bash
# View live logs
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f backend

# Check Celery worker status
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f celery

# Trigger ETL manually
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec celery \
    celery -A tasks.celery_app call tasks.etl_tasks.run_zillow_etl

# Trigger model retrain manually
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec celery \
    celery -A tasks.celery_app call tasks.ml_tasks.retrain_lightgbm

# Open a DB shell
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec postgres \
    psql -U touse touse

# Check service health
curl https://touse.app/health
```

---

## 6. Scheduled tasks (Celery Beat)

| Task | Schedule | What it does |
|------|----------|--------------|
| Zillow ETL | 15th of month, 03:00 UTC | Fetches new median price data |
| FRED ETL | Every Monday, 02:00 UTC | Updates mortgage rate, CPI, etc. |
| BLS ETL | 5th of month, 02:30 UTC | Updates unemployment by metro |
| BEA ETL | 1st of Jan/Apr/Jul/Oct, 04:00 UTC | State GDP growth |
| Policy ETL | Jan 1st, 05:00 UTC | Annual policy flags update |
| Prophet retrain | 16th of month, 04:00 UTC | Retrains per-metro time series models |
| LightGBM retrain | 17th of month, 04:00 UTC | Retrains global macro+policy model |

---

## 7. Disk / memory notes

- `t3.small` (2 GB RAM) is the minimum. LightGBM training peaks at ~800 MB.
- PostgreSQL + Redis together use ~300-400 MB at rest.
- Add a 20 GB EBS volume (gp3) for the OS + Docker images + Postgres data.
- Run `docker system prune -f` monthly to reclaim image layers.

---

## 8. Updating API keys

```bash
# SSH into EC2
nano /opt/touse/.env   # edit the key

# Restart only the affected services
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d backend celery
```

---

## 9. Rollback

```bash
# SSH into EC2
cd /opt/touse
git log --oneline -10          # find the last good commit hash
git checkout <commit-hash>
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```
