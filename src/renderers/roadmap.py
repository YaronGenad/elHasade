from typing import Dict
from .css import get_css


def render_roadmap(title: str, roadmap: Dict, english_mode: bool = False) -> str:
    is_steam = roadmap.get('is_steam', False)
    goals_raw = roadmap.get('learning_goals', [])
    # learning_goals can be a list or a dict with knowledge/skills/values
    if isinstance(goals_raw, dict):
        goals_flat = (list(goals_raw.get('knowledge') or []) + list(goals_raw.get('skills') or []) + list(goals_raw.get('values') or []))
    else:
        goals_flat = goals_raw
    goals = "".join([
        f'<span class="word-pill" style="background:#eaf2ff; border-color:#2c5aa0; color:#1a3a6b;">{g}</span>'
        for g in goals_flat
    ])

    # Adapt column headers + central line based on mode
    if english_mode:
        col1_header = "Round"
        col2_header = "🔵 Methods Station<br><small>(structured writing)</small>"
        col3_header = "🟢 Precision Station<br><small>(spelling & grammar)</small>"
        col4_header = "🟡 Vocabulary Station<br><small>(printed/hands-on activity)</small>"
        comp_header = "🔴 Comprehension Station<br><small>(text + oral discussion)</small>"
        central_line = f"<strong>Central text type:</strong> {roadmap.get('central_text_type', '')} | <strong>Language focus:</strong> {roadmap.get('language_focus', '')}"
        mode_badge = '<span style="background:#1a5276; color:white; padding:3px 12px; border-radius:14px; font-size:12px; margin-right:8px;">🇬🇧 English Edition</span>'
        iron_rule = "All 4 stations in every round are <strong>fully independent (STAND-ALONE)</strong> — a student can start at any station without depending on the others."
        goals_label = "Learning Goals:"
        rounds_label = "Round"
        iron_label = "⚡ Iron Rule:"
        html_dir = "ltr"
        html_lang = "en"
        page_title = f"Unit Roadmap - {title}"
        footer_text = f"Al-HaSadeh | Unit Roadmap | {title} — © All rights reserved"
        method_label = "שיטת א\"ל השד\"ה"
        rounds_count_label = "rounds"
    elif is_steam:
        col1_header = "סבב"
        col3_header = "🟢 תחנת דיוק<br><small>(HANDS-ON ניסוי/בנייה)</small>"
        col4_header = "🟡 תחנת אוצר מילים<br><small>(מושגי STEAM + עברית/אנגלית)</small>"
        col2_header = "🔵 תחנת שיטות<br><small>(חשיבה תהליכית-מדעית)</small>"
        comp_header = "🔴 תחנת הבנה<br><small>(ערוצי קלט מגוונים)</small>"
        central_line = f"<strong>התופעה המרכזית:</strong> {roadmap.get('central_phenomenon', roadmap.get('central_text_type', ''))}"
        mode_badge = '<span style="background:#e74c3c; color:white; padding:3px 12px; border-radius:14px; font-size:12px; margin-right:8px;">🔬 STEAM Edition</span>'
        iron_rule = "כל 4 תחנות בכל סבב הן <strong>עצמאיות לחלוטין (STAND-ALONE)</strong> — גם בגרסת STEAM! אם תחנה צריכה תוצר מתחנה אחרת — הכניסי אותו ישירות."
        goals_label = "מטרות הלמידה:"
        rounds_label = "סבב"
        iron_label = "⚡ עקרון ברזל:"
        html_dir = "rtl"
        html_lang = "he"
        page_title = f"מפת דרכים - {title}"
        footer_text = f"א\"ל השד\"ה STEAM | מפת דרכים | {title} — © כל הזכויות שמורות"
        method_label = "שיטת א\"ל השד\"ה"
        rounds_count_label = "סבבים"
    else:
        col1_header = "סבב"
        col3_header = "🟢 תחנת דיוק<br><small>(לשון ודקדוק)</small>"
        col4_header = "🟡 תחנת אוצר מילים<br><small>(פעילות מודפסת)</small>"
        col2_header = "🔵 תחנת שיטות<br><small>(כתיבה מובנית)</small>"
        comp_header = "🔴 תחנת הבנה<br><small>(טקסט + דיון בע\"פ)</small>"
        central_line = f"<strong>טקסט מרכזי:</strong> {roadmap.get('central_text_type', '')}"
        mode_badge = ""
        iron_rule = "כל 4 תחנות בכל סבב הן <strong>עצמאיות לחלוטין</strong> — תלמיד יכול להתחיל בכל תחנה ולעבור לכל תחנה בלי תלות בתחנות אחרות."
        goals_label = "מטרות הלמידה:"
        rounds_label = "סבב"
        iron_label = "⚡ עקרון ברזל:"
        html_dir = "rtl"
        html_lang = "he"
        page_title = f"מפת דרכים - {title}"
        footer_text = f"א\"ל השד\"ה | מפת דרכים | {title} — © כל הזכויות שמורות"
        method_label = "שיטת א\"ל השד\"ה"
        rounds_count_label = "סבבים"

    # Per-round rows
    rounds_html = ""
    for r in roadmap.get('rounds', []):
        rn = r.get('round', '')
        comp = r.get('comprehension', {})
        meth = r.get('methods', {})
        prec = r.get('precision', {})
        vocab = r.get('vocabulary', {})

        comp_type = comp.get('input_type') or comp.get('text_type', '')
        meth_type = meth.get('thinking_framework') or meth.get('writing_type', '')
        prec_type = prec.get('hands_on_type') or prec.get('activity_type', '')
        vocab_type = vocab.get('game_type') or vocab.get('activity_type', '')

        rounds_html += f"""
        <tr>
            <td style="font-weight:800; text-align:center; background:#f8f9fa; font-size:14px;">{rounds_label} {rn}</td>
            <td style="background:#fadbd8;">
                <div style="font-weight:700; color:#c0392b; font-size:11px;">🔴 {comp_type}</div>
                <div style="font-size:11.5px; margin-top:3px;">{comp.get('description', '')}</div>
            </td>
            <td style="background:#d6eaf8;">
                <div style="font-weight:700; color:#1a5276; font-size:11px;">🔵 {meth_type}</div>
                <div style="font-size:11.5px; margin-top:3px;">{meth.get('description', '')}</div>
            </td>
            <td style="background:#d5f5e3;">
                <div style="font-weight:700; color:#1e8449; font-size:11px;">🟢 {prec_type}</div>
                <div style="font-size:11.5px; margin-top:3px;">{prec.get('description', '')}</div>
            </td>
            <td style="background:#fef9e7;">
                <div style="font-weight:700; color:#7d6608; font-size:11px;">🟡 {vocab_type}</div>
                <div style="font-size:11.5px; margin-top:3px;">{vocab.get('description', '')}</div>
            </td>
        </tr>
        """

    return f"""<!DOCTYPE html>
<html dir="{html_dir}" lang="{html_lang}">
<head><meta charset="UTF-8"><title>{page_title}</title>
<style>{get_css('teacher')}
.roadmap-table {{ width:100%; border-collapse:collapse; }}
.roadmap-table th {{ background:#4a235a; color:white; padding:10px 12px; font-size:13px; }}
.roadmap-table td {{ border:1.5px solid #ddd; padding:10px 12px; vertical-align:top; }}
</style></head>
<body>
<div style="background:linear-gradient(135deg, #4a235a, #8e44ad); color:white; padding:16px; border-radius:10px; margin-bottom:16px;">
    <div style="font-size:22px; font-weight:800; text-align:center; margin-bottom:4px;">{mode_badge}📋 {'Unit Roadmap' if english_mode else 'מפת דרכים'} — {roadmap.get('unit_title', title)}</div>
    <div style="font-size:13px; text-align:center; opacity:0.9;">{method_label} | {len(roadmap.get('rounds', []))} {rounds_count_label}</div>
</div>

<div style="margin-bottom:14px; font-size:12.5px;">
    <strong>{goals_label}</strong> {goals}<br>
    <span style="margin-top:6px; display:inline-block;">{central_line}</span>
</div>

<table class="roadmap-table">
    <tr>
        <th>{col1_header}</th>
        <th>{comp_header}</th>
        <th>{col2_header}</th>
        <th>{col3_header}</th>
        <th>{col4_header}</th>
    </tr>
    {rounds_html}
</table>

<div style="margin-top:14px; background:#fef9e7; border:1.5px solid #f1c40f; border-radius:8px; padding:10px; font-size:12px;">
    <strong>{iron_label}</strong> {iron_rule}
</div>

<div class="page-footer">{footer_text}</div>
</body></html>"""
