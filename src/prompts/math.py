from typing import Any, Dict, List
from ..config import get_grade_level, get_curriculum_profile


def _math_curric_note(grade: str, topic: str) -> str:
    cp = get_curriculum_profile(grade, "מתמטיקה")
    if not cp:
        return ""
    parts = []
    key_concepts = cp.get("key_concepts", [])
    if key_concepts:
        parts.append(f"מושגי מפתח בתכנית הלימודים: {', '.join(key_concepts[:5])}")
    prior = cp.get("expected_prior_knowledge", "")
    if prior:
        parts.append(f"ידע קודם מוכר: {prior}")
    avoid = cp.get("avoid_in_content", "")
    if avoid:
        parts.append(f"יש להימנע מ: {avoid}")
    if not parts:
        return ""
    body = "\n".join(f"• {p}" for p in parts)
    return f"\n<curriculum_context>\n{body}\n</curriculum_context>\n"


def build_math_roadmap_prompt(subject: str, topic: str, grade: str, rounds: int) -> str:
    gl = get_grade_level(grade)
    curric = _math_curric_note(grade, topic)
    return f"""אתה מתכנן יחידת לימוד בשיטת **מתמטיקה יומית** מבית א"ל השד"ה.

<user_input>
מקצוע: {subject} | נושא: {topic}
כיתה: {grade} | גיל: {gl['age']} | מספר סבבים: {rounds}
</user_input>
{curric}
**ארבע תחנות מתמטיקה יומית — כל תחנה ברמת חשיבה אחרת:**
1. **מתמטיקה בעצמי** (🔴 אדום) — שיום, ידע וזיהוי — "מה זה?" — המילה המתמטית — עצמאי לחלוטין, קינסטטי
2. **מתמטיקה עם חבר** (🔵 כחול) — חשיבה אלגוריתמית — "איך עושים את זה?" — המשפט המתמטי — זוגי, משחק
3. **קבוצת ניצ"ה** (🟢 ירוק) — חשיבה תהליכית-פרוצדורלית — "מה הסיפור השלם?" — בעיות מציאות רב-שלביות
4. **מתמטיקה עם המורה** (🟡 צהוב) — חיפוש פתוח והנמקה — "למה?" — **הקנייה ראשונית בלבד בתחנה זו**

**חוקי ברזל:**
1. כל 4 תחנות **עצמאיות לחלוטין** — תלמיד יכול להתחיל בכל תחנה; לא תלוי בתחנות אחרות
2. **הסבב האחרון תמיד = מדידה, בקרה והערכה** (is_assessment: true בתחנות)
3. **כל סבב חייב להיות נדבכי** — מרחיב את הסבב הקודם על ציר אחד ברור (תחום מספרים / מורכבות מושג / עומק יישום)
4. הקנייה — **תחנת המורה בלבד**; שאר התחנות עצמאיות לחלוטין
5. בתחנת "עם חבר" — משחק הוא ברירת מחדל, עם תפקידים מתחלפים ובקרה הדדית
6. טווח סבבים: 3-8; גיאומטריה עד 4, שברים עד 8; ברירת מחדל: {rounds}

**ציר הנדבכיות:** בחר ציר אחד וצעד עליו בכל סבב (דוגמה: תחום 100 → תחום 1,000 → תחום רבבה → הערכה)

**פורמט פלט — JSON בלבד:**
{{
  "unit_title": "שם היחידה",
  "is_math": true,
  "layering_axis": "ציר הנדבכיות: [תחום מספרים / מורכבות מושג / עומק יישום]",
  "curriculum_anchor": "עיגון בתכנית לימודים של משרד החינוך לכיתה {grade}",
  "learning_goals": {{
    "knowledge": ["ידע 1", "ידע 2"],
    "skills": ["מיומנות 1", "מיומנות 2"],
    "values": ["הרגל/ערך 1"]
  }},
  "rounds": [
    {{
      "round": 1,
      "layer_label": "נדבך זה — תיאור קצר (למשל: בתחום ה-100)",
      "myself": {{
        "description": "תיאור קצר: מה עושים בתחנת בעצמי בסבב זה",
        "task_type": "flash_cards / number_board / dice_solo / self_check_cards"
      }},
      "friend": {{
        "description": "תיאור קצר: שם המשחק הזוגי ומה עושים",
        "task_type": "dice_game / memory_game / mutual_check / estimation_game"
      }},
      "nitzah": {{
        "description": "תיאור קצר: סוג הבעיה המציאותית הרב-שלבית",
        "task_type": "real_world_problem / competition_puzzle / open_investigation"
      }},
      "teacher": {{
        "description": "תיאור קצר: נושא ההקנייה ומשימת פתיחה",
        "acquisition_topic": "הנושא שהמורה מלמדת בתחנה זו",
        "is_assessment": false
      }}
    }}
  ]
}}

**חשוב:** הסבב האחרון (סבב {rounds}) חייב לכלול `"is_assessment": true` בכל ארבע התחנות."""


