import hashlib
import json
import os
import re
import unicodedata
from typing import Any, Dict, List


# ─── LLM Configuration ─────────────────────────────────────────────────────────
GEMINI_MODEL: str = "gemini-3-flash-preview"

# Fallback chain — tried in order only when the current model hits a quota/daily-limit error.
# RPM rate-limits (temporary) still retry the same model with backoff.
GEMINI_MODEL_FALLBACK_CHAIN: list = [
    "gemini-3-flash-preview",    # primary
    "gemini-3.1-flash-lite",     # fallback 1: lighter quota pressure
    "gemini-2.5-flash",          # fallback 2: high free-tier quota (1500 req/day)
]

GEMINI_MAX_RETRIES: int = 3
GEMINI_RATE_LIMIT_BACKOFF_BASE: int = 20  # seconds, multiplied by (attempt + 1)

# ─── Token & Cost Configuration ─────────────────────────────────────────────
GEMINI_MAX_OUTPUT_TOKENS: int = 65536         # model maximum — no artificial cap
# Gemini Flash 2.0 pricing (USD per 1M tokens)
GEMINI_FLASH_INPUT_COST_PER_1M: float = 0.10
GEMINI_FLASH_OUTPUT_COST_PER_1M: float = 0.40
# Hard safety cap per generation. Set conservatively; tighten after collecting
# real data from the 6 test scenarios.
GEMINI_MAX_COST_PER_GENERATION_USD: float = 2.00  # 3x observed max ($0.017); tighten further once stable


# --- Claude (primary provider) ---
CLAUDE_MODEL: str = "claude-sonnet-5"
CLAUDE_MAX_OUTPUT_TOKENS: int = 32000
CLAUDE_INPUT_COST_PER_1M: float = 2.00
CLAUDE_OUTPUT_COST_PER_1M: float = 10.00

# USD per 1M tokens, keyed by the provider that actually answered.
PROVIDER_PRICING = {
    "anthropic": (CLAUDE_INPUT_COST_PER_1M, CLAUDE_OUTPUT_COST_PER_1M),
    "gemini": (GEMINI_FLASH_INPUT_COST_PER_1M, GEMINI_FLASH_OUTPUT_COST_PER_1M),
    "openai": (CLAUDE_INPUT_COST_PER_1M, CLAUDE_OUTPUT_COST_PER_1M),
}

# ─── Pipeline Configuration ─────────────────────────────────────────────────────
SAFE_NAME_MAX_LENGTH: int = 50


def make_safe_name(text: str, max_len: int = 40) -> str:
    """Return an ASCII-safe filesystem token from text (works for Hebrew or Latin).
    Latin text is slugified; non-ASCII-only text falls back to a short MD5 hash."""
    normalized = unicodedata.normalize("NFKD", text)
    ascii_part = re.sub(r"[^\x00-\x7F]+", "", normalized)
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", ascii_part).strip("_")
    slug = re.sub(r"_+", "_", slug)
    if not slug:
        slug = hashlib.md5(text.encode("utf-8")).hexdigest()[:10]
    return slug[:max_len]
DEFAULT_ROUNDS: int = 4

