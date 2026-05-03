from typing import Any, Dict, List
from ..config import get_grade_level


def build_roadmap_prompt(subject: str, topic: str, grade: str, rounds: int) -> str:
    gl = get_grade_level(grade)
    return f"""אתה מתכנן יחידת לימוד בשיטת א"ל השד"ה (הבנה, שיטות, דיוק, הרחבת אוצר מילים).

<user_input>
נושא: {subject} — {topic}
כיתה: {grade} | גיל: {gl['age']} | רמת שפה: {gl['language']}
מספר סבבים: {rounds}
</user_input>

**חוקי ברזל:**
1. כל 4 תחנות בכל סבב — **עצמאיות לחלוטין** (תלמיד יכול להתחיל בכל אחת)
2. תחנת הבנה = טקסט עשיר לקריאה + דיון בעל פה בלבד, ללא כתיבה
3. תחנת שיטות = כתיבה מובנית ומדורגת — המורה נמצאת פה פיזית
4. תחנת דיוק = לשון ודקדוק טכני (מגוון: הכתבות, שורשים, בניינים, מאזכרים, הומופוניות, זמנים, גופים)
5. תחנת אוצר מילים = **חוויה ופעולה** — פיזית או מודפסת, לפי מה שמתאים לנושא
6. תחנת הבנה: חייב להתחיל עם טקסט סיפורי, לא לחזור על אותו טקסט בסבבים
7. שלב ב-STEAM: שלב רב-תחומיות אמיתית (מדע/טכנולוגיה/אמנות/מתמטיקה) איפה שמתאים
8. הפעילויות מתקדמות מסבב לסבב: מבוא → העמקה → שיא

**סוגי כתיבה לתחנת שיטות (בחר לפי גיל וסבב):**
טיעון (בעד/נגד), תיאור (דמות/מקום/אירוע), תשובה מיטבית, סיכום, מיזוג, חוות דעת,
דוח (ניסוי/חקר/תצפית), מכתב (א-ב), שיר קצר (א-ב), יומן אישי (ג ומעלה), ניתוח טקסט מידעי (ה-ו), תרשים זרימה

**סוגי פעילות לתחנת אוצר מילים:**
מודפסות: matching_cards, sorting_table, dominoes, fill_in_poster, clothesline, idiom_cards, definition_table, crossword_mini
פיזיות/חווייתיות: physical_plasticine (פיסול מילה), physical_model (בניית מודל), physical_game (משחק קלפים/התאמה), physical_poster (כרזה/תערוכה), physical_simulation (משחק תפקידים/סימולציה)

**אפשרויות לפי גיל {gl['age']}:**
- הבנה: {', '.join(gl['comprehension_options'])}
- שיטות: {', '.join(gl['methods_options'])}
- דיוק: {', '.join(gl['precision_options'])}
- אוצר מילים: {', '.join(gl['vocabulary_options'])}

**פורמט פלט — JSON בלבד:**
{{
  "unit_title": "שם היחידה",
  "central_text_type": "סוג הטקסט המרכזי",
  "steam_connections": ["חיבור STEAM 1", "חיבור STEAM 2"],
  "learning_goals": {{
    "knowledge": ["ידע 1", "ידע 2"],
    "skills": ["מיומנות 1", "מיומנות 2"],
    "values": ["ערך/הרגל 1", "ערך/הרגל 2"]
  }},
  "rounds": [
    {{
      "round": 1,
      "comprehension": {{
        "text_type": "סיפורי/מידעי/רב-היצגי",
        "description": "תיאור קצר של הטקסט",
        "discussion_focus": "מי/מה/מדוע/קונפליקט/דילמה"
      }},
      "methods": {{
        "writing_type": "סוג הכתיבה מהרשימה",
        "description": "תיאור המשימה"
      }},
      "precision": {{
        "activity_type": "הכתבה/שורשים/בניינים/מאזכרים/זמנים/גופים/הומופוניות/רצף משפטים",
        "description": "תיאור"
      }},
      "vocabulary": {{
        "activity_type": "סוג הפעילות (מודפסת או פיזית)",
        "is_physical": false,
        "description": "תיאור"
      }}
    }}
  ]
}}"""


