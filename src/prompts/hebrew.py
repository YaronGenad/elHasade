from typing import Any, Dict, List
from ..config import get_grade_level, get_curriculum_profile, needs_nikud, parse_literature_context, get_learning_skills


def _curriculum_block(subject: str, grade: str) -> str:
    """Return a <curriculum_context> block for prompt injection, or empty string."""
    cp = get_curriculum_profile(grade, subject)
    if not cp:
        return ""
    concepts = ", ".join(cp.get("key_concepts", [])[:6])
    topics = ", ".join(cp.get("typical_authentic_topics", [])[:4])
    avoid = cp.get("avoid_in_content", "")
    prior = cp.get("expected_prior_knowledge", "")
    vocab = cp.get("vocabulary_profile", "")
    parts = []
    if concepts:
        parts.append(f"מושגי מפתח בתכנית הלימודים לגיל זה: {concepts}")
    if prior:
        parts.append(f"ידע קודם מוכר לתלמיד: {prior}")
    if vocab:
        parts.append(f"פרופיל אוצר מילים: {vocab}")
    if topics:
        parts.append(f"נושאים אותנטיים מהתכנית הרשמית: {topics}")
    if avoid:
        parts.append(f"יש להימנע מ: {avoid}")
    if not parts:
        return ""
    body = "\n".join(f"• {p}" for p in parts)
    return f"\n<curriculum_context>\n{body}\n</curriculum_context>\n"


def _nikud_note(grade: str) -> str:
    """Return a nikud instruction line for young grades, empty string otherwise."""
    if not needs_nikud(grade):
        return ""
    return (
        "\n⚠️ חשוב מאוד: כיתה זו צעירה (כיתות א′–ג′). "
        "יש לכתוב את כל הטקסט העברי עם ניקוד מלא וסימני דגש. "
        "כל מילה חייבת לכלול ניקוד. לדוגמה: הַכֶּלֶב אָכַל לֶחֶם. "
        "אַל תִּכְתֹּב אַף מִלָּה בְּלִי נִיקּוּד.\n"
    )


def _vocabulary_word_types_note(gl: dict, grade: str) -> str:
    """Return a <vocabulary_word_types> block enforcing age-appropriate word choices."""
    min_age = int(gl['age'].split('-')[0])
    if min_age >= 14:
        return ""
    if min_age <= 7:
        guidance = "בחר: מילים בסיסיות ויפות מהסיפור, יחיד/רבים, זכר/נקבה, מילים נרדפות פשוטות."
    elif min_age <= 9:
        guidance = "בחר: ביטויים, ניבים, מילות קישור, מילים נרדפות — כולם מהטקסט ומהנושא."
    elif min_age <= 11:
        guidance = "בחר: ביטויים ופתגמים, מילים מעניינות מהטקסט, מילות קישור מורכבות, שורשים. **אסור בהחלט: מינוח ניתוח ספרותי.**"
    else:
        guidance = "אפשר לכלול מטפורה, אירוניה, סמל **רק** אם הם מוסברים בטקסט עצמו. עדיין אסור: אלגוריה, קתרזיס, לייטמוטיב."
    if min_age <= 11:
        ban = (
            f"✗ מונחי ניתוח ספרותי (אלגוריה, מוטיב, קתרזיס, מטפורה, אירוניה, פרסונה, סמל, פתוס, "
            f"אבסורד, פרדוקס, דיכוטומיה, קונפליקט כמונח ספרותי, לייטמוטיב) — אלה מושגים לכיתות י-יב בלבד.\n"
            f"✗ מילים לועזיות-אקדמיות: אבסורד, דרמה, טרגדיה, קומדיה, פרוטגוניסט, אנטגוניסט, "
            f"נרטיב, רטוריקה, אסתטיקה, תזה — גם אם הן מהטקסט, **אל תבחר אותן כמילות אוצר לגיל {gl['age']}**.\n"
            f"✗ מינוח מדעי/אקדמי שלא נמצא בטקסט עצמו (סימביוזה, אקולוגיה, פנומנולוגיה וכו׳).\n"
            f"✗ מושגים פסיכולוגיים מופשטים שאינם מהטקסט.\n"
            f"✗ כלל זהב: המילים שתבחר חייבות להיות מילים שילד בן {gl['age']} יכול להבין, להשתמש ולזכור — "
            f"לא מילים מהמילון האקדמי."
        )
    else:
        ban = (
            f"✗ אלגוריה, קתרזיס, לייטמוטיב, פתוס, אבסורד, פרדוקס — אלה מושגים לכיתות י-יב.\n"
            f"✗ מילים לועזיות-אקדמיות שאינן שגורות בפי תלמידים בגיל {gl['age']}.\n"
            f"✗ מינוח מדעי/אקדמי שלא נמצא בטקסט עצמו."
        )
    return (
        f"\n<vocabulary_word_types>\n"
        f"מה הן \"מילות אוצר\" בשיטת א\"ל השד\"ה:\n"
        f"✓ מילים, ביטויים, ניבים שמופיעים בטקסט — מילים מעניינות שהתלמיד יפגוש שוב בחיים.\n"
        f"✓ מילים נרדפות והפכים.\n"
        f"✓ משפחות מילים ושורשים שנמצאים בטקסט.\n"
        f"\n"
        f"מה אסור לכיתה {grade} (גיל: {gl['age']}):\n"
        f"{ban}\n"
        f"\n"
        f"הנחיה לגיל זה: {guidance}\n"
        f"</vocabulary_word_types>\n"
    )


