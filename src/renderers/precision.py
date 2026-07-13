from typing import Dict, Optional
from ..config import STATION_COLORS
from .css import get_css, ENGLISH_LABELS
from .header import render_header


def render_precision(title: str, round_num: int, data: Dict, english_mode: bool = False,
                     math_mode: bool = False,
                     topic_image: Optional[str] = None,
                     decorative_image: Optional[str] = None) -> str:
    # ── Math ניצ"ה branch ──────────────────────────────────────────
    if math_mode or data.get('is_math_nitzah'):
        return _render_math_precision(title, round_num, data, topic_image=topic_image,
                                      decorative_image=decorative_image)

    # ── STEAM HANDS-ON branch ──────────────────────────────────────
    if data.get('is_hands_on'):
        return _render_stem_precision(title, round_num, data, topic_image=topic_image,
                                      decorative_image=decorative_image)

    # ── Language / English grammar branch ─────────────────────────
    if english_mode:
        lbl = ENGLISH_LABELS
        diff_color = {"easy": "#d5f5e3", "medium": "#fef9e7", "hard": "#fadbd8",
                      "קל": "#d5f5e3", "בינוני": "#fef9e7", "קשה": "#fadbd8"}
        dictation_title = lbl['dictation_title']
        dictation_note = lbl['dictation_note']
        word_th = lbl['word']
        spelling_th = lbl['spelling']
        sentences_title = lbl['sentences_title']
        instruction_suffix = "Work in pairs: one dictates, the other writes — then swap."
        html_dir = "ltr"
        html_lang = "en"
        page_title = f"Precision Station - {title} - Round {round_num}"
        footer_text = f"מחולל יחידות לימוד | Precision Station | {title} | Round {round_num} — {lbl['footer_copy']}"
        list_padding = "padding-left:20px;"
    else:
        diff_color = {"קל": "#d5f5e3", "בינוני": "#fef9e7", "קשה": "#fadbd8"}
        dictation_title = "✏️ הכתבה ({n} מילים)"
        dictation_note = "* עמית/ה מכתיב/ה, אתה/את כותב/ת בשורה הריקה"
        word_th = "מילה"
        spelling_th = "הכתבה"
        sentences_title = "📝 הכתבת משפטים (למורה)"
        instruction_suffix = "עבוד/י בזוגות: אחד/ת מכתיב/ה, השני/ה כותב/ת ומחליפים."
        html_dir = "rtl"
        html_lang = "he"
        page_title = f"תחנת דיוק - {title} - סבב {round_num}"
        footer_text = f"א\"ל השד\"ה | תחנת דיוק | {title} | סבב {round_num} — © כל הזכויות שמורות"
        list_padding = "padding-right:20px;"

    dict_items = data.get('dictation_list', [])
    dict_rows = ""
    for i in range(0, len(dict_items), 2):
        w1 = dict_items[i] if i < len(dict_items) else {}
        w2 = dict_items[i + 1] if i + 1 < len(dict_items) else {}
        c1 = diff_color.get(w1.get('difficulty', 'בינוני'), '#fff')
        c2 = diff_color.get(w2.get('difficulty', 'בינוני'), '#fff')
        note1 = f"<br><span style='font-size:10px;color:#888;'>{w1.get('note', '')}</span>" if w1.get('note') else ""
        note2 = f"<br><span style='font-size:10px;color:#888;'>{w2.get('note', '')}</span>" if w2.get('note') else ""
        dict_rows += f"""
        <tr>
            <td style="text-align:center; background:{c1}; font-weight:700;">{i + 1}. {w1.get('word', '')}{note1}</td>
            <td style="min-width:120px;"></td>
            <td style="text-align:center; background:{c2}; font-weight:700;">{i + 2}. {w2.get('word', '')}{note2}</td>
            <td style="min-width:120px;"></td>
        </tr>
        """

    dictation_html = f"""
    <div class="section-block">
    <div class="section-title">✏️ {dictation_title.format(n=len(dict_items))}</div>
    <div style="font-size:11px; color:#888; margin-bottom:6px;">{dictation_note}</div>
    <table><tr><th>{word_th}</th><th>{spelling_th}</th><th>{word_th}</th><th>{spelling_th}</th></tr>{dict_rows}</table>
    </div>
    """ if dict_items else ""

    exercises_html = ""
    for ex in data.get('exercises', []):
        items_html = ""
        for item in ex.get('items', []):
            items_html += f"""
            <div style="display:flex; align-items:flex-start; gap:8px; margin-bottom:10px;">
                <div style="font-size:13px; flex:1; font-weight:600;">{item.get('question', '')}</div>
                <div style="flex:2; border-bottom:1.5px solid #aaa; min-height:20px;"></div>
            </div>
            """
        exercises_html += f"""
        <div class="section-block" style="margin-bottom:16px;">
            <div class="section-title">{ex.get('title', '')}</div>
            <div style="font-size:12.5px; color:#555; margin:6px 0 10px 0; font-style:italic;">{ex.get('instruction', '')}</div>
            {items_html}
        </div>
        """

    sent_html = ""
    if data.get('sentences_for_dictation'):
        sents = "".join([f'<li style="margin-bottom:3px;">{s}</li>' for s in data.get('sentences_for_dictation', [])])
        sent_html = f"""
        <div style="margin-top:14px; break-inside:avoid; page-break-inside:avoid;">
            <div class="section-title">📝 {sentences_title}</div>
            <ol style="font-size:12.5px; {list_padding} color:#555;">{sents}</ol>
        </div>
        """

    # Topic image float
    image_html = ""
    if topic_image:
        try:
            from ..images import ImageService
            data_url = ImageService.to_data_url(topic_image)
            c = STATION_COLORS['precision']
            image_html = f"""
            <div style="float:left; margin:0 0 14px 18px; clear:left;">
                <img src="{data_url}"
                     style="width:210px; height:145px; object-fit:cover;
                            border-radius:12px; border:3px solid {c['border']};
                            box-shadow:0 4px 10px rgba(0,0,0,0.22); display:block;" alt="">
            </div>"""
        except Exception:
            pass

    decorative_html = ""
    if decorative_image:
        try:
            from ..images import ImageService
            dec_url = ImageService.to_data_url(decorative_image)
            decorative_html = f"""
            <div style="clear:both; margin-top:14px; text-align:center;
                        break-before:avoid; page-break-before:avoid; break-inside:avoid;">
                <img src="{dec_url}"
                     style="max-width:100%; max-height:130px; object-fit:contain;
                            border-radius:8px; opacity:0.92;" alt="">
            </div>"""
        except Exception:
            pass

    return f"""<!DOCTYPE html>
<html dir="{html_dir}" lang="{html_lang}">
<head><meta charset="UTF-8"><title>{page_title}</title>
<style>{get_css('precision', english_mode=english_mode, math_mode=False)}</style></head>
<body>
{render_header(title, round_num, 'precision', english_mode=english_mode, math_mode=False)}
{image_html}
<div class="instruction-box">📌 {data.get('title', '')} — {instruction_suffix}</div>
{dictation_html}
{exercises_html}
{sent_html}
{decorative_html}
<div class="page-footer">{footer_text}</div>
</body></html>"""