def build_comprehension_prompt(subject: str, topic: str, grade: str,
                                round_num: int, total_rounds: int,
                                round_plan: Dict, prev_texts: List[str]) -> str:
    gl = get_grade_level(grade)
    prev = ""
    if prev_texts:
        prev = f"\n\n**טקסטים קודמים (אל תחזור על תוכן זה):**\n" + "\n".join(prev_texts[-2:])

    text_type = round_plan.get('comprehension', {}).get('text_type', 'סיפורי')
    text_desc = round_plan.get('comprehension', {}).get('description', '')
    disc_focus = round_plan.get('comprehension', {}).get('discussion_focus', 'קונפליקט ודילמה')

    return f"""כתוב טקסט לתחנת ההבנה בשיטת א"ל השד"ה.

<user_input>
נושא: {subject} — {topic}
כיתה: {grade} | גיל: {gl['age']} | שפה: {gl['language']}
סבב {round_num} מתוך {total_rounds} | סוג טקסט: {text_type} | תכנון: {text_desc}
מוקד הדיון: {disc_focus}{prev}
</user_input>

**אפשרויות פעילות לתחנת הבנה לגיל זה:** {', '.join(gl['comprehension_options'])}

**⚠️ חוקים קריטיים:**
1. **אורך: {gl['text_length']}** — אל תקצר! זה טקסט לקריאה בעל פה, חייב להיות ארוך ועשיר
2. **אל תכלול שאלות בגוף הטקסט** — התחנה כולה בעל פה, הדיון הוא בין התלמידים
3. כלול 8-12 **מונחי מפתח** — מודגשים בטקסט
4. חלק ל-4-6 פסקאות עם כותרות משנה
5. כל פסקה לפחות 80 מילים
6. כל מושג חדש — הסבר בסוגריים בתוך הטקסט
7. שלב: {'רקע, הכרת הדמויות/המצב' if round_num == 1 else 'המשך ישיר, העמקה' if round_num < total_rounds else 'שיא, קונפליקט, סיום'}

**שאלות הדיון בעל פה (חמשת הממים + עומק):**
כלול 4-5 שאלות מדורגות:
- רמה 1: מי/מה/מתי/איפה (עובדתי)
- רמה 2: מדוע/כיצד (ניתוח)
- רמה 3: דילמה, קונפליקט, ערך ("מה היית עושה אם...")

**פורמט פלט — JSON בלבד:**
{{
  "section_title": "כותרת הסבב",
  "intro_sentence": "משפט פתיחה מרתק (שאלה רטורית / מצב מסקרן)",
  "paragraphs": [
    {{
      "subtitle": "כותרת משנה",
      "text": "טקסט הפסקה (מינימום 80 מילים)",
      "key_terms": ["מונח1", "מונח2"]
    }}
  ],
  "all_key_terms": ["כל המונחים המרכזיים (8-12)"],
  "discussion_starters": [
    "שאלת עובדה (מי/מה/מתי)",
    "שאלת ניתוח (מדוע/כיצד)",
    "שאלת דילמה / ערך / קונפליקט",
    "שאלה פתוחה להרחבה",
    "שאלת סיכום והפנמה"
  ]
}}"""