def build_roadmap_prompt(subject: str, topic: str, grade: str, rounds: int) -> str:
    gl = get_grade_level(grade)
    curr = _curriculum_block(subject, grade)
    lit = parse_literature_context(subject, topic)
    if lit["mode"] == "author_rotating":
        lit_block = (
            f'\n<literature_control>\n'
            f'יוצר: {lit["author"]}. כל סבב חייב לעסוק ביצירה שונה של אותו יוצר.\n'
            f'ציין שם יצירה ספציפי בשדה description של תחנת ההבנה בכל סבב. אסור לחזור על אותה יצירה.\n'
            f'</literature_control>\n'
        )
    elif lit["mode"] == "specific_work":
        lit_block = (
            f'\n<literature_control>\n'
            f'כל הסבבים עוסקים ביצירה: "{lit["specific_work"]}". '
            f'כל סבב בוחן היבט אחר של אותה יצירה (עלילה / דמויות / מסר / שפה / מבנה).\n'
            f'</literature_control>\n'
        )
    else:
        lit_block = ""
    return f"""אתה מתכנן יחידת לימוד בשיטת א"ל השד"ה (הבנה, שיטות, דיוק, הרחבת אוצר מילים).

<user_input>
נושא: {subject} — {topic}
כיתה: {grade} | גיל: {gl['age']} | רמת שפה: {gl['language']}
מספר סבבים: {rounds}
</user_input>
{curr}{lit_block}

**חוקי ברזל:**
1. כל 4 תחנות בכל סבב — **עצמאיות לחלוטין** (תלמיד יכול להתחיל בכל אחת)
2. תחנת הבנה = טקסט עשיר לקריאה + דיון בעל פה בלבד, ללא כתיבה
3. תחנת שיטות = כתיבה מובנית ומדורגת — המורה נמצאת פה פיזית
4. תחנת דיוק = לשון ודקדוק טכני (מגוון: הכתבות, שורשים, בניינים, מאזכרים, הומופוניות, זמנים, גופים)
5. תחנת אוצר מילים = **חוויה ופעולה** — פיזית או מודפסת, לפי מה שמתאים לנושא
6. תחנת הבנה: **תמיד** טקסט סיפורי-נרטיבי — גם לנושאים מדעיים/היסטוריים (סיפור על מדען, משל, ביוגרפיה דרמטית, אגדה). אסור: כתבה/מאמר/דוח מידעי ישיר. לא לחזור על אותו טקסט בסבבים.
7. שלב ב-STEAM: שלב רב-תחומיות אמיתית (מדע/טכנולוגיה/אמנות/מתמטיקה) איפה שמתאים
8. הפעילויות מתקדמות מסבב לסבב: מבוא → העמקה → שיא
9. **תחנת דיוק — רוטציה מחייבת לפי סבב (אסור לחזור על אותה קטגוריה):**
   סבב 1: הכתבת מילים בלבד (חובה תמיד — לעולם לא אחר בסבב 1)
   סבב 2: שורשים ומשפחות מילים / מאזכרים (שם עצם, פועל, תואר) / בניינים (קל/פיעל/הפעיל)
   סבב 3: זמנים (עבר/הווה/עתיד) / גופים (ראשון/שני/שלישי יחיד-רבים) / אותיות הומופוניות (ט-ת, ח-כ, א-ה-ע)
   סבב 4+: רצף משפטים / נכון-לא נכון / סוגי משפטים (חיווי/שאלה/פקודה) / חיבור מילים למשפט תקין
   **כל activity_type ייחודי לסבבו — אסור בהחלט חזרה.**
10. **תחנת אוצר מילים — רוטציה מחייבת לפי סבב (אסור לחזור על אי אחד מהסוגים):**
   סבב 1: פעילות פיזית/חווייתית **חובה** — physical_plasticine / physical_game / physical_clothesline / physical_simulation
   סבב 2: קלפי התאמה / מיון / דומינו — matching_cards / sorting_table / dominoes
   סבב 3: תשבץ / תשחץ / חבל כביסה / כרזה — crossword_mini / word_search / clothesline / fill_in_poster
   סבב 4+: קלפי ביטויים / טבלת הגדרות / מודל פיזי — idiom_cards / definition_table / physical_model / physical_poster
   **אסור לבחור matching_cards יותר מפעם אחת. אסור לחזור על שום סוג בין סבבים.**

**סוגי כתיבה לתחנת שיטות (בחר לפי גיל וסבב):**
טיעון (בעד/נגד), תיאור (דמות/מקום/אירוע), תשובה מיטבית, סיכום, מיזוג, חוות דעת,
דוח (ניסוי/חקר/תצפית), מכתב (א-ב), שיר קצר (א-ב), יומן אישי (ג ומעלה), ניתוח טקסט מידעי (ה-ו), תרשים זרימה

**סוגי פעילות לתחנת אוצר מילים:**
מודפסות: matching_cards, sorting_table, dominoes, fill_in_poster, clothesline, idiom_cards, definition_table, crossword_mini, word_search
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
        "activity_type": "בחר בדיוק אחד (שונה מכל הסבבים האחרים): שורשים | בניינים | מאזכרים | זמנים | גופים | הומופוניות | רצף_משפטים | הכתבה",
        "description": "תיאור קצר של הפעילות הנבחרת"
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

    curr = _curriculum_block(subject, grade)
    return f"""כתוב טקסט לתחנת ההבנה בשיטת א"ל השד"ה.{_nikud_note(grade)}
