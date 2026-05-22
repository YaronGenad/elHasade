import random
from typing import Dict, Optional
from ..config import STATION_COLORS
from .css import get_css, ENGLISH_LABELS, ENGLISH_STATION_NAMES
from .header import render_header


def _decorative_html(decorative_image: Optional[str]) -> str:
    if not decorative_image:
        return ""
    try:
        from ..images import ImageService
        dec_url = ImageService.to_data_url(decorative_image)
        return (
            '<div style="clear:both; margin-top:18px; text-align:center;">'
            f'<img src="{dec_url}" style="max-width:100%; max-height:130px; '
            'object-fit:contain; border-radius:8px; opacity:0.92;" alt=""></div>'
        )
    except Exception:
        return ""


def render_vocabulary(title: str, round_num: int, data: Dict, english_mode: bool = False,
                      decorative_image: Optional[str] = None) -> str:
    # ── STEAM bilingual game branch ────────────────────────────────
    activity_type = str(data.get('activity_type') or data.get('game_type') or 'matching_cards')
    if activity_type.startswith('stem_') or data.get('bilingual'):
        return _render_stem_vocabulary(title, round_num, data, decorative_image=decorative_image)
    # ── Language / English vocabulary branch ──────────────────────
    words = data.get('words', [])
    word_bank = data.get('word_bank', [w.get('word', '') for w in words[:8]])
    left_col = data.get('left_column', [])
    right_col = data.get('right_column', []).copy()
    categories = data.get('categories', [])

    # Localised labels
    if english_mode:
        lbl = ENGLISH_LABELS
        html_dir = "ltr"
        html_lang = "en"
        page_title = f"Vocabulary Station - {title} - Round {round_num}"
        footer_text = f"Al-HaSadeh | Vocabulary Station | {title} | Round {round_num} — {lbl['footer_copy']}"
        cards_title = "✂️ Word Cards (cut out)"
        defs_title = "✂️ Definition Cards (cut out — shuffled!)"
        scissors_hint = lbl['scissors']
        clothesline_hint = "💡 Draw a line to connect each word (right column) to its definition/opposite/synonym (left column)"
        sort_words_title = "✂️ Words to Sort (cut out)"
        sort_paste_title = "📋 Paste each word in the correct category:"
        word_bank_label = lbl['word_bank']
        def_table_headers = "<tr><th>Word</th><th>Definition</th><th>Write your own sentence</th></tr>"
        crossword_across = "↔️ Across"
        crossword_down = "↕️ Down"
        crossword_placeholder = "[Crossword grid — draw or print manually]"
        physical_labels = {
            'physical_plasticine': ('🧱', 'Clay Sculpting'),
            'physical_model':      ('🏗️', 'Model Building'),
            'physical_game':       ('🃏', 'Card / Board Game'),
            'physical_poster':     ('🖼️', 'Poster / Display'),
            'physical_simulation': ('🎭', 'Role Play / Simulation'),
            'physical_clothesline':('🪢', 'Washing Line — Pair Matching'),
        }
        physical_badge_prefix = "Hands-on Activity"
        materials_title = lbl['materials_title']
        steps_title = lbl['steps_title']
        word_cards_title = "✂️ Word Cards for Printing and Cutting"
        cut_hint = lbl['cut_hint']
        dominoes_hint = "✂️ Cut out the cards and connect the end of one card to the start of the next (word → definition)"
        list_padding = "padding-left:18px;"
    else:
        html_dir = "rtl"
        html_lang = "he"
        page_title = f"תחנת אוצר מילים - {title} - סבב {round_num}"
        footer_text = f"א\"ל השד\"ה | תחנת הרחבת אוצר מילים | {title} | סבב {round_num} — © כל הזכויות שמורות"
        cards_title = "✂️ קלפי מושגים (גזור)"
        defs_title = "✂️ קלפי הגדרות (גזור — מעורבבים!)"
        scissors_hint = "✂️ גזור את כל הקלפים, ערבב, וחבר כל מושג להגדרה שלו"
        clothesline_hint = "💡 חבר/י בקו כל מושג (עמודה ימין) להגדרה/הפך/נרדפת שלו (עמודה שמאל)"
        sort_words_title = "✂️ מילים למיון (גזור)"
        sort_paste_title = "📋 הדבק כל מילה בקטגוריה הנכונה:"
        word_bank_label = "📚 בנק מילים:"
        def_table_headers = "<tr><th>מילה</th><th>הגדרה</th><th>כתוב משפט משלך</th></tr>"
        crossword_across = "↔️ מאוזן"
        crossword_down = "↕️ מאונך"
        crossword_placeholder = "[תשבץ — ציירו/הדפיסו ידנית]"
        physical_labels = {
            'physical_plasticine': ('🧱', 'פיסול בפלסטלינה / בצק'),
            'physical_model':      ('🏗️', 'בניית מודל / דיאגרמה'),
            'physical_game':       ('🃏', 'משחק קלפים / זכרון / לוח'),
            'physical_poster':     ('🖼️', 'בניית כרזה / תערוכה'),
            'physical_simulation': ('🎭', 'משחק תפקידים / סימולציה'),
            'physical_clothesline':('🪢', 'חבל כביסה — התאמת זוגות'),
        }
        physical_badge_prefix = "פעילות חווייתית"
        materials_title = "🎒 מה צריך להכין:"
        steps_title = "📋 שלבי הפעילות:"
        word_cards_title = "✂️ קלפי מילים להדפסה וגזירה"
        cut_hint = "גזרו את הקלפים לפני הפעילות"
        dominoes_hint = "✂️ גזור את הקלפים וחבר סוף קלף אחד לתחילת הקלף הבא (מושג → הגדרה)"
        list_padding = "padding-right:18px;"

    body_html = ""

    if activity_type in ("matching_cards", "idiom_cards"):
        term_cards = "".join([
            f'<div class="cut-card cut-card-term">{w.get("word", "")}\n'
            f'<div style="font-size:10px;color:#888;font-weight:400;">{str(w.get("example") or "")[:40]}</div></div>'
            for w in words
        ])
        def_cards_shuffled = words.copy()
        random.shuffle(def_cards_shuffled)
        def_cards = "".join([f'<div class="cut-card cut-card-def">{w.get("definition", "")}</div>' for w in def_cards_shuffled])
        body_html = f"""
        <div class="section-title">{cards_title}</div>
        <div class="cards-grid">{term_cards}</div>
        <div class="section-title" style="margin-top:12px;">{defs_title}</div>
        <div class="cards-grid">{def_cards}</div>
        <div class="scissors-hint">{scissors_hint}</div>
        """

    elif activity_type == "clothesline":
        if not left_col:
            left_col = [w.get('word', '') for w in words]
        if not right_col:
            right_col = [w.get('partner', w.get('definition', '')) for w in words]
        random.shuffle(right_col)
        match_html = ""
        for i in range(min(len(left_col), len(right_col))):
            match_html += f"""
            <div class="match-container">
                <div class="match-left">{left_col[i]}</div>
                <div class="match-line-area">—</div>
                <div class="match-right">{right_col[i]}</div>
            </div>
            """
        body_html = f"""
        <div style="font-size:12px; color:#888; margin-bottom:10px; background:#fffde7; padding:8px; border-radius:6px;">
            {clothesline_hint}
        </div>
        {match_html}
        """

    elif activity_type == "sorting_table":
        pills = "".join([f'<span class="word-pill">{w.get("word", "")} ✂️</span>' for w in words])
        sort_boxes = "".join([
            f'<div class="sort-box"><div class="sort-box-title">{cat}</div></div>'
            for cat in categories[:4]
        ])
        body_html = f"""
        <div style="margin-bottom:10px;">
            <div class="section-title">{sort_words_title}</div>
            <div style="margin-top:8px;">{pills}</div>
        </div>
        <div class="section-title">{sort_paste_title}</div>
        <div class="sort-categories">{sort_boxes}</div>
        """

    elif activity_type == "fill_in_poster":
        sentences = data.get('fill_sentences', [])
        pills = "".join([f'<span class="word-pill">{w}</span>' for w in word_bank])
        sents_html = "".join([f"""
        <div style="display:flex; align-items:center; gap:6px; margin-bottom:12px; font-size:13.5px;">
            <strong>{i + 1}.</strong>
            {str(s.get('sentence') or '').replace('_____', '<span style="border-bottom:2px solid #f1c40f; min-width:80px; display:inline-block;">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span>')}
        </div>
        """ for i, s in enumerate(sentences)])
        body_html = f"""
        <div class="word-bank">{word_bank_label} {pills}</div>
        {sents_html}
        """

    elif activity_type == "definition_table":
        rows = "".join([
            f"<tr><td><strong>{w.get('word', '')}</strong></td><td>{w.get('definition', '')}</td><td style='min-width:150px;'></td></tr>"
            for w in words
        ])
        body_html = f"<table>{def_table_headers}{rows}</table>"

    elif activity_type == "crossword_mini":
        clues = data.get('crossword_clues', [])
        across = [c for c in clues if c.get('direction') in ('מאוזן', 'across')]
        down = [c for c in clues if c.get('direction') in ('מאונך', 'down')]
        across_html = "".join([f'<li><strong>{c["number"]}.</strong> {c["clue"]}</li>' for c in across])
        down_html = "".join([f'<li><strong>{c["number"]}.</strong> {c["clue"]}</li>' for c in down])
        body_html = f"""
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:16px;">
            <div>
                <div class="section-title">{crossword_across}</div>
                <ol style="font-size:13px; {list_padding}">{across_html}</ol>
                <div class="section-title" style="margin-top:10px;">{crossword_down}</div>
                <ol style="font-size:13px; {list_padding}">{down_html}</ol>
            </div>
            <div style="background:#fafafa; border:2px solid #f1c40f; border-radius:8px; min-height:200px; display:flex; align-items:center; justify-content:center; font-size:12px; color:#888;">
                {crossword_placeholder}
            </div>
        </div>
        """

    elif activity_type.startswith("physical_"):
        materials = data.get('materials_needed', [])
        steps = data.get('physical_steps', [])

        emoji, label = physical_labels.get(activity_type, ('✋', 'Hands-on Activity' if english_mode else 'פעילות ידנית'))

        materials_html = ""
        if materials:
            items_html = "".join([f"<li>{m}</li>" for m in materials])
            materials_html = f"""
            <div class="materials-box">
                <div class="materials-box-title">{materials_title}</div>
                <ul class="materials-list">{items_html}</ul>
            </div>
            """

        steps_html = ""
        if steps:
            steps_li = "".join([f"<li>{s}</li>" for s in steps])
            steps_html = f"""
            <div class="steps-box">
                <div class="steps-box-title">{steps_title}</div>
                <ol class="steps-list">{steps_li}</ol>
            </div>
            """

        # Word cards for cutting/use
        cards_html = ""
        if words:
            cards = "".join([f"""
            <div class="word-card-print">
                <div class="word-card-term">{w.get('word', '')}</div>
                <div class="word-card-def">{w.get('definition', '')}</div>
            </div>""" for w in words])
            cards_html = f"""
            <div class="section-title" style="margin-top:14px;">{word_cards_title}</div>
            <div class="scissors-hint" style="margin-bottom:8px;">{cut_hint}</div>
            <div class="word-cards-print">{cards}</div>
            """

        body_html = f"""
        <div class="physical-badge">{emoji} {physical_badge_prefix} — {label}</div>
        {materials_html}
        {steps_html}
        {cards_html}
        """

    else:  # dominoes or fallback
        dom_cards = ""
        shuffled = words.copy()
        random.shuffle(shuffled)
        for i in range(len(words)):
            left = words[i].get('word', '')
            right_idx = (i + 1) % len(shuffled)
            right = shuffled[right_idx].get('definition', '') if shuffled else ''
            dom_cards += f"""
            <div style="border:2.5px dashed #f1c40f; border-radius:8px; display:grid; grid-template-columns:1fr 4px 1fr; min-height:60px; overflow:hidden; break-inside:avoid;">
                <div style="background:#fef9e7; display:flex; align-items:center; justify-content:center; font-weight:800; font-size:13px; padding:6px; text-align:center;">{left}</div>
                <div style="background:#7d6608;"></div>
                <div style="background:white; display:flex; align-items:center; justify-content:center; font-size:11px; padding:6px; text-align:center; color:#444;">{right}</div>
            </div>
            """
        body_html = f"""
        <div class="scissors-hint" style="margin-bottom:8px;">{dominoes_hint}</div>
        <div style="display:grid; grid-template-columns: repeat(2, 1fr); gap:8px;">{dom_cards}</div>
        """

    return f"""<!DOCTYPE html>
<html dir="{html_dir}" lang="{html_lang}">
<head><meta charset="UTF-8"><title>{page_title}</title>
<style>{get_css('vocabulary')}</style></head>
<body>
{render_header(title, round_num, 'vocabulary', english_mode=english_mode)}
<div class="instruction-box">📌 {data.get('instruction', '')}</div>
{body_html}
{_decorative_html(decorative_image)}
<div class="page-footer">{footer_text}</div>
</body></html>"""