def build_math_comprehension_prompt(subject: str, topic: str, grade: str,
                                     round_num: int, total_rounds: int,
                                     round_plan: Dict, prev_texts: List[str]) -> str:
    gl = get_grade_level(grade)
    curric = _math_curric_note(grade, topic)
    myself_plan = round_plan.get('myself', round_plan.get('comprehension', {}))
    layer_label = round_plan.get('layer_label', '')
    task_type = myself_plan.get('task_type', 'self_check_cards')
    task_desc = myself_plan.get('description', '')
    is_assessment = myself_plan.get('is_assessment', round_num == total_rounds)

    return f"""צור דף משימה לתחנת **מתמטיקה בעצמי** (🔴) בשיטת מתמטיקה יומית.

<user_input>
מקצוע: {subject} | נושא: {topic}
כיתה: {grade} | גיל: {gl['age']} | סבב {round_num} מתוך {total_rounds}
נדבך: {layer_label} | סוג משימה: {task_type}
תיאור: {task_desc}
{"⚠️ סבב הערכה — כל המשימות הן בקרה והערכה עצמית" if is_assessment else ""}{curric}
</user_input>

**חוקי תחנת מתמטיקה בעצמי:**
1. עצמאי לחלוטין — ניתן לבצע ולבדוק ללא מורה (מנגנון בקרה עצמית חובה)
2. קינסטטי — כרטיסיות לגזירה, לוח מאה, קוביות, הפיכות ובדיקה עצמית
3. רמת חשיבה: שיום, ידע וזיהוי — "מה זה?" ולא "איך מחשבים?"
4. כל משימה חייבת שלושה רכיבים: הוראה מפורשת + דוגמה פתורה + כלל גנרי
5. שלוש רמות רמזור: ירוק (קל) / צהוב (בינוני) / אדום (מאתגר)
6. לא צריך מורה בשום שלב

**פורמט פלט — JSON בלבד (כל הטקסט בעברית):**
{{
  "section_title": "מתמטיקה בעצמי — {layer_label}",
  "intro_sentence": "הוראה מפורשת: [מה עושים, בלשון ציווי פשוטה]",
  "paragraphs": [
    {{
      "subtitle": "📌 הוראה מפורשת",
      "text": "[הוראה ברורה ופשוטה מה לעשות — לשון ציווי, משפט אחד לפעולה]",
      "key_terms": ["מונח מתמטי 1", "מונח מתמטי 2"]
    }},
    {{
      "subtitle": "✏️ דוגמה פתורה",
      "text": "[מודלינג מלא: ממחיש את ביצוע המשימה עם מספרים ספציפיים, שלב אחרי שלב]",
      "key_terms": []
    }},
    {{
      "subtitle": "📐 הכלל הגנרי",
      "text": "[החוק או העיקרון המתמטי שהמשימה מתרגלת — בניסוח שתלמיד מבין]",
      "key_terms": []
    }}
  ],
  "all_key_terms": ["מושגים מתמטיים מרכזיים (3-6 מושגים)"],
  "difficulty_levels": {{
    "green": "גרסה קלה: [תיאור משימה ירוקה + ערכי מספרים קטנים יותר]",
    "yellow": "גרסה בינונית: [תיאור משימה צהובה]",
    "red": "גרסה מאתגרת: [תיאור משימה אדומה + ערכים מורכבים יותר]"
  }},
  "discussion_starters": [
    "✓ בדוק/בדקי: [שאלת בקרה עצמית 1 — האם ביצעתי נכון?]",
    "✓ בדוק/בדקי: [שאלת בקרה עצמית 2]",
    "✓ בדוק/בדקי: [שאלת בקרה עצמית 3 — בדיקת התשובה]"
  ],
  "cutout_cards": {"true" if task_type in ["flash_cards", "self_check_cards", "memory_game"] else "false"},
  "card_pairs": [
    {{"term": "צד א (שאלה/מושג/תרגיל)", "definition": "צד ב (תשובה/הגדרה/פתרון)"}},
    {{"term": "...", "definition": "..."}}
  ],
  "is_math_myself": true
}}"""


