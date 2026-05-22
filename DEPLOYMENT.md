# Deployment Runbook — א"ל השד"ה

## דרישות מוקדמות

| רכיב | גרסה מינימלית |
|------|--------------|
| AWS LightSail instance | 2 vCPU / 4GB RAM (מינימום) |
| Docker | 24+ |
| Docker Compose | v2+ |
| מפתח Gemini API | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) |
| דומיין + DNS | A-record מצביע ל-LightSail IP |

---

## פריסה ראשונה

### 1. הגדרת שרת

```bash
# על שרת LightSail חדש (Ubuntu 22.04 LTS)
sudo apt-get update && sudo apt-get install -y docker.io docker-compose-plugin
sudo usermod -aG docker $USER && newgrp docker
```

### 2. שכפול הריפוזיטורי

```bash
git clone https://github.com/<YOUR_ORG>/alHasade.git ~/alhasade
cd ~/alhasade
```

### 3. הגדרת `.env.prod`

```bash
cp .env.prod.example .env.prod
nano .env.prod   # מלא את כל ה-REPLACE_WITH_... values
```

ערכים נדרשים:
- `DOMAIN` — הדומיין שלך (ללא https://)
- `SECRET_KEY` — `openssl rand -hex 32`
- `GEMINI_API_KEY` — מפתח מ-Google AI Studio
- `AURORA_CONNECTION_STRING` — או החלף ב-Postgres מקומי לסביבה פשוטה
- `GRAFANA_PASSWORD` — סיסמה חזקה

### 4. אתחול SSL (Let's Encrypt)

```bash
chmod +x scripts/init-ssl.sh
./scripts/init-ssl.sh
```

הסקריפט מפעיל Certbot, מבקש תעודה ל-`$DOMAIN`, ומגדיר nginx.

### 5. הפעלת הסטאק

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d
```

סדר עלייה אוטומטי: `db → redis → backend (migrations + warmup) → frontend → nginx`

### 6. בדיקת מיגרציות

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod \
  exec -T backend alembic upgrade head
```

### 7. אימות בריאות

```bash
DOMAIN=yourdomain.com SCHEME=https ./scripts/health-check.sh
```

פלט תקין:
```
✓ Root (200)
✓ Health (200)
✓ Metrics (200)
✓ Generations (no auth → 401)
✓ nginx: healthy
✓ backend: healthy
✓ redis: healthy
```

---

## CI/CD אוטומטי (GitHub Actions)

הפייפליין מוגדר ב-[.github/workflows/deploy.yml](.github/workflows/deploy.yml).

**זרימה:** `push ל-main` → בדיקות backend + frontend → build Docker images → push ל-GHCR → SSH deploy

### Secrets נדרשים ב-GitHub Repository Settings:

| Secret | תיאור |
|--------|-------|
| `LIGHTSAIL_HOST` | ה-IP הציבורי של שרת LightSail |
| `LIGHTSAIL_USER` | שם משתמש SSH (בדרך כלל `ubuntu`) |
| `SSH_PRIVATE_KEY` | מפתח SSH פרטי לחיבור לשרת |
| `DOMAIN` | הדומיין (ללא https://) |
| `SLACK_WEBHOOK_URL` | (אופציונלי) — Slack notifications |

---

## עדכון גרסה (Upgrade)

```bash
# ב-branch main, אחרי שהבדיקות עברו:
git push origin main
# GitHub Actions מטפל בשאר אוטומטית
```

---

## Rollback ידני

במקרה שה-deployment החדש נכשל:

```bash
# 1. SSH לשרת
ssh ubuntu@<LIGHTSAIL_HOST>
cd ~/alhasade

# 2. ראה ת'ג הקודם
cat .rollback-tags

# 3. הורד את הסטאק
docker compose -f docker-compose.prod.yml --env-file .env.prod down

# 4. שחזר Image ישן
docker tag <previous-backend-tag> ghcr.io/<ORG>/alhasade/backend:latest
docker tag <previous-frontend-tag> ghcr.io/<ORG>/alhasade/frontend:latest

# 5. הפעל מחדש
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d

# 6. אמת
DOMAIN=yourdomain.com SCHEME=https ./scripts/health-check.sh
```

**הערה:** מיגרציות DB אינן מתבצעות rollback אוטומטית. במקרה הצורך:
```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod \
  exec -T backend alembic downgrade -1
```

---

## גיבוי ושחזור

```bash
# גיבוי ידני
chmod +x scripts/backup.sh
./scripts/backup.sh      # שומר dump ב-./backups/

# שחזור
./scripts/restore.sh backups/alhasade_20260522.sql
```

מומלץ להגדיר cron יומי:
```bash
crontab -e
# 0 2 * * * /home/ubuntu/alhasade/scripts/backup.sh
```

---

## Monitoring

```bash
# הפעלת סטאק monitoring (מעל prod)
docker compose \
  -f docker-compose.prod.yml \
  -f docker-compose.monitoring.yml \
  --env-file .env.prod up -d
```

| שירות | כתובת | אישורים |
|-------|-------|---------|
| Grafana | `https://<DOMAIN>:3001` | admin / `GRAFANA_PASSWORD` |
| Prometheus | `https://<DOMAIN>:9090` | — |
| AlertManager | `https://<DOMAIN>:9093` | — |

**Dashboards מומלצים לייבא ב-Grafana:**
- FastAPI Observability: ID `16110`
- Redis: ID `11835`

**Alerts מוגדרים** ב-`prometheus_rules.yml`:
- שגיאות > 5% בדקה
- Latency p95 > 2 שניות
- שירות מת > 1 דקה

---

## ניהול SSL בחידוש

Certbot מתחדש אוטומטית דרך cron. לחידוש ידני:

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod \
  run --rm certbot renew
docker compose -f docker-compose.prod.yml --env-file .env.prod \
  exec nginx nginx -s reload
```

---

## משתני סביבה נדרשים (סיכום)

ראה [.env.prod.example](.env.prod.example) לרשימה מלאה עם הסברים.

---

## Troubleshooting

| תסמין | בדיקה | פתרון |
|--------|-------|-------|
| Backend לא עולה | `docker logs alhasade-backend-1` | בדוק `DATABASE_URL`, `GEMINI_API_KEY` |
| מיגרציות נכשלות | `docker compose exec backend alembic current` | ודא ש-Postgres רץ ויש הרשאות |
| SSL נכשל | `docker logs certbot` | ודא DNS מוצביע ו-port 80 פתוח |
| 502 מ-nginx | `docker compose ps` | ודא backend בריא |
| Redis disconnect | `docker logs alhasade-redis-1` | בדוק memory limits |
| Generation timeout | `/health` endpoint + Gemini usage logs | בדוק GEMINI_API_KEY תקף |