def build_methods_prompt(subject: str, topic: str, grade: str,
                          round_num: int, round_plan: Dict,
                          comprehension_text: Dict) -> str:
    gl = get_grade_level(grade)
    writing_type = round_plan.get('methods', {}).get('writing_type', 'תשובה מיטבית')
    methods_desc = round_plan.get('methods', {}).get('description', '')
    key_terms = comprehension_text.get('all_key_terms', [])

    text_summary = comprehension_text.get('section_title', '') + ": "
    for p in comprehension_text.get('paragraphs', [])[:2]:
        text_summary += p.get('text', '')[:200] + "... "

    return f"""צור משימת כתיבה מובנית לתחנת השיטות — א"ל השד"ה.

<user_input>
נושא: {subject} — {topic} | סבב {round_num}
כיתה: {grade} | גיל: {gl['age']}
סוג הכתיבה: {writing_type} | תכנון: {methods_desc}
מונחים מהטקסט: {', '.join(key_terms[:8])}
הקשר הטקסט: {text_summary[:300]}
</user_input>

**סוגי כתיבה אפשריים ודרישותיהם:**
- טיעון: עמדה + 3 נימוקים + סיכום, כיתה ד ומעלה
- תיאור: דמות/מקום/אירוע — חושים + פרטים + תחושות
- תשובה מיטבית: מבוססת טקסט, מלאה ומפורטת
- סיכום: רעיונות מרכזיים, בלי העתקה
- חוות דעת: עמדה אישית מנומקת + דוגמאות
- דוח: מבנה מדעי — שאלה, שיטה, ממצאים, מסקנות
- מכתב: פנייה, גוף, סיום — א-ב
- יומן אישי: קול אישי, רגשות, אירועים — ג ומעלה
- מיזוג: שילוב מידע מ-2+ מקורות לטקסט חדש
- ניתוח טקסט מידעי: מבנה + מסר + שכנוע — ה-ו

**אפשרויות סוגי כתיבה לגיל זה:** {', '.join(gl['methods_options'])}

**חוקים:**
1. המשימה מובנית ומדורגת — ניתן לפגום (scaffold) לתלמידים חלשים
2. כלול: הוראה ברורה + דוגמה/תבנית + שאלות מנחות
3. מותאם לגיל {gl['age']} ולדרישות משרד החינוך
4. כלול 3 רמות קושי (רמזור ירוק/צהוב/אדום) לאותה משימה בדיוק

**פורמט פלט — JSON בלבד:**
{{
  "title": "שם המשימה",
  "writing_type": "{writing_type}",
  "main_instruction": "הוראה ראשית ברורה לתלמיד",
  "context_prompt": "השאלה/הנושא שעליו כותבים",
  "scaffold_template": "תבנית/פיגום לכתיבה (כותרת, מבנה, משפטי פתיחה מוצעים)",
  "guiding_questions": [
    "שאלה מנחה 1",
    "שאלה מנחה 2",
    "שאלה מנחה 3"
  ],
  "difficulty_levels": {{
    "green": "משימה בסיסית (לתלמידים שמתקשים) — היקף קצר, תבנית נתונה",
    "yellow": "המשימה הרגילה — עצמאות חלקית",
    "red": "הרחבה לתלמידים מתקדמים — יצירתיות, עומק, היקף גדול"
  }},
  "words_range": "X-Y מילים",
  "lines_needed": 10,
  "success_criteria": ["קריטריון 1", "קריטריון 2", "קריטריון 3"]
}}"""


def build_precision_prompt(subject: str, topic: str, grade: str,
                            round_num: int, round_plan: Dict,
                            key_terms: List[str]) -> str:
    gl = get_grade_level(grade)
    activity_type = round_plan.get('precision', {}).get('activity_type', 'הכתבה ושורשים')
    precision_desc = round_plan.get('precision', {}).get('description', '')

    return f"""צור פעילות לתחנת הדיוק (לשון ודקדוק) — א"ל השד"ה.

<user_input>
נושא: {subject} — {topic} | סבב {round_num}
כיתה: {grade} | גיל: {gl['age']}
סוג הפעילות: {activity_type} | תכנון: {precision_desc}
מילים מהטקסט: {', '.join(key_terms[:12])}
מספר מילים להכתבה לגיל זה: {gl['dictation_words']}
</user_input>

**ארגז הכלים הלשוני המלא — בחר מגוון:**
- הכתבה: מילים ומשפטים מהטקסט
- מאזכרים: שם עצם / פועל / תואר — זיהוי וסיווג
- זמנים: עבר / הווה / עתיד — המרה
- גופים: ראשון/שני/שלישי, יחיד/רבים, זכר/נקבה
- יחיד ורבים: שם עצם ← שינוי צורה
- זכר ונקבה: התאמה
- שורשים ומשפחות מילים: חילוץ שורש, בניית משפחה
- בניינים: קל / פיעל / הפעיל / התפעל — זיהוי ושימוש
- אותיות הומופוניות: ט/ת, ח/כ, כ/ק, כ/ה, ע/א — מילוי
- סוגי משפטים: חיווי / שאלה / פקודה / קריאה
- רצף משפטים: סידור משפטים להקשר הגיוני
- חיבור מילים למשפט תקין
- נכון/לא נכון: בדיקת משפטים לשוניים

**אפשרויות פעילות לתחנת דיוק לגיל זה:** {', '.join(gl['precision_options'])}

**חוקים:**
1. כל המילים/משפטים — **מהטקסט** שנקרא בתחנת ההבנה
2. לכלול {gl['dictation_words']} מילים להכתבה
3. לכלול **2-3 סוגי תרגילים שונים** — לא רק הכתבה
4. הכל טכני-לשוני (לא שאלות הבנה)
5. מגוון: כל סבב — סוגי תרגילים שונים מהסבב הקודם

**פורמט פלט — JSON בלבד:**
{{
  "title": "שם הפעילות",
  "activity_type": "{activity_type}",
  "dictation_list": [
    {{"word": "מילה", "difficulty": "קל/בינוני/קשה", "note": "הערה אם צריך"}}
  ],
  "exercises": [
    {{
      "type": "שורשים/מאזכרים/זמנים/גופים/בניינים/הומופוניות/רצף/...",
      "title": "כותרת התרגיל",
      "instruction": "הוראה לתלמיד",
      "items": [
        {{"question": "...", "answer": "..."}}
      ]
    }}
  ],
  "sentences_for_dictation": [
    "משפט 1 מהטקסט להכתבה",
    "משפט 2 מהטקסט להכתבה"
  ],
  "answer_key": "מפתח תשובות מלא"
}}"""


