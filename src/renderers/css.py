import random
from typing import Any, Dict, List
from ..config import STATION_COLORS, get_grade_level, is_english as _is_english_subject


# ─── English-mode UI labels ──────────────────────────────────────────────────
ENGLISH_STATION_NAMES = {
    "comprehension": {"name": "Comprehension Station", "emoji": "\U0001f534"},
    "methods":       {"name": "Methods Station",       "emoji": "\U0001f535"},
    "precision":     {"name": "Precision Station",     "emoji": "\U0001f7e2"},
    "vocabulary":    {"name": "Vocabulary Station",    "emoji": "\U0001f7e1"},
    "teacher":       {"name": "Teacher Preparation",   "emoji": "\U0001f4cb"},
    "answers":       {"name": "Answer Key",            "emoji": "\U0001f511"},
}

ENGLISH_LABELS = {
    "student_name":    "Name:",
    "student_class":   "Class:",
    "student_date":    "Date:",
    "round":           "Round",
    "key_terms":       "\U0001f4cc Key Vocabulary:",
    "discussion":      "\U0001f4ac Oral Discussion with your group:",
    "discussion_note": "* Discussion questions \u2014 oral only, no writing needed!",
    "reading_instr":   "\U0001f4cc Read the text carefully.",
    "dictation_title": "\u270f\ufe0f Spelling ({n} words)",
    "dictation_note":  "* A partner dictates, you write in the blank row",
    "word":            "Word",
    "spelling":        "Spelling",
    "sentences_title": "\U0001f4dd Sentences for Dictation (for teacher)",
    "writing_title":   "\u270f\ufe0f Write here:",
    "scaffold_title":  "\U0001f4dd Writing Structure (scaffold)",
    "guiding_title":   "\u2753 Guiding Questions",
    "traffic_green":   "\U0001f7e2 Basic",
    "traffic_yellow":  "\U0001f7e1 Regular",
    "traffic_red":     "\U0001f534 Challenge",
    "scissors":        "\u2702\ufe0f Cut out all cards, shuffle, and match each word to its definition",
    "word_bank":       "\U0001f4da Word Bank:",
    "footer_copy":     "\u00a9 All rights reserved",
    "teacher_only":    "\u26a0\ufe0f This sheet is for the teacher only \u2014 do not distribute to students",
    "answers_only":    "\u26a0\ufe0f Answer Key \u2014 for teacher only",
    "materials_title": "\U0001f392 What you need:",
    "steps_title":     "\U0001f4cb Activity steps:",
    "physical_badge":  "Hands-on Activity",
    "cut_hint":        "\u2702\ufe0f Cut out the cards before the activity",
}


