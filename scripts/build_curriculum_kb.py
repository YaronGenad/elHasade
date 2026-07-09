"""
build_curriculum_kb.py — One-time script to extract curriculum knowledge from
Ministry of Education PDFs/DOCXs and produce curriculum_kb.json.

Run from the alHasade root:
    python scripts/build_curriculum_kb.py

Requirements (already installed locally):
    pip install pypdf python-docx google-genai

When new curriculum files arrive, drop them in matirials/ and re-run.
"""

import json
import os
import sys
import time

from dotenv import dotenv_values

# ── PDF / DOCX readers ────────────────────────────────────────────────────────
try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

try:
    from docx import Document as DocxDocument
except ImportError:
    DocxDocument = None

# ── Gemini client ─────────────────────────────────────────────────────────────
try:
    from google import genai
    from google.genai import types as gtypes
except ImportError:
    print("ERROR: google-genai not installed. Run: pip install google-genai")
    sys.exit(1)

# ─────────────────────────────────────────────────────────────────────────────
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MATIRIALS_DIR = os.path.join(ROOT, "matirials")
OUTPUT_PATH = os.path.join(ROOT, "curriculum_kb.json")
ENV_PATH = os.path.join(ROOT, ".env")

GRADE_BANDS = ["א-ב", "ג-ד", "ה-ו", "ז-ח", "ט-י", "יא-יב"]

EXTRACTION_PROMPT = """אתה מנתח מסמך תכנית לימודים רשמית של משרד החינוך הישראלי.

מסמך זה:
{doc_desc}

תוכן המסמך:
---
{text}
---

חלץ מהמסמך מידע מובנה לפי כיתות. החזר JSON בלבד (ללא markdown) בפורמט הבא:

{{
  "grade_band": "ז-ח",
  "subject_domain": "math|science|hebrew|history|social_studies|english",
  "key_concepts": [
    "מושג/נושא מרכזי 1 שנלמד בכיתות אלו",
    "מושג/נושא מרכזי 2",
    ...עד 10 מושגים
  ],
  "vocabulary_profile": "תיאור 1-2 משפטים של רמת המינוח: אילו סוגי מילים/מושגים אופייניים לגיל זה",
  "expected_prior_knowledge": "מה התלמיד אמור לדעת כבר מכיתות קודמות (2-3 משפטים)",
  "typical_authentic_topics": [
    "נושא אמיתי מהתכנית שתלמיד בגיל זה לומד",
    ...עד 6 נושאים
  ],
  "text_complexity": "תיאור קצר (משפט אחד) של מורכבות הטקסטים הצפויה בגיל זה",
  "avoid_in_content": "מה אסור לכלול — מושגים ממתקדמים מדי, גישות שלא נלמדו עדיין"
}}

אם המסמך מכסה מספר שנות לימוד (כמו ז ו-ח ביחד), תחזיר את ה-grade_band כ-"ז-ח".
אם המסמך לא רלוונטי לכיתות א-יב או אינו תכנית לימודים — החזר {{"skip": true}}.
"""

MAX_TEXT_CHARS = 40000


def clean_text(text: str) -> str:
    """Remove non-printable and non-Hebrew/Latin characters from extracted PDF text."""
    import unicodedata
    result = []
    for ch in text:
        cat = unicodedata.category(ch)
        # Keep: printable chars, Hebrew (block 0590-05FF), spaces, newlines, punctuation
        if cat.startswith("L") or cat.startswith("N") or cat.startswith("P") \
                or cat in ("Zs", "Cc") or "֐" <= ch <= "׿" \
                or ch in (" ", "\n", "\t", ".", ",", ":", ";", "-", "(", ")", "[", "]", "/", "%", "="):
            result.append(ch)
        else:
            result.append(" ")
    # Collapse runs of whitespace
    import re
    cleaned = re.sub(r"[ \t]{3,}", "  ", "".join(result))
    cleaned = re.sub(r"\n{4,}", "\n\n\n", cleaned)
    return cleaned.strip()


def load_api_key() -> str:
    env = dotenv_values(ENV_PATH)
    for key_var in ["GEMINI_API_KEY_BECKUP2", "GEMINI_API_KEY_BECKUP3",
                    "GEMINI_API_KEY", "GEMINI_API_KEY_BECKUP"]:
        k = env.get(key_var, "").strip()
        if k and k.startswith("AIzaSy"):
            return k
    raise RuntimeError(f"No valid Gemini API key found in {ENV_PATH}")