GRADE_LEVELS = {
    "א-ב": {
        "age": "6-8",
        "language": "פשוט מאוד, מילים קצרות, משפטים קצרים",
        "reading_mode": "קריאת מורה + חזרה / קריאה בזוגות",
        "dictation_words": 6,
        "text_length": "250-350 מילים",
        "comprehension_options": ["שאלות בעל פה חמשת ממים", "כרטיסיות 2 שאלות", "מצגות מוקראות"],
        "methods_options": ["כתיבת שיר קצר (בנק מילים)", "כתיבת מכתב עם פיגום", "סידור משפטים מבולבלים"],
        "precision_options": ["הכתבת מילים עד 6", "גלגל דיוק", "השלמת אותיות חסרות"],
        "vocabulary_options": ["קלפי זכר/נקבה לגזירה", "קלפי יחיד/רבים לגזירה", "ציור למשפט", "השלמת אותיות"]
    },
    "ג-ד": {
        "age": "8-10",
        "language": "פשוט, מושגים מוכרים, פסקאות בינוניות",
        "reading_mode": "קריאת מורה ראשונה + קריאה בזוגות + שחזור הדדי",
        "dictation_words": 10,
        "text_length": "350-500 מילים",
        "comprehension_options": ["קוביית ממים", "שאלות קונפליקטים ודעה", "המחזה של טקסטים"],
        "methods_options": ["כתיבת חוות דעת", "כתיבת סיפור בעקבות סיפור", "כתיבת יומן אישי", "טקסט מידעי + שאלות"],
        "precision_options": ["הכתבת מילים עד 10-15", "אותיות הומופוניות", "הכתבת משפטים מהסיפור", "מילים נרדפות"],
        "vocabulary_options": ["ביטויים ומשמעותם", "כרזות פרסום", "כתב סתרים ביטויים", "התאמת זוגות מילים (חולצה-מכנסיים)"]
    },
    "ה-ו": {
        "age": "10-12",
        "language": "בינוני, מושגים חדשים עם הסברים",
        "reading_mode": "קריאה קולית זוגית + שחזור + שאלות עמוקות",
        "dictation_words": 15,
        "text_length": "700-1000 מילים",
        "comprehension_options": ["קוביית ממים ומידעית", "שאלות ערכים ודילמות", "המחזה של טקסט"],
        "methods_options": ["כתיבת טיעון בעד/נגד", "תיאור דמות", "חוות דעת על אירוע", "כתיבת דוח", "תרשים זרימה"],
        "precision_options": ["הכתבות 15-20 מילים", "הכתבת משפטים", "אפיון דמות", "ביטויים ומשמעותם", "מאזכרים", "פאזל מילים נרדפות"],
        "vocabulary_options": ["קלפי ביטויים ופירושים לגזירה", "בניית כרזות", "משחקי מילים מורכבים (קלפים לגזירה)", "פאזל מילים נרדפות", "תשחץ מילים (word_search)", "תשבץ מיני (crossword_mini)"]
    },
    "ז-ח": {
        "age": "12-14",
        "language": "מפותח, טרמינולוגיה מקצועית",
        "reading_mode": "קריאה עצמאית + שחזור + ניתוח ביקורתי",
        "dictation_words": 18,
        "text_length": "800-1000 מילים",
        "comprehension_options": ["שאלות ניתוח וביקורת", "דיון על ערכים ודילמות", "קוביית ממים מתקדמת", "השוואת שני טקסטים"],
        "methods_options": ["כתיבת טיעון מנומק עם ראיות", "ניתוח טקסט לפי תבחינים", "כתיבת סיכום", "תשובה מיטבית", "כתיבת מאמר דעה"],
        "precision_options": ["הכתבות 18-20 מילים", "שורשים ובניינים", "סוגי משפטים", "מאזכרים מתקדמים", "תחביר: פסוקית זיקה"],
        "vocabulary_options": ["טבלת מילים-הגדרות-משפטים", "כרזות ביטויים מורכבים", "קלפי נרדפות/הפכים לגזירה", "תשחץ מילים (word_search)", "תשבץ מיני (crossword_mini)"]
    },
    "ט-י": {
        "age": "14-16",
        "language": "מתקדם, מושגים מופשטים, שפה עשירה",
        "reading_mode": "קריאה עצמאית + ניתוח ביקורתי",
        "dictation_words": 20,
        "text_length": "700-1000 מילים",
        "comprehension_options": ["ניתוח ביקורתי", "השוואת טקסטים", "דיון על סוגיות"],
        "methods_options": ["כתיבת מאמר טיעוני", "ניתוח ספרותי", "כתיבת מיזוג מקורות"],
        "precision_options": ["הכתבת קטעים", "ניתוח לשוני מעמיק", "תרגילי בניינים"],
        "vocabulary_options": ["ניתוח שדה סמנטי", "מפת מושגים", "קלפי אסוציאציות לגזירה"]
    },
    "יא-יב": {
        "age": "16-18",
        "language": "אקדמי, מקצועי, ניתוח עמוק",
        "reading_mode": "קריאה עצמאית + ניתוח אקדמי + שיח ביקורתי",
        "dictation_words": 20,
        "text_length": "800-1200 מילים",
        "comprehension_options": ["ניתוח אקדמי מעמיק", "השוואה ביקורתית בין טקסטים", "ניתוח רטורי וסגנוני", "ניתוח טקסט לפי תיאוריות"],
        "methods_options": ["כתיבה אקדמית מובנית", "ניתוח ספרותי מעמיק", "עבודת חקר קצרה", "מאמר השוואתי"],
        "precision_options": ["תרגילים לשוניים ברמה גבוהה", "ניתוח לשוני-סגנוני", "עשרה תרגילי תחביר", "ניתוח שגיאות נפוצות בכתיבה"],
        "vocabulary_options": ["מילון מושגים אישי עם הקשרים", "ניתוח שדות סמנטיים", "קלפי אסוציאציות לגזירה", "תשבץ מיני (crossword_mini)"]
    }
}

