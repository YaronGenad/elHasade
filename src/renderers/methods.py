from pathlib import Path
from typing import Dict, List, Optional
from ..config import STATION_COLORS
from .css import get_css, ENGLISH_LABELS
from .header import render_header


def _svg_decorative_html(svg_path: Optional[str]) -> str:
    if not svg_path:
        return ""
    try:
        svg_content = Path(svg_path).read_text(encoding="utf-8")
        return (
            '<div style="clear:both; margin-top:18px; text-align:center; '
            'break-before:avoid; page-break-before:avoid;">'
            f'{svg_content}'
            '</div>'
        )
    except Exception:
        return ""


def _svg_row_html(svg_paths: Optional[List[str]]) -> str:
    """Render a horizontal row of small SVG illustrations to fill whitespace."""
    if not svg_paths:
        return ""
    items = []
    for path in svg_paths:
        try:
            svg_content = Path(path).read_text(encoding="utf-8")
            items.append(
                f'<div style="flex:1; max-width:180px; display:flex; '
                f'align-items:center; justify-content:center;">'
                f'{svg_content}</div>'
            )
        except Exception:
            continue
    if not items:
        return ""
    return (
        '<div style="clear:both; display:flex; gap:12px; justify-content:center; '
        'align-items:center; margin-bottom:10px; '
        'break-before:avoid; page-break-before:avoid;">'
        + "".join(items)
        + '</div>'
    )


def _self_review_html(checklist: list, english_mode: bool = False) -> str:
    if not checklist:
        return ""
    items = "".join([
        f'<div style="display:flex; align-items:flex-start; gap:8px; margin-bottom:6px; font-size:12.5px;">'
        f'<span style="font-size:15px; line-height:1;">☐</span>'
        f'<span>{item}</span></div>'
        for item in checklist
    ])
    title_txt = "Self-Review Checklist — before handing in" if english_mode else "✅ ביקורת עצמית — לפני שמגישים"
    note_txt = "Check ✓ each item you verified:" if english_mode else "סמן/י ✓ בכל משפט שבדקת:"
    return f"""
<div style="margin-top:14px; background:#eaf3fb; border:1.5px solid #2980b9;
     border-radius:8px; padding:12px 14px;
     break-before:avoid; page-break-before:avoid; break-inside:avoid;">
    <div class="section-title">{title_txt}</div>
    <div style="font-size:12px; color:#555; margin-bottom:8px;">{note_txt}</div>
    {items}
</div>"""