def build_vocabulary_prompt(subject: str, topic: str, grade: str,
                             round_num: int, round_plan: Dict,
                             key_terms: List[str], used_types: List[str]) -> str:
    gl = get_grade_level(grade)
    activity_type = round_plan.get('vocabulary', {}).get('activity_type', 'matching_cards')
    is_physical = round_plan.get('vocabulary', {}).get('is_physical', False)
    vocab_desc = round_plan.get('vocabulary', {}).get('description', '')

    physical_note = """
**⚠️ פעילות פיזית/חווייתית — הנחיות:**
התחנה הזו היא hands-on. המוצר הוא:
1. גיליון הוראות לתלמיד (מה לעשות, שלב אחרי שלב)
2. רשימת חומרים (מה צריך להכין)
3. קלפי מילים להדפסה וגזירה (אם צריך)
הפעילות חייבת לערב גוף, ידיים, תנועה — "מה שנצרב בעור נשמר לנצח"
""" if is_physical else ""

    return f"""צור פעילות לתחנת הרחבת אוצר מילים — א"ל השד"ה.

<user_input>
נושא: {subject} — {topic} | סבב {round_num}
כיתה: {grade} | גיל: {gl['age']}
סוג הפעילות: {activity_type} | תכנון: {vocab_desc}
מונחים מהטקסט: {', '.join(key_terms[:12])}
סוגים שכבר השתמשנו בהם: {', '.join(used_types) if used_types else 'אין'}
</user_input>
{physical_note}

**עקרון התחנה:** "מה שנצרב בעור נשמר לנצח" — זיכרון ויזואלי + שמיעתי + תחושתי-מוטורי

**סוגי פעילויות מודפסות:**
- matching_cards: קלפי התאמה לגזירה (מילה ↔ הגדרה)
- sorting_table: טבלת מיון לקטגוריות (גזור ↔ הדבק)
- dominoes: דומינו מילים לגזירה
- fill_in_poster: כרזה עם רווחים למילוי
- clothesline: חיבור זוגות עם קו (נרדפות/הפכים)
- idiom_cards: קלפי ביטויים + פירוש
- definition_table: מילה | הגדרה | משפט
- crossword_mini: תשבץ מיני

**סוגי פעילויות פיזיות/חווייתיות:**
- physical_plasticine: פיסול מילה/מושג בפלסטלינה/בצק — כולל הוראות + רשימת מילים לפיסול
- physical_model: בניית מודל/דיאגרמה מקרטון/קלפים — כולל הוראות + תוויות להדפסה
- physical_game: משחק קלפים/זכרון/דומינו/סולמות ונחשים — כולל לוח/קלפים מודפסים
- physical_poster: בניית כרזה/תערוכה — כולל שאלות מנחות + פריסת עיצוב
- physical_simulation: משחק תפקידים/סימולציה — כולל תפקידים + הוראות הנחיה
- physical_clothesline: "חבל כביסה" — תליית קלפי מילים + זוגות (נרדפות/הפכים)

**חוקים:**
1. הפעילות חווייתית ומגוונת — לא רק "כתוב משפט"
2. המילים/ביטויים: מהטקסט + מונחי נושא חדשים
3. כלול הוראות ברורות + בנק מילים אם רלוונטי
4. כל סבב — סוג שונה (אל תחזור על מה שבוצע)

**פורמט פלט — JSON בלבד:**
{{
  "title": "שם הפעילות",
  "activity_type": "סוג הפעילות",
  "is_physical": {str(is_physical).lower()},
  "instruction": "הוראה ברורה לתלמיד (שלב אחרי שלב לפיזית)",
  "materials_needed": ["חומר 1", "חומר 2"],
  "words": [
    {{
      "word": "מילה/ביטוי",
      "definition": "הגדרה קצרה",
      "example": "משפט דוגמה",
      "category": "קטגוריה (אם רלוונטי)",
      "partner": "נרדפת/הפך (אם רלוונטי)"
    }}
  ],
  "word_bank": ["מילה1", "מילה2"],
  "left_column": ["פריט1", "פריט2", "פריט3", "פריט4", "פריט5", "פריט6", "פריט7", "פריט8"],
  "right_column": ["זוג1", "זוג2", "זוג3", "זוג4", "זוג5", "זוג6", "זוג7", "זוג8"],
  "categories": ["קטגוריה1", "קטגוריה2", "קטגוריה3"],
  "fill_sentences": [
    {{"sentence": "משפט עם _____ חלל", "answer": "התשובה"}}
  ],
  "crossword_clues": [
    {{"direction": "מאונך/מאוזן", "number": 1, "clue": "רמז", "answer": "תשובה"}}
  ],
  "physical_steps": [
    "שלב 1: ...",
    "שלב 2: ...",
    "שלב 3: ..."
  ],
  "answer_key": "מפתח תשובות מלא"
}}"""