STATION_COLORS = {
    "comprehension": {"primary": "#c0392b", "light": "#fadbd8", "border": "#e74c3c", "emoji": "🔴", "name": "תחנת הבנה"},
    "methods":       {"primary": "#1a5276", "light": "#d6eaf8", "border": "#2980b9", "emoji": "🔵", "name": "תחנת שיטות"},
    "precision":     {"primary": "#1e8449", "light": "#d5f5e3", "border": "#27ae60", "emoji": "🟢", "name": "תחנת דיוק"},
    "vocabulary":    {"primary": "#7d6608", "light": "#fef9e7", "border": "#f1c40f", "emoji": "🟡", "name": "תחנת הרחבת אוצר מילים"},
    "teacher":       {"primary": "#4a235a", "light": "#f5eef8", "border": "#8e44ad", "emoji": "📋", "name": "הכנה למורה"},
    "answers":       {"primary": "#1a3a6b", "light": "#eaf2ff", "border": "#2c5aa0", "emoji": "🔑", "name": "פתרונות ומדדי הצלחה"},
}


_GRADE_MAP = {
    "א": "א-ב", "ב": "א-ב",
    "ג": "ג-ד", "ד": "ג-ד",
    "ה": "ה-ו", "ו": "ה-ו",
    "ז": "ז-ח", "ח": "ז-ח",
    "ט": "ט-י", "י": "ט-י",
    "יא": "יא-יב", "יב": "יא-יב"
}


def get_grade_level(grade: str) -> Dict:
    g = grade.replace("׳", "").replace("'", "")
    return GRADE_LEVELS.get(_GRADE_MAP.get(g, "ז-ח"), GRADE_LEVELS["ז-ח"])


def needs_nikud(grade: str) -> bool:
    """Returns True for grades alef–gimel (ages 6–9) where vowel marks aid reading."""
    clean = grade.replace("׳", "").replace("'", "")
    clean = re.sub(r'כיתה|שנה|grade|year', '', clean, flags=re.IGNORECASE).strip()
    if clean and clean[0] in ('א', 'ב', 'ג'):
        return True
    if re.fullmatch(r'[1-3]', clean):
        return True
    return False


# ─── Curriculum Knowledge Base ───────────────────────────────────────────────

_CURRICULUM_KB: Dict | None = None
_CURRICULUM_SCIENCE: Dict | None = None

_SCIENCE_KEYWORDS = (
    "מדע", "פיזיקה", "כימיה", "ביולוגיה", "science",
    "מדעי הטבע", "מדע וטבע", "מד' וטכ'", "מדעי הסביבה",
    "אסטרונומיה", "גיאולוגיה", "טכנולוגיה", "הנדסה",
)


def _load_curriculum_kb() -> Dict:
    global _CURRICULUM_KB
    if _CURRICULUM_KB is None:
        kb_path = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'curriculum_kb.json'))
        try:
            with open(kb_path, encoding='utf-8') as f:
                _CURRICULUM_KB = json.load(f)
        except Exception:
            _CURRICULUM_KB = {}
    return _CURRICULUM_KB


def _load_curriculum_science() -> Dict:
    global _CURRICULUM_SCIENCE
    if _CURRICULUM_SCIENCE is None:
        path = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'curriculum_science.json'))
        try:
            with open(path, encoding='utf-8') as f:
                _CURRICULUM_SCIENCE = json.load(f)
        except Exception:
            _CURRICULUM_SCIENCE = {}
    return _CURRICULUM_SCIENCE


_CURRICULUM_ENGLISH: Dict | None = None


def _load_curriculum_english() -> Dict:
    global _CURRICULUM_ENGLISH
    if _CURRICULUM_ENGLISH is None:
        path = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'curriculum_english.json'))
        try:
            with open(path, encoding='utf-8') as f:
                _CURRICULUM_ENGLISH = json.load(f)
        except Exception:
            _CURRICULUM_ENGLISH = {}
    return _CURRICULUM_ENGLISH


def _subject_to_domain(subject: str) -> str:
    """Map a free-text subject string to a curriculum_kb domain key."""
    s = subject.lower()
    if any(k in s for k in ("היסטוריה", "history", "אזרחות", "גיאוגרפיה", "geography")):
        return "history"
    if any(k in s for k in ("english", "אנגלית")):
        return "english"
    if any(k in s for k in ("מתמטיקה", "חשבון", "math", "אלגברה", "גיאומטריה")):
        return "math"
    if any(k in s for k in _SCIENCE_KEYWORDS):
        return "science"
    return "hebrew"


