from pathlib import Path
from typing import Dict, List, Optional
from ..config import STATION_COLORS, get_grade_level
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
        'align-items:center; margin-top:14px; '
        'break-before:avoid; page-break-before:avoid;">'
        + "".join(items)
        + '</div>'
    )


def _decorative_img_html(decorative_image: Optional[str]) -> str:
    if not decorative_image:
        return ""
    try:
        from ..images import ImageService
        dec_url = ImageService.to_data_url(decorative_image)
        return (
            '<div style="clear:both; margin-top:14px; text-align:center;">'
            '<img src="' + dec_url + '" style="max-width:98%; max-height:280px; '
            'width:98%; object-fit:cover; border-radius:10px; '
            'box-shadow:0 4px 12px rgba(0,0,0,0.18);" alt=""></div>'
        )
    except Exception:
        return ""


def render_comprehension(title: str, round_num: int, data: Dict, grade: str,
                          english_mode: bool = False,
                          topic_image: Optional[str] = None,
                          svg_decorative: Optional[str] = None,
                          extra_svgs: Optional[List[str]] = None,
                          decorative_image: Optional[str] = None) -> str:
    gl = get_grade_level(grade)

    paras_html = ""
    for p in data.get('paragraphs', []):
        text = p.get('text', '')
        for term in p.get('key_terms', []):
            if term and len(term) > 1:
                text = text.replace(term, f'<span class="key-term">{term}</span>', 1)
        paras_html += f"""
        <div style="margin-bottom: 14px;">
            <div style="font-weight: 700; color: #c0392b; font-size: 14px; margin-bottom: 4px;
                        break-after:avoid; page-break-after:avoid;">{p.get('subtitle', '')}</div>
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
        footer_text = f"מחולל יחידות לימוד | Comprehension Station | {title} | Round {round_num} — {lbl['footer_copy']}"
    else:
        disc_box = f"""
        <div class="section-block" style="background:#fadbd8; border:2px solid #e74c3c; border-radius:8px; padding:10px 14px; margin-top:14px;">
            <div style="font-weight:700; color:#c0392b; margin-bottom:6px;">\U0001f4ac לדיון בעל פה עם הקבוצה:</div>
            <ul style="margin:0; padding-right:20px; font-size:13px;">{disc_items}</ul>
            <div style="font-size:11px; color:#888; margin-top:6px; font-style:italic;">* שאלות לדיון בעל פה בלבד — אין צורך לכתוב!</div>
        </div>
        """
        key_terms_label = "\U0001f4cc מונחי מפתח:"
        html_dir = "rtl"
        html_lang = "he"
        page_title = f"תחנת הבנה - {title} - סבב {round_num}"

    is_steam = data.get('is_steam', False)
    input_type_labels = {
        'text': '\U0001f4c4 קרא/י את הטקסט המדעי',
        'video': '\U0001f3ac צפה/י בסרטון + ענה/י על שאלות ההכוונה',
        'observation': '\U0001f52c בצע/י תצפית מונחת ותעד/י',
        'experiment': '⚗️ בצע/י את הניסוי הקצר + שוחח/י על מה שראית',
        'multi_source': '\U0001f4ca קרא/י את החומרים + נתח/י את הגרפים',
    }
    if english_mode:
        reading_instruction = ENGLISH_LABELS['reading_instr']
    elif is_steam:
        input_type = data.get('input_type', 'text')
        reading_instruction = input_type_labels.get(input_type, f"\U0001f4cc {gl['reading_mode']}")
    else:
        reading_instruction = f"\U0001f4cc {gl['reading_mode']}"

    if not english_mode:
        footer_text = f"א\"ל השד\"ה{' STEAM' if is_steam else ''} | תחנת הבנה | {title} | סבב {round_num} — © כל הזכויות שמורות"

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
            <div class="section-title">\U0001f4cb טבלת KWL — לפני הקריאה</div>
            <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:8px; margin-top:8px;">
                <div style="background:#d5f5e3; border:1.5px solid #27ae60; border-radius:8px; padding:10px;">
                    <div style="font-weight:800; color:#1e8449; margin-bottom:6px; font-size:12px;">✅ יודע/ת</div>
                    {know_prompts}{know_items}
                </div>
                <div style="background:#d6eaf8; border:1.5px solid #2980b9; border-radius:8px; padding:10px;">
                    <div style="font-weight:800; color:#1a5276; margin-bottom:6px; font-size:12px;">❓ רוצה לדעת</div>
                    {wonder_prompts}{wonder_items}
                </div>
                <div style="background:#fef9e7; border:1.5px solid #f1c40f; border-radius:8px; padding:10px;">
                    <div style="font-weight:800; color:#7d6608; margin-bottom:6px; font-size:12px;">\U0001f4a1 למדתי</div>
                    <div style="font-size:11px; color:#888; font-style:italic; margin-bottom:4px;">— ימולא לאחר הפעילות —</div>
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
            <div style="font-weight:700; color:#1e8449; margin-bottom:6px;">✍️ {wr.get('instruction', 'כתוב/כתבי תשובה קצרה (1-3 משפטים)')}</div>
            <div style="font-size:13px; font-weight:600; margin-bottom:8px;">{wr.get('question', '')}</div>
            <div style="font-size:11.5px; color:#888; font-style:italic; margin-bottom:8px;">פיגום: {wr.get('scaffold', '')}</div>
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
{_svg_row_html(extra_svgs)}
<div style="break-inside:avoid; page-break-inside:avoid;">
{disc_box}
{_decorative_img_html(decorative_image)}
</div>
{_svg_decorative_html(svg_decorative)}
<div class="page-footer">{footer_text}</div>
</body></html>"""
