# א"ל השד"ה — סיכום פרויקט ומצב נוכחי

> עודכן לאחרונה: 2026-07-09  
> ריפוזיטורי: https://github.com/YaronGenad/elHasade  
> ענף עיקרי: `master` (לא `main`)

---

## מה הפרויקט הזה

פלטפורמת SaaS לאוטומציה של שיטת **א"ל השד"ה (PACE)** — שיטה פדגוגית ישראלית ליצירת יחידות לימוד מובנות.  
המורה מכניס: מקצוע + נושא + כיתה + מספר מחזורים ← המערכת מפיקה: PDF מודפס עם מפת דרכים, הבנת הנקרא, שאלות, ולוח מילים.

**מה כבר עובד:** FastAPI backend, React frontend, Postgres + Redis, Gemini API, יצירת PDF עם תמונות מ-Pexels, pipeline עברית + STEAM.  
**מה עוד לא:** cache layer, BM25 fuzzy search, batch scheduler, production deployment.

---

## ארכיטקטורה

```
frontend (React/Vite) :3000
        ↓ REST API
backend (FastAPI)      :8000
  ├── src/pipeline.py      — אורקסטרטור ראשי
  ├── src/gemini.py        — קריאות ל-Gemini עם failover בין מפתחות
  ├── src/config.py        — פרמטרי כיתה, curriculum KB
  ├── src/prompts/
  │   ├── hebrew.py        — פרומפטים לעברית
  │   ├── steam.py         — פרומפטים ל-STEAM (מתמטיקה/מדעים/אנגלית/אמנות)
  │   └── english.py       — פרומפטים לאנגלית
  ├── src/renderers/       — HTML→PDF renderers לכל חלק
  ├── src/images.py        — חיפוש תמונות ב-Pexels
  └── src/pdf.py           — Playwright → PDF
Postgres (pgvector)    :5432  — users, queries, materials, audit_log
Redis                  :6379  — task queue + cache (עתידי)
```

---

## הרצה מקומית (Development)

### עלייה ראשונה / אחרי `git pull`

```powershell
cd "c:\Users\yaron\OneDrive - Newcinema\newFixTemp\alHasade"

# Build + start all services
docker compose up -d --build

# Wait ~30 seconds, then verify
docker compose ps
docker logs alhasade-backend-1 --tail 20
```

### הפעלה רגילה (כבר built)

```powershell
docker compose up -d
```

### כיבוי

```powershell
docker compose down
# שמור volumes (DB + Redis data):  docker compose down
# מחק הכל כולל data:               docker compose down -v
```

### בדיקת בריאות

```powershell
docker compose ps
# צפוי: כל 4 שירותים Status = Up (healthy)

# בדיקה ידנית:
Invoke-RestMethod http://localhost:8000/health
# צפוי: {"status":"healthy"}

# frontend:
Start-Process "http://localhost:3000"
```

### לוגים שימושיים

```powershell
docker logs alhasade-backend-1 --tail 50 --follow
docker logs alhasade-frontend-1 --tail 20
docker logs alhasade-db-1 --tail 10
```

### Restart שירות בודד (אחרי שינוי קוד)

```powershell
# אחרי שינוי ב-src/ — Docker מריץ את הקוד ישירות כ-volume mount:
docker restart alhasade-backend-1

# אחרי שינוי ב-frontend/:
docker compose up -d --build frontend
```

---

## קבצי סביבה

```
alHasade/.env                 ← משמש ב-docker compose (dev)
alHasade/backend/.env         ← משמש ב-tests ישירים
alHasade/.env.prod.example    ← template לייצור
```

משתני סביבה קריטיים:
```env
GEMINI_API_KEY=...            # מפתח ראשי
GEMINI_API_KEY_2=...          # failover 1
GEMINI_API_KEY_BECKUP=...     # failover 2
GEMINI_API_KEY_BECKUP2=...    # failover 3
GEMINI_API_KEY_BECKUP3=...    # failover 4
PEXEL_API_KEY=...             # לתמונות
SECRET_KEY=...                # JWT signing
```

---

## מה עשינו — סדר כרונולוגי

### שלב 1: POC
- Python script פשוט: `main.py` + `config.json`
- Gemini API לעברית, PDF דרך Playwright
- תיקון: URL encoding ב-Hebrew PDF, page breaks, HTML concatenation