def get_curriculum_profile(grade: str, subject: str) -> Dict:
    """Return the curriculum knowledge profile for this grade band + subject.

    Returns an empty dict if no data is available — callers must handle that.
    Science subjects use per-grade data from curriculum_science.json (grades א-ו).
    All other subjects fall back to curriculum_kb.json (grade-band granularity).
    """
    g = grade.replace("׳", "").replace("'", "").strip()
    domain = _subject_to_domain(subject)

    if domain == "english":
        eng = _load_curriculum_english()
        if g in eng:
            return eng[g]

    if domain == "science":
        sci = _load_curriculum_science()
        if g in sci:
            return sci[g]

    kb = _load_curriculum_kb()
    band = _GRADE_MAP.get(g, "ז-ח")
    band_data = kb.get(band, {})
    return band_data.get(domain, band_data.get("hebrew", {}))


# ─── STEM / STEAM ───────────────────────────────────────────────────────────

STEM_SUBJECTS = {
    # Core STEAM subjects (Hebrew)
    "מתמטיקה", "מדעים", "מדע", "טכנולוגיה", "הנדסה", "אמנויות", "אמנות",
    # Specific sciences
    "פיזיקה", "כימיה", "ביולוגיה", "גיאוגרפיה", "גיאולוגיה", "אסטרונומיה",
    # Technology / Computers
    "חשמל", "אלקטרוניקה", "מחשבים", "מחשב", "תכנות", "קוד", "רובוטיקה",
    # Common Israeli curriculum names
    "מד' וטכ'", "מד וטכ", "מדע וטכ", "מדע וטבע",
    "מדעי הטבע", "מדעי הסביבה", "מדעי האדמה",
    "מדעי החיים", "מדעי החומר", "מדעי כדור הארץ",
    "חינוך טכנולוגי", "טכנולוגיה ועיצוב",
    # Elementary-level subject names
    "טבע", "אנרגיה", "חקר", "ניסויים", "מעבדה",
    # Arts in STEAM
    "מוזיקה", "תיאטרון", "עיצוב", "אדריכלות",
    # English names
    "math", "mathematics", "science", "technology", "engineering", "arts",
    "physics", "chemistry", "biology", "computer", "coding", "robotics",
    "geography", "geology", "astronomy",
}

# Subjects that sound like STEM but are NOT (explicit exclusions prevent false positives)
_NON_STEM_SUBJECTS = {
    "מדעי החברה", "מדעי הדתות", "מדעי הדת", "מדעי המדינה",
    "סביבה חברתית", "חברה",
}

ENGLISH_SUBJECTS = {
    "אנגלית", "אנגלי", "english", "English",
    "אנגלית כשפה זרה", "אנגלית כשפה שנייה",
    "שפה אנגלית", "לשון אנגלית",
    "EFL", "ESL", "PACE",
}


def is_stem(subject: str) -> bool:
    """Returns True when the subject calls for the STEAM edition of א\"ל השד\"ה."""
    # Explicit non-STEM check first (social sciences, etc.)
    if any(ns in subject for ns in _NON_STEM_SUBJECTS):
        return False
    return any(s in subject for s in STEM_SUBJECTS)


def is_english(subject: str) -> bool:
    """Returns True when the subject is English — output will be fully in English."""
    return any(s.lower() in subject.lower() for s in ENGLISH_SUBJECTS)


# ─── MATH (מתמטיקה יומית) ────────────────────────────────────────────────────

MATH_SUBJECTS = {
    "מתמטיקה", "חשבון", "גיאומטריה", "אלגברה", "חשבון ואלגברה",
    "סטטיסטיקה", "הסתברות", "טריגונומטריה", "אנליזה",
    "math", "mathematics", "geometry", "algebra", "statistics",
}


def is_math(subject: str) -> bool:
    """Returns True when the subject calls for the מתמטיקה יומית edition."""
    return any(s.lower() in subject.lower() for s in MATH_SUBJECTS)


# ─── ENGLISH GRADE LEVELS ────────────────────────────────────────────────────
# Parallel to GRADE_LEVELS but calibrated for EFL/ESL proficiency per grade band.

