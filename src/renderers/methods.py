from typing import Dict
from .css import get_css, ENGLISH_LABELS
from .header import render_header


def render_methods(title: str, round_num: int, data: Dict, english_mode: bool = False) -> str:
    lines_html = "".join([f'<div class="writing-line"></div>' for _ in range(data.get('lines_needed', 10))])

    dl = data.get('difficulty_levels', {})
    if english_mode:
        lbl = ENGLISH_LABELS
        traffic = f"""
        <div class="traffic-light">
            <div class="tl-green"><div class="tl-label">{lbl['traffic_green']}</div>{dl.get('green', '')}</div>
            <div class="tl-yellow"><div class="tl-label">{lbl['traffic_yellow']}</div>{dl.get('yellow', '')}</div>
            <div class="tl-red"><div class="tl-label">{lbl['traffic_red']}</div>{dl.get('red', '')}</div>
        </div>
        """
        scaffold_title = "\U0001f4dd Writing Structure (scaffold)"
        write_title = "\u270f\ufe0f Write here:"
        guiding_title = "\u2753 Guiding Questions"
        scope_label = "Scope:"
        footer_text = f"Al-HaSadeh | Methods Station | {title} | Round {round_num} \u2014 {lbl['footer_copy']}"
        html_dir = "ltr"
        html_lang = "en"
        page_title = f"Methods Station - {title} - Round {round_num}"
        list_padding = "padding-left:20px;"
    else:
        traffic = f"""
        <div class="traffic-light">
            <div class="tl-green"><div class="tl-label">\U0001f7e2 \u05d1\u05e1\u05d9\u05e1\u05d9</div>{dl.get('green', '')}</div>
            <div class="tl-yellow"><div class="tl-label">\U0001f7e1 \u05e8\u05d2\u05d9\u05dc</div>{dl.get('yellow', '')}</div>
            <div class="tl-red"><div class="tl-label">\U0001f534 \u05de\u05d0\u05ea\u05d2\u05e8</div>{dl.get('red', '')}</div>
        </div>
        """
        scope_label = "\u05d4\u05d9\u05e7\u05e3:"
        guiding_title = "\u2753 \u05e9\u05d0\u05dc\u05d5\u05ea \u05de\u05e0\u05d7\u05d5\u05ea"
        html_dir = "rtl"
        html_lang = "he"
        page_title = f"\u05ea\u05d7\u05e0\u05ea \u05e9\u05d9\u05d8\u05d5\u05ea - {title} - \u05e1\u05d1\u05d1 {round_num}"
        list_padding = "padding-right:20px;"

    guiding = "".join([f'<li style="margin-bottom:4px;">{q}</li>' for q in data.get('guiding_questions', [])])
    scaffold = data.get('scaffold_template', '').replace('\n', '<br>')

    # STEAM: framework steps + context data
    framework_steps = data.get('framework_steps', [])
    fw_steps_html = ""
    if framework_steps:
        fw_label = {
            'scientific_method': '\U0001f52c \u05de\u05ea\u05d5\u05d3\u05d4 \u05de\u05d3\u05e2\u05d9\u05ea',
            'EDP': '\U0001f3d7\ufe0f \u05ea\u05d4\u05dc\u05d9\u05da \u05ea\u05d9\u05db\u05d5\u05df \u05d4\u05e0\u05d3\u05e1\u05d9 (EDP)',
            'data_analysis': '\U0001f4ca \u05e0\u05d9\u05ea\u05d5\u05d7 \u05e0\u05ea\u05d5\u05e0\u05d9\u05dd',
            'mathematical_thinking': '\U0001f4d0 \u05d7\u05e9\u05d9\u05d1\u05d4 \u05de\u05ea\u05de\u05d8\u05d9\u05ea',
            'art_design': '\U0001f3a8 \u05d7\u05e9\u05d9\u05d1\u05d4 \u05e2\u05d9\u05e6\u05d5\u05d1\u05d9\u05ea',
        }.get(data.get('thinking_framework', ''), '\U0001f52c \u05de\u05e1\u05d2\u05e8\u05ea \u05d7\u05e9\u05d9\u05d1\u05d4')
        steps_li = "".join([f"<li>{s}</li>" for s in framework_steps])
        fw_steps_html = f"""
        <div class="section-block" style="margin-bottom:12px;">
            <div class="section-title">{fw_label} \u2014 \u05e9\u05dc\u05d1\u05d9 \u05d4\u05e2\u05d1\u05d5\u05d3\u05d4</div>
            <ol style="font-size:12.5px; padding-right:20px; margin-top:6px;">{steps_li}</ol>
        </div>"""

    context_data = data.get('context_data', '')
    context_html = ""
    if context_data:
        context_html = f"""
        <div class="section-block" style="margin-bottom:12px; background:#fef9e7; border:2px solid #f39c12; border-radius:8px; padding:10px 14px;">
            <div style="font-weight:700; color:#e67e22; margin-bottom:6px;">\U0001f4ca \u05e0\u05ea\u05d5\u05e0\u05d9\u05dd / \u05d4\u05e7\u05e9\u05e8 \u05dc\u05e0\u05d9\u05ea\u05d5\u05d7:</div>
            <div style="font-size:12.5px; line-height:1.8;">{context_data.replace(chr(10), '<br>')}</div>
        </div>"""

    is_steam = bool(framework_steps or context_data)
    if english_mode:
        scaffold_title = "\U0001f4dd Writing Structure (scaffold)"
        write_title = "\u270f\ufe0f Write here:"
    elif is_steam:
        scaffold_title = "\U0001f4dd \u05de\u05e1\u05d2\u05e8\u05ea / \u05e4\u05d9\u05d2\u05d5\u05dd \u05dc\u05d7\u05e9\u05d9\u05d1\u05d4"
        write_title = "\u270f\ufe0f \u05db\u05ea\u05d5\u05d1/\u05db\u05ea\u05d1\u05d9 \u05d0\u05ea \u05d4\u05e0\u05d9\u05ea\u05d5\u05d7/\u05d4\u05d3\u05d5\u05d7/\u05d4\u05e4\u05ea\u05e8\u05d5\u05df:"
        footer_text = f"\u05d0\"\u05dc \u05d4\u05e9\u05d3\"\u05d4 STEAM | \u05ea\u05d7\u05e0\u05ea \u05e9\u05d9\u05d8\u05d5\u05ea | {title} | \u05e1\u05d1\u05d1 {round_num} \u2014 \u00a9 \u05db\u05dc \u05d4\u05d6\u05db\u05d5\u05d9\u05d5\u05ea \u05e9\u05de\u05d5\u05e8\u05d5\u05ea"
    else:
        scaffold_title = "\U0001f4dd \u05de\u05d1\u05e0\u05d4 \u05d4\u05db\u05ea\u05d9\u05d1\u05d4 (\u05e4\u05d9\u05d2\u05d5\u05dd)"
        write_title = "\u270f\ufe0f \u05db\u05ea\u05d5\u05d1/\u05db\u05ea\u05d1\u05d9 \u05db\u05d0\u05df:"
        footer_text = f"\u05d0\"\u05dc \u05d4\u05e9\u05d3\"\u05d4 | \u05ea\u05d7\u05e0\u05ea \u05e9\u05d9\u05d8\u05d5\u05ea | {title} | \u05e1\u05d1\u05d1 {round_num} \u2014 \u00a9 \u05db\u05dc \u05d4\u05d6\u05db\u05d5\u05d9\u05d5\u05ea \u05e9\u05de\u05d5\u05e8\u05d5\u05ea"

    return f"""<!DOCTYPE html>
<html dir="{html_dir}" lang="{html_lang}">
<head><meta charset="UTF-8"><title>{page_title}</title>
<style>{get_css('methods')}</style></head>
<body>
{render_header(title, round_num, 'methods', english_mode=english_mode)}
<div class="instruction-box">\U0001f4cc {data.get('main_instruction', '')}</div>

<div style="background:#d6eaf8; border:2px solid #2980b9; border-radius:8px; padding:10px 14px; margin-bottom:12px;">
    <div style="font-weight:700; font-size:14px; color:#1a5276; margin-bottom:6px;">\u270f\ufe0f {data.get('context_prompt', '')}</div>
    <div style="font-size:12px; color:#555;">{scope_label} {data.get('words_range', '')}</div>
</div>

{fw_steps_html}
{context_html}
{traffic}

<div class="section-block" style="margin-bottom:12px;">
    <div class="section-title">{guiding_title}</div>
    <ul style="font-size:13px; {list_padding} margin-top:6px;">{guiding}</ul>
</div>

<div class="section-block" style="margin-bottom:10px;">
    <div class="section-title">{scaffold_title}</div>
    <div style="background:#eaf3fb; border:1px solid #2980b9; border-radius:6px; padding:10px; font-size:12.5px; margin-top:6px; line-height:1.7;">{scaffold}</div>
</div>

<div class="section-block">
    <div class="section-title">{write_title}</div>
    <div class="writing-box">{lines_html}</div>
</div>

<div class="page-footer">{footer_text}</div>
</body></html>"""