<user_input>
נושא: {subject} — {topic}
כיתה: {grade} | גיל: {gl['age']} | שפה: {gl['language']}
סבב {round_num} מתוך {total_rounds} | סוג טקסט: {text_type} | תכנון: {text_desc}
מוקד הדיון: {disc_focus}{prev}
</user_input>
{curr}
<standalone_rule>
יחידה זו עצמאית לחלוטין. תלמיד מגיע ישירות לתחנה זו ללא קשר לתחנות אחרות.
אסור לכתוב "כפי שקראנו", "הטקסט שלמדנו", "מהפעילות הקודמת", או כל התייחסות לתחנה אחרת.
</standalone_rule>
<story_requirement>
תחנת ההבנה מבוססת תמיד על טקסט נרטיבי-סיפורי, גם אם הנושא מדעי או היסטורי.
הטקסט חייב לכלול: דמויות, עלילה, קונפליקט או דילמה, קול מספר.
גם אם "מידעי" או "רב-היצגי" תוכנן — יש ליישמו כסיפור עם רקע מידעי שזור בתוכו.
אסור: טקסט מידעי יבש ללא עלילה, כתבה עיתונאית, סיכום עובדות.
</story_requirement>
<literary_anchor>
הטקסט חייב לעסוק ישירות ב: {topic}
אם הנושא הוא סופר, משורר או יוצר — השתמש ביצירות האותנטיות שלו בלבד (ציטוטים, דמויות, עלילות מוכרות מספריו/שיריו).
אסור ביצירות בדויות שהוחסו לסופר. הסיפור חייב לנבוע ישירות מהנושא — לא רק לאזכר אותו בשוליים.
{text_desc}
</literary_anchor>
<vocabulary_level>
רמת שפה: כיתה {grade} (גיל {gl['age']}).
השתמש במילים שגרתיות המוכרות לתלמידים בגיל זה.
הימנע ממונחים ספרותיים אקדמיים, מילים ארכאיות, שאילות מלועזית, או מילות יחס מורכבות שאינן בפי ילדים.
כל מונח מקצועי שמופיע — הסבר אותו בסוגריים ישירות לאחריו בטקסט.
</vocabulary_level>