ENGLISH_GRADE_LEVELS: Dict = {
    "א-ב": {
        "age": "6-8",
        "cefr": "Pre-A1",
        "language": "very simple: single words, short phrases, basic sight words",
        "reading_mode": "Teacher reads aloud + students repeat / pair reading with pictures",
        "dictation_words": 5,
        "text_length": "80-150 words",
        "comprehension_options": ["picture-based questions", "yes/no questions", "point and say"],
        "methods_options": ["label a picture", "fill-in-the-blank sentence", "copy and draw"],
        "precision_options": ["spell 5 sight words", "match word to picture", "circle the correct word"],
        "vocabulary_options": ["word-picture matching cards", "flashcard memory game", "draw and label"],
    },
    "ג-ד": {
        "age": "8-10",
        "cefr": "A1",
        "language": "simple sentences, familiar vocabulary, present tense focus",
        "reading_mode": "Paired reading + comprehension check + oral retell",
        "dictation_words": 8,
        "text_length": "150-250 words",
        "comprehension_options": ["WH-questions (who/what/where/when)", "true/false statements", "sequence events"],
        "methods_options": ["write 3-5 sentences about the topic", "fill-in dialogue", "simple description"],
        "precision_options": ["spell 8 topic words", "singular/plural", "present simple sentences"],
        "vocabulary_options": ["word-definition matching", "word search", "sentence completion"],
    },
    "ה-ו": {
        "age": "10-12",
        "cefr": "A1",
        "language": "short paragraphs, familiar topics, present and past tense",
        "reading_mode": "Silent reading + pair discussion + summary",
        "dictation_words": 12,
        "text_length": "250-400 words",
        "comprehension_options": ["open WH-questions", "find evidence in text", "compare characters/events"],
        "methods_options": ["write a short paragraph", "personal opinion with reason", "simple narrative"],
        "precision_options": ["spell 12 words", "past tense transformation", "adjective use"],
        "vocabulary_options": ["crossword", "word-definition table", "idiom cards"],
    },
    "ז-ח": {
        "age": "12-14",
        "cefr": "A2–B1",
        "language": "multi-paragraph texts, varied tenses, topic-specific vocabulary",
        "reading_mode": "Independent reading + analysis + group discussion",
        "dictation_words": 15,
        "text_length": "350-550 words",
        "comprehension_options": ["inference questions", "author's purpose", "text structure analysis"],
        "methods_options": ["opinion paragraph with evidence", "compare and contrast", "summary writing"],
        "precision_options": ["spell 15 words", "tense review (past/present/future)", "prepositions"],
        "vocabulary_options": ["definition table with example sentences", "matching cards", "fill-in-the-blank"],
    },
    "ט-י": {
        "age": "14-16",
        "cefr": "B1",
        "language": "extended texts, academic vocabulary, complex sentences",
        "reading_mode": "Independent reading + critical analysis",
        "dictation_words": 18,
        "text_length": "450-700 words",
        "comprehension_options": ["critical thinking questions", "compare two texts", "evaluate arguments"],
        "methods_options": ["argumentative paragraph", "formal letter", "analytical response"],
        "precision_options": ["spell 18 words", "passive voice", "conditionals"],
        "vocabulary_options": ["semantic field map", "collocations table", "word-form table (noun/verb/adj)"],
    },
    "יא-יב": {
        "age": "16-18",
        "cefr": "B1–B2",
        "language": "academic and literary texts, nuanced vocabulary, complex grammar",
        "reading_mode": "Independent reading + academic analysis",
        "dictation_words": 20,
        "text_length": "550-900 words",
        "comprehension_options": ["literary analysis", "rhetorical analysis", "cross-text synthesis"],
        "methods_options": ["essay writing", "literary analysis paragraph", "research-based writing"],
        "precision_options": ["advanced spelling", "complex grammar structures", "style and register"],
        "vocabulary_options": ["academic word list activities", "connotation/denotation cards", "etymology exploration"],
    },
}


def get_english_grade_level(grade: str) -> Dict:
    """Returns English-specific grade level settings."""
    g = grade.replace("׳", "").replace("'", "")
    if g == "ג":  # Grade 3 = Pre-A1 per MoE 2020, not grouped with grade 4 A1
        return {
            "age": "8-9", "cefr": "Pre-A1",
            "language": "phonics-based: CVC/CVCE words, sight words, short supported sentences",
            "reading_mode": "Paired reading with picture support + oral retell",
            "dictation_words": 5,
            "text_length": "80-130 words",
            "comprehension_options": ["picture-based WH questions", "yes/no oral", "point and say", "sentence starters"],
            "methods_options": ["label a picture", "fill-in-the-blank 1-2 words", "copy and draw", "simple sentence frame"],
            "precision_options": ["spell 5 phonics words", "match word to picture", "circle correct word", "phonics sorting (sh/ch/th)"],
            "vocabulary_options": ["word-picture matching", "flashcard memory game", "draw and label", "word-picture sort"],
        }
    band = _GRADE_MAP.get(g, "ז-ח")
    return ENGLISH_GRADE_LEVELS.get(band, ENGLISH_GRADE_LEVELS["ז-ח"])


