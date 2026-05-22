from typing import Dict, Optional
from ..config import STATION_COLORS, get_grade_level
from .css import get_css, ENGLISH_LABELS
from .header import render_header


def render_comprehension(title: str, round_num: int, data: Dict, grade: str,
                          english_mode: bool = False,
                          topic_image: Optional[str] = None) -> str:
    gl = get_grade_level(grade)

    paras_html = ""
    for p in data.get('paragraphs', []):
        text = p.get('text', '')
        for term in p.get('key_terms', []):
            if term and len(term) > 1:
                text = text.replace(term, f'<span class="key-term">{term}</span>', 1)
        paras_html += f"""
        <div style="margin-bottom: 14px;">
            <div style="font-weight: 700; color: #c0392b; font-size: 14px; margin-bottom: 4px;">{p.get('subtitle', '')}</div>
            <div style="font-size: 13.5px; line-height: 1.9; text-align: justify;">{text}</div>
        </div>
        """

    pills = "".join([f'<span class="word-pill">{t}</span>' for t in data.get('all_key_terms', [])])

    disc_items = "".join([f'<li style="margin-bottom:5px;">{q}</li>' for q in data.get('discussion_starters', [])])

    if english_mode:
        lbl = ENGLISH_LABELS
        disc_box = f"""
        <div class="section-block" style="background:#fadbd8; border:2px solid #e74c3c; border-radius:8px; padding:10px 14px; margin-top:14px;">
            <div style="font-weight:700; color:#c0392b; margin-bottom:6px;">{lbl['discussion']}</div>
            <ul style="margin:0; padding-left:20px; font-size:13px;">{disc_items}</ul>
            <div style="font-size:11px; color:#888; margin-top:6px; font-style:italic;">{lbl['discussion_note']}</div>
        </div>
        """
        reading_instruction = lbl['reading_instr']
        key_terms_label = lbl['key_terms']
        html_dir = "ltr"
        html_lang = "en"
        page_title = f"Comprehension Station - {title} - Round {round_num}"
        footer_text = f"Al-HaSadeh | Comprehension Station | {title} | Round {round_num} \u2014 {lbl['footer_copy']}"
    else:
        disc_box = f"""
        <div class="section-block" style="background:#fadbd8; border:2px solid #e74c3c; border-radius:8px; padding:10px 14px; margin-top:14px;">
            <div style="font-weight:700; color:#c0392b; margin-bottom:6px;">\U0001f4ac \u05dc\u05d3\u05d9\u05d5\u05df \u05d1\u05e2\u05dc \u05e4\u05d4 \u05e2\u05dd \u05d4\u05e7\u05d1\u05d5\u05e6\u05d4:</div>
            <ul style="margin:0; padding-right:20px; font-size:13px;">{disc_items}</ul>
            <div style="font-size:11px; color:#888; margin-top:6px; font-style:italic;">* \u05e9\u05d0\u05dc\u05d5\u05ea \u05dc\u05d3\u05d9\u05d5\u05df \u05d1\u05e2\u05dc \u05e4\u05d4 \u05d1\u05dc\u05d1\u05d3 \u2014 \u05d0\u05d9\u05df \u05e6\u05d5\u05e8\u05da \u05dc\u05db\u05ea\u05d5\u05d1!</div>
        </div>
        """
        key_terms_label = "\U0001f4cc \u05de\u05d5\u05e0\u05d7\u05d9 \u05de\u05e4\u05ea\u05d7:"
        html_dir = "rtl"
        html_lang = "he"
        page_title = f"\u05ea\u05d7\u05e0\u05ea \u05d4\u05d1\u05e0\u05d4 - {title} - \u05e1\u05d1\u05d1 {round_num}"

    is_steam = data.get('is_steam', False)
    input_type_labels = {
        'text': '\U0001f4c4 \u05e7\u05e8\u05d0/\u05d9 \u05d0\u05ea \u05d4\u05d8\u05e7\u05e1\u05d8 \u05d4\u05de\u05d3\u05e2\u05d9',
        'video': '\U0001f3ac \u05e6\u05e4\u05d4/\u05d9 \u05d1\u05e1\u05e8\u05d8\u05d5\u05df + \u05e2\u05e0\u05d4/\u05d9 \u05e2\u05dc \u05e9\u05d0\u05dc\u05d5\u05ea \u05d4\u05d4\u05db\u05d5\u05d5\u05e0\u05d4',
        'observation': '\U0001f52c \u05d1\u05e6\u05e2/\u05d9 \u05ea\u05e6\u05e4\u05d9\u05ea \u05de\u05d5\u05e0\u05d7\u05ea \u05d5\u05ea\u05e2\u05d3/\u05d9',
        'experiment': '\u2697\ufe0f \u05d1\u05e6\u05e2/\u05d9 \u05d0\u05ea \u05d4\u05e0\u05d9\u05e1\u05d5\u05d9 \u05d4\u05e7\u05e6\u05e8 + \u05e9\u05d5\u05d7\u05d7/\u05d9 \u05e2\u05dc \u05de\u05d4 \u05e9\u05e8\u05d0\u05d9\u05ea',
        'multi_source': '\U0001f4ca \u05e7\u05e8\u05d0/\u05d9 \u05d0\u05ea \u05d4\u05d7\u05d5\u05de\u05e8\u05d9\u05dd + \u05e0\u05ea\u05d7/\u05d9 \u05d0\u05ea \u05d4\u05d2\u05e8\u05e4\u05d9\u05dd',
    }
    if english_mode:
        reading_instruction = ENGLISH_LABELS['reading_instr']
    elif is_steam:
        input_type = data.get('input_type', 'text')
        reading_instruction = input_type_labels.get(input_type, f"\U0001f4cc {gl['reading_mode']}")
    else:
        reading_instruction = f"\U0001f4cc {gl['reading_mode']}"

    if not english_mode:
        footer_text = f"\u05d0\"\u05dc \u05d4\u05e9\u05d3\"\u05d4{' STEAM' if is_steam else ''} | \u05ea\u05d7\u05e0\u05ea \u05d4\u05d1\u05e0\u05d4 | {title} | \u05e1\u05d1\u05d1 {round_num} \u2014 \u00a9 \u05db\u05dc \u05d4\u05d6\u05db\u05d5\u05d9\u05d5\u05ea \u05e9\u05de\u05d5\u05e8\u05d5\u05ea"

    # KWL table (STEAM only)
    kwl = data.get('kwl_table', {})
    kwl_html = ""
    if kwl and not english_mode:
        _kp = kwl.get('know_prompts') if isinstance(kwl.get('know_prompts'), list) else []
        _wp = kwl.get('wonder_prompts') if isinstance(kwl.get('wonder_prompts'), list) else []
        know_items = "".join([f'<div class="answer-line" style="margin-bottom:4px;"></div>' for _ in range(len(_kp) + 1)])
        wonder_items = "".join([f'<div class="answer-line" style="margin-bottom:4px;"></div>' for _ in range(len(_wp) + 1)])
        know_prompts = "".join([f'<div style="font-size:11px;color:#888;font-style:italic;margin-bottom:2px;">{p}</div>' for p in _kp])
        wonder_prompts = "".join([f'<div style="font-size:11px;color:#888;font-style:italic;margin-bottom:2px;">{p}</div>' for p in _wp])
        kwl_html = f"""
        <div class="section-block" style="margin-bottom:14px;">
            <div class="section-title">\U0001f4cb \u05d8\u05d1\u05dc\u05ea KWL \u2014 \u05dc\u05e4\u05e0\u05d9 \u05d4\u05e7\u05e8\u05d9\u05d0\u05d4</div>
            <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:8px; margin-top:8px;">
                <div style="background:#d5f5e3; border:1.5px solid #27ae60; border-radius:8px; padding:10px;">
                    <div style="font-weight:800; color:#1e8449; margin-bottom:6px; font-size:12px;">\u2705 \u05d9\u05d5\u05d3\u05e2/\u05ea</div>
                    {know_prompts}{know_items}
                </div>
                <div style="background:#d6eaf8; border:1.5px solid #2980b9; border-radius:8px; padding:10px;">
                    <div style="font-weight:800; color:#1a5276; margin-bottom:6px; font-size:12px;">\u2753 \u05e8\u05d5\u05e6\u05d4 \u05dc\u05d3\u05e2\u05ea</div>
                    {wonder_prompts}{wonder_items}
                </div>
                <div style="background:#fef9e7; border:1.5px solid #f1c40f; border-radius:8px; padding:10px;">
                    <div style="font-weight:800; color:#7d6608; margin-bottom:6px; font-size:12px;">\U0001f4a1 \u05dc\u05de\u05d3\u05ea\u05d9</div>
                    <div style="font-size:11px; color:#888; font-style:italic; margin-bottom:4px;">\u2014 \u05d9\u05de\u05d5\u05dc\u05d0 \u05dc\u05d0\u05d7\u05e8 \u05d4\u05e4\u05e2\u05d9\u05dc\u05d5\u05ea \u2014</div>
                    <div class="answer-line"></div><div class="answer-line"></div><div class="answer-line"></div>
                </div>
            </div>
        </div>"""

    # Short written response (STEAM only)
    wr = data.get('written_response', {})
    written_response_html = ""
    if wr and not english_mode:
        written_response_html = f"""
        <div class="section-block" style="margin-bottom:14px; background:#eafaf1; border:2px solid #27ae60; border-radius:8px; padding:12px 14px;">
            <div style="font-weight:700; color:#1e8449; margin-bottom:6px;">\u270d\ufe0f {wr.get('instruction', '\u05db\u05ea\u05d5\u05d1/\u05db\u05ea\u05d1\u05d9 \u05ea\u05e9\u05d5\u05d1\u05d4 \u05e7\u05e6\u05e8\u05d4 (1-3 \u05de\u05e9\u05e4\u05d8\u05d9\u05dd)')}</div>
            <div style="font-size:13px; font-weight:600; margin-bottom:8px;">{wr.get('question', '')}</div>
            <div style="font-size:11.5px; color:#888; font-style:italic; margin-bottom:8px;">\u05e4\u05d9\u05d2\u05d5\u05dd: {wr.get('scaffold', '')}</div>
            <div class="answer-line"></div><div class="answer-line"></div><div class="answer-line"></div>
        </div>"""

    # Topic image float (right side in RTL = float:left in CSS)
    image_html = ""
    if topic_image:
        try:
            from ..images import ImageService
            data_url = ImageService.to_data_url(topic_image)
            c = STATION_COLORS['comprehension']
            image_html = f"""
            <div style="float:left; margin:0 0 14px 20px; clear:left;">
                <img src="{data_url}"
                     style="width:230px; height:160px; object-fit:cover;
                            border-radius:12px; border:3px solid {c['border']};
                            box-shadow:0 4px 10px rgba(0,0,0,0.22); display:block;" alt="">
            </div>"""
        except Exception:
            pass

    return f"""<!DOCTYPE html>
<html dir="{html_dir}" lang="{html_lang}">
<head><meta charset="UTF-8"><title>{page_title}</title>
<style>{get_css('comprehension')}</style></head>
<body>
{render_header(title, round_num, 'comprehension', english_mode=english_mode)}
<div class="instruction-box">{reading_instruction}</div>
{image_html}
{kwl_html}
<div style="background:#fafafa; border:1px solid #ddd; border-radius:10px; padding:18px 22px;">
    <div style="font-size:26px; font-weight:800; color:#c0392b; text-align:center; margin-bottom:6px;">{data.get('section_title', '')}</div>
    <div style="font-size:14px; font-style:italic; text-align:center; color:#555; border-bottom:1px solid #eee; padding-bottom:10px; margin-bottom:14px;">{data.get('intro_sentence') or data.get('intro_question', '')}</div>
    {paras_html}
    <div style="background:#fadbd8; border:1.5px solid #e74c3c; border-radius:6px; padding:8px 12px; margin-top:12px; font-size:12px;">
        <strong style="color:#c0392b;">{key_terms_label}</strong><br>{pills}
    </div>
</div>
{written_response_html}
{disc_box}
<div class="page-footer">{footer_text}</div>
</body></html>"""