def build_teacher_prep_prompt(subject: str, topic: str, grade: str,
                               round_num: int, all_content: Dict) -> str:
    comp = all_content.get('comprehension', {})
    meth = all_content.get('methods', {})
    prec = all_content.get('precision', {})
    vocab = all_content.get('vocabulary', {})
    is_physical_vocab = vocab.get('is_physical', False)

    return f"""צור דף הכנה למורה לסבב {round_num} של יחידה בשיטת א"ל השד"ה.

<user_input>
נושא: {subject} — {topic} | כיתה: {grade} | סבב {round_num}
</user_input>

**תחנות הסבב:**
- הבנה: {comp.get('section_title', '')} ({len(comp.get('paragraphs', []))} פסקאות) — **תחנה בעל פה בלבד**, המורה לא נמצאת כאן
- שיטות: {meth.get('title', '')} — {meth.get('writing_type', '')} — **המורה יושבת כאן**
- דיוק: {prec.get('title', '')} — {prec.get('activity_type', '')}
- אוצר מילים: {vocab.get('title', '')} — {vocab.get('activity_type', '')} {'(פעילות פיזית — נדרשת הכנת חומרים)' if is_physical_vocab else '(מודפס)'}

**פורמט פלט — JSON בלבד:**
{{
  "objectives": {{
    "knowledge": ["ידע שיירכש 1", "ידע שיירכש 2"],
    "skills": ["מיומנות שתתפתח 1", "מיומנות 2"],
    "values": ["ערך/הרגל 1", "ערך/הרגל 2"]
  }},
  "steam_connections": ["חיבור בין-תחומי 1 (מדע/טכנולוגיה/אמנות/מתמטיקה)"],
  "materials": {{
    "comprehension": ["עותקי הטקסט לכל תלמיד", "..."],
    "methods": ["דף משימה", "..."],
    "precision": ["דף תרגילים", "..."],
    "vocabulary": ["חומרים נדרשים — במיוחד לפיזי: {', '.join(vocab.get('materials_needed', ['דפי הפעילות']))}"]
  }},
  "timing": {{
    "comprehension": "15-20 דקות",
    "methods": "20-25 דקות",
    "precision": "15-20 דקות",
    "vocabulary": "15-20 דקות"
  }},
  "rotation_tip": "הוראה לסיבוב קבוצות בין התחנות",
  "teacher_notes": [
    "נקודה חשובה לתחנת הבנה (בעל פה בלבד!)",
    "נקודה לתחנת שיטות (המורה כאן)",
    "קושי צפוי + פתרון מוצע",
    "הצעה להרחבה לתלמידים מתקדמים"
  ],
  "differentiation": {{
    "struggling": "איך לתמוך בתלמידים חלשים בכל תחנה",
    "advanced": "הרחבה לתלמידים חזקים",
    "special_needs": "התאמות לחינוך מיוחד"
  }},
  "self_check": [
    "האם כל תחנה עצמאית לחלוטין?",
    "האם תחנת הבנה ללא כתיבה?",
    "האם תחנת אוצר מילים hands-on/חווייתית?",
    "האם יש דיפרנציאציה מובנית?"
  ]
}}"""