**אפשרויות פעילות לתחנת הבנה לגיל זה:** {', '.join(gl['comprehension_options'])}

**⚠️ חוקים קריטיים:**
1. **אורך: {gl['text_length']}** — אל תקצר! זה טקסט לקריאה בעל פה, חייב להיות ארוך ועשיר
2. **אל תכלול שאלות בגוף הטקסט** — התחנה כולה בעל פה, הדיון הוא בין התלמידים
3. כלול 8-12 **מונחי מפתח** — מודגשים בטקסט
4. חלק ל-5-7 פסקאות עם כותרות משנה (לכיתות ה-ו: 6-7 פסקאות)
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
    for p in comprehension_text.get('paragraphs', [])[:3]:
        text_summary += p.get('text', '')[:180] + "... "

    skills = get_learning_skills(grade)
    skills_block = ""
    if skills:
        skills_lines = "\n".join(f"• {s}" for s in skills)
        skills_block = (
            f"\n<grade_learning_skills>\n"
            f"מיומנויות הלמידה הרשמיות לכיתה {grade} לפי תכנית הלימודים:\n"
            f"{skills_lines}\n"
            f"בחר מיומנות מהרשימה שמתאימה לסוג הכתיבה הנוכחי ({writing_type}) ושלב אותה במשימה.\n"
            f"</grade_learning_skills>\n"
        )

    return f"""צור משימת כתיבה מובנית לתחנת השיטות — א"ל השד"ה.{_nikud_note(grade)}
<user_input>
נושא: {subject} — {topic} | סבב {round_num}
כיתה: {grade} | גיל: {gl['age']}
סוג הכתיבה: {writing_type} | תכנון: {methods_desc}
מונחים מהטקסט: {', '.join(key_terms[:8])}
הקשר הטקסט: {text_summary[:500]}
</user_input>

<standalone_rule>
יחידה זו עצמאית לחלוטין. תלמיד מגיע ישירות לתחנה זו ללא גישה לטקסט מהתחנות האחרות.
אסור לכתוב "כפי שקראנו", "הטקסט שלמדנו", "מהפעילות הקודמת", או כל התייחסות לתחנה אחרת.
כלול בראש דף המשימה "רקע קצר" (3-4 משפטים) על הנושא, כך שתלמיד שלא ראה טקסט אחר יוכל להבין את ההקשר.
</standalone_rule>
{skills_block}
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
5. כלול 4-5 פריטי ביקורת עצמית (self_review_checklist) — לפי סוג הכתיבה הנוכחי

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
  "success_criteria": ["קריטריון 1", "קריטריון 2", "קריטריון 3"],
  "self_review_checklist": [
    "בדקתי: יש לי פתיחה/מבוא",
    "בדקתי: השתמשתי ב-2 מונחים לפחות מהטקסט",
    "בדקתי: יש לי סיום/מסקנה",
    "בדקתי: המשפטים מחוברים זה לזה",
    "בדקתי: אין שגיאות כתיב בסיסיות"
  ]
}}"""


