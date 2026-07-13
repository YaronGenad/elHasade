from typing import Dict
from ..config import STATION_COLORS
from .css import get_css, ENGLISH_LABELS, ENGLISH_STATION_NAMES, MATH_STATION_NAMES
from .header import render_header


def render_teacher_prep(title: str, round_num: int, data: Dict, content: Dict,
                         english_mode: bool = False, math_mode: bool = False) -> str:
    objectives = data.get('objectives', {})
    materials = data.get('materials', {})
    timing = data.get('timing', {})
    notes = data.get('teacher_notes', [])
    diff = data.get('differentiation', {})

    def list_html(items):
        return "".join([f'<li style="margin-bottom:4px;">{i}</li>' for i in items])

    if english_mode:
        lbl = ENGLISH_LABELS
        html_dir = "ltr"
        html_lang = "en"
        page_title = f"Teacher Preparation - {title} - Round {round_num}"
        footer_text = f"מחולל יחידות לימוד | Teacher Preparation | {title} | Round {round_num} — {lbl['footer_copy']}"
        teacher_only_msg = lbl['teacher_only']
        objectives_title = "🎯 Round Objectives"
        knowledge_label = "Knowledge:"
        skills_label = "Skills:"
        values_label = "Values:"
        timing_title = "⏱️ Recommended Timing"
        materials_title = "🗃️ Materials for Each Station"
        notes_title = "📌 Notes and Key Points"
        diff_title = "🎯 Differentiation"
        struggling_label = "🟢 Struggling students:"
        advanced_label = "🔴 Advanced students:"
        special_label = "♿ Special education:"
        list_pad = "padding-left:16px;"
        notes_pad = "padding-left:18px;"
        station_name_fn = lambda k: ENGLISH_STATION_NAMES.get(k, {}).get('name', k)
    elif math_mode:
        html_dir = "rtl"
        html_lang = "he"
        page_title = f"מדריך הכנה למורה — מתמטיקה יומית — {title} — סבב {round_num}"
        footer_text = f"מתמטיקה יומית — א\"ל השד\"ה | מדריך הכנה למורה | {title} | סבב {round_num} — © כל הזכויות שמורות"
        teacher_only_msg = "⚠️ מדריך זה מיועד למורה בלבד — אין להעביר לתלמידים"
        objectives_title = "🎯 מטרות הסבב (ידע, מיומנות, הרגל)"
        knowledge_label = "ידע:"
        skills_label = "מיומנויות:"
        values_label = "הרגלים/ערכים:"
        timing_title = "⏱️ תזמון מומלץ (20 דקות לכל תחנה)"
        materials_title = "🗃️ ציוד וחומרים לכל תחנה"
        notes_title = "📌 הוראות הפעלה ונקודות לתשומת לב"
        diff_title = "🎯 דיפרנציאציה"
        struggling_label = "🟢 תלמידים מתקשים:"
        advanced_label = "🔴 תלמידים מתקדמים:"
        special_label = "♿ חינוך מיוחד:"
        list_pad = "padding-right:16px;"
        notes_pad = "padding-right:18px;"
        station_name_fn = lambda k: MATH_STATION_NAMES.get(k, {}).get('name', STATION_COLORS.get(k, {}).get('name', k))
    else:
        html_dir = "rtl"
        html_lang = "he"
        page_title = f"הכנה למורה - {title} - סבב {round_num}"
        footer_text = f"א\"ל השד\"ה | הכנה למורה | {title} | סבב {round_num} — © כל הזכויות שמורות"
        teacher_only_msg = "⚠️ דף זה מיועד למורה בלבד — אין להעביר לתלמידים"
        objectives_title = "🎯 מטרות הסבב (ימ\"ה)"
        knowledge_label = "ידע:"
        skills_label = "מיומנויות:"
        values_label = "ערכים:"
        timing_title = "⏱️ תזמון מומלץ"
        materials_title = "🗃️ ציוד וחומרים לכל תחנה"
        notes_title = "📌 הערות ונקודות לתשומת לב"
        diff_title = "🎯 דיפרנציאציה"
        struggling_label = "🟢 תלמידים מתקשים:"
        advanced_label = "🔴 תלמידים מתקדמים:"
        special_label = "♿ חינוך מיוחד:"
        list_pad = "padding-right:16px;"
        notes_pad = "padding-right:18px;"
        station_name_fn = lambda k: STATION_COLORS.get(k, {}).get('name', k)

    mat_html = ""
    for station, mat_list in materials.items():
        c = STATION_COLORS.get(station, STATION_COLORS['teacher'])
        items = "".join([f'<li>{m}</li>' for m in (mat_list if isinstance(mat_list, list) else [str(mat_list)])])
        sname = station_name_fn(station)
        mat_html += f"<div style='margin-bottom:8px;'><strong style='color:{c['primary']};'>{c['emoji']} {sname}:</strong><ul style='margin:3px 0; {list_pad}'>{items}</ul></div>"

    timing_html = "".join([
        f'<div style="display:flex; justify-content:space-between; padding:5px 0; border-bottom:1px solid #eee;">'
        f'<span><strong>{STATION_COLORS.get(k, {}).get("emoji", "")} {station_name_fn(k)}</strong></span>'
        f'<span style="color:#666;">{v}</span></div>'
        for k, v in timing.items()
    ])

    # STEAM-only extra sections
    safety_checklist = data.get('safety_checklist', [])
    steam_connections = data.get('steam_connections', [])
    rotation_tip = data.get('rotation_tip', '')

    safety_html = ""
    if safety_checklist and not english_mode:
        items = "".join([f'<li style="margin-bottom:3px;">{s}</li>' for s in safety_checklist])
        safety_html = f"""
<div style="background:#fdebd0; border:1.5px solid #e67e22; border-radius:8px; padding:12px; margin-bottom:14px;">
    <div style="font-weight:800; color:#935116; margin-bottom:8px;">⚠️ רשימת ביטחון לניסוי/פעילות HANDS-ON</div>
    <ul style="font-size:12px; {list_pad}">{items}</ul>
</div>"""

    steam_html = ""
    if (steam_connections or rotation_tip) and not english_mode:
        conn_items = "".join([f'<li style="margin-bottom:3px;">{c}</li>' for c in steam_connections])
        rot_div = f'<div style="margin-top:8px; font-size:12px; color:#555;"><strong>🔄 סיבוב קבוצות:</strong> {rotation_tip}</div>' if rotation_tip else ''
        steam_html = f"""
<div style="background:#eaf4fb; border:1.5px solid #2980b9; border-radius:8px; padding:12px; margin-bottom:14px;">
    <div style="font-weight:800; color:#1a5276; margin-bottom:8px;">🔬 חיבורי STEAM ורב-תחומיות</div>
    <ul style="font-size:12px; {list_pad}">{conn_items}</ul>
    {rot_div}
</div>"""

    # Math-specific sections
    math_prep_html = ""
    if math_mode:
        printing_list = data.get('printing_list', [])
        cutting_prep = data.get('cutting_prep', [])
        anticipated = data.get('anticipated_difficulties', [])
        traffic_cards = data.get('traffic_light_cards_prep', '')
        teacher_topic = data.get('teacher_station_topic', '')
        teacher_opening = data.get('teacher_opening_task', '')

        printing_items = "".join([f"<li>{p}</li>" for p in printing_list])
        cutting_items = "".join([f"<li>{c}</li>" for c in cutting_prep])
        diff_items = "".join([
            f'<div style="margin-bottom:8px; background:white; border-radius:6px; padding:8px;">'
            f'<div style="font-weight:600; color:#4a235a;">{d.get("difficulty","")}</div>'
            f'<div style="font-size:12px; color:#555; margin-top:3px;">💡 {d.get("generic_response","")}</div>'
            f'</div>'
            for d in anticipated
        ])

        math_prep_html = f"""
<div style="display:grid; grid-template-columns:1fr 1fr; gap:14px; margin-bottom:14px;">
    <div style="background:#eafaf1; border:1.5px solid #27ae60; border-radius:8px; padding:12px;">
        <div style="font-weight:800; color:#1e8449; margin-bottom:8px;">🖨️ רשימת הדפסה</div>
        <ul style="font-size:12px; {list_pad} margin:0;">{printing_items}</ul>
    </div>
    <div style="background:#fef9e7; border:1.5px solid #f1c40f; border-radius:8px; padding:12px;">
        <div style="font-weight:800; color:#7d6608; margin-bottom:8px;">✂️ הכנת חיתוכים</div>
        <ul style="font-size:12px; {list_pad} margin:0;">{cutting_items}</ul>
        {f'<div style="font-size:11.5px; color:#7d6608; margin-top:6px; font-style:italic;">🚦 {traffic_cards}</div>' if traffic_cards else ''}
    </div>
</div>
<div style="background:#fffde7; border:2px solid #f1c40f; border-radius:8px; padding:12px; margin-bottom:14px;">
    <div style="font-weight:800; color:#7d6608; margin-bottom:6px;">💛 תחנת המורה — נושא ההקנייה: {teacher_topic}</div>
    <div style="font-size:12.5px;">{teacher_opening}</div>
</div>
{f'<div style="background:#f5eef8; border:1.5px solid #8e44ad; border-radius:8px; padding:12px; margin-bottom:14px;"><div style="font-weight:800; color:#4a235a; margin-bottom:8px;">⚠️ קשיים צפויים ותגובות גנריות מוכנות</div>{diff_items}</div>' if anticipated else ''}"""

    return f"""<!DOCTYPE html>
<html dir="{html_dir}" lang="{html_lang}">
<head><meta charset="UTF-8"><title>{page_title}</title>
<style>{get_css('teacher', english_mode=english_mode, math_mode=math_mode)}</style></head>
<body>
{render_header(title, round_num, 'teacher', include_student_bar=False, english_mode=english_mode, math_mode=math_mode)}

<div style="background:#f5eef8; border:2px solid #8e44ad; border-radius:8px; padding:12px 16px; margin-bottom:14px; font-size:12px; color:#4a235a; font-weight:600;">
    {teacher_only_msg}
</div>

{math_prep_html}
<div style="display:grid; grid-template-columns:1fr 1fr; gap:14px; margin-bottom:14px;">
    <div style="background:#f5eef8; border:1.5px solid #8e44ad; border-radius:8px; padding:12px;">
        <div style="font-weight:800; color:#4a235a; margin-bottom:8px;">{objectives_title}</div>
        <div style="font-size:12px;">
            <strong style="color:#1a5276;">{knowledge_label}</strong><ul style="{list_pad} margin:3px 0 6px 0; font-size:11.5px;">{list_html(objectives.get('knowledge', []))}</ul>
            <strong style="color:#1e8449;">{skills_label}</strong><ul style="{list_pad} margin:3px 0 6px 0; font-size:11.5px;">{list_html(objectives.get('skills', []))}</ul>
            <strong style="color:#7d6608;">{values_label}</strong><ul style="{list_pad} margin:3px 0; font-size:11.5px;">{list_html(objectives.get('values', []))}</ul>
        </div>
    </div>
    <div style="background:#f0f5ff; border:1.5px solid #2980b9; border-radius:8px; padding:12px;">
        <div style="font-weight:800; color:#1a5276; margin-bottom:8px;">{timing_title}</div>
        <div style="font-size:12px;">{timing_html}</div>
    </div>
</div>

<div style="background:#eafaf1; border:1.5px solid #27ae60; border-radius:8px; padding:12px; margin-bottom:14px;">
    <div style="font-weight:800; color:#1e8449; margin-bottom:8px;">{materials_title}</div>
    <div style="font-size:12px;">{mat_html}</div>
</div>
{safety_html}
{steam_html}
<div style="background:#fef9e7; border:1.5px solid #f1c40f; border-radius:8px; padding:12px; margin-bottom:14px;">
    <div style="font-weight:800; color:#7d6608; margin-bottom:8px;">{notes_title}</div>
    <ul style="font-size:12px; {notes_pad}">{list_html(notes)}</ul>
</div>

<div style="background:#fadbd8; border:1.5px solid #e74c3c; border-radius:8px; padding:12px;">
    <div style="font-weight:800; color:#c0392b; margin-bottom:8px;">{diff_title}</div>
    <div style="font-size:12px;">
        <div style="margin-bottom:6px;"><strong>{struggling_label}</strong> {diff.get('struggling', '')}</div>
        <div style="margin-bottom:6px;"><strong>{advanced_label}</strong> {diff.get('advanced', '')}</div>
        <div><strong>{special_label}</strong> {diff.get('special_needs', '')}</div>
    </div>
</div>

<div class="page-footer">{footer_text}</div>
</body></html>"""


