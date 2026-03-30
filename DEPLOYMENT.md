# Al-Hasade — Deployment Runbook

## Table of Contents
1. [Architecture Overview](#1-architecture-overview)
2. [Prerequisites](#2-prerequisites)
3. [VPC Peering — LightSail ↔ Aurora](#3-vpc-peering--lightsail--aurora)
4. [First-Time Deployment](#4-first-time-deployment)
5. [CI/CD — GitHub Actions](#5-cicd--github-actions)
6. [Backups & Disaster Recovery](#6-backups--disaster-recovery)
7. [Monitoring](#7-monitoring)
8. [Routine Operations](#8-routine-operations)
9. [Troubleshooting](#9-troubleshooting)

---

## 1. Architecture Overview

```
Browser
  └─► Nginx (443/80)  ─► React frontend (/:80)
                      └─► FastAPI backend (/api/:8000)
                               ├─► Redis 7 (hot unit cache)
                               └─► Aurora Serverless PostgreSQL
                                       (pgvector + tsvector)
```

| Component | Service | Notes |
|-----------|---------|-------|
| Web server | LightSail instance | 2 GB RAM recommended |
| App server | Docker Compose (prod) | nginx + frontend + backend + redis |
| Database | Aurora Serverless v2 (PostgreSQL 15) | Auto-scales; cold start 10-30s |
| Cache | Redis 7 (Docker) | 256 MB, allkeys-lru eviction |
| LLM | Gemini Flash API | Only called on cache/search miss |
| Embeddings | Gemini text-embedding-004 | 768-dim, stored in pgvector |

---

## 2. Prerequisites

### Server (LightSail)
- Ubuntu 22.04 LTS, ≥ 2 GB RAM
- Docker 24+ and Docker Compose v2
- Ports open: 22 (SSH), 80 (HTTP), 443 (HTTPS)
- Hostname: `yourdomain.com` (A record → server IP)

```bash
# Install Docker on LightSail Ubuntu
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker ubuntu
```

### Database (AWS Aurora Serverless v2)
- Engine: PostgreSQL 15
- Cluster: Serverless v2, min 0.5 ACU, max 4 ACU
- Database: `alhasade`, User: `alhasade`
- Extensions: `pgvector` (install via migration)

### Tools (local dev machine)
```bash
pip install locust       # load testing
pip install awscli       # AWS CLI for Aurora management
```

---

## 3. VPC Peering — LightSail ↔ Aurora

Aurora Serverless runs inside a VPC. LightSail must be peered to reach it.

### Steps
1. **Enable LightSail VPC peering** (AWS Console → LightSail → Account → VPC Peering → Enable)
2. **Note the LightSail VPC CIDR** (shown in the peering dialog)
3. **Update Aurora security group** (AWS Console → VPC → Security Groups):
   - Add Inbound rule: Type=PostgreSQL (5432), Source=LightSail CIDR
4. **Test connectivity** from the LightSail instance:
   ```bash
   psql postgresql://alhasade:PASSWORD@AURORA_ENDPOINT:5432/alhasade -c "SELECT version();"
   ```

### Connection string format
```
postgresql://alhasade:PASSWORD@AURORA_CLUSTER_ENDPOINT:5432/alhasade
```

> **Note on Aurora cold start:** When Aurora scales to 0, the first query takes 10–30 seconds.
> The backend connection pool (min=2, max=10) is set small to tolerate this.
> The `/health` endpoint reports `database: healthy` only after a successful `SELECT 1`.
> Monitor cold-start latency via the `http_request_duration_seconds{endpoint="/health"}` metric.

---

## 4. First-Time Deployment

### 4.1 Set up the server
```bash
ssh ubuntu@YOUR_SERVER_IP

# Create project directory
mkdir ~/alhasade && cd ~/alhasade

# Clone the repository
git clone https://github.com/YOUR_ORG/alhasade.git .
```

### 4.2 Configure environment
```bash
cp .env.prod.example .env.prod
nano .env.prod   # Fill in: AURORA_CONNECTION_STRING, SECRET_KEY, GEMINI_API_KEY, DOMAIN
```

Generate a strong `SECRET_KEY`:
```bash
openssl rand -hex 32
```

### 4.3 Obtain SSL certificate
```bash
chmod +x scripts/*.sh
DOMAIN=yourdomain.com EMAIL=admin@yourdomain.com ./scripts/init-ssl.sh
```

Then update `nginx.conf`: replace every `YOURDOMAIN.COM` with your actual domain.

### 4.4 Run database migrations
```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod \
  run --rm backend alembic upgrade head
```

### 4.5 Start the production stack
```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d

# Verify
./scripts/health-check.sh   # or: DOMAIN=yourdomain.com SCHEME=https ./scripts/health-check.sh
```

### 4.6 Verify
```bash
curl -sf https://yourdomain.com/health
# Expected: {"status":"healthy","components":{"database":"healthy","redis":"healthy",...}}
```

---

## 5. CI/CD — GitHub Actions

### Required secrets (Settings → Secrets → Actions)

| Secret | Value |
|--------|-------|
| `LIGHTSAIL_HOST` | Server IP address |
| `LIGHTSAIL_USER` | `ubuntu` |
| `SSH_PRIVATE_KEY` | Private SSH key (contents of `~/.ssh/id_rsa`) |
| `DOMAIN` | `yourdomain.com` |

### Pipeline stages
1. **test** — runs all pytest suites (auth, cache/search, generations, approval, security)
2. **build** — builds backend + frontend Docker images, pushes to GHCR
3. **deploy** — copies compose files to server, pulls images, runs `up -d`, runs migrations

Only `build` and `deploy` run on `push` to `main`. PRs only run `test`.

### Manual deploy (without CI)
```bash
cd ~/alhasade
docker compose -f docker-compose.prod.yml --env-file .env.prod pull
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --remove-orphans
docker compose -f docker-compose.prod.yml --env-file .env.prod exec backend alembic upgrade head
```

---

## 6. Backups & Disaster Recovery

### Aurora Serverless (production database)
Aurora provides automated backups with a configurable retention window.

**Enable automated backups:**
```
AWS Console → RDS → Your Cluster → Maintenance & Backups
  → Backup retention period: 7 days (minimum recommended)
  → Enable automated backups: Yes
```

**Point-in-time restore (AWS Console):**
```
RDS → Clusters → Actions → Restore to point in time
→ Select timestamp → Create new cluster → Update AURORA_CONNECTION_STRING
```

### Dev/local Postgres backup
```bash
./scripts/backup.sh              # saves to ./backups/TIMESTAMP.sql.gz
./scripts/restore.sh backups/X   # restore (drops and recreates DB)
```

### Redis
Redis data is persisted to a Docker volume (`redis_data`) with RDB snapshots every 60s.
```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod exec redis \
  redis-cli BGSAVE   # force snapshot

# Backup the volume
docker run --rm -v alhasade_redis_data:/data -v $(pwd)/backups:/backup \
  alpine tar czf /backup/redis_$(date +%Y%m%d).tar.gz -C /data .
```

---

## 7. Monitoring

### Start the monitoring stack
```bash
docker compose \
  -f docker-compose.prod.yml \
  -f docker-compose.monitoring.yml \
  --env-file .env.prod up -d
```

### Prometheus — http://server:9090
- Scrapes `/metrics` from backend every 15s
- Scrapes Redis exporter every 30s
- **Key metrics to watch:**
  - `http_request_duration_seconds{endpoint="/health"}` — Aurora wake-up latency
  - `http_requests_total{status_code="500"}` — error rate
  - `http_requests_total{endpoint="/generations/"}` — generation volume

### Grafana — http://server:3001
- Default login: `admin` / `${GRAFANA_PASSWORD}`
- Add Prometheus data source: `http://prometheus:9090`
- **Suggested dashboards:**
  - Redis dashboard (ID: 11835)
  - FastAPI dashboard (custom — track `/metrics` endpoint)

### Aurora cold-start monitoring
Aurora Serverless scales to 0 after idle. Monitor wake-up latency:
```bash
# Check the last 5 /health response times
docker logs alhasade-backend-1 2>&1 | grep health_check | tail -5
```
Alert threshold: if `/health` latency > 30s, Aurora is cold — consider setting min ACU to 0.5.

### pgvector threshold calibration
After 200+ queries, review the similarity score distribution:
```sql
SELECT
  AVG(embedding <=> embedding) AS avg_self_distance,
  PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY ts_rank(fts_vector, fts_vector)) AS p90_bm25_rank
FROM materials
WHERE embedding IS NOT NULL;
```
If most semantic hits are poor quality (teacher rejects), increase `VECTOR_SIMILARITY_THRESHOLD` (e.g., 0.3 → 0.2).

---

## 8. Routine Operations

### SSL certificate renewal
Certbot inside the prod compose renews automatically every 12 hours.
Manual renewal:
```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod \
  exec certbot certbot renew --quiet
docker compose -f docker-compose.prod.yml --env-file .env.prod \
  exec nginx nginx -s reload
```

### File cleanup
Old generated output files are cleaned automatically by the backend (every startup).
Manual trigger:
```python
# In a Python shell inside the container:
from app.services.cleanup import cleanup_old_files
cleanup_old_files()
```

### Cache warming
After a server restart, Redis is empty. Cache warming runs automatically on backend startup.
Manual trigger:
```python
from app.db.session import SessionLocal
from app.services.cleanup import warm_cache
db = SessionLocal(); warm_cache(db); db.close()
```

### View logs
```bash
docker compose -f docker-compose.prod.yml logs -f backend      # JSON structured logs
docker compose -f docker-compose.prod.yml logs -f nginx        # access + error logs
docker compose -f docker-compose.prod.yml logs -f --tail=50    # all services
```

---

## 9. Troubleshooting

### Database connection fails
```bash
# Check Aurora endpoint is reachable
nc -zv AURORA_ENDPOINT 5432
# If timeout → VPC peering is not configured (see §3)
```

### Backend health shows "degraded"
```bash
curl -s https://yourdomain.com/health | python3 -m json.tool
# Check components.database — if "unhealthy" → Aurora may be cold-starting
# Check components.redis — if "unavailable" → Redis container is down
```

### Generation stuck in "processing"
```bash
docker compose -f docker-compose.prod.yml logs backend | grep "ERROR\|error" | tail -20
# Common causes: Gemini API key expired, Aurora cold start timeout
```

### Redis eviction (OOM)
```bash
docker compose -f docker-compose.prod.yml exec redis redis-cli INFO memory
# evicted_keys > 0 is expected (allkeys-lru policy)
# If too high, increase --maxmemory in docker-compose.prod.yml
```

### Load test (performance tuning)
```bash
pip install locust
locust -f locustfile.py --host=https://yourdomain.com \
       --users 50 --spawn-rate 5 --run-time 5m --headless
```
Target: p95 < 500ms for `/generations/` (submit), p95 < 50ms for `/search/`.

---

*Last updated: 2026-03-29 | Sprint 9 — Documentation Sync*
