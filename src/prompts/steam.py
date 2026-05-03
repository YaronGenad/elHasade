from typing import Any, Dict, List
from ..config import get_grade_level, get_stem_grade_level, STEAM_GAMES_LIST


def build_stem_roadmap_prompt(subject: str, topic: str, grade: str, rounds: int) -> str:
    gl = get_grade_level(grade)
    sgl = get_stem_grade_level(grade)
    return f"""אתה מתכנן יחידת לימוד בשיטת א"ל השד"ה — גרסת STEAM (מתמטיקה/מדעים/הנדסה/טכנולוגיה/אמנויות).

<user_input>
מקצוע: {subject} | נושא: {topic}
כיתה: {grade} | גיל: {gl['age']} | מספר סבבים: {rounds}
</user_input>

**שינויים עיקריים בגרסת STEAM לעומת גרסת השפה:**
- תחנת הבנה: ערוצי קלט מגוונים (טקסט/סרטון/תצפית/ניסוי) + תיעוד כתוב קצר מותר
- תחנת שיטות: חשיבה תהליכית-פרוצדורלית (EDP / מתודה מדעית / ניתוח נתונים / חשיבה מתמטית)
- תחנת דיוק: **HANDS-ON** — ניסויים, מדידות, בנייה הנדסית, יצירה מוחשית (לא דקדוק!)
- תחנת אוצר מילים: מושגי STEAM בעברית + אנגלית + 17 משחקים ייחודיים

**חוקי ברזל:**
1. כל 4 תחנות — **עצמאיות לחלוטין** (STAND-ALONE); אם תחנה X צריכה תוצר של תחנה Y — הכניסי אותו ישירות לתחנה X
2. תחנת דיוק = HANDS-ON בלבד — ניסוי/בנייה/מדידה; כולל הוראות ורקע מינימלי עצמאי
3. נתוני ניסוי לתחנת שיטות — מסופקים בתוך התחנה (לא תלויים בתחנת הדיוק)
4. תחנת אוצר מילים: חייבת לכלול מונחים בעברית ובאנגלית + משחק מהרשימה
5. התקדמות סבבים לפי מודל STEAM: גילוי → חקירה מעמיקה → ישום ותיכון → סיכום והצגה

**מודל התקדמות STEAM:**
- סבב 1: היכרות עם התופעה — הבנה ראשונית, ניסוי גילוי, מושגים בסיסיים
- סבב 2: חקירה מעמיקה — קריאה מדעית, ניסוי מובנה, ניתוח נתונים
- סבב 3: ישום ותיכון — פתרון בעיה, בנייה הנדסית, קישור לעולם אמיתי
- סבב 4: סיכום ושיקוף — הצגה, כתיבה סיכומית, מושגים מתקדמים

**ערוצי קלט לתחנת הבנה לגיל {gl['age']}:** {', '.join(sgl['comprehension_channels'])}
**מסגרות חשיבה לתחנת שיטות לגיל {gl['age']}:** {', '.join(sgl['methods_frameworks'])}
**פעילויות HANDS-ON לתחנת דיוק לגיל {gl['age']}:** {', '.join(sgl['precision_activities'])}
**משחקים לתחנת אוצר מילים לגיל {gl['age']}:** {', '.join(sgl['vocabulary_games'])}

**פורמט פלט — JSON בלבד:**
{{
  "unit_title": "שם היחידה",
  "is_steam": true,
  "central_phenomenon": "התופעה/הבעיה/השאלה המרכזית שמניעה את היחידה",
  "steam_connections": ["חיבור STEAM 1", "חיבור STEAM 2"],
  "learning_goals": {{
    "knowledge": ["ידע 1", "ידע 2"],
    "skills": ["מיומנות 1", "מיומנות 2"],
    "values": ["ערך/הרגל 1"]
  }},
  "rounds": [
    {{
      "round": 1,
      "comprehension": {{
        "input_type": "text|video|observation|experiment|multi_source",
        "description": "תיאור קצר של החומר/הפעילות",
        "discussion_focus": "שאלת חקירה / תופעה מעוררת מחשבה"
      }},
      "methods": {{
        "thinking_framework": "scientific_method|EDP|data_analysis|mathematical_thinking|art_design",
        "description": "תיאור המשימה"
      }},
      "precision": {{
        "hands_on_type": "science_experiment|measurement_data|engineering_building|math_hands_on|art_design",
        "description": "תיאור הניסוי/הבנייה/המדידה"
      }},
      "vocabulary": {{
        "game_type": "stem_memory|stem_alias|stem_taboo|stem_quartets|stem_bingo|stem_snakes|stem_quiz|stem_who_am_i|stem_dominoes|stem_flashcard|stem_concept_puzzle|stem_word_chain|stem_matching_board|stem_20_questions|stem_track|stem_catan|stem_monopoly",
        "description": "תיאור המשחק ומה לומדים"
      }}
    }}
  ]
}}"""