# STEM-specific grade adaptations (parallel to GRADE_LEVELS)
STEM_GRADE_ADAPTATIONS = {
    "א-ב": {
        "text_length": "200-350 מילים",
        "comprehension_channels": [
            "צפייה בסרטון קצר + שאלות בעל פה",
            "תצפית מונחת + ציור תיעוד",
            "טקסט קצר מוקרא + שחזור בעל פה",
        ],
        "methods_frameworks": [
            "מילוי טבלת תצפית פשוטה (מה ראיתי / מה קרה)",
            "ציור תוצאת ניסוי + הסבר בעל פה",
        ],
        "precision_activities": [
            "ניסוי גילוי פשוט (מגנטים / מים / צמחים)",
            "מדידת אורך עם סרגל + רישום",
            "בנייה מקלות ארטיק לפי הנחיות",
        ],
        "vocabulary_games": [
            "זיכרון מושגים (Hebrew↔English)",
            "פיסול מושג בפלסטלינה",
            "כרטיסיות מושגים + ציור ביחד",
        ],
    },
    "ג-ד": {
        "text_length": "300-500 מילים",
        "comprehension_channels": [
            "קריאת כתבה מדעית + ניתוח גרף פשוט",
            "ניתוח תמונה מדעית + שאלות הבנה",
            "השוואת שני מקורות מדעיים קצרים",
        ],
        "methods_frameworks": [
            "דף ניסוי מדעי מובנה: שאלה → השערה → שיטה → תוצאות → מסקנה",
            "ניתוח גרף נתון + כתיבת 3 משפטי פרשנות",
            "תהליך תיכון הנדסי (EDP) בסיסי",
        ],
        "precision_activities": [
            "ניסוי מדידות (אורך / משקל / זמן) + תיעוד בטבלה",
            "בנייה עם מגבלות (מגדל גבוה / גשר נושא משקל)",
            "ניסוי השוואה בין שני תנאים",
        ],
        "vocabulary_games": [
            "קטאן מדעי (Science Catan)",
            "אליאס מדעי (10 מושגים)",
            "סולמות ונחשים STEAM",
            "זיכרון מושגים Hebrew↔English",
        ],
    },
    "ה-ו": {
        "text_length": "400-650 מילים",
        "comprehension_channels": [
            "קריאת כתבה מדעית בעברית + שאלות הבנה",
            "קריאת מאמר מדעי פשוט באנגלית + זיהוי טענה-ראיה-מסקנה",
            "ניתוח גרפים ונתונים מורכבים",
        ],
        "methods_frameworks": [
            "כתיבת דוח ניסוי מלא (שאלה/השערה/שיטה/תוצאות/מסקנה)",
            "תהליך תיכון הנדסי (EDP): זיהוי בעיה → תכנון → בנייה → בדיקה → שיפור",
            "ניתוח נתונים סטטיסטי בסיסי (ממוצע/מינימום/מקסימום/מגמות)",
        ],
        "precision_activities": [
            "ניסוי עם משתנים (בלתי-תלוי / תלוי / קבוע) + תיעוד",
            "בנייה הנדסית + בדיקה + שיפור מנומק",
            "תיכון הנדסי + בנייה + מדידת ביצועים",
        ],
        "vocabulary_games": [
            "טאבו מדעי (Science Taboo)",
            "20 שאלות מדעיות",
            "Bingo מדעי (STEAM Bingo)",
            "שרשרת מדעית (Word Chain)",
        ],
    },
    "ז-ח": {
        "text_length": "500-800 מילים",
        "comprehension_channels": [
            "קריאת מאמר מדעי + זיהוי טענות וראיות",
            "ניתוח נתונים מורכב + פרשנות",
            "השוואת שני מקורות מדעיים + זיהוי הסכמות ומחלוקות",
        ],
        "methods_frameworks": [
            "כתיבת דוח מחקר מלא ומובנה",
            "ניתוח ביקורתי של ניסוי קיים",
            "תיכון הנדסי מתקדם עם מפרט טכני",
        ],
        "precision_activities": [
            "ניסוי מובנה עם תיעוד כמותי מלא",
            "ניתוח נתונים וגרפים (מגמות / חריגות / מסקנות)",
            "בנייה הנדסית מתקדמת + ניתוח כשלים",
        ],
        "vocabulary_games": [
            "אליאס מדעי מתקדם",
            "טאבו מדעי",
            "שרשרת מדעית",
            "פאזל מושגים (Concept Puzzle)",
            "Quiz Bowl",
        ],
    },
    "ט-י": {
        "text_length": "600-900 מילים",
        "comprehension_channels": [
            "קריאת מאמר מדעי מתקדם (עברית/אנגלית)",
            "ניתוח כמותי ואיכותני של נתונים",
            "ביקורת מתודולוגית של מחקר",
        ],
        "methods_frameworks": [
            "כתיבה מדעית אקדמית",
            "ניתוח ביקורתי של מחקרים",
            "עיצוב ניסוי מחקרי עצמאי",
        ],
        "precision_activities": [
            "ניסוי מחקרי מתקדם + דוח מלא",
            "עיצוב הנדסי + אופטימיזציה",
            "ניתוח נתונים כמותי עם סטטיסטיקה",
        ],
        "vocabulary_games": [
            "Taboo מדעי",
            "Quiz Bowl STEAM",
            "20 שאלות מדעיות",
            "Concept Mapping",
        ],
    },
    "יא-יב": {
        "text_length": "700-1000 מילים",
        "comprehension_channels": [
            "קריאת מאמר מדעי אקדמי בעברית ובאנגלית",
            "ביקורת מחקר מבוססת מתודולוגיה",
            "ניתוח השוואתי של מחקרים מרובים",
        ],
        "methods_frameworks": [
            "כתיבה מדעית אקדמית מלאה",
            "כתיבת הצעת מחקר",
            "ניתוח נתונים סטטיסטי מתקדם",
        ],
        "precision_activities": [
            "ניסוי מחקרי עצמאי + דוח מלא",
            "עיצוב הנדסי מתקדם + אופטימיזציה",
            "ניתוח סטטיסטי מלא",
        ],
        "vocabulary_games": [
            "שרשרת מדעית",
            "Concept Mapping מתקדם",
            "Quiz Bowl אקדמי",
        ],
    },
}

