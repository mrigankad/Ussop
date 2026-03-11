# Deployment Guide

## Quick Start (Development)

```bash
# 1. Install dependencies
pip install -e ".[dev]"

# 2. Download ML models
python scripts/download_models.py

# 3. Start the server
python ussop/run.py
# → Open http://localhost:8080  (login: admin / admin)
```

---

## Production Deployment (Docker Compose)

### Prerequisites
- Docker ≥ 24 + Docker Compose v2
- TLS certificates (see [TLS Setup](#tls-setup))
- At least 4 GB RAM, 20 GB disk

### 1. Clone & configure

```bash
git clone https://github.com/ussop/ussop.git
cd ussop

cp .env.example .env
# Edit .env — at minimum set:
#   SECRET_KEY=<long random string>
#   POSTGRES_PASSWORD=<strong password>
```

### 2. Place ML models

```bash
mkdir -p docker/models
# Copy resnet18_image_encoder.onnx and mobile_sam_mask_decoder.onnx
# OR run the downloader from inside the container:
docker compose run --rm api python scripts/download_models.py
```

### 3. TLS Setup

Place your certificates in `docker/nginx/certs/`:
```
docker/nginx/certs/fullchain.pem
docker/nginx/certs/privkey.pem
```

**Self-signed (dev/staging):**
```bash
mkdir -p docker/nginx/certs
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout docker/nginx/certs/privkey.pem \
  -out docker/nginx/certs/fullchain.pem \
  -subj "/CN=ussop.local"
```

**Let's Encrypt (production):**
```bash
certbot certonly --standalone -d your-domain.com
cp /etc/letsencrypt/live/your-domain.com/fullchain.pem docker/nginx/certs/
cp /etc/letsencrypt/live/your-domain.com/privkey.pem  docker/nginx/certs/
```

### 4. Start the stack

```bash
docker compose -f docker/docker-compose.yml up -d

# Watch logs
docker compose -f docker/docker-compose.yml logs -f api
```

Services started:
| Service    | Internal port | External (if exposed) |
|------------|--------------|------------------------|
| api        | 8080         | via nginx              |
| worker     | —            | —                      |
| postgres   | 5432         | not exposed            |
| redis      | 6379         | not exposed            |
| nginx      | 80 / 443     | 80, 443                |
| prometheus | 9090         | 9090                   |
| grafana    | 3000         | 3001                   |

### 5. First login

Navigate to `https://your-domain.com`
Default credentials: **admin / admin** — **change immediately in Settings → Account**

---

## Database Migrations

Migrations run automatically at API startup via Alembic.

Manual commands:
```bash
# Apply all pending migrations
python scripts/migrate.py

# Show current revision
python scripts/migrate.py current

# Show full history
python scripts/migrate.py history

# Roll back one step
python scripts/migrate.py downgrade
```

To generate a new migration after changing a model:
```bash
python -m alembic revision --autogenerate -m "describe_change"
```

---

## Switching to PostgreSQL

Update `.env`:
```env
DATABASE_URL=postgresql+psycopg2://ussop:yourpassword@localhost:5432/ussop
```

Create the database:
```bash
psql -U postgres -c "CREATE USER ussop WITH PASSWORD 'yourpassword';"
psql -U postgres -c "CREATE DATABASE ussop OWNER ussop;"
```

Apply migrations:
```bash
python scripts/migrate.py
```

---

## Enabling Redis Cache

Update `.env`:
```env
REDIS_URL=redis://localhost:6379/0
```

The API will automatically use Redis for caching `/statistics` (30s TTL) and `/trends` (60s TTL). Without Redis it falls back to an in-process LRU cache — no functionality is lost, only persistence across restarts.

---

## Scaling

**Multiple API workers** (single machine):
```env
API_WORKERS=4
```

**Multi-node** requires:
- PostgreSQL (not SQLite) — shared state
- Redis — shared cache + WebSocket pub/sub
- Shared volume or object storage for `data/images/`

---

## Monitoring

**Prometheus** scrapes `/metrics` every 15 s.
**Grafana** is pre-configured with the Prometheus datasource at `http://localhost:3001` (admin / `$GRAFANA_PASSWORD`).

Key metrics exposed:
- `ussop_inspections_total` — counter by decision
- `ussop_inspection_ms` — histogram of cycle times
- Standard uvicorn / FastAPI metrics

---

## Updating

```bash
git pull
docker compose -f docker/docker-compose.yml build api worker
docker compose -f docker/docker-compose.yml up -d
# Migrations are applied automatically on restart
```