def read_pdf(path: str) -> str:
    if PdfReader is None:
        raise ImportError("pypdf not installed")
    reader = PdfReader(path)
    parts = []
    for page in reader.pages:
        try:
            t = page.extract_text()
            if t:
                parts.append(t)
        except Exception:
            pass
    return "\n".join(parts)


def read_docx(path: str) -> str:
    if DocxDocument is None:
        raise ImportError("python-docx not installed")
    doc = DocxDocument(path)
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def extract_curriculum(client: genai.Client, doc_desc: str, text: str) -> dict | None:
    # Escape Hebrew typographic quotes that can corrupt JSON generation
    text_safe = text.replace('"', "'").replace('"', "'").replace('"', "'")
    text_chunk = text_safe[:MAX_TEXT_CHARS]
    prompt = EXTRACTION_PROMPT.format(doc_desc=doc_desc, text=text_chunk)
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=gtypes.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=2048,
                response_mime_type="application/json",
            ),
        )
        raw = response.text.strip()
        result = json.loads(raw)
        if result.get("skip"):
            return None
        return result
    except json.JSONDecodeError as e:
        # Try to salvage: find first { ... last }
        try:
            raw = response.text
            start = raw.index("{")
            end = raw.rindex("}") + 1
            result = json.loads(raw[start:end])
            if result.get("skip"):
                return None
            return result
        except Exception:
            print(f"  ⚠ JSON parse failed: {e}")
            return None
    except Exception as e:
        print(f"  ⚠ Gemini extraction failed: {e}")
        return None


def merge_into_kb(kb: dict, extracted: dict) -> None:
    band = extracted.get("grade_band", "")
    domain = extracted.get("subject_domain", "")
    if not band or not domain:
        return
    if band not in kb:
        kb[band] = {}
    existing = kb[band].get(domain, {})

    def merge_list(key):
        old = existing.get(key, [])
        new = extracted.get(key, [])
        merged = list(dict.fromkeys(old + new))  # deduplicate, preserve order
        return merged[:12]

    kb[band][domain] = {
        "key_concepts": merge_list("key_concepts"),
        "vocabulary_profile": extracted.get("vocabulary_profile") or existing.get("vocabulary_profile", ""),
        "expected_prior_knowledge": extracted.get("expected_prior_knowledge") or existing.get("expected_prior_knowledge", ""),
        "typical_authentic_topics": merge_list("typical_authentic_topics"),
        "text_complexity": extracted.get("text_complexity") or existing.get("text_complexity", ""),
        "avoid_in_content": extracted.get("avoid_in_content") or existing.get("avoid_in_content", ""),
    }