def build_math_methods_prompt(subject: str, topic: str, grade: str,
                               round_num: int, round_plan: Dict,
                               comprehension_text: Dict) -> str:
    gl = get_grade_level(grade)
    curric = _math_curric_note(grade, topic)
    friend_plan = round_plan.get('friend', round_plan.get('methods', {}))
    layer_label = round_plan.get('layer_label', '')
    task_type = friend_plan.get('task_type', 'dice_game')
    task_desc = friend_plan.get('description', '')
    is_assessment = friend_plan.get('is_assessment', False)

    math_terms = comprehension_text.get('all_key_terms', [])
    math_context = comprehension_text.get('section_title', '')

    return f"""צור דף משימה לתחנת **מתמטיקה עם חבר** (🔵) בשיטת מתמטיקה יומית.

<user_input>
מקצוע: {subject} | נושא: {topic}
כיתה: {grade} | גיל: {gl['age']} | סבב {round_num}
נדבך: {layer_label} | סוג משימה: {task_type}
תיאור: {task_desc}
מושגים מהסבב: {', '.join(math_terms[:6])} | הקשר: {math_context}
{"⚠️ סבב הערכה — משימות בקרה זוגית" if is_assessment else ""}{curric}
</user_input>

**חוקי תחנת מתמטיקה עם חבר:**
1. זוגי תמיד — תפקידים מתחלפים ובקרה הדדית מובנית (לא יחיד!)
2. משחק הוא ברירת מחדל — זיכרון, קוביות, אומדן משותף, בדיקה הדדית
3. רמת חשיבה: אלגוריתמית — "איך עושים את זה?" בשיח עם חבר
4. כל משימה: הוראה מפורשת + דוגמה פתורה + כלל גנרי
5. שלוש רמות רמזור עם תפקידים מפורשים לכל אחד
6. חובה: מנגנון בקרה הדדית — "החבר בודק ואנחנו מחליפים"

**פורמט פלט — JSON בלבד (כל הטקסט בעברית):**
{{
  "main_instruction": "🎮 [הוראת המשחק הזוגי — מה עושים, מי מתחיל, איך מחליפים תפקידים]",
  "context_prompt": "[הנחיה: ספציפי מה הזוג מבצע יחד — שם המשחק ותיאורו]",
  "words_range": "[מספר הסבבים/תרגילים לכל שחקן]",
  "pair_roles": {{
    "role_a": "שחקן א — [מה הוא עושה]",
    "role_b": "שחקן ב — [מה הוא עושה ובודק]",
    "switch": "מחליפים תפקידים לאחר [X] סבבים"
  }},
  "difficulty_levels": {{
    "green": "גרסה קלה: [תיאור — מספרים קטנים, פעולה פשוטה]",
    "yellow": "גרסה בינונית: [תיאור]",
    "red": "גרסה מאתגרת: [תיאור — מספרים גדולים, צעד נוסף]"
  }},
  "guiding_questions": [
    "❓ שאל/שאלי את החבר/ה: [שאלה לוודא הבנה]",
    "❓ איך ידעת? הסבר/הסבירי לחבר/ה..."
  ],
  "scaffold_template": "[תבנית/מבנה המשחק — שלבים, כרטיסיות, מה כותבים]",
  "self_review_checklist": [
    "☑ שנינו הסברנו זה לזה את הפתרון",
    "☑ בדקנו יחד את התשובות",
    "☑ החלפנו תפקידים לפחות פעם אחת"
  ],
  "is_math_friend": true
}}"""