STEAM_HANDS_ON_TYPES = {
    'science_experiment': 'ניסוי מדעי',
    'measurement_data':   'מדידות ואיסוף נתונים',
    'engineering_building': 'בנייה הנדסית',
    'math_hands_on':      'מתמטיקה מוחשית',
    'art_design':         'יצירה ועיצוב',
}

STEAM_GAMES_LIST = """רשימת 17 המשחקים לתחנת הרחבת אוצר מילים — גרסת STEAM:
1. stem_memory — זיכרון מושגים (Memory Match): זוגות עברית↔אנגלית / מונח↔הגדרה / מושג↔תמונה
2. stem_alias — אליאס מדעי (Science Alias): הסבר מושג ללא המילה; צוות מנחש
3. stem_taboo — טאבו מדעי (Science Taboo): הסבר ללא מילות המפתח האסורות
4. stem_quartets — רביעיות מדעיות (Quartets): אסיפת רביעיית קלפים מאותה קטגוריה
5. stem_bingo — Bingo מדעי (STEAM Bingo): המורה קוראת הגדרות; מי שמזהה — סומן
6. stem_snakes — סולמות ונחשים STEAM: שאלת מושג בכל ריבוע; נכון=עלה, טעות=ירד
7. stem_quiz — שאלות ותשובות (Quiz Bowl): קלפי שאלות STEAM; תחרות קבוצתית
8. stem_who_am_i — מי אני? (Who Am I? Science): כרטיס מושג על המצח; שאלות כן/לא
9. stem_dominoes — דומינו STEAM: מושג↔הגדרה; הנח קלף כך שמושג פוגש הגדרתו
10. stem_flashcard — כרטיסיות אוצר (Flashcard Battle): מי עונה מהר יותר
11. stem_concept_puzzle — פאזל מושגים (Concept Puzzle): שם/הגדרה/דוגמה/ציור — הרכב
12. stem_word_chain — שרשרת מדעית (Word Chain): מושג שמתחיל באות אחרונה + הסבר הקשר
13. stem_matching_board — התאמת מושגים (Concept Matching Board): לוח גדול + חיבור בחוט
14. stem_20_questions — 20 שאלות מדעיות: שאלות כן/לא לגילוי המושג הנסתר
15. stem_track — מסלול מדעי (STEAM Track): כרטיסיות ירוק/צהוב/אדום לפי קושי
16. stem_catan — קטאן מדעי (Science Catan): בניית ממלכה; ענה נכון — קבל משאב
17. stem_monopoly — מונופול מדעי (Science Monopoly): נכסים=מושגי STEAM; ענה הגדרה — רכוש
"""


def get_stem_grade_level(grade: str) -> Dict:
    """Returns STEM-specific grade adaptations."""
    g = grade.replace("׳", "").replace("'", "")
    band = _GRADE_MAP.get(g, "ז-ח")
    return STEM_GRADE_ADAPTATIONS.get(band, STEM_GRADE_ADAPTATIONS["ז-ח"])