def render_answer_key(title: str, round_num: int, precision_data: Dict, vocab_data: Dict,
                       methods_data: Dict, comp_data: Dict = None,
                       english_mode: bool = False, math_mode: bool = False) -> str:
    is_steam_prec = precision_data.get('is_hands_on', False)
    comp_data = comp_data or {}

    if english_mode:
        html_dir = "ltr"
        html_lang = "en"
        page_title = f"Answer Key - {title} - Round {round_num}"
        answers_only_msg = "⚠️ Answer Key — for teacher only"
        prec_title_steam = "🟢 Precision Station HANDS-ON — Expected Results"
        expected_label = "Expected results:"
        q_label = "Q:"
        a_label = "A:"
        prec_title_lang = "🟢 Precision Station — Answer Key"
        spelling_label = "Spelling words:"
        extra_key_label = "Additional answer key:"
        vocab_title = "🟡 Vocabulary Station — Answer Key"
        fill_label = "Fill-in sentence answers:"
        methods_title = "🔵 Success Criteria — Methods Station"
        criteria_label = "Assessment criteria:"
        model_label = "📝 Sample student answer:"
        comp_title = "🔴 Discussion Guidance — Comprehension Station"
        list_pad = "padding-left:18px;"
        footer_text = f"מחולל יחידות לימוד | Answer Key | {title} | Round {round_num} — © All rights reserved"
    else:
        html_dir = "rtl"
        html_lang = "he"
        page_title = f"פתרונות - {title} - סבב {round_num}"
        answers_only_msg = "⚠️ דף פתרונות — למורה בלבד"
        prec_title_steam = "🟢 תחנת דיוק HANDS-ON — תוצאות צפויות"
        expected_label = "תוצאות צפויות:"
        q_label = "ש:"
        a_label = "ת:"
        prec_title_lang = "🟢 פתרונות תחנת דיוק"
        spelling_label = "מילות ההכתבה:"
        extra_key_label = "מפתח תשובות נוסף:"
        vocab_title = "🟡 פתרונות תחנת אוצר מילים"
        fill_label = "תשובות השלמות:"
        methods_title = "🔵 מדדי הצלחה — תחנת שיטות"
        criteria_label = "קריטריונים להערכה:"
        model_label = "📝 תשובה לדוגמה:"
        comp_title = "🔴 הנחיות דיון — תחנת ההבנה"
        list_pad = "padding-right:18px;"
        is_steam = is_steam_prec or vocab_data.get('bilingual', False)
        footer_text = f"א\"ל השד\"ה{' STEAM' if is_steam else ''} | פתרונות ומדדי הצלחה | {title} | סבב {round_num} — © כל הזכויות שמורות"

    if is_steam_prec:
        # STEAM precision answer section: expected results + analysis answers
        analysis_html = ""
        for q in precision_data.get('analysis_questions', []):
            analysis_html += (f'<div style="margin-bottom:8px;"><strong style="color:#1e8449;">{q_label}</strong> {q.get("question","")}'
                              f' → <strong style="color:#c0392b;">{a_label} {q.get("answer","")}</strong></div>')
        prec_section = f"""
        <div style="margin-bottom:16px;">
            <div class="section-title" style="background:#1e8449;">{prec_title_steam}</div>
            <div style="background:#d5f5e3; border-radius:6px; padding:8px; margin-top:8px; font-size:12.5px;">
                <strong>{expected_label}</strong><br>{precision_data.get('expected_results', '')}
            </div>
            <div style="margin-top:10px; font-size:12.5px;">{analysis_html}</div>
        </div>"""
    else:
        # Language / English precision answer section: dictation + exercises
        dict_answers = "".join([
            f'<span class="word-pill">{d.get("word", "")}</span>'
            for d in precision_data.get('dictation_list', [])
        ])
        exercises_answers = ""
        for ex in precision_data.get('exercises', []):
            items = "".join([
                f'<li><strong>{q_label}</strong> {item.get("question", "")} → '
                f'<strong style="color:#1e8449;">{a_label} {item.get("answer", "")}</strong></li>'
                for item in ex.get('items', [])
            ])
            exercises_answers += f"<div style='margin-bottom:10px;'><strong>{ex.get('title', '')}</strong><ul style='{list_pad} font-size:12px;'>{items}</ul></div>"
        prec_section = f"""
        <div style="margin-bottom:16px;">
            <div class="section-title" style="background:#1e8449;">{prec_title_lang}</div>
            <div style="margin-top:8px; font-size:12.5px;">
                <strong>{spelling_label}</strong><br><div style="margin-top:5px;">{dict_answers}</div>
            </div>
            <div style="margin-top:10px;">{exercises_answers}</div>
            <div style="background:#d5f5e3; border-radius:6px; padding:8px; margin-top:6px; font-size:12px;">
                <strong>{extra_key_label}</strong> {precision_data.get('answer_key', '')}
            </div>
        </div>"""

    if english_mode:
        footer_text = f"מחולל יחידות לימוד | Answer Key | {title} | Round {round_num} — © All rights reserved"

    if math_mode and not english_mode:
        html_dir = "rtl"
        html_lang = "he"
        page_title = f"דפי פתרונות מלאים — {title} — סבב {round_num}"
        answers_only_msg = "⚠️ דף פתרונות — למורה בלבד"
        footer_text = f"מתמטיקה יומית — א\"ל השד\"ה | פתרונות מלאים | {title} | סבב {round_num} — © כל הזכויות שמורות"
        prec_title_lang = '🟢 פתרונות קבוצת ניצ"ה'
        vocab_title = "🟡 פתרונות מתמטיקה עם המורה"
        methods_title = "🔵 מדדי הצלחה — מתמטיקה עם חבר"
        comp_title = "🔴 הנחיות דיון — מתמטיקה בעצמי"

    # ── Comprehension section (discussion notes) ──────────────────────────
    disc_notes = comp_data.get('discussion_notes', [])
    written_model = (comp_data.get('written_response_model', '') or
                     comp_data.get('answer_guide', ''))
    comp_section = ""
    if disc_notes or written_model:
        notes_html = "".join([
            f'<div style="margin-bottom:10px; padding:8px; background:#fff; border-radius:6px; border:1px solid #e8d4d4;">'
            f'<div style="font-weight:600; color:#c0392b; font-size:12.5px;">{n.get("question","")}</div>'
            f'<div style="font-size:12px; color:#555; margin-top:4px;">💡 {n.get("key_ideas","")}</div>'
            f'</div>'
            for n in disc_notes
        ])
        model_html = (f'<div style="background:#fde8e8; border-radius:6px; padding:8px; margin-top:8px; font-size:12px;">'
                      f'<strong>✍️ תשובה כתובה לדוגמה:</strong><br>{written_model}</div>'
                      if written_model else "")
        comp_section = f"""
<div style="margin-bottom:16px;">
    <div class="section-title" style="background:#c0392b;">{comp_title}</div>
    <div style="margin-top:8px;">{notes_html}{model_html}</div>
</div>"""

    # ── Vocabulary fill-sentences answers ─────────────────────────────────
    fill_html = ""
    fill_sentences = vocab_data.get('fill_sentences', [])
    if fill_sentences:
        fills = "".join([
            f'<li style="margin-bottom:4px;">{fs.get("sentence","").replace("_____", "<u>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</u>")} '
            f'→ <strong style="color:#7d6608;">{fs.get("answer","")}</strong></li>'
            for fs in fill_sentences
        ])
        fill_html = f'<div style="margin-top:8px;"><strong>{fill_label}</strong><ul style="{list_pad} font-size:12px;">{fills}</ul></div>'

    # ── Methods model answer ───────────────────────────────────────────────
    model_answer = (methods_data.get('model_answer', '') or
                    methods_data.get('sample_work', '') or
                    methods_data.get('model_solution', ''))
    model_html = ""
    if model_answer:
        model_html = (f'<div style="background:#e8f4fd; border:1px solid #2980b9; border-radius:6px; '
                      f'padding:8px; margin-top:10px; font-size:12px;">'
                      f'<strong>{model_label}</strong><br>{model_answer}</div>')

    return f"""<!DOCTYPE html>
<html dir="{html_dir}" lang="{html_lang}">
<head><meta charset="UTF-8"><title>{page_title}</title>
<style>{get_css('answers', english_mode=english_mode, math_mode=math_mode)}</style></head>
<body>
{render_header(title, round_num, 'answers', include_student_bar=False, english_mode=english_mode, math_mode=math_mode)}

<div style="background:#eaf2ff; border:2px solid #2c5aa0; border-radius:8px; padding:8px 14px; margin-bottom:14px; font-size:12px; font-weight:600; color:#1a3a6b;">
    {answers_only_msg}
</div>

{comp_section}

{prec_section}

<div style="margin-bottom:16px;">
    <div class="section-title" style="background:#7d6608;">{vocab_title}</div>
    <div style="background:#fef9e7; border:1px solid #f1c40f; border-radius:6px; padding:10px; margin-top:8px; font-size:12.5px;">
        {vocab_data.get('answer_key', '')}
    </div>
    {fill_html}
</div>

<div style="margin-bottom:16px;">
    <div class="section-title" style="background:#1a5276;">{methods_title}</div>
    <div style="margin-top:8px; font-size:12.5px;">
        <strong>{criteria_label}</strong>
        <ul style="{list_pad}">{"".join([f"<li>{c}</li>" for c in methods_data.get('success_criteria', [])])}</ul>
        {model_html}
    </div>
</div>

<div class="page-footer">{footer_text}</div>
</body></html>"""