def build_math_precision_prompt(subject: str, topic: str, grade: str,
                                 round_num: int, round_plan: Dict,
                                 key_terms: List[str]) -> str:
    gl = get_grade_level(grade)
    curric = _math_curric_note(grade, topic)
    nitzah_plan = round_plan.get('nitzah', round_plan.get('precision', {}))
    layer_label = round_plan.get('layer_label', '')
    task_type = nitzah_plan.get('task_type', 'real_world_problem')
    task_desc = nitzah_plan.get('description', '')
    is_assessment = nitzah_plan.get('is_assessment', False)

    return f"""צור דף משימה לתחנת **קבוצת ניצ"ה — נצא מהקופסה** (🟢) בשיטת מתמטיקה יומית.

<user_input>
מקצוע: {subject} | נושא: {topic}
כיתה: {grade} | גיל: {gl['age']} | סבב {round_num}
נדבך: {layer_label} | סוג משימה: {task_type}
תיאור: {task_desc}
מושגים: {', '.join(key_terms[:6])}
{"⚠️ סבב הערכה — בעיות בקרה ומדידה" if is_assessment else ""}{curric}
</user_input>

**חוקי תחנת ניצ"ה:**
1. בעיות מציאותיות רב-שלביות — "הסיפור המתמטי" — יישום ותובנה
2. קישור בין מושגים והתאמת מודל מתמטי לסיטואציה
3. "מצאו את הנעלם", חידות קנגורו/טימס, בעיות חיי יומיום
4. כל משימה: הוראה מפורשת + דוגמה פתורה + כלל גנרי
5. שלוש רמות רמזור
6. חובה: תיבת "למורה" עם מטרה פדגוגית ומקור אקדמי אם רלוונטי
7. שאלות פתוחות: "האם יש פתרון נוסף? הסבר/הסבירי."

**פורמט פלט — JSON בלבד (כל הטקסט בעברית):**
{{
  "title": "ניצ\"ה: [כותרת המשימה המציאותית]",
  "main_instruction": "📌 [הוראה מפורשת — מה עושים, לשון ציווי]",
  "is_math_nitzah": true,
  "formula": {{
    "explicit_instruction": "הוראה מפורשת: [מה עושים]",
    "solved_example": "דוגמה פתורה: [מספרים ספציפיים, שלב אחרי שלב]",
    "generic_rule": "הכלל הגנרי: [החוק המתמטי]"
  }},
  "context": "[הקשר מציאותי מושך שמציג את הבעיה — סיפור קצר]",
  "difficulty_levels": {{
    "green": "🟢 קל: [גרסה קלה של הבעיה]",
    "yellow": "🟡 בינוני: [גרסה בינונית]",
    "red": "🔴 מאתגר: [גרסה מורכבת, רב-שלבית]"
  }},
  "open_question": "האם יש פתרון נוסף? [שאלה פתוחה]",
  "exercises": [
    {{
      "title": "🔵 שלב א",
      "instruction": "[הוראה לשלב זה]",
      "items": [
        {{"question": "שאלה 1 (שלב ראשון בבעיה)", "answer": "תשובה מלאה עם דרך"}},
        {{"question": "שאלה 2", "answer": "תשובה מלאה עם דרך"}}
      ]
    }}
  ],
  "teacher_note": {{
    "pedagogical_goal": "מטרה: [מה מטרת המשימה פדגוגית]",
    "hints": ["רמז 1 לתלמיד מתקשה", "רמז 2"],
    "discussion_extensions": ["שאלת הרחבה לדיון בכיתה"],
    "academic_source": "[מקור אקדמי/תחרות אם רלוונטי, אחרת null]"
  }},
  "answer_key": "[פתרון מלא עם דרך הפתרון לכל רמות הרמזור]"
}}"""


