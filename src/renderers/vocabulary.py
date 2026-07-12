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
            '<div style="clear:both; margin-top:14px; text-align:center; '
            'break-before:avoid; page-break-before:avoid; break-inside:avoid;">'
            f'<img src="{dec_url}" style="max-width:100%; max-height:130px; '
            'object-fit:contain; border-radius:8px; opacity:0.92;" alt=""></div>'
        )
    except Exception:
        return ""


def _extension_html(ext: dict, english_mode: bool = False) -> str:
    if not ext or not ext.get('items'):
        return ""
    title_txt = ext.get('title', 'Extension Activity' if english_mode else 'המשך ואתגר')
    instruction = ext.get('instruction', '')
    items_html = "".join([
        f'<div style="margin-bottom:5px; font-size:12.5px;">{i + 1}. {item}</div>'
        for i, item in enumerate(ext['items'])
    ])
    return f"""
<div style="margin-top:14px; background:#fef9e7; border:1.5px solid #f1c40f;
     border-radius:8px; padding:10px 14px;
     break-before:avoid; page-break-before:avoid; break-inside:avoid;">
    <div class="section-title">⭐ {title_txt}</div>
    <div style="font-size:12.5px; margin-bottom:8px; color:#555;">{instruction}</div>
    {items_html}
</div>"""


