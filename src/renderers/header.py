from typing import Dict
from ..config import STATION_COLORS
from .css import ENGLISH_STATION_NAMES, ENGLISH_LABELS


def render_header(title: str, round_num: int, station: str,
                  include_student_bar: bool = True, english_mode: bool = False) -> str:
    c = STATION_COLORS[station]
    if english_mode:
        en = ENGLISH_STATION_NAMES.get(station, {"name": c['name'], "emoji": c['emoji']})
        station_name = en['name']
        station_emoji = en['emoji']
        lbl = ENGLISH_LABELS
        round_label = f"{lbl['round']} {round_num}"
    else:
        station_name = c['name']
        station_emoji = c['emoji']
        round_label = f"\u05e1\u05d1\u05d1 {round_num}"

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
                <div class="student-field"><label>\u05e9\u05dd:</label><div class="student-line"></div></div>
                <div class="student-field"><label>\u05db\u05d9\u05ea\u05d4:</label><div class="student-line"></div></div>
                <div class="student-field"><label>\u05ea\u05d0\u05e8\u05d9\u05da:</label><div class="student-line"></div></div>
            </div>
            """
    return f"""
    <div class="page-header">
        <div class="header-left">
            <div class="header-icon">{station_emoji}</div>
            <div>
                <div class="header-title">{station_name}</div>
                <div class="header-subtitle">{title}</div>
            </div>
        </div>
        <div class="header-badge">{round_label}</div>
    </div>
    {student_bar}
    """