def build_math_vocabulary_prompt(subject: str, topic: str, grade: str,
                                  round_num: int, round_plan: Dict,
                                  key_terms: List[str],
                                  used_activity_types: List[str]) -> str:
    gl = get_grade_level(grade)
    curric = _math_curric_note(grade, topic)
    teacher_plan = round_plan.get('teacher', round_plan.get('vocabulary', {}))
    layer_label = round_plan.get('layer_label', '')
    acquisition_topic = teacher_plan.get('acquisition_topic', topic)
    task_desc = teacher_plan.get('description', '')
    is_assessment = teacher_plan.get('is_assessment', round_num == int(round_plan.get('round', round_num)) and False)

    return f"""צור דף משימה לתחנת **מתמטיקה עם המורה** (🟡) בשיטת מתמטיקה יומית.

<user_input>
מקצוע: {subject} | נושא: {topic}
כיתה: {grade} | גיל: {gl['age']} | סבב {round_num}
נדבך: {layer_label} | נושא ההקנייה: {acquisition_topic}
תיאור: {task_desc}
מושגים: {', '.join(key_terms[:6])}
{"⚠️ סבב הערכה — משימות בקרה ומדידה עם הנמקה" if is_assessment else ""}{curric}
</user_input>

**חוקי תחנת מתמטיקה עם המורה:**
1. זו **תחנת ההקנייה הבלעדית** — המורה מקנה בקבוצות קטנות (20 דקות)
2. המורה שואלת "למה?" ומנחה להנמקה — לא רק "מה?" ו"איך?"
3. מודל ק.צ.פ.ת: קוראים ומסבירים → צובעים נתונים → פותרים → תשובה מילולית מלאה
4. כרטיסיות רמזור מוכנות מראש (ירוק/צהוב/אדום)
5. אין הפרעות מבחוץ בזמן הקנייה
6. כל משימה: הוראה מפורשת + דוגמה פתורה + כלל גנרי
7. אם סבב הערכה: כל המשימות = הערכה ובקרה עצמית עם הנמקה

**פורמט פלט — JSON בלבד (כל הטקסט בעברית):**
{{
  "title": "מתמטיקה עם המורה — {acquisition_topic}",
  "is_math_teacher": true,
  "activity_type": "math_teacher",
  "acquisition_topic": "{acquisition_topic}",
  "opening_task": "💛 משימת פתיחה: [משימה קצרה שמורה מציגה לפתיחת ההקנייה]",
  "ktzpt_model": {{
    "k": "ק — קוראים ומסבירים: [מה קוראים/מסבירים בבעיה זו]",
    "tz": "צ — צובעים/מסמנים: [אילו נתונים מסמנים בבעיה]",
    "p": "פ — פותרים ומחשבים: [הפתרון שלב אחרי שלב]",
    "t": "ת — תשובה מילולית: [תבנית תשובה מילולית מלאה]"
  }},
  "formula": {{
    "explicit_instruction": "[הוראה מפורשת]",
    "solved_example": "[דוגמה פתורה מלאה עם דרך]",
    "generic_rule": "[הכלל הגנרי — למה זה עובד]"
  }},
  "difficulty_levels": {{
    "green": "🟢 קל: [בעיה קלה למודל ק.צ.פ.ת]",
    "yellow": "🟡 בינוני: [בעיה בינונית]",
    "red": "🔴 מאתגר: [בעיה מאתגרת עם שאלת 'למה?']"
  }},
  "why_question": "💭 למה: [שאלת הנמקה — למה הנוסחה/השיטה עובדת?]",
  "words": [
    {{"word": "מונח מתמטי 1", "definition": "הגדרה פשוטה"}},
    {{"word": "מונח מתמטי 2", "definition": "הגדרה פשוטה"}}
  ],
  "answer_key": "[פתרון מלא לכל שלושת רמות הרמזור + תשובה לשאלת 'למה?']"
}}"""