def _render_stem_vocabulary(title: str, round_num: int, data: Dict,
                            decorative_image: Optional[str] = None) -> str:
    """Renders bilingual STEAM vocabulary game cards."""
    c = STATION_COLORS['vocabulary']
    game_type = data.get('game_type') or data.get('activity_type', 'stem_memory')
    words = data.get('words', [])

    game_labels = {
        'stem_memory':         ('🃏', 'זיכרון מושגים (Memory Match)', 'מצא זוגות: עברית↔אנגלית'),
        'stem_alias':          ('🗣️', 'אליאס מדעי (Science Alias)', 'הסבר את המושג ללא לומר אותו — הצוות מנחש'),
        'stem_taboo':          ('🚫', 'טאבו מדעי (Science Taboo)', 'הסבר ללא שימוש במילים האסורות'),
        'stem_quartets':       ('♦️', 'רביעיות מדעיות (Quartets)', 'אסוף 4 קלפים מאותה קטגוריה STEAM'),
        'stem_bingo':          ('🎯', 'Bingo מדעי (STEAM Bingo)', 'המורה קוראת הגדרות — מי שמזהה סומן'),
        'stem_snakes':         ('🐍', 'סולמות ונחשים STEAM', 'שאלת מושג בכל ריבוע — נכון=עלה, טעות=ירד'),
        'stem_quiz':           ('❓', 'שאלות ותשובות (Quiz Bowl)', 'תחרות קבוצתית — קלפי שאלות STEAM'),
        'stem_who_am_i':       ('🤔', 'מי אני? (Who Am I? Science)', 'כרטיס מושג על המצח — שאלות כן/לא'),
        'stem_dominoes':       ('🁣', 'דומינו STEAM', 'הנח קלף כך שמושג פוגש את הגדרתו'),
        'stem_flashcard':      ('⚡', 'כרטיסיות אוצר (Flashcard Battle)', 'מי עונה על ההגדרה מהר יותר — מנצח'),
        'stem_concept_puzzle': ('🧩', 'פאזל מושגים (Concept Puzzle)', 'חתוך ל-4 חלקים: שם/הגדרה/דוגמה/ציור'),
        'stem_word_chain':     ('🔗', 'שרשרת מדעית (Word Chain)', 'מושג שמתחיל באות האחרונה + הסבר הקשר'),
        'stem_matching_board': ('🗺️', 'התאמת מושגים (Matching Board)', 'לוח גדול — חיבור מושג↔הגדרה/תמונה'),
        'stem_20_questions':   ('🔢', '20 שאלות מדעיות', 'שאלות כן/לא לגילוי המושג הנסתר'),
        'stem_track':          ('🏁', 'מסלול מדעי (STEAM Track)', 'קלפי ירוק/צהוב/אדום — לפי רמת הקושי'),
        'stem_catan':          ('🏰', 'קטאן מדעי (Science Catan)', 'בנה ממלכה מדעית — ענה נכון, קבל משאב'),
        'stem_monopoly':       ('🎲', 'מונופול מדעי (Science Monopoly)', 'מושגי STEAM כנכסים — ענה הגדרה, רכוש'),
    }
    emoji, game_name, mechanic = game_labels.get(game_type, ('🃏', 'משחק מושגים STEAM', 'לפי הוראות'))

    # Materials & steps
    materials = data.get('materials_needed', [])
    mat_items = "".join([f"<li>{m}</li>" for m in materials])
    mat_html = f"""
    <div class="materials-box">
        <div class="materials-box-title">🎒 מה צריך להכין:</div>
        <ul class="materials-list">{mat_items}</ul>
    </div>""" if materials else ""

    steps = data.get('physical_steps', [])
    steps_li = "".join([f"<li>{s}</li>" for s in steps])
    steps_html = f"""
    <div class="steps-box">
        <div class="steps-box-title">📋 הוראות המשחק:</div>
        <ol class="steps-list">{steps_li}</ol>
    </div>""" if steps else ""

    # Bilingual concept cards
    cards_html = ""
    if words:
        cards = "".join([f"""
        <div class="word-card-print" style="background:{c['light']}; border-color:{c['border']};">
            <div class="word-card-term" style="color:{c['primary']};">{w.get('word', '')}</div>
            <div style="font-size:11px; color:#888; font-style:italic; margin:2px 0 4px;">{w.get('english', '')}</div>
            <div class="word-card-def">{w.get('definition', '')}</div>
            {f'<div style="font-size:10px; color:#aaa; margin-top:3px; border-top:1px dashed #eee; padding-top:3px;">{w.get("category", "")}</div>' if w.get('category') else ''}
        </div>""" for w in words])

        # Also create matching pairs cards (Hebrew on one side, English on other)
        heb_cards = "".join([f'<div class="cut-card cut-card-term" style="background:{c["light"]}; border-color:{c["border"]};">'
                              f'<span style="color:{c["primary"]}; font-weight:800;">{w.get("word", "")}</span>'
                              f'<div style="font-size:9px;color:#888;">{str(w.get("example") or "")[:35]}</div></div>'
                              for w in words])
        eng_cards_shuffled = words.copy()
        random.shuffle(eng_cards_shuffled)
        eng_cards = "".join([f'<div class="cut-card cut-card-def">'
                              f'<strong style="font-size:12px;">{w.get("english","")}</strong>'
                              f'<div style="font-size:10px;color:#666;margin-top:3px;">{str(w.get("definition") or "")[:50]}</div></div>'
                              for w in eng_cards_shuffled])

        cards_html = f"""
        <div class="section-title" style="margin-top:14px;">✂️ קלפי מושגים מלאים (להדפסה)</div>
        <div class="scissors-hint">כרטיס לכל מושג: עברית + אנגלית + הגדרה + קטגוריה</div>
        <div class="word-cards-print">{cards}</div>
        <div class="section-title" style="margin-top:14px;">✂️ קלפי התאמה — עברית (גזור)</div>
        <div class="cards-grid">{heb_cards}</div>
        <div class="section-title" style="margin-top:10px;">✂️ קלפי התאמה — English (גזור — מעורבב!)</div>
        <div class="cards-grid">{eng_cards}</div>
        <div class="scissors-hint">✂️ גזור את כל הקלפים, ערבב, וחבר כל מושג לתרגומו/הגדרתו</div>
        """

    return f"""<!DOCTYPE html>
<html dir="rtl" lang="he">
<head><meta charset="UTF-8"><title>תחנת אוצר מילים STEAM - {title} - סבב {round_num}</title>
<style>{get_css('vocabulary')}</style></head>
<body>
{render_header(title, round_num, 'vocabulary')}
<div class="instruction-box">
    <span style="background:{c['primary']}; color:white; padding:3px 10px; border-radius:12px; font-size:12px; margin-left:8px;">{emoji} {game_name}</span>
    📌 {mechanic}
</div>
<div style="background:#fef9e7; border:1.5px solid #f1c40f; border-radius:6px; padding:8px 12px; margin-bottom:12px; font-size:12px; color:#7d6608;">
    📌 {data.get('instruction', '')}
</div>
{mat_html}
{steps_html}
{cards_html}
{_decorative_html(decorative_image)}
<div class="page-footer">א"ל השד"ה STEAM | תחנת אוצר מילים | {title} | סבב {round_num} — © כל הזכויות שמורות</div>
</body></html>"""