def build_stem_comprehension_prompt(subject: str, topic: str, grade: str,
                                     round_num: int, total_rounds: int,
                                     round_plan: Dict, prev_texts: List[str]) -> str:
    gl = get_grade_level(grade)
    sgl = get_stem_grade_level(grade)
    prev = ""
    if prev_texts:
        prev = f"\n\n**חומרים קודמים (אל תחזור על תוכן זה):**\n" + "\n".join(prev_texts[-2:])

    input_type = round_plan.get('comprehension', {}).get('input_type', 'text')
    desc = round_plan.get('comprehension', {}).get('description', '')
    disc_focus = round_plan.get('comprehension', {}).get('discussion_focus', 'תופעה מדעית מעוררת חשיבה')

    input_labels = {
        'text': 'טקסט מדעי / כתבה',
        'video': 'תיאור סרטון מדעי + שאלות הכוונה',
        'observation': 'תצפית מונחת + תיעוד',
        'experiment': 'ניסוי קצר להמחשה (לא ניתוח — זה שמור לתחנת הדיוק)',
        'multi_source': 'שילוב של מקורות (טקסט + גרף/תמונה/נתונים)',
    }
    input_label = input_labels.get(input_type, 'טקסט מדעי')

    progression = {
        1: 'היכרות ראשונית עם התופעה — עורר סקרנות, הצג את השאלה המרכזית',
        2: 'חקירה מעמיקה — הצג נתונים, ראיות, מנגנון',
        3: 'ישום — הצג קישור לעולם אמיתי, פתרון בעיה, הנדסה',
        4: 'סיכום — הצג סינתזה, תובנות, שאלות פתוחות לעתיד',
    }
    stage = progression.get(round_num, progression[min(round_num, 4)])

    return f"""כתוב חומר לתחנת ההבנה — א"ל השד"ה גרסת STEAM.

<user_input>
מקצוע: {subject} | נושא: {topic}
כיתה: {grade} | גיל: {gl['age']}
סבב {round_num} מתוך {total_rounds} | שלב: {stage}
ערוץ קלט: {input_label} | תכנון: {desc}
מוקד חקירה: {disc_focus}{prev}
</user_input>

**⚠️ הבדלים מגרסת השפה:**
- מותר לכלול תשובה כתובה קצרה (1-3 משפטים) לצורך תיעוד הבנה
- שלב טבלת KWL (יודע / רוצה לדעת / למדתי)
- כל מונח מדעי חדש: עברית + אנגלית + הגדרה קצרה
- שאלות החקירה יכולות לכלול: ניבוי, השוואה, קישור לחיים, שאלת ניסוי

**⚠️ חוקים קריטיים:**
1. **אורך: {sgl['text_length']}** — עשיר ומעמיק
2. כלול 8-12 **מונחי מפתח** — עברית + אנגלית בסוגריים
3. חלק ל-4-5 פסקאות עם כותרות משנה
4. כל מושג חדש — הסבר בסוגריים בתוך הטקסט
5. שלב גרפים/נתונים/מספרים כשרלוונטי

**פורמט פלט — JSON בלבד:**
{{
  "section_title": "כותרת הסבב",
  "is_steam": true,
  "input_type": "{input_type}",
  "intro_question": "שאלת פתיחה מעוררת סקרנות (תופעה / בעיה / שאלה מדעית)",
  "paragraphs": [
    {{
      "subtitle": "כותרת משנה",
      "text": "טקסט מדעי עשיר (כולל מונחים מודגשים, מספרים, דוגמאות)",
      "key_terms": ["מונח בעברית (English Term)", "מונח2 (Term2)"]
    }}
  ],
  "kwl_table": {{
    "know_prompts": ["מה אני כבר יודע/ת על נושא זה: ___", "דוגמה שאני מכיר/ה: ___"],
    "wonder_prompts": ["שאלה שאני רוצה לברר: ___", "תהייה שעלתה לי: ___"]
  }},
  "written_response": {{
    "question": "שאלה קצרה לתשובה כתובה (1-3 משפטים)",
    "scaffold": "_____ קורה כי _____. לדעתי _____ כי _____.",
    "instruction": "כתוב/כתבי תשובה קצרה (1-3 משפטים) — אין צורך בפסקה מלאה"
  }},
  "all_key_terms": ["מונח1 (Term1)", "מונח2 (Term2)", "מונח3 (Term3)"],
  "discussion_starters": [
    "שאלת תצפית: מה קורה כאן? מה אתה/את מבחין/ה?",
    "שאלת תהליך: מדוע? באיזה סדר? מה גורם למה?",
    "שאלת ניבוי: מה יקרה אם נשנה את ___?",
    "שאלת קישור: איפה רואים את זה בחיים? מה הקשר ל___?",
    "שאלת ניסוי: מה היית רוצה לבדוק? מה ההשערה שלך?"
  ]
}}"""