def _render_stem_precision(title: str, round_num: int, data: Dict,
                           topic_image: Optional[str] = None,
                           decorative_image: Optional[str] = None) -> str:
    """Renders the STEAM HANDS-ON lab card for the precision station."""
    c = STATION_COLORS['precision']

    type_badges = {
        'science_experiment': ('🔬', 'ניסוי מדעי'),
        'measurement_data': ('📏', 'מדידות ואיסוף נתונים'),
        'engineering_building': ('🏗️', 'בנייה הנדסית'),
        'math_hands_on': ('📐', 'מתמטיקה מוחשית'),
        'art_design': ('🎨', 'יצירה ועיצוב מדעי'),
    }
    emoji, label = type_badges.get(data.get('hands_on_type', ''), ('🔬', 'פעילות מדעית'))

    # Background box
    bg_html = ""
    if data.get('background_mini'):
        bg_html = f"""
        <div style="background:#eafaf1; border:1.5px solid #27ae60; border-radius:8px; padding:10px 14px; margin-bottom:12px; font-size:12.5px;">
            <strong style="color:#1e8449;">📖 רקע קצר:</strong> {data['background_mini']}
        </div>"""

    # Research question + hypothesis
    rq_html = f"""
    <div class="section-block" style="margin-bottom:12px;">
        <div class="section-title">❓ שאלת החקירה</div>
        <div style="font-size:14px; font-weight:700; color:#1e8449; padding:8px 0;">{data.get('research_question', '')}</div>
        <div style="font-size:12.5px; color:#555; font-style:italic;">ההשערה שלי: {data.get('hypothesis_scaffold', '_____ כי _____')}</div>
        <div class="answer-line" style="margin-top:6px;"></div>
    </div>"""

    # Materials
    materials = data.get('materials_needed', [])
    safety = data.get('safety_notes', [])
    mat_items = "".join([f"<li>{m}</li>" for m in materials])
    safety_items = "".join([f"<li style='color:#c0392b;'>⚠️ {s}</li>" for s in safety])
    mat_html = ""
    if materials:
        mat_html = f"""
        <div class="materials-box">
            <div class="materials-box-title">🎒 מה צריך להכין:</div>
            <ul class="materials-list">{mat_items}</ul>
            {f'<ul style="padding:6px 0 0 0; margin:0; list-style:none; font-size:11.5px;">{safety_items}</ul>' if safety else ''}
        </div>"""

    # Steps
    steps = data.get('steps', [])
    steps_li = "".join([f"<li>{s}</li>" for s in steps])
    steps_html = f"""
    <div class="steps-box">
        <div class="steps-box-title">📋 שלבי הפעילות:</div>
        <ol class="steps-list">{steps_li}</ol>
    </div>""" if steps else ""

    # Data table
    dt = data.get('data_table', {})
    headers = dt.get('headers', [])
    rows = dt.get('rows', [])
    table_html = ""
    if headers:
        th_html = "".join([f"<th>{h}</th>" for h in headers])
        tr_html = "".join([
            "<tr>" + "".join([f"<td style='min-height:28px; height:28px;'>{cell}</td>" for cell in row]) + "</tr>"
            for row in rows
        ])
        table_html = f"""
        <div class="section-block" style="margin-bottom:12px;">
            <div class="section-title">📊 טבלת תיעוד תוצאות</div>
            <table style="margin-top:8px;"><tr>{th_html}</tr>{tr_html}</table>
        </div>"""

    # Analysis questions
    analysis = data.get('analysis_questions', [])
    analysis_html = ""
    if analysis:
        q_items = "".join([f"""
        <div style="margin-bottom:12px;">
            <div style="font-size:13px; font-weight:600; color:#1e8449;">{q.get('question', '')}</div>
            <div class="answer-line"></div><div class="answer-line"></div>
        </div>""" for q in analysis])
        analysis_html = f"""
        <div class="section-block" style="margin-bottom:12px;">
            <div class="section-title">🔍 שאלות ניתוח</div>
            {q_items}
        </div>"""

    # Conclusion scaffold
    conc = data.get('conclusion_scaffold', '')
    conc_html = f"""
    <div class="section-block" style="margin-bottom:12px;">
        <div class="section-title">💡 מסקנה</div>
        <div style="font-size:12.5px; color:#555; margin:6px 0 8px; font-style:italic;">{conc}</div>
        <div class="answer-line"></div><div class="answer-line"></div>
    </div>""" if conc else ""

    # Difficulty levels
    dl = data.get('difficulty_levels', {})
    traffic_html = f"""
    <div class="traffic-light">
        <div class="tl-green"><div class="tl-label">🟢 קל</div>{dl.get('green', '')}</div>
        <div class="tl-yellow"><div class="tl-label">🟡 בינוני</div>{dl.get('yellow', '')}</div>
        <div class="tl-red"><div class="tl-label">🔴 מאתגר</div>{dl.get('red', '')}</div>
    </div>""" if dl else ""

    # Graph scaffold (empty graph box for students to draw results)
    graph = data.get('graph_scaffold', {})
    graph_html = ""
    if graph:
        graph_html = f"""
    <div class="section-block" style="margin-bottom:12px;">
        <div class="section-title">📈 {graph.get('title', 'גרף תוצאות')}</div>
        <div style="font-size:11.5px; color:#555; margin-bottom:6px; font-style:italic;">{graph.get('note', '')}</div>
        <div style="position:relative; border:2px solid #27ae60; border-radius:6px; height:170px; background:#f9fef9; margin-top:6px; overflow:hidden;">
            <div style="position:absolute; left:0; top:50%; transform:rotate(-90deg) translateX(50%); transform-origin:left center; font-size:10px; color:#555; white-space:nowrap;">{graph.get('y_axis_label', '')}</div>
            <div style="position:absolute; bottom:4px; left:50%; transform:translateX(-50%); font-size:10px; color:#555; white-space:nowrap;">{graph.get('x_axis_label', '')}</div>
        </div>
    </div>"""

    # Self-assessment
    sa = data.get('self_assessment', [])
    sa_html = ""
    if sa:
        sa_items = "".join([
            f'<div style="margin-bottom:10px; font-size:12.5px;">'
            f'<strong>☐ {item}</strong>'
            f'<div class="answer-line"></div></div>'
            for item in sa
        ])
        sa_html = f"""
    <div style="margin-top:12px; background:#eaf3fb; border:1.5px solid #2980b9;
         border-radius:8px; padding:12px 14px; break-before:avoid; page-break-before:avoid; break-inside:avoid;">
        <div class="section-title">✅ הערכה עצמית</div>
        {sa_items}
    </div>"""

    stem_image_html = ""
    if topic_image:
        try:
            from ..images import ImageService
            data_url = ImageService.to_data_url(topic_image)
            stem_image_html = f"""
            <div style="float:left; margin:0 0 14px 18px; clear:left;">
                <img src="{data_url}"
                     style="width:210px; height:145px; object-fit:cover;
                            border-radius:12px; border:3px solid {c['border']};
                            box-shadow:0 4px 10px rgba(0,0,0,0.22); display:block;" alt="">
            </div>"""
        except Exception:
            pass

    stem_decorative_html = ""
    if decorative_image:
        try:
            from ..images import ImageService
            dec_url = ImageService.to_data_url(decorative_image)
            stem_decorative_html = f"""
            <div style="clear:both; margin-top:14px; text-align:center;
                        break-before:avoid; page-break-before:avoid; break-inside:avoid;">
                <img src="{dec_url}"
                     style="max-width:100%; max-height:130px; object-fit:contain;
                            border-radius:8px; opacity:0.92;" alt="">
            </div>"""
        except Exception:
            pass

    return f"""<!DOCTYPE html>
<html dir="rtl" lang="he">
<head><meta charset="UTF-8"><title>תחנת דיוק STEAM - {title} - סבב {round_num}</title>
<style>{get_css('precision')}</style></head>
<body>
{render_header(title, round_num, 'precision')}
{stem_image_html}
<div class="instruction-box">
    <span style="background:{c['primary']}; color:white; padding:3px 10px; border-radius:12px; font-size:12px; margin-left:8px;">{emoji} {label}</span>
    📌 {data.get('title', '')} — תחנת HANDS-ON: בצע/י את הפעילות ותעד/י את הממצאים
</div>
{bg_html}
{rq_html}
{mat_html}
{steps_html}
{table_html}
{analysis_html}
{conc_html}
{graph_html}
{traffic_html}
{sa_html}
{stem_decorative_html}
<div class="page-footer">א"ל השד"ה STEAM | תחנת דיוק HANDS-ON | {title} | סבב {round_num} — © כל הזכויות שמורות</div>
</body></html>"""