def build_precision_prompt(subject: str, topic: str, grade: str,
                            round_num: int, round_plan: Dict,
                            key_terms: List[str]) -> str:
    gl = get_grade_level(grade)
    activity_type = round_plan.get('precision', {}).get('activity_type', 'הכתבה ושורשים')
    precision_desc = round_plan.get('precision', {}).get('description', '')

    return f"""צור פעילות לתחנת הדיוק (לשון ודקדוק) — א"ל השד"ה.{_nikud_note(grade)}
<user_input>
נושא: {subject} — {topic} | סבב {round_num}
כיתה: {grade} | גיל: {gl['age']}
סוג הפעילות: {activity_type} | תכנון: {precision_desc}
מילים מהטקסט: {', '.join(key_terms[:12])}
מספר מילים להכתבה לגיל זה: {gl['dictation_words']}
</user_input>

<standalone_rule>
יחידה זו עצמאית לחלוטין. תלמיד מגיע ישירות לתחנה זו ללא קשר לתחנות אחרות.
אסור לכתוב "כפי שקראנו" או כל התייחסות לטקסט מתחנות אחרות.
בראש הדף הוסף: "בשביל ההקשר: [2-3 משפטים קצרים על {topic}]" לפני הפעילות.
</standalone_rule>

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
4. כלול **3-4 משפטים** להכתבה (לא 2 בלבד) ב-sentences_for_dictation
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
    "משפט 2 מהטקסט להכתבה",
    "משפט 3 מהטקסט להכתבה",
    "משפט 4 מהטקסט להכתבה"
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

    return f"""צור פעילות לתחנת הרחבת אוצר מילים — א"ל השד"ה.{_nikud_note(grade)}
<user_input>
נושא: {subject} — {topic} | סבב {round_num}
כיתה: {grade} | גיל: {gl['age']}
סוג הפעילות: {activity_type} | תכנון: {vocab_desc}
מונחים מהטקסט: {', '.join(key_terms[:12])}
סוגים שכבר השתמשנו בהם: {', '.join(used_types) if used_types else 'אין'}
</user_input>
{_vocabulary_word_types_note(gl, grade)}
<standalone_rule>
יחידה זו עצמאית לחלוטין. תלמיד מגיע ישירות לתחנה זו ללא קשר לתחנות אחרות.
אסור לכתוב "כפי שקראנו" או כל התייחסות לתוכן מתחנות אחרות.
בראש הדף הוסף: "בשביל ההקשר: [2-3 משפטים קצרים על {topic}]" לפני רשימת המילים.
</standalone_rule>
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
- crossword_mini: תשבץ מיני — רשת עם רמזים מאוזן/מאונך
- word_search: תשחץ מילים — מצא מילים נסתרות ברשת אותיות

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
5. הוסף פעילות המשך קצרה (extension_activity) — 2-3 דקות לתלמידים שסיימו מוקדם

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
  "answer_key": "מפתח תשובות מלא",
  "extension_activity": {{
    "title": "המשך ואתגר",
    "instruction": "הוראה קצרה לתלמידים שסיימו (1-2 משפטים)",
    "items": ["פריט 1", "פריט 2", "פריט 3"]
  }}
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

<standalone_rule>
כל תחנה עצמאית לחלוטין — תלמיד יכול להתחיל בכל תחנה שהיא ללא תלות בתחנות אחרות.
ודא שהמורה מודעת לכך ושכל דף תחנה כולל את כל הרקע שהתלמיד צריך.
</standalone_rule>

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