def build_stem_methods_prompt(subject: str, topic: str, grade: str,
                               round_num: int, round_plan: Dict,
                               comprehension_text: Dict) -> str:
    gl = get_grade_level(grade)
    sgl = get_stem_grade_level(grade)
    framework = round_plan.get('methods', {}).get('thinking_framework', 'scientific_method')
    methods_desc = round_plan.get('methods', {}).get('description', '')
    key_terms = comprehension_text.get('all_key_terms', [])

    text_summary = comprehension_text.get('section_title', '') + ": "
    for p in comprehension_text.get('paragraphs', [])[:2]:
        text_summary += p.get('text', '')[:200] + "... "

    framework_descriptions = {
        'scientific_method': 'המתודה המדעית: תצפית → שאלת חקירה → השערה → ניסוי → ניתוח → מסקנה',
        'EDP': 'תהליך התיכון ההנדסי (EDP): זיהוי בעיה → מחקר → הצעת פתרונות → בחירה ותכנון → בנייה ובדיקה → שיפור',
        'data_analysis': 'ניתוח נתונים: קריאת גרף/טבלה → זיהוי מגמות → פרשנות → מסקנות',
        'mathematical_thinking': 'חשיבה מתמטית: הבנת הבעיה → תכנון → פתרון שלב אחר שלב → בדיקה → הכללה',
        'art_design': 'חשיבה עיצובית: ניתוח → כוונה → תכנון → ביצוע → הצגה',
    }
    fw_desc = framework_descriptions.get(framework, framework_descriptions['scientific_method'])

    # For data_analysis framework, we provide sample data directly in the station
    data_note = ""
    if framework == 'data_analysis':
        data_note = "\n**חשוב:** כלול בתוך המשימה נתונים/גרף/טבלה ספציפיים לניתוח — התחנה עצמאית לחלוטין ואינה תלויה בניסוי מתחנת הדיוק!"

    return f"""צור משימת חשיבה תהליכית-פרוצדורלית לתחנת השיטות — א"ל השד"ה גרסת STEAM.

<user_input>
מקצוע: {subject} | נושא: {topic} | סבב {round_num}
כיתה: {grade} | גיל: {gl['age']}
מסגרת חשיבה: {fw_desc}
תכנון: {methods_desc}
מונחים מהחומר: {', '.join(key_terms[:8])}
הקשר: {text_summary[:300]}
</user_input>{data_note}

**מסגרות חשיבה זמינות לגיל זה:** {', '.join(sgl['methods_frameworks'])}

**חוקים:**
1. המשימה מובנית — כלול פיגום (scaffold) מלא: תבנית, שלבים, דוגמה
2. אם הניתוח מצריך נתוני ניסוי — **ספק אותם ישירות בתוך המשימה** (תחנה עצמאית!)
3. כלול 3 רמות קושי (רמזור ירוק/צהוב/אדום)
4. מותאם לגיל {gl['age']}

**פורמט פלט — JSON בלבד:**
{{
  "title": "שם המשימה",
  "thinking_framework": "{framework}",
  "main_instruction": "הוראה ראשית ברורה לתלמיד",
  "context_prompt": "הבעיה/השאלה/הנתונים שעובדים איתם",
  "framework_steps": ["שלב 1: ...", "שלב 2: ...", "שלב 3: ..."],
  "context_data": "נתונים/גרף/טבלה/בעיה מוחשית לניתוח (אם נדרש — מלא כאן!)",
  "scaffold_template": "תבנית/פיגום לכתיבה עם מבנה ברור",
  "guiding_questions": [
    "שאלה מנחה 1",
    "שאלה מנחה 2",
    "שאלה מנחה 3"
  ],
  "difficulty_levels": {{
    "green": "משימה בסיסית — שלבים נתונים, מבנה מלא, תמיכה מרבית",
    "yellow": "המשימה הרגילה — עצמאות חלקית לפי המסגרת",
    "red": "הרחבה — יישום בהקשר חדש, ביקורת, הכללה"
  }},
  "words_range": "X-Y מילים / משפטים / פריטים",
  "lines_needed": 12,
  "success_criteria": ["קריטריון 1", "קריטריון 2", "קריטריון 3"]
}}"""