def _render_math_precision(title: str, round_num: int, data: Dict,
                            topic_image: Optional[str] = None,
                            decorative_image: Optional[str] = None) -> str:
    """Renders the ניצ\"ה — נצא מהקופסה station for math mode."""
    c = STATION_COLORS['precision']

    # Formula box (instruction + example + rule)
    formula = data.get('formula', {})
    formula_html = ""
    if formula:
        formula_html = f"""
    <div style="background:#eafaf1; border:2px solid #27ae60; border-radius:8px; padding:12px 14px; margin-bottom:12px;">
        <div style="font-weight:700; color:#1e8449; margin-bottom:6px;">📐 נוסחת הצלחה (שלושה רכיבים חובה)</div>
        <div style="font-size:13px; margin-bottom:4px;"><strong>1. הוראה מפורשת:</strong> {formula.get('explicit_instruction', '')}</div>
        <div style="font-size:13px; margin-bottom:4px;"><strong>2. דוגמה פתורה:</strong> {formula.get('solved_example', '')}</div>
        <div style="font-size:13px;"><strong>3. הכלל הגנרי:</strong> {formula.get('generic_rule', '')}</div>
    </div>"""

    # Context (real-world scenario)
    context_html = ""
    if data.get('context'):
        context_html = f"""
    <div style="background:#fef9e7; border:1.5px solid #f39c12; border-radius:8px; padding:10px 14px; margin-bottom:12px; font-size:13px;">
        <strong style="color:#e67e22;">📖 הקשר מציאותי:</strong> {data['context']}
    </div>"""

    # Traffic light (3 levels)
    dl = data.get('difficulty_levels', {})
    traffic_html = f"""
    <div class="traffic-light">
        <div class="tl-green"><div class="tl-label">🟢 קל</div>{dl.get('green', '')}</div>
        <div class="tl-yellow"><div class="tl-label">🟡 בינוני</div>{dl.get('yellow', '')}</div>
        <div class="tl-red"><div class="tl-label">🔴 מאתגר</div>{dl.get('red', '')}</div>
    </div>""" if dl else ""

    # Exercises (multi-step problems)
    exercises_html = ""
    for ex in data.get('exercises', []):
        items_html = ""
        for item in ex.get('items', []):
            items_html += f"""
            <div style="display:flex; align-items:flex-start; gap:8px; margin-bottom:12px;">
                <div style="font-size:13px; flex:1; font-weight:600;">{item.get('question', '')}</div>
                <div style="flex:2;">
                    <div class="answer-line"></div>
                    <div class="answer-line"></div>
                </div>
            </div>
            """
        exercises_html += f"""
        <div class="section-block" style="margin-bottom:16px;">
            <div class="section-title" style="color:#1e8449;">{ex.get('title', '')}</div>
            <div style="font-size:12.5px; color:#555; margin:6px 0 10px; font-style:italic;">{ex.get('instruction', '')}</div>
            {items_html}
        </div>
        """

    # Open question
    open_q_html = ""
    if data.get('open_question'):
        open_q_html = f"""
    <div style="background:#d5f5e3; border:1.5px solid #27ae60; border-radius:8px; padding:10px 14px; margin-bottom:12px;">
        <div style="font-weight:700; color:#1e8449; margin-bottom:6px;">💭 שאלה פתוחה:</div>
        <div style="font-size:13px; margin-bottom:8px;">{data['open_question']}</div>
        <div class="answer-line"></div><div class="answer-line"></div>
    </div>"""

    # Teacher note (hidden in student copy, shown in teacher prep)
    tn = data.get('teacher_note', {})
    teacher_note_html = ""
    if tn:
        hints_html = "".join([f"<li>{h}</li>" for h in tn.get('hints', [])])
        ext_html = "".join([f"<li>{e}</li>" for e in tn.get('discussion_extensions', [])])
        academic = tn.get('academic_source') or ''
        teacher_note_html = f"""
    <div style="background:#f5eef8; border:2px dashed #8e44ad; border-radius:8px; padding:10px 14px; margin-top:12px; font-size:12px;">
        <div style="font-weight:700; color:#4a235a; margin-bottom:6px;">📋 הערת מורה (לא לתלמידים)</div>
        <div style="margin-bottom:4px;"><strong>מטרה:</strong> {tn.get('pedagogical_goal', '')}</div>
        {f'<ul style="padding-right:18px; margin:4px 0;">{hints_html}</ul>' if hints_html else ''}
        {f'<div style="margin-top:4px;"><strong>הרחבה לדיון:</strong><ul style="padding-right:18px; margin:2px 0;">{ext_html}</ul></div>' if ext_html else ''}
        {f'<div style="margin-top:4px; font-size:11px; color:#888;"><em>מקור: {academic}</em></div>' if academic else ''}
    </div>"""

    # Topic image
    image_html = ""
    if topic_image:
        try:
            from ..images import ImageService
            data_url = ImageService.to_data_url(topic_image)
            image_html = f"""
            <div style="float:left; margin:0 0 14px 18px; clear:left;">
                <img src="{data_url}"
                     style="width:210px; height:145px; object-fit:cover;
                            border-radius:12px; border:3px solid {c['border']};
                            box-shadow:0 4px 10px rgba(0,0,0,0.22); display:block;" alt="">
            </div>"""
        except Exception:
            pass

    decorative_html = ""
    if decorative_image:
        try:
            from ..images import ImageService
            dec_url = ImageService.to_data_url(decorative_image)
            decorative_html = f"""
            <div style="clear:both; margin-top:14px; text-align:center;">
                <img src="{dec_url}" style="max-width:100%; max-height:130px; object-fit:contain; border-radius:8px; opacity:0.92;" alt="">
            </div>"""
        except Exception:
            pass

    return f"""<!DOCTYPE html>
<html dir="rtl" lang="he">
<head><meta charset="UTF-8"><title>קבוצת ניצ"ה — {title} — סבב {round_num}</title>
<style>{get_css('precision', math_mode=True)}</style></head>
<body>
{render_header(title, round_num, 'precision', math_mode=True)}
{image_html}
<div class="instruction-box">📌 {data.get('title', 'קבוצת ניצ"ה — נצא מהקופסה')} — {data.get('main_instruction', 'פתרו את הבעיות המציאותיות הבאות')}</div>
{formula_html}
{context_html}
{traffic_html}
{exercises_html}
{open_q_html}
{teacher_note_html}
{decorative_html}
<div class="page-footer">מתמטיקה יומית — א"ל השד"ה | קבוצת ניצ"ה | {title} | סבב {round_num} — © כל הזכויות שמורות</div>
</body></html>"""