def get_css(station: str = "comprehension") -> str:
    c = STATION_COLORS[station]
    return f"""
    @page {{ size: A4; margin: 10mm; }}
    * {{ box-sizing: border-box; }}
    body {{
        font-family: 'Arial Hebrew', Arial, 'Segoe UI', sans-serif;
        direction: rtl;
        line-height: 1.9;
        color: #1e2a3a;
        background: white;
        font-size: 13.5px;
        margin: 0;
        padding: 0 0 4mm;
    }}
    /* Thin elegant frame — 3.5mm instead of 10mm */
    .page-frame-border {{
        position: fixed;
        top: 0; left: 0; right: 0; bottom: 0;
        border: 3.5mm solid {c['primary']};
        pointer-events: none;
        z-index: 100;
    }}
    /* Station header — gradient bar stretching edge-to-edge within the margin */
    .page-header {{
        background: linear-gradient(110deg, {c['primary']} 0%, {c['border']} 100%);
        color: white;
        padding: 13px 20px;
        border-radius: 0;
        margin: 0 0 16px;
        direction: ltr;
        display: flex;
        flex-direction: row;
        align-items: center;
        gap: 14px;
        box-shadow: 0 3px 10px rgba(0,0,0,0.18);
    }}
    .header-icon-circle {{
        width: 58px; height: 58px;
        background: rgba(255,255,255,0.2);
        border: 2px solid rgba(255,255,255,0.45);
        border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        flex-shrink: 0;
    }}
    .header-icon-circle svg {{ width: 32px; height: 32px; display: block; }}
    .header-center {{
        flex: 1;
        text-align: center;
        direction: rtl;
    }}
    .header-round-badge {{
        display: inline-block;
        background: rgba(255,255,255,0.22);
        border: 1.5px solid rgba(255,255,255,0.55);
        border-radius: 20px;
        padding: 3px 18px;
        font-size: 12.5px;
        font-weight: 700;
        color: white;
        margin-bottom: 5px;
        letter-spacing: 0.3px;
    }}
    .header-station-name {{
        font-size: 21px;
        font-weight: 800;
        color: white;
        letter-spacing: 0.5px;
    }}
    .header-logo-img {{
        width: 58px; height: 58px;
        border-radius: 50%;
        object-fit: cover;
        flex-shrink: 0;
        border: 2.5px solid rgba(255,255,255,0.5);
        box-shadow: 0 2px 8px rgba(0,0,0,0.25);
    }}
    /* legacy classes */
    .header-left {{ display: flex; align-items: center; gap: 12px; }}
    .header-icon {{
        width: 44px; height: 44px;
        background: rgba(255,255,255,0.22);
        border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-size: 22px;
    }}
    .header-title {{ font-size: 18px; font-weight: 800; }}
    .header-subtitle {{ font-size: 12px; opacity: 0.85; }}
    .header-badge {{
        background: rgba(255,255,255,0.2);
        border: 1.5px solid rgba(255,255,255,0.5);
        border-radius: 20px;
        padding: 5px 14px;
        font-size: 13px;
        font-weight: 700;
    }}
    /* Student fields */
    .student-bar {{
        display: flex; gap: 18px;
        margin-bottom: 14px;
        font-size: 12px;
        background: #f8f9fc;
        border-radius: 8px;
        padding: 8px 14px;
        border: 1px solid #e8ecf2;
    }}
    .student-field {{
        display: flex; align-items: center; gap: 6px; flex: 1;
    }}
    .student-field label {{ font-weight: 700; color: #4a5568; white-space: nowrap; }}
    .student-line {{
        flex: 1; border-bottom: 2px solid {c['border']}; min-width: 60px; height: 18px;
    }}
    /* Instruction box */
    .instruction-box {{
        background: linear-gradient(135deg, {c['light']}, white);
        border-right: 4px solid {c['primary']};
        border-radius: 0 8px 8px 0;
        padding: 10px 14px;
        margin-bottom: 14px;
        font-size: 13.5px;
        font-weight: 600;
        color: {c['primary']};
        box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    }}
    /* Section titles — cleaner accent style */
    .section-title {{
        background: {c['light']};
        color: {c['primary']};
        border-right: 5px solid {c['primary']};
        padding: 7px 12px 7px 10px;
        border-radius: 0 6px 6px 0;
        font-size: 14px;
        font-weight: 800;
        margin: 16px 0 10px 0;
        display: inline-block;
        page-break-after: avoid;
        letter-spacing: 0.2px;
    }}
    .section-block {{
        page-break-inside: avoid;
    }}
    /* Writing lines */
    .answer-line {{
        border-bottom: 1.5px solid #c8d0da;
        height: 24px; width: 100%; margin-bottom: 5px;
    }}
    .writing-box {{
        border: 1.5px solid {c['border']};
        border-radius: 10px;
        padding: 12px;
        min-height: 120px;
        background: #fafbfd;
        margin-top: 8px;
        page-break-inside: avoid;
        box-shadow: inset 0 1px 4px rgba(0,0,0,0.04);
    }}
    .writing-line {{
        border-bottom: 1px solid #dde3ec;
        height: 26px; width: 100%; margin-bottom: 2px;
    }}
    /* Tables */
    table {{ width: 100%; border-collapse: collapse; margin-top: 10px; page-break-inside: avoid; border-radius: 8px; overflow: hidden; }}
    th {{ background: {c['primary']}; color: white; padding: 9px 12px; font-size: 13px; font-weight: 700; }}
    td {{ border: 1px solid #e0e6ee; padding: 8px 11px; font-size: 12.5px; }}
    tr:nth-child(even) td {{ background: {c['light']}; }}
    tr:hover td {{ background: rgba(0,0,0,0.02); }}
    /* Word bank */
    .word-bank {{
        background: #fffbf0;
        border: 1.5px dashed #e6a817;
        border-radius: 10px;
        padding: 9px 14px;
        margin-bottom: 12px;
        font-size: 12.5px;
    }}
    .word-pill {{
        display: inline-block;
        background: {c['light']};
        border: 1.5px solid {c['border']};
        color: {c['primary']};
        padding: 3px 13px;
        border-radius: 16px;
        margin: 2px 3px;
        font-size: 12px;
        font-weight: 700;
    }}
    .key-term {{
        font-weight: 700;
        color: {c['primary']};
        background: {c['light']};
        padding: 1px 5px;
        border-radius: 4px;
    }}
    /* Card grids */
    .cards-grid {{
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 9px;
        margin-top: 10px;
    }}
    .cut-card {{
        border: 2px dashed {c['border']};
        border-radius: 10px;
        padding: 11px;
        min-height: 72px;
        display: flex;
        align-items: center;
        justify-content: center;
        text-align: center;
        font-size: 12px;
        background: {c['light']};
    }}
    .cut-card-term {{
        font-weight: 800;
        font-size: 14px;
        color: {c['primary']};
    }}
    .cut-card-def {{
        font-size: 11px;
        color: #555;
        background: white;
    }}
    .scissors-hint {{
        font-size: 11px; color: #9aa; margin-top: 6px;
        text-align: center; font-style: italic;
    }}
    /* Match exercises */
    .match-container {{
        display: grid;
        grid-template-columns: 1fr 36px 1fr;
        gap: 6px;
        align-items: center;
        margin-bottom: 7px;
    }}
    .match-left {{
        background: {c['light']};
        border: 2px solid {c['border']};
        border-radius: 7px;
        padding: 7px 10px;
        font-weight: 700;
        font-size: 12px;
        text-align: center;
        color: {c['primary']};
    }}
    .match-right {{
        background: white;
        border: 2px solid #d0d8e4;
        border-radius: 7px;
        padding: 7px 10px;
        font-size: 11.5px;
        text-align: center;
        color: #444;
    }}
    .match-line-area {{
        text-align: center;
        font-size: 18px;
        color: #bbb;
    }}
    /* Sort boxes */
    .sort-categories {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
        gap: 10px;
        margin-top: 12px;
    }}
    .sort-box {{
        border: 2px solid {c['border']};
        border-radius: 10px;
        min-height: 100px;
        padding: 9px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.05);
    }}
    .sort-box-title {{
        background: {c['primary']};
        color: white;
        border-radius: 6px;
        padding: 5px 9px;
        font-size: 12px;
        font-weight: 700;
        text-align: center;
        margin-bottom: 9px;
    }}
    /* Difficulty levels */
    .traffic-light {{
        display: flex; gap: 8px; margin: 10px 0;
        page-break-inside: avoid;
    }}
    .tl-green {{ background: #e8f8f0; border: 1.5px solid #27ae60; border-radius: 8px; padding: 8px 10px; font-size: 12px; flex: 1; }}
    .tl-yellow {{ background: #fefce8; border: 1.5px solid #f1c40f; border-radius: 8px; padding: 8px 10px; font-size: 12px; flex: 1; }}
    .tl-red {{ background: #fef0ee; border: 1.5px solid #e74c3c; border-radius: 8px; padding: 8px 10px; font-size: 12px; flex: 1; }}
    .tl-label {{ font-size: 10.5px; font-weight: 800; margin-bottom: 4px; }}
    /* Footer */
    .page-footer {{
        position: fixed;
        bottom: 2mm;
        left: 0; right: 0;
        text-align: center;
        font-size: 9.5px;
        color: #a0aab8;
        padding-top: 4px;
        background: transparent;
        z-index: 200;
        letter-spacing: 0.3px;
    }}
    .page-break {{ page-break-before: always; }}
    /* Physical activity badge */
    .physical-badge {{
        background: linear-gradient(135deg, #e74c3c, #c0392b);
        color: white;
        padding: 6px 18px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 700;
        display: inline-block;
        margin-bottom: 12px;
        box-shadow: 0 2px 6px rgba(231,76,60,0.35);
    }}
    .materials-box {{
        background: #fffbf0;
        border: 1.5px dashed #e6a817;
        border-radius: 10px;
        padding: 10px 14px;
        margin-bottom: 14px;
    }}
    .materials-box-title {{
        font-weight: 700;
        font-size: 13px;
        color: #d4870a;
        margin-bottom: 6px;
    }}
    .materials-list {{
        list-style: none;
        padding: 0; margin: 0;
        display: flex; flex-wrap: wrap; gap: 6px;
    }}
    .materials-list li {{
        background: white;
        border: 1.5px solid #e6a817;
        border-radius: 7px;
        padding: 4px 11px;
        font-size: 12px;
        color: #555;
    }}
    .steps-box {{
        background: #f7f9fc;
        border: 1.5px solid {c['border']};
        border-radius: 10px;
        padding: 12px 16px;
        margin-bottom: 14px;
        page-break-inside: avoid;
    }}
    .steps-box-title {{
        font-weight: 700;
        font-size: 13px;
        color: {c['primary']};
        margin-bottom: 8px;
    }}
    .steps-list {{
        list-style: none;
        padding: 0; margin: 0;
        counter-reset: step-counter;
    }}
    .steps-list li {{
        counter-increment: step-counter;
        display: flex;
        align-items: flex-start;
        gap: 10px;
        margin-bottom: 9px;
        font-size: 13px;
    }}
    .steps-list li::before {{
        content: counter(step-counter);
        background: {c['primary']};
        color: white;
        border-radius: 50%;
        min-width: 24px;
        height: 24px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 11px;
        font-weight: 800;
        flex-shrink: 0;
        box-shadow: 0 1px 4px rgba(0,0,0,0.2);
    }}
    /* Word cards for cut-out activity */
    .word-cards-print {{
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 9px;
        margin-top: 10px;
    }}
    .word-card-print {{
        border: 2px dashed {c['border']};
        border-radius: 10px;
        padding: 11px 9px;
        text-align: center;
        background: {c['light']};
        page-break-inside: avoid;
    }}
    .word-card-term {{
        font-weight: 800;
        font-size: 14px;
        color: {c['primary']};
        margin-bottom: 5px;
    }}
    .word-card-def {{
        font-size: 10.5px;
        color: #666;
        border-top: 1px dashed #ccc;
        padding-top: 5px;
        margin-top: 4px;
    }}
    """