def build_stem_precision_prompt(subject: str, topic: str, grade: str,
                                 round_num: int, round_plan: Dict,
                                 key_terms: List[str]) -> str:
    gl = get_grade_level(grade)
    sgl = get_stem_grade_level(grade)
    hands_on_type = round_plan.get('precision', {}).get('hands_on_type', 'science_experiment')
    precision_desc = round_plan.get('precision', {}).get('description', '')

    type_descriptions = {
        'science_experiment': 'ניסוי מדעי — בדיקת השערה, מדידה, תיעוד תוצאות, מסקנה',
        'measurement_data': 'מדידות ואיסוף נתונים — מדידה, רישום בטבלה, בניית גרף',
        'engineering_building': 'בנייה הנדסית — בנייה לפי מפרט, בדיקת ביצועים, שיפור',
        'math_hands_on': 'מתמטיקה מוחשית — מניפולטיבים, מדידה, פיצול/הרכבה גיאומטרי',
        'art_design': 'יצירה ועיצוב — יצירת מודל/אינפוגרפיקה/פרוטוטייפ המדגים מושג',
    }
    type_desc = type_descriptions.get(hands_on_type, type_descriptions['science_experiment'])

    return f"""צור פעילות HANDS-ON לתחנת הדיוק — א"ל השד"ה גרסת STEAM.

<user_input>
מקצוע: {subject} | נושא: {topic} | סבב {round_num}
כיתה: {grade} | גיל: {gl['age']}
סוג הפעילות: {type_desc}
תכנון: {precision_desc}
מונחי מפתח: {', '.join(key_terms[:10])}
</user_input>

**פעילויות HANDS-ON מתאימות לגיל זה:** {', '.join(sgl['precision_activities'])}

**⚠️ חוקים קריטיים — גרסת STEAM:**
1. זו תחנת HANDS-ON בלבד — **אין הכתבות ואין תרגילי דקדוק**
2. כלול הוראות מלאות ועצמאיות — תלמיד יכול להתחיל ישירות ללא תלות בתחנות אחרות
3. כלול שאלת חקירה + השערה לפני הניסוי
4. כלול טבלת תיעוד ריקה + שאלות ניתוח + מסקנה מובנית
5. ציין חומרים בטוחים לגיל {gl['age']} + הערות בטיחות
6. כלול 3 רמות קושי (ירוק/צהוב/אדום) — קל/רגיל/מאתגר

**פורמט פלט — JSON בלבד:**
{{
  "title": "שם הניסוי/הפעילות",
  "is_hands_on": true,
  "hands_on_type": "{hands_on_type}",
  "research_question": "מה אנחנו בודקים/בונים/מודדים?",
  "background_mini": "רקע מינימלי (2-3 משפטים) לביצוע עצמאי של הפעילות",
  "hypothesis_scaffold": "ההשערה שלי: אני חושב/ת שיקרה ___ כי ___",
  "materials_needed": ["חומר 1", "חומר 2", "כלי 1"],
  "safety_notes": ["הערת בטיחות 1 (אם רלוונטי)"],
  "steps": [
    "שלב 1: ...",
    "שלב 2: ...",
    "שלב 3: ..."
  ],
  "data_table": {{
    "headers": ["תצפית/מדידה", "תוצאה 1", "תוצאה 2"],
    "rows": [["ניסיון 1", "", ""], ["ניסיון 2", "", ""], ["ניסיון 3", "", ""]]
  }},
  "analysis_questions": [
    {{"question": "מה גילינו? האם ההשערה אושרה?", "answer": "תשובה צפויה למורה"}},
    {{"question": "מה השפיע על התוצאה?", "answer": "תשובה צפויה למורה"}},
    {{"question": "מה היית משנה בניסוי הבא?", "answer": "תשובה פתוחה"}}
  ],
  "conclusion_scaffold": "גילינו ש ___ כי ___. הדבר קורה בגלל ___. קישור לחיים: ___.",
  "difficulty_levels": {{
    "green": "גרסה קלה — שלבים נתונים, טבלה ממולאת חלקית, הוראות מפורטות יותר",
    "yellow": "הגרסה הרגילה — כמתואר למעלה",
    "red": "אתגר נוסף — שאלת הרחבה, שינוי משתנה, ניסוי נוסף עצמאי"
  }},
  "expected_results": "תוצאות צפויות + הסבר מדעי מלא — למורה בלבד"
}}"""