### שלב 2: FastAPI Platform (commit `2c62a35`)
- FastAPI backend עם auth (JWT), Postgres, Redis, Alembic migrations
- React/Vite frontend עם RTL support
- Docker Compose stack (dev + prod)
- DEPLOYMENT.md + ARCHITECTURE.md

### שלב 3: Infrastructure Fixes (commits `e9753d7`, `652a0e8`, `a5314ae`, `053af81`)
- תיקון: bcrypt==4.0.1 (passlib incompatibility)
- תיקון: Docker frontend build failures
- תיקון: parallel thread deadlock ב-pipeline
- תיקון: Pexels Cloudflare block → rotate User-Agent
- תיקון: כפילות תמונות — מעקב per-session
- תיקון: ThinkingConfig version mismatch ב-Gemini SDK

### שלב 4: STEAM + Diversity (commit `6dd0b83`)
- **STEAM pipeline**: pipeline נפרד למתמטיקה, מדעים, אנגלית, אמנות
  - `src/prompts/steam.py` — פרומפטים מותאמים לSTEAM
  - `src/pipeline.py` מנתב ל-STEAM vs עברית לפי נושא
- **Crossword renderer**: תשחץ אוטומטי בפלט
- **Word-search renderer**: חיפוש מילים בפלט
- **Content diversity**: וריאציות מרובות למניעת תוצאות זהות

