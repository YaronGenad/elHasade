# ארכיטקטורה טכנית — פלטפורמת א"ל השד"ה

## סקירה כללית

```
[Web UI]
    │
    ▼
[API Gateway - FastAPI]
    │
    ├──► [Cache Layer] ──► hit → return PDF URL
    │         │
    │         └──► miss → [Job Queue - Redis/SQS]
    │                              │
    │                              ▼
    │                      [Worker Service]
    │                              │
    │                      [Gemini Flash API]
    │                              │
    │                      [PDF Generator - Playwright]
    │                              │
    │                      [Object Storage - S3]
    │                              │
    └──────────────────────────────┘
                                   │
                            [Cache Update]
```

## רכיבים

### 1. API Gateway (FastAPI)
**endpoints:**
```
POST /api/generate
  body: { subject, topic, grade, rounds }
  returns: { job_id, status: "queued"|"cached" }

GET /api/job/{job_id}
  returns: { status, pdf_url, variants_count }

POST /api/feedback
  body: { job_id, action: "save"|"regenerate" }

GET /api/cache/stats (admin)
  returns: hit_rate, total_variants, miss_log
```

### 2. Cache Layer

**Storage:** PostgreSQL או DynamoDB
```sql
table: units
  key          TEXT PRIMARY KEY  -- hash(subject+topic+grade)
  subject      TEXT
  topic        TEXT
  grade        TEXT
  created_at   TIMESTAMP

table: variants
  id           UUID PRIMARY KEY
  unit_key     TEXT FK → units.key
  version      INT
  s3_path_html TEXT  -- path to HTML files
  s3_path_pdf  TEXT  -- path to student PDF
  s3_path_pdf_teacher TEXT
  saves        INT DEFAULT 0
  regenerates  INT DEFAULT 0
  score        FLOAT GENERATED (saves / (saves + regenerates + 1))
  created_at   TIMESTAMP

table: miss_log
  id           UUID
  subject      TEXT
  topic        TEXT
  grade        TEXT
  requested_at TIMESTAMP
  source       TEXT  -- 'user_request' | 'batch_check'
```

**BM25 index:** Elasticsearch או pg_trgm על subject+topic+grade

**Cache key normalization:**
```python
def normalize_key(subject, topic, grade):
    # "ח'" = "כיתה ח" = "ח" → "8"
    # "ירמיה" = "ירמיהו"
    # strip whitespace, sort tokens
    return hash(f"{subject}_{normalize_topic(topic)}_{normalize_grade(grade)}")
```

### 3. Job Queue

**Redis + Celery** או **AWS SQS + Lambda**

Job payload:
```json
{
  "job_id": "uuid",
  "unit_key": "hash",
  "subject": "תנך",
  "topic": "ירמיה א",
  "grade": "ח",
  "rounds": 4,
  "priority": "user_request|batch",
  "existing_variants": 2
}
```

Temperature strategy (בworker):
- variant 1: temperature=0.2 (עקבי)
- variant 2: temperature=0.5
- variant 3+: temperature=0.7 (מגוון)

### 4. Worker Service

בעצם `pipeline.py` הקיים + wrapper:
```python
class GenerationWorker:
    def process(self, job):
        # 1. generate all HTML via Gemini Flash
        result = generate_all_rounds(job.input, OUTPUT_DIR)
        # 2. create PDF via Playwright
        pdf_paths = create_pdfs(result)
        # 3. upload to S3
        s3_paths = upload_to_s3(pdf_paths)
        # 4. update cache
        save_variant(job.unit_key, s3_paths)
        # 5. notify job complete
        update_job_status(job.job_id, "complete", s3_paths)
```

### 5. Object Storage (S3)
```
s3://alhashade-units/
  {unit_key}/
    v1/
      student.pdf
      teacher.pdf
      round1_comprehension.html
      ...
    v2/
      ...
```

### 6. Batch Scheduler (חודשי)

```python
def monthly_batch():
    # 1. fetch MOE curriculum for next month
    topics = fetch_moe_curriculum(next_month)

    # 2. add missed topics from last month
    missed = get_miss_log(last_month)
    topics += missed

    # 3. filter already-cached
    to_generate = [t for t in topics if not cache_exists(t)]

    # 4. queue all
    for topic in to_generate:
        queue_job(topic, priority="batch")

    # 5. drift report
    hit_rate = calculate_hit_rate(last_month)
    send_drift_report(hit_rate, missed)
```

### 7. Web UI

**Stack:** React + TypeScript (או Next.js)

**מסכים:**
1. **Generate** — form: מקצוע / נושא / כיתה / מספר סבבים → submit
2. **Status** — polling על job_id → progress bar → download buttons
3. **Result** — preview + "צור גרסה אחרת" button + שמור
4. **History** — כל היחידות של המורה

## Stack המלצה

| רכיב | בחירה | סיבה |
|------|-------|-------|
| Backend | FastAPI (Python) | אותה שפה כמו ה-pipeline הקיים |
| Queue | Redis + Celery | פשוט, self-hosted או Redis Cloud |
| DB | PostgreSQL (Supabase) | managed, פשוט, SQL |
| Storage | S3 / Cloudflare R2 | R2 זול יותר לבandwidth |
| Frontend | Next.js | SSR לטעינה מהירה |
| Hosting | Railway / Render | פשוט יותר מ-AWS לשלב הראשון |
| Worker | Same server או Celery worker נפרד | תלוי בעומס |

## סביבות
- **dev:** local, SQLite, local Redis, Gemini API
- **staging:** Railway, PostgreSQL, Redis Cloud, real Gemini
- **prod:** same as staging + monitoring

## משתני סביבה נדרשים
```
GEMINI_API_KEY=
DATABASE_URL=
REDIS_URL=
S3_BUCKET=
S3_ACCESS_KEY=
S3_SECRET_KEY=
JWT_SECRET=
```