def build_base_kb() -> dict:
    """
    Baseline curriculum knowledge for all grade bands.
    Based on general Israeli Ministry of Education standards.
    Will be enriched by PDF extraction for bands that have documents.
    """
    return {
        "א-ב": {
            "hebrew": {
                "key_concepts": ["אותיות ועיצורים", "ניקוד מלא", "מילים בסיסיות", "משפטים פשוטים", "קריאה ראשונית", "כתיבה ראשונית"],
                "vocabulary_profile": "מאגר 300-600 מילים. מילים חד-הברתיות ודו-הברתיות. מילות יחס ומחבר בסיסיות",
                "expected_prior_knowledge": "הכרת האלפבית, ספירה, צבעים, חיות ומשפחה",
                "typical_authentic_topics": ["משפחה וחברים", "חיות מחמד", "ירקות ופירות", "גוף האדם", "חגים ומועדים"],
                "text_complexity": "משפטים של 3-5 מילים, פסקאות של 2-3 משפטים, עם ניקוד מלא",
                "avoid_in_content": "מילים זרות ללא הסבר, מבנים תחביריים מורכבים, נושאים מופשטים",
            },
            "math": {
                "key_concepts": ["ספירה עד 100", "חיבור וחיסור עד 20", "צורות גיאומטריות", "מדידה בסיסית", "גרפים פשוטים"],
                "vocabulary_profile": "מספרים, יותר/פחות, גדול/קטן, צורות (עיגול, ריבוע, משולש)",
                "expected_prior_knowledge": "ספירה עד 10, הכרת עצמים בסביבה",
                "typical_authentic_topics": ["כמה יש?", "חיבור וחיסור בסיסי", "צורות בסביבה"],
                "text_complexity": "משפטי מתמטיקה קצרים עם מספרים קטנים",
                "avoid_in_content": "כפל וחילוק, שברים, מספרים מעל 100",
            },
        },
        "ג-ד": {
            "hebrew": {
                "key_concepts": ["שורשים", "משקלים", "ביטויים נפוצים", "סוגי טקסטים", "כתיבה מובנית", "הומופוניות נפוצות"],
                "vocabulary_profile": "מאגר 800-1200 מילים. ביטויים ופתגמים נפוצים. מילים נרדפות בסיסיות",
                "expected_prior_knowledge": "קריאה שוטפת, כתיבה בסיסית, הכרת משפט פשוט",
                "typical_authentic_topics": ["חגים ומסורות", "חיות ובעלי חיים", "ספורט ופנאי", "גיבורי ילדות", "ידידות ומשפחה"],
                "text_complexity": "פסקאות של 4-6 משפטים, טקסטים של 200-400 מילים, שפה פשוטה",
                "avoid_in_content": "מינוח מקצועי, עברית גבוהה, טקסטים ספרותיים מורכבים",
            },
            "math": {
                "key_concepts": ["כפל וחילוק", "שברים פשוטים", "עשרוניות בסיסיות", "שטח ופאה", "זמן וכסף", "נתונים בגרפים"],
                "vocabulary_profile": "כפל, חילוק, שבר, מחצית, רבע, אחוז בסיסי, שטח, פאה",
                "expected_prior_knowledge": "חיבור וחיסור עד 1000, צורות גיאומטריות",
                "typical_authentic_topics": ["לוח כפל", "חישובי כסף", "בעיות מילוליות פשוטות", "גרפים ותרשימים"],
                "text_complexity": "בעיות מילוליות של 2-3 משפטים עם נתונים מוחשיים",
                "avoid_in_content": "אלגברה, משוואות, שברים מורכבים",
            },
        },
        "ה-ו": {
            "hebrew": {
                "key_concepts": ["ניתוח טקסט", "טיעון ודעה", "דמויות ועלילה", "אוצר מילים עשיר", "סוגות ספרותיות", "מאזכרים"],
                "vocabulary_profile": "מאגר 1500-2500 מילים. ביטויים ספרותיים, מילות קישור מורכבות, מינוח תחומי בסיסי",
                "expected_prior_knowledge": "קריאה שוטפת, ניסוח בכתב, סוגי טקסטים, שורשים ובניינים בסיסיים",
                "typical_authentic_topics": ["ספרות ילדים ונוער", "אירועים היסטוריים מוכרים", "מדע וטבע", "חברה ועזרה הדדית"],
                "text_complexity": "טקסטים של 400-800 מילים, פסקאות מורכבות, שפה ספרותית עם מילים לא מוכרות",
                "avoid_in_content": "ניתוח ספרותי פורמלי, מינוח אקדמי, ספרות מבוגרים",
            },
            "math": {
                "key_concepts": ["חלוקה עם שארית", "שברים ועשרוניות מורכבים", "אחוזים", "שטח ונפח", "ביטויים מספריים", "יחס ופרופורציה"],
                "vocabulary_profile": "אחוז, פרופורציה, יחס, נפח, שטח, ביטוי מספרי, סדר פעולות",
                "expected_prior_knowledge": "כפל וחילוק, שברים פשוטים, גיאומטריה בסיסית",
                "typical_authentic_topics": ["חישובי מסחר ואחוזים", "גיאומטריה מישורית", "נתונים וסטטיסטיקה", "בעיות יחס ופרופורציה"],
                "text_complexity": "בעיות מילוליות מורכבות, טקסט עם נתונים מספריים וגרפים",
                "avoid_in_content": "אלגברה סמלית, משוואות, הוכחות",
            },
            "history": {
                "key_concepts": ["ציר זמן", "ציוויליזציות קדומות", "מנהיגים ואירועים מרכזיים", "הקשר סיבה-תוצאה", "עם ישראל בתקופות שונות"],
                "vocabulary_profile": "מינוח היסטורי: תקופה, מלוכה, ציוויליזציה, גלות, שיבה, מנהיג, אמנה",
                "expected_prior_knowledge": "ידע בסיסי על מנהיגים ישראליים, חגים ומועדים היסטוריים",
                "typical_authentic_topics": ["מצרים העתיקה", "יוון ורומא", "ממלכת ישראל ויהודה", "גלויות ושיבות", "ימי הביניים"],
                "text_complexity": "טקסטים נרטיביים של 500-800 מילים עם דמויות ואירועים",
                "avoid_in_content": "ניתוח פוליטי מורכב, רוויזיוניזם היסטורי, אירועים של המאה ה-20",
            },
        },
        "ז-ח": {
            "hebrew": {
                "key_concepts": ["ניתוח ספרותי", "שכבות משמעות", "אירוניה ואלגוריה", "טיעון מנומק", "ז'אנרים ספרותיים", "תחביר מורכב"],
                "vocabulary_profile": "מאגר 3000+ מילים. מינוח ספרותי, מילים בינלאומיות, שפה רשמית ובלתי-רשמית",
                "expected_prior_knowledge": "ניתוח פשוט של טקסטים, כתיבת טיעון, מינוח ספרותי בסיסי",
                "typical_authentic_topics": ["ספרות עברית מודרנית", "שואה ותקומה", "עלייה וקליטה", "זהות ישראלית", "קונפליקטים ודילמות"],
                "text_complexity": "טקסטים של 600-1000 מילים, שפה ספרותית, רמיזות תרבותיות",
                "avoid_in_content": "ניתוח אקדמי פורמלי, שיח פוסט-מודרני, ספרות בלתי-מתאימה לגיל",
            },
            "math": {
                "key_concepts": ["משוואות ממעלה ראשונה", "ביטויים אלגבריים", "גיאומטריה אוקלידית", "סטטיסטיקה ואי-ודאות", "פונקציות ראשוניות", "מספרים שלמים"],
                "vocabulary_profile": "מינוח אלגברי: משוואה, פתרון, נעלם, ביטוי, פונקציה, גרף, ציר, מקדם",
                "expected_prior_knowledge": "פעולות חשבון מלאות, שברים ועשרוניות, אחוזים, גיאומטריה מישורית",
                "typical_authentic_topics": ["פתרון משוואות", "גרפים ופונקציות לינאריות", "משפט פיתגורס", "הסתברות", "אי-ודאות ונתונים"],
                "text_complexity": "בעיות מילוליות עם נתונים כמותיים, גרפים ותרשימים מורכבים",
                "avoid_in_content": "חשבון דיפרנציאלי, אלגברה מופשטת, הוכחות פורמליות",
            },
            "science": {
                "key_concepts": ["כימיה: חומרים ותכונות, שינויים פיזיקליים וכימיים", "פיזיקה: אנרגיה וסוגיה, חום ומעבר חום", "ביולוגיה: תא ורקמה, מערכות הגוף, אקולוגיה"],
                "vocabulary_profile": "מינוח מדעי: אטום, מולקולה, צפיפות, אנרגיה קינטית/פוטנציאלית, פוטוסינתזה, תא, רקמה",
                "expected_prior_knowledge": "מדע וטבע מכיתות ה-ו: גוף האדם, כוחות בסיסיים, חי/צומח/דומם",
                "typical_authentic_topics": ["ניסויים עם משתנים", "מודלים מדעיים", "שינויי אנרגיה", "מערכות ביולוגיות", "איכות סביבה"],
                "text_complexity": "מאמרים מדעיים פשוטים, דוחות ניסוי, גרפים ותרשימים",
                "avoid_in_content": "חישובים כימיים מתקדמים, מכניקה קוואנטית, גנטיקה מורכבת",
            },
            "history": {
                "key_concepts": ["עת החדשה", "מהפכות (תעשייתית, צרפתית, אמריקאית)", "לאומיות וציונות", "מלחמות עולם", "שואה ותקומה"],
                "vocabulary_profile": "מינוח היסטורי: לאומיות, אימפריאליזם, מהפכה, ג'נוסייד, מנדט, הסכם, אידיאולוגיה",
                "expected_prior_knowledge": "היסטוריה עתיקה, ממלכת ישראל, ימי הביניים",
                "typical_authentic_topics": ["הציונות וקום המדינה", "שואה ושאלות אתיות", "מלחמת העולם הראשונה", "הריבוי ה'ים האירופי"],
                "text_complexity": "טקסטים ניתוחיים של 600-900 מילים, מקורות ראשוניים קצרים",
                "avoid_in_content": "גישות רוויזיוניסטיות לא מאוזנות, תוכן לא מתאים לגיל",
            },
        },
        "ט-י": {
            "hebrew": {
                "key_concepts": ["ניתוח ספרותי מעמיק", "כתיבת מאמר", "ביקורת ספרותית", "השוואת טקסטים", "שיח רטורי", "תיאוריות פרשנות"],
                "vocabulary_profile": "אוצר מילים אקדמי-ספרותי, מינוח ביקורתי, שפה פורמלית",
                "expected_prior_knowledge": "ניתוח ספרותי, טיעון מנומק, ז'אנרים ספרותיים",
                "typical_authentic_topics": ["ספרות עברית קלאסית", "שירה מודרנית", "פרוזה ישראלית עכשווית", "טקסטים עיתונאיים"],
                "text_complexity": "טקסטים ספרותיים ועיתונאיים של 700-1000 מילים",
                "avoid_in_content": "שפה אקדמית גבוהה מדי, תיאוריות פוסט-מודרניות",
            },
            "math": {
                "key_concepts": ["פונקציות ריבועיות", "גיאומטריה בחלל", "סטטיסטיקה", "הסתברות", "לוגריתמים בסיסיים", "טריגונומטריה"],
                "vocabulary_profile": "פרבולה, שורש ריבועי, נגזרת בסיסית, הסתברות מותנית, סינוס/קוסינוס",
                "expected_prior_knowledge": "אלגברה של כיתות ז-ח, גיאומטריה אוקלידית, פונקציות לינאריות",
                "typical_authentic_topics": ["פונקציות ריבועיות ויישומן", "טריגונומטריה בסיסית", "גיאומטריה אנליטית", "סטטיסטיקה יישומית"],
                "text_complexity": "בעיות מורכבות, הוכחות קצרות, ניתוח גרפים",
                "avoid_in_content": "חשבון אינפיניטסימלי, לוגיקה פורמלית, תורת קבוצות מתקדמת",
            },
            "science": {
                "key_concepts": ["כימיה: קשרים כימיים, חומצות ובסיסים", "פיזיקה: מכניקה, חשמל ומגנטיות", "ביולוגיה: גנטיקה, אבולוציה", "מדעי כדור הארץ"],
                "vocabulary_profile": "מינוח מדעי מתקדם: אלקטרון, קשר קוולנטי, pH, תאוצה, שדה מגנטי, DNA, מוטציה",
                "expected_prior_knowledge": "כימיה ופיזיקה מכיתות ז-ח, ביולוגיה תאית",
                "typical_authentic_topics": ["ניסויים מבוקרים", "גנטיקה מנדלית", "חשמל ומעגלים", "ריאקציות כימיות"],
                "text_complexity": "מאמרים מדעיים ברמת כתב עת נוער, דוחות ניסוי מפורטים",
                "avoid_in_content": "כימיה אורגנית מתקדמת, מכניקה קוונטית, ביולוגיה מולקולרית עמוקה",
            },
        },
        "יא-יב": {
            "hebrew": {
                "key_concepts": ["ניתוח ספרותי אקדמי", "כתיבת עבודת חקר", "הבעה בכתב מתקדמת", "ספרות השוואתית", "ביקורת תרבותית"],
                "vocabulary_profile": "אוצר מילים אקדמי מלא, מינוח תיאורטי, שפה עניינית ומקצועית",
                "expected_prior_knowledge": "ניתוח ספרותי, כתיבת מאמר, ביקורת",
                "typical_authentic_topics": ["יצירות מופת בספרות העברית", "השוואה בין-תרבותית", "ספרות עכשווית", "כתיבה אקדמית"],
                "text_complexity": "טקסטים אקדמיים מלאים, מאמרי ביקורת, פרוזה ספרותית מורכבת",
                "avoid_in_content": "תוכן לא מתאים לגיל, גישות שאינן מאוזנות",
            },
            "math": {
                "key_concepts": ["חשבון דיפרנציאלי ואינטגרלי בסיסי", "מספרים מרוכבים", "סטטיסטיקה מתקדמת", "גיאומטריה אנליטית", "ווקטורים"],
                "vocabulary_profile": "נגזרת, אינטגרל, גבול, ווקטור, מטריצה, סדרה",
                "expected_prior_knowledge": "אלגברה מלאה, טריגונומטריה, גיאומטריה אנליטית, הסתברות",
                "typical_authentic_topics": ["שיעור שינוי ונגזרות", "אינטגרציה ושטחים", "ווקטורים בחלל", "הסתברות מתקדמת"],
                "text_complexity": "הוכחות מתמטיות, בעיות מורכבות עם מספר שלבים",
                "avoid_in_content": "מתמטיקה אוניברסיטאית (תורת קבוצות פורמלית, מבנים אלגבריים)",
            },
            "science": {
                "key_concepts": ["כימיה אורגנית בסיסית", "פיזיקה מודרנית (אטום ואופטיקה)", "ביולוגיה מולקולרית", "גיאולוגיה ואסטרופיזיקה"],
                "vocabulary_profile": "מינוח מדעי מלא ברמת בגרות, אנגלית מדעית בסיסית",
                "expected_prior_knowledge": "פיזיקה, כימיה וביולוגיה של כיתות ט-י",
                "typical_authentic_topics": ["פיצול גרעיני", "ביוטכנולוגיה", "קוסמולוגיה", "כימיה סביבתית"],
                "text_complexity": "מאמרים מדעיים ברמת Scientific American Hebrew, ניתוח ביקורתי",
                "avoid_in_content": "מחקר ברמת אוניברסיטה, נוסחאות מתמטיות ללא הקשר פדגוגי",
            },
        },
    }