### שלב 5: Curriculum Knowledge Base (commit `bb323ba`) — הכי אחרון
- **הבעיה שנפתרה**: ה-LLM לא ידע מה מלמדים בכל כיתה — יצר תוכן שלא מתאים לתכנית הלימודים
- **הפתרון**:
  - `curriculum_kb.json` — מסד ידע של 6 טווחי כיתות × 5 תחומים (עברית/מתמטיקה/מדע/היסטוריה/אנגלית)
  - כיתות ז-ח: מועשר מתוכניות לימודים רשמיות (אלגברה 68ש', גיאומטריה 52ש', מדע כיתה ז')
  - `src/config.py` — `get_curriculum_profile(grade, subject)` + `_subject_to_domain()`
  - `src/prompts/hebrew.py` — `_curriculum_block()` מוזרק לכל פרומפט
  - `src/prompts/steam.py` — `_steam_curriculum_block()` מוזרק לכל פרומפט
  - תוקן: אורך טקסט ז-ח היה נמוך מה-ו (תוקן ל-800-1000 מילים)
  - תוקן: יא-יב — רשימות אפשרויות היו 2 פריטים בלבד (הורחב ל-4+)
  - `scripts/build_curriculum_kb.py` — סקריפט חד-פעמי לעיבוד PDF/DOCX ← Gemini JSON

---

## מבנה ה-curriculum_kb.json

```json
{
  "א-ב": { "hebrew": {...}, "math": {...} },
  "ג-ד": { "hebrew": {...}, "math": {...}, "science": {...} },
  "ה-ו": { "hebrew": {...}, "math": {...}, "science": {...}, "history": {...} },
  "ז-ח": { "hebrew": {...}, "math": {...}, "science": {...}, "history": {...}, "english": {...} },
  "ט-י": { ... },
  "יא-יב": { ... }
}
```

כל entry מכיל:
- `key_concepts` — מושגים עיקריים לטווח הכיתה
- `vocabulary_profile` — פרופיל אוצר מילים
- `expected_prior_knowledge` — מה הילד כבר יודע
- `typical_authentic_topics` — נושאים מהתכנית הרשמית
- `text_complexity` — רמת מורכבות לשונית
- `avoid_in_content` — מה אסור לכלול

---

## מה נשאר לעשות

### עדיפות גבוהה

1. **`src/prompts/english.py` — curriculum injection חסר**
   - `_curriculum_block()` כבר ב-hebrew.py ו-steam.py אבל לא ב-english.py
   - צריך להוסיף `get_curriculum_profile` ו-`<curriculum_context>` block לכל prompt builder

2. **`reading_mode` לא מוזרק לפרומפטים**
   - `gl['reading_mode']` קיים ב-config אבל לא מועבר להוראות פרומפט ההבנה
   - צריך להוסיף בפרומפטי comprehension ב-hebrew.py ו-steam.py

3. **enrichment כיתות א-ו**
   - ה-KB לכיתות א-ב, ג-ד, ה-ו מבוסס על baseline ידני בלבד
   - קבצי kita1-kita6.pdf (Google Drive — תכנית עברית) טרם הורדו
   - כשיהיו זמינים: הכנס ל-`matirials/` והרץ `python scripts/build_curriculum_kb.py`

### עדיפות בינונית

4. **Cache layer (Phase 2)**
   - Postgres table `materials` כבר קיים ועם pgvector
   - BM25 fuzzy search עבור cache miss → similar topic lookup
   - LLM judge לאמינות התוצאה
   - אין עדיין routing logic ב-pipeline שבודק cache לפני generation

5. **Frontend — יצירת unit**
   - הממשק לא מחובר במלואו לgeneration flow
   - אין progress indicator אמיתי בזמן יצירה (10-30 שניות)

6. **Batch scheduler (Phase 4)**
   - pre-generation של נושאים נפוצים מתכנית הלימודים
   - drift detection: miss rate גוהה = איתות לשינוי בתכנית

### עדיפות נמוכה

7. **Build curriculum_kb מ-PDFs**
   - `scripts/build_curriculum_kb.py` כתוב אבל Gemini extraction לא עובד עם free-tier keys (MAX_TOKENS)
   - הפתרון: מפתח service account (לא AIzaSy...) או Vertex AI
   - כבר יש baseline טוב ידנית — זה עוד שיפור

8. **Production deployment**
   - `docker-compose.prod.yml` + SSL scripts קיימים
   - צריך: AWS LightSail instance, domain, Certbot

---

## הרצת smoke test (ודא שהכל עובד)

```powershell
cd "c:\Users\yaron\OneDrive - Newcinema\newFixTemp\alHasade"
$env:PYTHONIOENCODING="utf-8"

# בדיקת curriculum KB
python -c "
from src.config import get_curriculum_profile
p = get_curriculum_profile('ז', 'מתמטיקה')
print('key_concepts:', p.get('key_concepts', [])[:2])
print('avoid:', p.get('avoid_in_content', '')[:60])
"

# בדיקת prompt injection
python -c "
from src.prompts.hebrew import build_roadmap_prompt
p = build_roadmap_prompt('מתמטיקה', 'משוואות', 'ז', 3)
print('Length:', len(p), '| has curriculum_context:', '<curriculum_context>' in p)
from src.prompts.steam import build_stem_roadmap_prompt
p2 = build_stem_roadmap_prompt('מתמטיקה', 'משוואות', 'ז', 3)
print('STEAM Length:', len(p2), '| has curriculum_context:', '<curriculum_context>' in p2)
"
```

---

## קומיטים אחרונים

| Hash | תיאור |
|------|-------|
| `bb323ba` | feat: curriculum KB + injection into prompts (אחרון) |
| `6dd0b83` | feat: STEAM pipeline, crossword/word-search, content diversity |
| `053af81` | fix: Docker infra, Pexels Cloudflare, duplicate-image tracking |
| `a5314ae` | fix: ThinkingConfig mismatch + UnboundLocalError |
| `652a0e8` | fix: bcrypt==4.0.1 passlib incompatibility |
| `e9753d7` | fix: Docker frontend build + parallel thread deadlock |
| `2c62a35` | docs: DEPLOYMENT.md + ARCHITECTURE.md |

---

---

# סיכום לקלוד קוד — מחשב משרד

> **קרא את הסעיף הזה כשאתה מתחיל session חדש במחשב המשרד.**  
> אין לך גישה לשיחות הקודמות. זה הקשר שאתה צריך כדי להמשיך.

## הפרויקט

פלטפורמת SaaS לאוטומציה של שיטת "א"ל השד"ה" (PACE) — שיטה פדגוגית ישראלית.  
**ריפוזיטורי:** `https://github.com/YaronGenad/elHasade`  
**ענף:** `master`  
**Working directory:** `c:\Users\yaron\OneDrive - Newcinema\newFixTemp\alHasade` *(בבית)*  
**Working directory במשרד:** צריך לאתר לפי שם תיקיה דומה, או `git clone` מחדש.

## מצב נוכחי (נכון ל-2026-07-09)

הכל ב-`master`, commit `bb323ba`. הנה מה שעובד:
- **Docker stack מלא** — backend + frontend + postgres + redis
- **Generation pipeline** — עברית + STEAM
- **Curriculum KB** — `curriculum_kb.json` + injection לכל פרומפט

## הפעלה

```bash
git pull origin master
docker compose up -d
# wait ~30s
curl http://localhost:8000/health   # → {"status":"healthy"}
```

## קבצים הכי חשובים להבין

```
src/config.py          — פרמטרי כיתה + get_curriculum_profile()
src/pipeline.py        — אורקסטרטור: מנתב hebrew vs STEAM, מפעיל generation
src/prompts/hebrew.py  — פרומפטים לעברית + _curriculum_block()
src/prompts/steam.py   — פרומפטים ל-STEAM + _steam_curriculum_block()
curriculum_kb.json     — מסד ידע תכנית לימודים (6 טווחי כיתות × 5 תחומים)
backend/app/api/       — API endpoints (auth, generations, materials, search)
```

## משהו לא עובד? Troubleshooting מהיר

```bash
# backend לא עולה:
docker logs alhasade-backend-1 --tail 30

# GEMINI_API_KEY חסר:
# ודא שקובץ .env קיים ב-alHasade/ עם GEMINI_API_KEY=...

# rebuild:
docker compose down
docker compose up -d --build
```

## המשימות הדחופות הבאות

**1. הוסף curriculum injection ל-`src/prompts/english.py`**  
כל שאר הפרומפטים (hebrew.py, steam.py) כבר מקבלים `<curriculum_context>` block.  
צריך לעשות את אותו דבר לenglish.py. ראה pattern ב-hebrew.py:
- `from ..config import get_curriculum_profile`
- `def _curriculum_block(subject, grade)` → בונה `<curriculum_context>` XML block
- מזריק `{curr}` בתוך כל build_*_prompt()

**2. הזרק `reading_mode` לפרומפטי comprehension**  
`gl['reading_mode']` קיים ב-config אבל לא מגיע לפרומפט הסופי.  
בפרומפטי comprehension ב-hebrew.py ו-steam.py, הוסף הוראה מפורשת.

**3. Enrich curriculum_kb.json לכיתות א-ו**  
כרגע ה-KB לאלמנטרי (כיתות א-ו) הוא baseline ידני בלבד.  
כשיש קבצי תכנית לימודים לעברית (kita1-kita6.pdf):
- הכנס אותם ל-`matirials/`
- הרץ: `python scripts/build_curriculum_kb.py`
- הסקריפט ינסה Gemini extraction (צריך מפתח לא-free-tier)

**4. Cache layer (Phase 2 — לאחר שיהיו משתמשים אמיתיים)**  
- `backend/app/models/material.py` + pgvector כבר קיים
- צריך: BM25 index, cache lookup ב-pipeline לפני generation, variant scoring

## הקשר מלא על ה-Curriculum KB (הפיצ'ר האחרון שנעשה)

**הבעיה:** ה-LLM לא ידע מה מלמדים בכל כיתה — יצר תוכן שלא מתאים לתכנית הלימודים הרשמית.

**הפתרון שמומש:**
1. `curriculum_kb.json` — JSON סטטי עם 6 טווחי כיתות (א-ב, ג-ד, ה-ו, ז-ח, ט-י, יא-יב) × 5 תחומים
2. `get_curriculum_profile(grade, subject)` ב-`config.py` — lookup לפי כיתה ומקצוע  
3. `_curriculum_block()` ב-hebrew.py — מחזיר `<curriculum_context>` HTML-like block
4. Block מוזרק לכל פרומפט roadmap + comprehension

**כיצד ה-block נראה בפרומפט:**
```xml
<curriculum_context>
• מושגי מפתח בתכנית הלימודים לגיל זה: אלגברה (68 ש' כיתה ז'): ביטויים אלגבריים...
• ידע קודם מוכר לתלמיד: פעולות חשבון מלאות, שברים ועשרוניות, אחוזים
• פרופיל אוצר מילים: מינוח אלגברי: משוואה, פתרון, נעלם, ביטוי...
• נושאים אותנטיים מהתכנית הרשמית: בעיות יחס ופרופורציה בחיי יומיום...
• יש להימנע מ: חשבון דיפרנציאלי, אלגברה מופשטת...
</curriculum_context>
```

## מה לא לגעת בו

- `.env` (לא ב-git, מכיל API keys אמיתיים)
- `backend/alembic/versions/` — migration files, אל תמחק
- `output/` — תיקיית PDF זמנית, מנוהלת אוטומטית