def _render_crossword_grid(clues):
    """Auto-place crossword words on a grid and return a printable HTML table."""
    if not clues:
        return ''

    grid = {}       # (row, col) -> letter
    cell_nums = {}  # (row, col) -> min clue number at this cell (word start)
    placed = []     # (clue_dict, start_row, start_col, is_across)

    def _is_across(c):
        return c.get('direction', 'מאוזן') in ('מאוזן', 'across')

    def _cell(row, col, i, ia):
        return (row, col + i) if ia else (row + i, col)

    def _can_place(word, row, col, ia):
        pre  = (row, col - 1)        if ia else (row - 1, col)
        post = (row, col + len(word)) if ia else (row + len(word), col)
        if pre in grid or post in grid:
            return False
        for i, ch in enumerate(word):
            r, c = _cell(row, col, i, ia)
            if not (0 <= r <= 25 and 0 <= c <= 25):
                return False
            if (r, c) in grid and grid[(r, c)] != ch:
                return False
        return True

    def _place(clue, row, col, ia):
        word = clue['answer'].upper()
        for i, ch in enumerate(word):
            r, c = _cell(row, col, i, ia)
            grid[(r, c)] = ch
        try:
            num = int(clue.get('number', 0))
        except (TypeError, ValueError):
            num = 0
        prev = cell_nums.get((row, col), 9999)
        cell_nums[(row, col)] = min(prev, num)
        placed.append((clue, row, col, ia))

    # Place first word at center
    f = clues[0]
    fia = _is_across(f)
    fw = f['answer'].upper()
    if fia:
        _place(f, 7, max(0, 7 - len(fw) // 2), True)
    else:
        _place(f, max(0, 7 - len(fw) // 2), 7, False)

    # Place remaining words by intersecting with already-placed words
    for clue in clues[1:]:
        word = clue['answer'].upper()
        ia = _is_across(clue)
        done = False
        for pclue, pr, pcc, pia in placed:
            if pia == ia:
                continue
            pw = pclue['answer'].upper()
            for i, ch in enumerate(word):
                for j, pch in enumerate(pw):
                    if ch != pch:
                        continue
                    pr_j, pc_j = _cell(pr, pcc, j, pia)
                    tr = pr_j if ia else pr_j - i
                    tc = pc_j - i if ia else pc_j
                    if _can_place(word, tr, tc, ia):
                        _place(clue, tr, tc, ia)
                        done = True
                        break
                if done:
                    break
            if done:
                break
        if not done:
            for attempt in range(15):
                tr, tc = (1 + attempt * 2, max(0, 7 - len(word) // 2)) if ia else (max(0, 7 - len(word) // 2), 1 + attempt * 2)
                if _can_place(word, tr, tc, ia):
                    _place(clue, tr, tc, ia)
                    break

    if not grid:
        return ''

    min_r = min(r for r, _ in grid)
    max_r = max(r for r, _ in grid)
    min_c = min(c for _, c in grid)
    max_c = max(c for _, c in grid)

    html = '<table style="border-collapse:collapse;margin:0 auto;direction:ltr;">'
    for r in range(min_r, max_r + 1):
        html += '<tr>'
        for c in range(min_c, max_c + 1):
            if (r, c) in grid:
                n = cell_nums.get((r, c))
                ns = (f'<span style="position:absolute;top:1px;left:1px;font-size:7px;'
                      f'font-weight:700;color:#222;line-height:1;">{n}</span>'
                      ) if n and n < 9999 else ''
                html += (f'<td style="position:relative;width:24px;height:24px;'
                         f'border:1.5px solid #444;background:white;padding:0;">{ns}</td>')
            else:
                html += '<td style="width:24px;height:24px;background:#2c3e50;border:1px solid #1a252f;padding:0;"></td>'
        html += '</tr>'
    html += '</table>'
    return html


def _render_word_search(words, english_mode=False):
    """Generate and render a printable word search (תשחץ) puzzle."""
    import random as _rnd

    FILL_LETTERS = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ") if english_mode else list("אבגדהוזחטיכלמנסעפצקרשת")
    GRID_SIZE = 14
    DIRECTIONS = [(0, 1), (1, 0), (0, -1), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)]

    word_strs = []
    for w in words:
        txt = (w.get('word') or '').strip().upper()
        if 2 <= len(txt) <= GRID_SIZE - 1:
            word_strs.append(txt)
    if not word_strs:
        return ''

    grid = [['.' for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
    placed_words = []

    def _try_place(word, r, c, dr, dc):
        cells = []
        for i, ch in enumerate(word):
            nr, nc = r + i * dr, c + i * dc
            if not (0 <= nr < GRID_SIZE and 0 <= nc < GRID_SIZE):
                return False
            if grid[nr][nc] not in ('.', ch):
                return False
            cells.append((nr, nc, ch))
        for nr, nc, ch in cells:
            grid[nr][nc] = ch
        return True

    seed = sum(ord(c) for w in word_strs for c in w)
    rng = _rnd.Random(seed)
    for word in sorted(word_strs, key=len, reverse=True):
        attempts = [(r, c, dr, dc) for r in range(GRID_SIZE) for c in range(GRID_SIZE) for dr, dc in DIRECTIONS]
        rng.shuffle(attempts)
        for r, c, dr, dc in attempts[:300]:
            if _try_place(word, r, c, dr, dc):
                placed_words.append(word)
                break

    for r in range(GRID_SIZE):
        for c in range(GRID_SIZE):
            if grid[r][c] == '.':
                grid[r][c] = rng.choice(FILL_LETTERS)

    cs = ('width:22px;height:22px;text-align:center;vertical-align:middle;'
          'border:1px solid #ccc;font-size:13px;font-weight:600;background:white;padding:0;')
    rows_html = ''.join(
        '<tr>' + ''.join(f'<td style="{cs}">{ch}</td>' for ch in row) + '</tr>'
        for row in grid
    )
    g_dir = "ltr" if english_mode else "rtl"
    table_html = f'<table style="border-collapse:collapse;direction:{g_dir};margin:0 auto;">{rows_html}</table>'

    label = "Find the hidden words:" if english_mode else "מצאו את המילים הנסתרות:"
    ps = ('display:inline-block;background:#f1c40f;padding:3px 10px;margin:3px 2px;'
          'border-radius:4px;font-weight:700;font-size:12px;')
    pills = ''.join(f'<span style="{ps}">{w}</span>' for w in placed_words)

    return (f'<div style="overflow-x:auto;text-align:center;">{table_html}</div>'
            f'<div style="margin-top:12px;"><div class="section-title">{label}</div>'
            f'<div style="margin-top:6px;">{pills}</div></div>')


def render_vocabulary(title: str, round_num: int, data: Dict, english_mode: bool = False,
                      topic_image: Optional[str] = None,
                      decorative_image: Optional[str] = None) -> str:
    # ── STEAM bilingual game branch ────────────────────────────────
    activity_type = str(data.get('activity_type') or data.get('game_type') or 'matching_cards')
    if activity_type.startswith('stem_') or data.get('bilingual'):
        return _render_stem_vocabulary(title, round_num, data, topic_image=topic_image, decorative_image=decorative_image)
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
        footer_text = f"מחולל יחידות לימוד | Vocabulary Station | {title} | Round {round_num} — {lbl['footer_copy']}"
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

    topic_img_html = ""
    if topic_image:
        try:
            from ..images import ImageService
            img_url = ImageService.to_data_url(topic_image)
            float_dir = "right" if english_mode else "left"
            margin = "0 0 8px 12px" if english_mode else "0 12px 8px 0"
            topic_img_html = (
                f'<img src="{img_url}" style="float:{float_dir}; margin:{margin}; '
                'width:180px; height:120px; object-fit:cover; border-radius:8px; '
                'border:2px solid #f1c40f;" alt="">'
            )
        except Exception:
            pass

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

    elif activity_type == "word_search":
        ws_html = _render_word_search(words, english_mode=english_mode)
        body_html = ws_html if ws_html else f'<div style="text-align:center;color:#888;padding:20px;">{"[Word Search]" if english_mode else "[תשחץ — לא נוצר]"}</div>'

    elif activity_type == "crossword_mini":
        clues = data.get('crossword_clues', [])
        across = [c for c in clues if c.get('direction') in ('מאוזן', 'across')]
        down = [c for c in clues if c.get('direction') in ('מאונך', 'down')]
        across_html = "".join([f'<li><strong>{c["number"]}.</strong> {c["clue"]}</li>' for c in across])
        down_html = "".join([f'<li><strong>{c["number"]}.</strong> {c["clue"]}</li>' for c in down])
        grid_html = _render_crossword_grid(clues)
        if not grid_html:
            grid_html = f'<div style="text-align:center;color:#888;padding:20px;">{crossword_placeholder}</div>'
        body_html = f"""
        <div style="display:flex; flex-direction:column; gap:12px;">
            <div style="text-align:center; overflow-x:auto;">{grid_html}</div>
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-top:8px;">
                <div>
                    <div class="section-title">{crossword_across}</div>
                    <ol style="font-size:13px; {list_padding}">{across_html}</ol>
                </div>
                <div>
                    <div class="section-title">{crossword_down}</div>
                    <ol style="font-size:13px; {list_padding}">{down_html}</ol>
                </div>
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
{topic_img_html}
{body_html}
{_decorative_html(decorative_image)}
{_extension_html(data.get('extension_activity', {}), english_mode=english_mode)}
<div class="page-footer">{footer_text}</div>
</body></html>"""


def _render_stem_vocabulary(title: str, round_num: int, data: Dict,
                            topic_image: Optional[str] = None,
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

    stem_topic_img_html = ""
    if topic_image:
        try:
            from ..images import ImageService
            img_url = ImageService.to_data_url(topic_image)
            stem_topic_img_html = (
                f'<img src="{img_url}" style="float:left; margin:0 12px 8px 0; '
                'width:180px; height:120px; object-fit:cover; border-radius:8px; '
                'border:2px solid #f1c40f;" alt="">'
            )
        except Exception:
            pass

    return f"""<!DOCTYPE html>
<html dir="rtl" lang="he">
<head><meta charset="UTF-8"><title>תחנת אוצר מילים STEAM - {title} - סבב {round_num}</title>
<style>{get_css('vocabulary')}</style></head>
<body>
{render_header(title, round_num, 'vocabulary')}
{stem_topic_img_html}
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
{_extension_html(data.get('extension_activity', {}))}
<div class="page-footer">א"ל השד"ה STEAM | תחנת אוצר מילים | {title} | סבב {round_num} — © כל הזכויות שמורות</div>
</body></html>"""