def build_math_teacher_prep_prompt(subject: str, topic: str, grade: str,
                                    round_num: int, content: Dict) -> str:
    gl = get_grade_level(grade)

    myself_data = content.get('comprehension', {})
    friend_data = content.get('methods', {})
    nitzah_data = content.get('precision', {})
    teacher_data = content.get('vocabulary', {})

    myself_title = myself_data.get('section_title', 'מתמטיקה בעצמי')
    friend_title = friend_data.get('main_instruction', 'מתמטיקה עם חבר')[:60]
    nitzah_title = nitzah_data.get('title', 'ניצ"ה')
    teacher_title = teacher_data.get('title', 'מתמטיקה עם המורה')
    acquisition_topic = teacher_data.get('acquisition_topic', topic)
    cutout_cards = myself_data.get('cutout_cards', True)

    return f"""צור מדריך הכנה למורה לסבב {round_num} ביחידת מתמטיקה יומית.

<user_input>
מקצוע: {subject} | נושא: {topic}
כיתה: {grade} | גיל: {gl['age']} | סבב {round_num}
תחנת בעצמי: {myself_title}
תחנת עם חבר: {friend_title}
תחנת ניצ"ה: {nitzah_title}
תחנת המורה: {teacher_title} | נושא הקנייה: {acquisition_topic}
כרטיסיות לגזירה: {"כן" if cutout_cards else "לא"}
</user_input>

**המדריך מיועד למורה ללא הכשרה מתמטית מקיפה — חייב להיות ברור להפעלה מיידית.**

**פורמט פלט — JSON בלבד (כל הטקסט בעברית):**
{{
  "objectives": {{
    "knowledge": ["ידע 1: ...", "ידע 2: ..."],
    "skills": ["מיומנות 1: ...", "מיומנות 2: ..."],
    "values": ["הרגל 1: ..."]
  }},
  "printing_list": [
    "כיתה {grade}: הדפס X עותקים של דף 'מתמטיקה בעצמי'",
    "כיתה {grade}: הדפס X עותקים של דף 'עם חבר'",
    "כיתה {grade}: הדפס X עותקים של דף 'ניצ\"ה'",
    "כיתה {grade}: הדפס X עותקים של דף 'עם המורה'"
  ],
  "cutting_prep": {"['חתוך מראש: כרטיסיות הברקה — צלע כפולה לחיסכון', 'מיין לשקיות לפי כיתה']" if cutout_cards else "['אין חיתוך בסבב זה']"},
  "materials": {{
    "comprehension": ["חומרים לתחנת בעצמי: ..."],
    "methods": ["חומרים לתחנת עם חבר: קוביות (זוג לכל שניים), ..."],
    "precision": ["חומרים לניצ\"ה: כרטיסיות בעיות, אמצעי עזר מתמטיים..."],
    "vocabulary": ["חומרים לתחנת המורה: {acquisition_topic} — שטרות מודפסים / לוח מחיק / קוביות / ..."]
  }},
  "teacher_station_topic": "{acquisition_topic}",
  "teacher_opening_task": "משימת פתיחה: [המורה מציגה ...]",
  "traffic_light_cards_prep": "הכן/י 3 כרטיסיות רמזור לכל תלמיד: ירוק / צהוב / אדום",
  "timing": {{
    "comprehension": "20 דקות — מתמטיקה בעצמי",
    "methods": "20 דקות — מתמטיקה עם חבר",
    "precision": "20 דקות — קבוצת ניצ\"ה",
    "vocabulary": "20 דקות — מתמטיקה עם המורה (הקנייה)"
  }},
  "anticipated_difficulties": [
    {{
      "difficulty": "קושי צפוי 1: [מה תלמידים עשויים להתקשות]",
      "generic_response": "פתרון גנרי: [מה המורה אומרת/עושה — ניסוח מדויק]"
    }},
    {{
      "difficulty": "קושי צפוי 2: ...",
      "generic_response": "פתרון גנרי: ..."
    }}
  ],
  "teacher_notes": [
    "הוראה: אל תפריעי לתחנות העצמאיות — הן צריכות להיות שקטות ועצמאיות",
    "הוראה: הקנייה בתחנת המורה — קבוצות של 4-6 תלמידים בלבד"
  ],
  "differentiation": {{
    "struggling": "לתלמידים מתקשים: [כיצד לתמוך]",
    "advanced": "לתלמידים מתקדמים: [אתגר נוסף]",
    "special_needs": "לחינוך מיוחד: [התאמות נדרשות]"
  }}
}}"""