def build_stem_vocabulary_prompt(subject: str, topic: str, grade: str,
                                  round_num: int, round_plan: Dict,
                                  key_terms: List[str], used_types: List[str]) -> str:
    gl = get_grade_level(grade)
    sgl = get_stem_grade_level(grade)
    game_type = round_plan.get('vocabulary', {}).get('game_type', 'stem_memory')
    vocab_desc = round_plan.get('vocabulary', {}).get('description', '')

    game_labels = {
        'stem_memory': ('זיכרון מושגים (Memory Match)', 'זוגות עברית↔אנגלית / מונח↔הגדרה'),
        'stem_alias': ('אליאס מדעי (Science Alias)', 'הסבר מושג ללא המילה; צוות מנחש'),
        'stem_taboo': ('טאבו מדעי (Science Taboo)', 'הסבר ללא מילות המפתח האסורות'),
        'stem_quartets': ('רביעיות מדעיות (Quartets)', 'אסיפת 4 קלפים מאותה קטגוריה STEAM'),
        'stem_bingo': ('Bingo מדעי (STEAM Bingo)', 'הגדרות נקראות; מי שמזהה — סומן'),
        'stem_snakes': ('סולמות ונחשים STEAM', 'שאלת מושג בכל ריבוע; עלה/רד'),
        'stem_quiz': ('שאלות ותשובות (Quiz Bowl)', 'קלפי שאלות לפי נושאי STEAM'),
        'stem_who_am_i': ('מי אני? (Who Am I? Science)', 'כרטיס מושג על המצח; שאלות כן/לא'),
        'stem_dominoes': ('דומינו STEAM', 'מושג↔הגדרה; הנח קלף שמושג פוגש הגדרתו'),
        'stem_flashcard': ('כרטיסיות אוצר (Flashcard Battle)', 'מי עונה על ההגדרה מהר יותר'),
        'stem_concept_puzzle': ('פאזל מושגים (Concept Puzzle)', 'חתוך ל-4 חלקים: שם/הגדרה/דוגמה/ציור'),
        'stem_word_chain': ('שרשרת מדעית (Word Chain)', 'מושג שמתחיל באות אחרונה + הסבר הקשר'),
        'stem_matching_board': ('התאמת מושגים (Matching Board)', 'לוח גדול; חיבור מושג↔הגדרה/תמונה'),
        'stem_20_questions': ('20 שאלות מדעיות', 'שאלות כן/לא לגילוי המושג הנסתר'),
        'stem_track': ('מסלול מדעי (STEAM Track)', 'כרטיסיות ירוק/צהוב/אדום לפי קושי'),
        'stem_catan': ('קטאן מדעי (Science Catan)', 'בנה ממלכה; ענה נכון — קבל משאב'),
        'stem_monopoly': ('מונופול מדעי (Science Monopoly)', 'נכסים = מושגי STEAM; ענה הגדרה'),
    }
    game_name, game_mechanic = game_labels.get(game_type, ('זיכרון מושגים', 'זוגות מושגים'))

    return f"""צור פעילות לתחנת הרחבת אוצר מילים — א"ל השד"ה גרסת STEAM.

<user_input>
מקצוע: {subject} | נושא: {topic} | סבב {round_num}
כיתה: {grade} | גיל: {gl['age']}
המשחק: {game_name} | מנגנון: {game_mechanic}
תכנון: {vocab_desc}
מונחים מהחומר: {', '.join(key_terms[:12])}
סוגים שבוצעו כבר: {', '.join(used_types) if used_types else 'אין'}
</user_input>

**עקרון STEAM לתחנה זו:**
- כל מונח: עברית + אנגלית + הגדרה + קטגוריית STEAM (מדעים/מתמטיקה/הנדסה/טכנולוגיה/אמנויות)
- המשחק צריך להיות מהנה, תחרותי, ומפנים את המושגים לזיכרון ארוך-טווח

**רשימת 17 המשחקים לעיון:**
{STEAM_GAMES_LIST}

**משחקים מתאימים לגיל זה:** {', '.join(sgl['vocabulary_games'])}

**חוקים:**
1. כלול 8-14 מושגים בעברית + אנגלית
2. כלול הוראות משחק מפורטות שלב אחרי שלב
3. כלול רשימת חומרים נדרשים (קלפים לגזירה וכו')
4. כלול קלפי מושגים להדפסה/גזירה

**פורמט פלט — JSON בלבד:**
{{
  "title": "שם הפעילות",
  "game_type": "{game_type}",
  "is_physical": true,
  "bilingual": true,
  "instruction": "הוראות המשחק שלב אחרי שלב (כולל: הכנה / שחקנים / כיצד משחקים / כיצד מנצחים)",
  "materials_needed": ["קלפים להדפסה וגזירה", "חומר נוסף אם נדרש"],
  "words": [
    {{
      "word": "מונח בעברית",
      "english": "English Term",
      "definition": "הגדרה קצרה ובהירה",
      "example": "דוגמה מהחיים",
      "category": "מדעים|מתמטיקה|הנדסה|טכנולוגיה|אמנויות"
    }}
  ],
  "categories": ["קטגוריה 1", "קטגוריה 2"],
  "physical_steps": [
    "שלב 1: הדפס וגזור את הקלפים",
    "שלב 2: ...",
    "שלב 3: ..."
  ],
  "answer_key": "מפתח תשובות / רשימת ההתאמות הנכונות — למורה"
}}"""