def render_methods(title: str, round_num: int, data: Dict, english_mode: bool = False,
                   topic_image: Optional[str] = None,
                   svg_decorative: Optional[str] = None,
                   extra_svgs: Optional[List[str]] = None) -> str:
    try:
        _lines = int(data.get('lines_needed') or 10)
    except (TypeError, ValueError):
        _lines = 10
    lines_html = "".join([f'<div class="writing-line"></div>' for _ in range(_lines)])

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
        write_title = "✏️ Write here:"
        guiding_title = "❓ Guiding Questions"
        scope_label = "Scope:"
        footer_text = f"מחולל יחידות לימוד | Methods Station | {title} | Round {round_num} — {lbl['footer_copy']}"
        html_dir = "ltr"
        html_lang = "en"
        page_title = f"Methods Station - {title} - Round {round_num}"
        list_padding = "padding-left:20px;"
    else:
        traffic = f"""
        <div class="traffic-light">
            <div class="tl-green"><div class="tl-label">\U0001f7e2 קל</div>{dl.get('green', '')}</div>
            <div class="tl-yellow"><div class="tl-label">\U0001f7e1 בינוני</div>{dl.get('yellow', '')}</div>
            <div class="tl-red"><div class="tl-label">\U0001f534 מאתגר</div>{dl.get('red', '')}</div>
        </div>
        """
        scope_label = "היקף:"
        guiding_title = "❓ שאלות מנחות"
        html_dir = "rtl"
        html_lang = "he"
        page_title = f"תחנת שיטות - {title} - סבב {round_num}"
        list_padding = "padding-right:20px;"

    guiding = "".join([f'<li style="margin-bottom:4px;">{q}</li>' for q in data.get('guiding_questions', [])])
    scaffold = str(data.get('scaffold_template') or '').replace('\n', '<br>')

    # STEAM: framework steps + context data
    framework_steps = data.get('framework_steps', [])
    fw_steps_html = ""
    if framework_steps:
        fw_label = {
            'scientific_method': '\U0001f52c מתודה מדעית',
            'EDP': '\U0001f3d7️ תהליך תיכון הנדסי (EDP)',
            'data_analysis': '\U0001f4ca ניתוח נתונים',
            'mathematical_thinking': '\U0001f4d0 חשיבה מתמטית',
            'art_design': '\U0001f3a8 חשיבה עיצובית',
        }.get(data.get('thinking_framework', ''), '\U0001f52c מסגרת חשיבה')
        steps_li = "".join([f"<li>{s}</li>" for s in framework_steps])
        fw_steps_html = f"""
        <div class="section-block" style="margin-bottom:12px;">
            <div class="section-title">{fw_label} — שלבי העבודה</div>
            <ol style="font-size:12.5px; padding-right:20px; margin-top:6px;">{steps_li}</ol>
        </div>"""

    context_data = data.get('context_data', '')
    context_html = ""
    if context_data:
        context_html = f"""
        <div class="section-block" style="margin-bottom:12px; background:#fef9e7; border:2px solid #f39c12; border-radius:8px; padding:10px 14px;">
            <div style="font-weight:700; color:#e67e22; margin-bottom:6px;">\U0001f4ca נתונים / הקשר לניתוח:</div>
            <div style="font-size:12.5px; line-height:1.8;">{str(context_data).replace(chr(10), '<br>')}</div>
        </div>"""

    is_steam = bool(framework_steps or context_data)
    if english_mode:
        scaffold_title = "\U0001f4dd Writing Structure (scaffold)"
        write_title = "✏️ Write here:"
    elif is_steam:
        scaffold_title = "\U0001f4dd מסגרת / פיגום לחשיבה"
        write_title = "✏️ כתוב/כתבי את הניתוח/הדוח/הפתרון:"
        footer_text = f"א\"ל השד\"ה STEAM | תחנת שיטות | {title} | סבב {round_num} — © כל הזכויות שמורות"
    else:
        scaffold_title = "\U0001f4dd מבנה הכתיבה (פיגום)"
        write_title = "✏️ כתוב/כתבי כאן:"
        footer_text = f"א\"ל השד\"ה | תחנת שיטות | {title} | סבב {round_num} — © כל הזכויות שמורות"

    # Topic image float
    image_html = ""
    if topic_image:
        try:
            from ..images import ImageService
            data_url = ImageService.to_data_url(topic_image)
            c = STATION_COLORS['methods']
            image_html = f"""
            <div style="float:left; margin:0 0 14px 18px; clear:left;">
                <img src="{data_url}"
                     style="width:210px; height:145px; object-fit:cover;
                            border-radius:12px; border:3px solid {c['border']};
                            box-shadow:0 4px 10px rgba(0,0,0,0.22); display:block;" alt="">
            </div>"""
        except Exception:
            pass

    return f"""<!DOCTYPE html>
<html dir="{html_dir}" lang="{html_lang}">
<head><meta charset="UTF-8"><title>{page_title}</title>
<style>{get_css('methods')}</style></head>
<body>
{render_header(title, round_num, 'methods', english_mode=english_mode)}
{image_html}
<div class="instruction-box">\U0001f4cc {data.get('main_instruction', '')}</div>

<div style="background:#d6eaf8; border:2px solid #2980b9; border-radius:8px; padding:10px 14px; margin-bottom:12px;">
    <div style="font-weight:700; font-size:14px; color:#1a5276; margin-bottom:6px;">✏️ {data.get('context_prompt', '')}</div>
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

{_svg_row_html(extra_svgs)}

<div class="section-block">
    <div class="section-title">{write_title}</div>
    <div class="writing-box">{lines_html}</div>
</div>

{_self_review_html(data.get('self_review_checklist', []), english_mode=english_mode)}
{_svg_decorative_html(svg_decorative)}
<div class="page-footer">{footer_text}</div>
</body></html>"""