# ── Literature context detection ─────────────────────────────────────────────

_LIT_SUBJECTS = {"ספרות", "לשון", "עברית", "שירה", "מחזה"}
_AUTHOR_KEYWORDS = {"ויצירתו", "ויצירתה", "ויצירתם", "משורר", "סופרת", "מחבר", "סופר ויצירתו"}


def parse_literature_context(subject: str, topic: str) -> dict:
    """Detect literature mode and extract author/work details from user input."""
    if not any(k in subject for k in _LIT_SUBJECTS):
        return {"mode": "standard", "author": None, "specific_work": None}
    if any(k in topic for k in _AUTHOR_KEYWORDS):
        parts = [p.strip() for p in topic.replace("—", "–").replace("–", "-").split("-")]
        author = parts[-1] if parts else topic
        return {"mode": "author_rotating", "author": author, "specific_work": None}
    parts = [p.strip() for p in topic.replace("—", "–").replace("–", "-").split("-") if p.strip()]
    if len(parts) >= 2:
        return {"mode": "specific_work", "author": parts[0], "specific_work": "-".join(parts[1:])}
    return {"mode": "specific_work", "author": None, "specific_work": topic}


# ── Learning skills by grade (official MoE curriculum) ───────────────────────

LEARNING_SKILLS_BY_GRADE: Dict[str, List[str]] = {
    "א": [
        "טרום קריאה: זיהוי כותרת ותמונה", "מילות שאלה ומילות הוראה", "רצף ארועים",
        "הדגשת שאלה ותשובה בצבע זהה", "כתיבת תשובה מלאה / שאילת שאלות",
        "נקודה בסוף משפט וסימן שאלה", "מבנה המשפט", "הנגנה וחריזה",
        "זכר-נקבה, יחיד-רבים", "שיח בעל-פה: מי/מתי/איך",
    ],
    "ב": [
        "ניבוי עפ\"י כותרת", "מילון כיס", "רפלקציה אישית",
        "מסר גלוי / מסר סמוי", "כתיבת משפט סיבה + תוצאה", "פיצוח שאלה",
        "מאזכרים", "שייכות", "מילים נרדפות",
        "הבעת עמדה בכתב בעקבות קריאה", "כתיבת תשובה מיטבית",
        "מאפיינים זהים ב-2 טקסטים", "פיצוח שאלה בעלת 2 חלקים", "מילות רמז",
    ],
    "ג": [
        "חלוקת טקסט לפסקאות", "מציאת משפטי מפתח ומילות מפתח",
        "רעיון מרכזי של פסקה: על מי/מה? מה נאמר עליו?",
        "הבעת עמדה בהתבסס על קריאה", "הסקת מסקנות", "יישום והערכה",
        "שורשים ומשפחות מילים (פועל/שם/תואר)", "מילים נרדפות",
        "עמדה אישית בעל-פה", "הבנת מילים עפ\"י הקשר",
        "מרכאות ומאזכרים", "שאילת שאלות", "מיון בדרכים שונות",
    ],
    "ד": [
        "חזרה ובסוס מיומנויות ג'", "הסקת מסקנות", "יישום והערכה",
        "מילות קישור", "סמיכות", "טקסט רב-היצגי",
        "מיזוג והשוואה בין טקסטים", "אפיון דמות", "תרשים זרימה",
        "כתיבת המלצה: שכנוע והרצף המשפטי",
        "נקודות מבט שונות", "מילות שכנוע", "מילות העצמה",
    ],
    "ה": [
        "חזרה ובסוס מיומנויות ד'",
        "כתיבה טיעונית (להסיק ממסרטונים, ללא תבניות)",
        "מילות קישור ומיליות", "שם פעולה", "שם פועל",
        "סמיכות", "כינויי קניין", "מילות יחס", "טקסט רב-היצגי",
    ],
    "ו": [
        "חזרה ובסוס מיומנויות ה'", "פעיל-סביל", "נוכח-נסתר",
        "סיכום ומיזוג בין 2 טקסטים", "כתיבת פסקה תחת נושא",
        "הכללה ופירוט", "טקסט רב-היצגי",
    ],
}


def get_learning_skills(grade: str) -> List[str]:
    """Return the official learning skills list for a given grade."""
    g = grade.replace("׳", "").replace("'", "").replace("כיתה", "").strip()
    if "-" in g or "–" in g:
        parts = g.replace("–", "-").split("-")
        result: List[str] = []
        for p in parts:
            result += LEARNING_SKILLS_BY_GRADE.get(p.strip(), [])
        return list(dict.fromkeys(result))
    return LEARNING_SKILLS_BY_GRADE.get(g, [])
