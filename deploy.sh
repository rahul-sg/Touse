#!/usr/bin/env bash
# deploy.sh — deploy Touse to EC2
# Usage: ./deploy.sh [EC2_HOST] [SSH_KEY_PATH]
# Example: ./deploy.sh ec2-1-2-3-4.compute-1.amazonaws.com ~/.ssh/touse-key.pem

set -euo pipefail

HOST="${1:-}"
KEY="${2:-~/.ssh/touse-key.pem}"
REMOTE_DIR="/opt/touse"

if [[ -z "$HOST" ]]; then
    echo "Usage: $0 <ec2-host> [ssh-key-path]"
    exit 1
fi

SSH="ssh -i $KEY -o StrictHostKeyChecking=no ubuntu@$HOST"
SCP="scp -i $KEY -o StrictHostKeyChecking=no"

echo "==> Deploying Touse to $HOST"

# 1. Push production Caddyfile into place
$SSH "sudo mkdir -p $REMOTE_DIR"
$SCP Caddyfile.prod ubuntu@$HOST:/tmp/Caddyfile

$SSH "bash -s" <<'REMOTE'
set -euo pipefail
cd /opt/touse

echo "--- Pulling latest code ---"
git pull origin master

echo "--- Copying production Caddyfile ---"
cp /tmp/Caddyfile /opt/touse/Caddyfile

echo "--- Building images ---"
docker compose -f docker-compose.yml -f docker-compose.prod.yml build --pull

echo "--- Running DB migrations ---"
docker compose -f docker-compose.yml -f docker-compose.prod.yml run --rm backend \
    python -m alembic upgrade head

echo "--- Restarting services ---"
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --remove-orphans

echo "--- Pruning old images ---"
docker image prune -f

echo "--- Health check ---"
sleep 5
curl -fsS http://localhost/health | python3 -c "import sys,json; d=json.load(sys.stdin); print('Health:', d)"

echo "==> Deploy complete"
REMOTE
