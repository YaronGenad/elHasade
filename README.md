# א"ל השד"ה — מחולל יחידות לימוד אוטומטי

מחולל מבוסס AI שיוצר **חומרי הוראה מוכנים להדפסה** בשיטת א"ל השד"ה —
שיטת למידה פעילה בתחנות המיושמת בבתי ספר בישראל.

קלט: נושא + מקצוע + כיתה → פלט: PDF מלא לכל תחנה, לכל סבב, כולל מדריך למורה.

---

## ארכיטקטורה

```
Browser
  └─► React Frontend (port 3000)
        └─► FastAPI Backend (port 8000)
              ├─► Redis 7      — hot unit cache
              └─► PostgreSQL 15 (pgvector + tsvector)
                    └─► Gemini Flash — generation on cache/search miss
```

| שכבה | טכנולוגיה |
|------|-----------|
| Frontend | React 18 + TypeScript + Vite + MUI v5 (RTL) |
| Backend | FastAPI + SQLAlchemy 2.0 + Alembic |
| DB | PostgreSQL 15 + pgvector (embeddings) + tsvector (BM25) |
| Cache | Redis 7 — מפתחות `unit:{s}:{t}:{g}`, `hot:units:top50` |
| LLM | Gemini Flash (generation) + text-embedding-004 (semantic search) |
| Auth | JWT — access token 30min, refresh token 7d |

---

## הרצה מהירה עם Docker

### דרישות מוקדמות
- Docker 24+ ו-Docker Compose v2
- מפתח Gemini API

### 1. הגדרת סביבה

```bash
cp .env.example .env
# ערוך .env — מלא את GEMINI_API_KEY ואת SECRET_KEY
# לייצר SECRET_KEY: openssl rand -hex 32
```

### 2. הפעלה

```bash
docker compose up -d
```

הסטאק עולה בסדר: db → redis → backend (migrations + warmup) → frontend.

| שירות | כתובת |
|-------|-------|
| ממשק ווב | http://localhost:3000 |
| API | http://localhost:8000 |
| Swagger | http://localhost:8000/docs |
| Health | http://localhost:8000/health |

### 3. הרשמה ראשונה

פתח http://localhost:3000, לחץ "הרשמה", צור משתמש ותתחיל ליצור יחידות לימוד.

### עצירה

```bash
docker compose down          # עצור (שמור נתונים)
docker compose down -v       # עצור + מחק volumes
```

---

## הרצה ללא Docker (פיתוח)

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# הפעל Postgres ו-Redis מקומית, ואז:
cp .env.example .env   # ערוך DATABASE_URL, REDIS_URL, GEMINI_API_KEY
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev   # http://localhost:3000
```

---

## בדיקות

```bash
cd backend

# כל הבדיקות (SQLite + fakeredis — לא דורש Postgres/Redis חיצוני)
pytest -v

# סויטות ספציפיות
pytest test_auth_complete.py -v         # auth + JWT
pytest test_generations_complete.py -v  # pipeline ייצור
pytest test_cache_search.py -v          # cache + search
pytest test_approval_loop.py -v         # approve/reject/versions
pytest test_security.py -v              # OWASP A01/A03/A04/A07/A08
```

---

## מבנה הקוד

```
alHasade/
├── backend/
│   ├── app/
│   │   ├── api/          — endpoints: auth, generations, search, materials
│   │   ├── core/         — config, logging, security, exceptions
│   │   ├── db/           — session, base
│   │   ├── middleware/   — auth, request_id, request logging
│   │   ├── models/       — SQLAlchemy: User, Query, Material, Audit
│   │   ├── schemas/      — Pydantic schemas
│   │   ├── services/     — cache, search, embeddings, generation, audit, cleanup
│   │   └── main.py       — FastAPI app, /health, /metrics
│   ├── alembic/          — migrations (כולל pgvector extension + tsvector trigger)
│   ├── test_*.py         — 5 קבצי בדיקות
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── pages/        — Login, Register, Dashboard, NewGeneration, GenerationDetail
│       ├── components/   — ErrorBoundary
│       ├── hooks/        — useNotification
│       ├── api/          — API clients (auth, generations, search, materials)
│       ├── contexts/     — AuthContext
│       └── types/        — TypeScript types
├── scripts/              — init-ssl.sh, backup.sh, restore.sh, health-check.sh
├── .github/workflows/    — deploy.yml (test → build GHCR → SSH deploy LightSail)
├── docker-compose.yml          — dev stack (Postgres + Redis + backend + frontend)
├── docker-compose.prod.yml     — production (nginx + certbot + Aurora)
├── docker-compose.monitoring.yml — Prometheus + Grafana + redis-exporter
├── nginx.conf            — SSL termination, rate limiting, reverse proxy
├── prometheus.yml        — scrape config
├── prometheus_rules.yml  — alert rules (error rate, latency, service down)
├── alertmanager.yml      — alert routing (webhook/email)
├── locustfile.py         — load test: 50 מורים במקביל
└── DEPLOYMENT.md         — runbook מלא לפרודקשן (AWS LightSail + Aurora)
```

---

## זרימת הייצור

```
POST /generations/  (subject + topic + grade)
        │
        ▼
  Redis unit cache  ──hit──► return cached PDF
        │ miss
        ▼
  BM25 (tsvector / plainto_tsquery)  ──found──► return existing material
        │ miss
        ▼
  pgvector cosine similarity  ──found──► return similar material
        │ miss
        ▼
  Gemini Flash generate  ──► save Material + embedding ──► return new PDF
```

לאחר קבלת התוצאה המורה יכול לאשר (`/approve`) או לדחות (`/reject`) — `approval_count` ו-`times_served` מתעדכנים בהתאם ומשפיעים על דירוג תוצאות עתידיות.

---

## פרודקשן

לפריסה על AWS LightSail + Aurora Serverless v2 — ראה [DEPLOYMENT.md](DEPLOYMENT.md).

CI/CD אוטומטי דרך GitHub Actions: push ל-`main` → בדיקות → build GHCR → SSH deploy.

---

## Monitoring

```bash
# הפעלת סטאק monitoring (מעל docker-compose.prod.yml)
docker compose -f docker-compose.prod.yml -f docker-compose.monitoring.yml --env-file .env.prod up -d
```

| שירות | כתובת | תפקיד |
|-------|-------|-------|
| Prometheus | http://server:9090 | metrics scraping (backend + Redis) |
| Grafana | http://server:3001 | dashboards |
| AlertManager | http://server:9093 | alert routing (webhook/email) |

מדדים מרכזיים: `http_requests_total`, `http_request_duration_seconds`, Redis memory/eviction.

---

## שיטת א"ל השד"ה

ארבע תחנות עצמאיות — תלמיד יכול להתחיל בכל אחת:

| תחנה | תוכן |
|------|------|
| **הבנה** | טקסט עשיר לקריאה + שאלות דיון |
| **שיטות** | כתיבה מובנית ומדורגת לפי סוג הטקסט |
| **דיוק** | לשון ודקדוק: שורשים, בניינים, הכתבה |
| **אוצר מילים** | חוויה ופעולה — מודפסת או פיזית |