def process_file(path: str, filename: str, client: genai.Client) -> dict | None:
    print(f"  Reading {filename}...")
    ext = os.path.splitext(filename)[1].lower()
    try:
        if ext == ".pdf":
            text = read_pdf(path)
        elif ext in (".docx", ".doc"):
            text = read_docx(path)
        else:
            print(f"  Skipping unsupported format: {ext}")
            return None
    except Exception as e:
        print(f"  ⚠ Could not read file: {e}")
        return None

    if not text or len(text.strip()) < 100:
        print(f"  ⚠ File appears to be image-based or empty (extracted {len(text)} chars)")
        return None

    text = clean_text(text)
    print(f"  Extracted {len(text):,} chars (after cleaning). Sending to Gemini...")
    doc_desc = f"שם הקובץ: {filename}"
    result = extract_curriculum(client, doc_desc, text)
    time.sleep(2)  # rate limit buffer
    return result


def main():
    print("=== Building curriculum_kb.json ===\n")

    # Load API key
    api_key = load_api_key()
    client = genai.Client(api_key=api_key)
    print(f"✓ Gemini client ready\n")

    # Start with base KB (good defaults for all grades)
    kb = build_base_kb()

    # Process each file in matirials/
    if not os.path.isdir(MATIRIALS_DIR):
        print(f"⚠ matirials/ directory not found at {MATIRIALS_DIR}")
    else:
        files = sorted(os.listdir(MATIRIALS_DIR))
        print(f"Found {len(files)} files in matirials/\n")

        for filename in files:
            path = os.path.join(MATIRIALS_DIR, filename)
            if not os.path.isfile(path):
                continue
            ext = os.path.splitext(filename)[1].lower()
            if ext not in (".pdf", ".docx", ".doc"):
                continue

            print(f"→ Processing: {filename}")
            result = process_file(path, filename, client)
            if result:
                band = result.get("grade_band", "")
                domain = result.get("subject_domain", "")
                print(f"  ✓ Extracted: grade_band={band}, domain={domain}")
                merge_into_kb(kb, result)
            else:
                print(f"  ✗ Skipped (no usable curriculum data)")
            print()

    # Save result
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(kb, f, ensure_ascii=False, indent=2)

    print(f"\n✅ curriculum_kb.json saved to {OUTPUT_PATH}")
    print(f"   Grade bands: {list(kb.keys())}")
    for band, domains in kb.items():
        print(f"   {band}: {list(domains.keys())}")


if __name__ == "__main__":
    main()
