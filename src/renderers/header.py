from typing import Dict
from ..config import STATION_COLORS
from .css import ENGLISH_STATION_NAMES, ENGLISH_LABELS, MATH_STATION_NAMES
from .icons import STATION_ICONS
from .utils import logo_data_url

_LOGO_URL: str = ""  # loaded once on first use


def _get_logo() -> str:
    global _LOGO_URL
    if not _LOGO_URL:
        _LOGO_URL = logo_data_url()
    return _LOGO_URL


def render_header(title: str, round_num: int, station: str,
                  include_student_bar: bool = True, english_mode: bool = False,
                  math_mode: bool = False) -> str:
    c = STATION_COLORS[station]
    if math_mode:
        mn = MATH_STATION_NAMES.get(station, {"name": c['name'], "emoji": c['emoji']})
        station_name = mn['name']
        round_label = f"סבב {round_num}"
    elif english_mode:
        en = ENGLISH_STATION_NAMES.get(station, {"name": c['name'], "emoji": c['emoji']})
        station_name = en['name']
        lbl = ENGLISH_LABELS
        round_label = f"{lbl['round']} {round_num}"
    else:
        station_name = c['name']
        round_label = f"סבב {round_num}"

    svg_icon = STATION_ICONS.get(station, "")
    logo_url = _get_logo()
    logo_img = (
        f'<img src="{logo_url}" class="header-logo-img" alt="אל השדה">'
        if logo_url else '<div style="width:52px;"></div>'
    )

    student_bar = ""
    if include_student_bar:
        if english_mode:
            student_bar = f"""
            <div class="student-bar">
                <div class="student-field"><label>{ENGLISH_LABELS['student_name']}</label><div class="student-line"></div></div>
                <div class="student-field"><label>{ENGLISH_LABELS['student_class']}</label><div class="student-line"></div></div>
                <div class="student-field"><label>{ENGLISH_LABELS['student_date']}</label><div class="student-line"></div></div>
            </div>
            """
        else:
            student_bar = """
            <div class="student-bar">
                <div class="student-field"><label>שם:</label><div class="student-line"></div></div>
                <div class="student-field"><label>כיתה:</label><div class="student-line"></div></div>
                <div class="student-field"><label>תאריך:</label><div class="student-line"></div></div>
            </div>
            """

    title_color = c['primary']
    _title_dir = "ltr" if english_mode else "rtl"
    pace_badge = '<div style="font-size:8px; opacity:0.75; letter-spacing:1px; margin-top:2px;">PACE</div>' if english_mode else ''
    return f"""
    <div class="page-header">
        <div class="header-icon-circle">{svg_icon}</div>
        <div class="header-center">
            <div class="header-round-badge">{round_label}</div>
            <div class="header-station-name">{station_name}{pace_badge}</div>
        </div>
        {logo_img}
    </div>
    <div style="font-size:24px; font-weight:800; color:{title_color}; text-align:center;
                margin:10px 0 6px; direction:{_title_dir}; line-height:1.3;">{title}</div>
    {student_bar}
    """
