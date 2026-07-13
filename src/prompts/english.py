from typing import Any, Dict, List
from ..config import get_english_grade_level, get_curriculum_profile


def _curric_note(grade: str) -> str:
    curric = get_curriculum_profile(grade, "אנגלית")
    if not curric:
        return ""
    parts = []
    if curric.get("cefr"):
        parts.append(f"CEFR: {curric['cefr']}")
    if curric.get("grammar"):
        parts.append(f"grammar: {', '.join(curric['grammar'])}")
    if curric.get("productive_vocabulary"):
        parts.append(f"productive vocabulary: {curric['productive_vocabulary']} words")
    if curric.get("writing"):
        parts.append(f"max writing: {curric['writing']}")
    if curric.get("avoid"):
        parts.append(f"avoid: {', '.join(curric['avoid'])}")
    return f"\nMoE 2020 curriculum for grade {grade}: {'; '.join(parts)}\n" if parts else ""


def build_english_roadmap_prompt(subject: str, topic: str, grade: str, rounds: int) -> str:
    egl = get_english_grade_level(grade)
    curric = _curric_note(grade)
    return f"""You are planning an English language learning unit using the PACE method (Precision, Articulateness, Conception, Enhancing Vocabulary).

**IMPORTANT: ALL output — every word, title, instruction, question, and label — must be in English.**

<user_input>
Subject: {subject} | Topic: {topic}
Grade: {grade} | Age: {egl['age']} | CEFR Level: {egl['cefr']}
Number of rounds: {rounds}{curric}
</user_input>

**PACE station structure — four stations, one anchor text per unit:**
1. **Conception** — narrative text only, oral discussion with a partner (NO writing, ever)
2. **Articulateness** — guided writing, teacher physically present, ONE writing strategy per unit
3. **Precision** — game-based spelling/grammar accuracy (never a standard fill-in worksheet)
4. **Enhancing Vocabulary** — physical/sensorimotor creation required (clay, model, drawing, mobile)

**PACE iron rules — must be enforced in EVERY round:**
1. Conception: narrative text ONLY; ZERO writing; oral responses only; no multiple choice
2. Articulateness: teacher must be present at this station the entire time; ONE writing strategy per unit — choose from: optimal_response, description, narration, summarization, comparison, argumentation, synthesis
3. Precision: every task must have a game/play element (wheel, cards, sorting, competition) — no plain fill-in sheets
4. Enhancing Vocabulary: physical creation is mandatory (clay, model, illustrated dictionary, mobile, poster)
5. All 4 stations are fully independent — student can start at any station

**Writing strategies for Articulateness (one per unit):**
optimal_response, description, narration, summarization, comparison, argumentation, synthesis

**Age-appropriate options for grade {grade} ({egl['cefr']}):**
- Conception: {', '.join(egl['comprehension_options'])}
- Articulateness: {', '.join(egl['methods_options'])}
- Precision: {', '.join(egl['precision_options'])}
- Enhancing Vocabulary: {', '.join(egl['vocabulary_options'])}

**Output format — JSON only (all values in English):**
{{
  "unit_title": "Unit title in English",
  "central_text_type": "narrative/story/poem/prose",
  "language_focus": "main grammar/language focus of the unit",
  "writing_strategy": "single strategy used at Articulateness across ALL rounds",
  "learning_goals": {{
    "knowledge": ["knowledge goal 1", "knowledge goal 2"],
    "skills": ["skill 1", "skill 2"],
    "values": ["value/habit 1"]
  }},
  "rounds": [
    {{
      "round": 1,
      "conception": {{
        "text_type": "narrative/story/poem/prose",
        "description": "brief description of the text (oral only — no writing)",
        "discussion_focus": "main oral discussion question / theme / conflict"
      }},
      "articulateness": {{
        "writing_strategy": "strategy name (same across all rounds)",
        "description": "description of the scaffolded writing task"
      }},
      "precision": {{
        "activity_type": "spelling/grammar/word-forms/punctuation/tenses/prepositions",
        "game_element": "wheel/cards/sorting/competition/dominoes",
        "description": "description including the game element"
      }},
      "vocabulary": {{
        "activity_type": "physical_plasticine/physical_model/physical_game/crossword/matching_cards/illustrated_dictionary",
        "physical_creation": true,
        "description": "description including what students physically create"
      }}
    }}
  ]
}}"""


def build_english_comprehension_prompt(subject: str, topic: str, grade: str,
                                        round_num: int, total_rounds: int,
                                        round_plan: Dict, prev_texts: List[str]) -> str:
    egl = get_english_grade_level(grade)
    curric = _curric_note(grade)
    prev = ""
    if prev_texts:
        prev = f"\n\n**Previous texts (do not repeat this content):**\n" + "\n".join(prev_texts[-2:])

    text_type = round_plan.get('conception', round_plan.get('comprehension', {})).get('text_type', 'narrative')
    text_desc = round_plan.get('conception', round_plan.get('comprehension', {})).get('description', '')
    disc_focus = round_plan.get('conception', round_plan.get('comprehension', {})).get('discussion_focus', 'conflict and values')

    return f"""Write a rich NARRATIVE text for the Conception station of a PACE English lesson.

**IMPORTANT: ALL output — every word, title, instruction, question, and label — must be in English.**

<user_input>
Subject: {subject} | Topic: {topic}
Grade: {grade} | Age: {egl['age']} | CEFR: {egl['cefr']} | Language level: {egl['language']}
Round {round_num} of {total_rounds} | Text type: {text_type} | Plan: {text_desc}
Discussion focus: {disc_focus}{curric}{prev}
</user_input>

**⚠️ PACE Iron Rule — Conception is ORAL ONLY:**
- This station has ZERO writing tasks. Students speak to a partner, never write.
- All "questions" in this station are oral discussion prompts — students say their answers aloud.
- Include NO fill-in blanks, NO written answer lines, NO multiple choice boxes.
- All output must assume students respond by SPEAKING to a partner.

**Text requirements:**
1. **Narrative text only** — story, adventure, fable, poem, prose. NOT informational.
2. **Length: {egl['text_length']}** — do not shorten; this is a read-aloud text
3. Include 8-12 **key vocabulary words** — bolded in the text
4. Divide into 4-6 paragraphs with subheadings
5. Each paragraph minimum 50 words
6. Explain new words in parentheses within the text
7. Stage: {'introduction — meet the characters/situation' if round_num == 1 else 'development — deepen the story/topic' if round_num < total_rounds else 'climax — conflict, resolution, conclusion'}
8. Language complexity must match CEFR {egl['cefr']}

**Age-appropriate comprehension activities:** {', '.join(egl['comprehension_options'])}

**Oral discussion questions (5 Ws + depth) — all answered by speaking to a partner:**
Include 4-5 graded oral prompts:
- Level 1: Who/What/When/Where (factual — say aloud)
- Level 2: Why/How (analysis — discuss with partner)
- Level 3: Opinion, dilemma, personal connection ("What would YOU do?")

**Output format — JSON only (ALL values in English):**
{{
  "section_title": "Round title in English",
  "intro_sentence": "Engaging opening sentence (rhetorical question / intriguing situation)",
  "paragraphs": [
    {{
      "subtitle": "Subheading in English",
      "text": "Paragraph text (minimum 50 words, CEFR {egl['cefr']} level, narrative only)",
      "key_terms": ["term1", "term2"]
    }}
  ],
  "all_key_terms": ["all key vocabulary words (8-12)"],
  "discussion_starters": [
    "Factual oral question (Who/What/When/Where) — say the answer aloud",
    "Analysis oral question (Why/How) — discuss with your partner",
    "Opinion/dilemma oral question — share your view",
    "Open-ended oral discussion prompt",
    "Summary oral reflection — tell your partner 3 things that happened"
  ],
  "discussion_notes": [
    {{"question": "the discussion question", "key_ideas": "key ideas and expected responses — for teacher only"}}
  ]
}}"""


def build_english_methods_prompt(subject: str, topic: str, grade: str,
                                  round_num: int, round_plan: Dict,
                                  comprehension_text: Dict) -> str:
    egl = get_english_grade_level(grade)
    curric = _curric_note(grade)
    art_plan = round_plan.get('articulateness', round_plan.get('methods', {}))
    writing_strategy = art_plan.get('writing_strategy', art_plan.get('writing_type', 'description'))
    methods_desc = art_plan.get('description', '')
    key_terms = comprehension_text.get('all_key_terms', [])

    text_summary = comprehension_text.get('section_title', '') + ": "
    for p in comprehension_text.get('paragraphs', [])[:2]:
        text_summary += p.get('text', '')[:200] + "... "

    return f"""Create a structured writing task for the Articulateness station of a PACE English lesson.

**IMPORTANT: ALL output — every word, title, instruction, question, and label — must be in English.**

<user_input>
Subject: {subject} | Topic: {topic} | Round {round_num}
Grade: {grade} | Age: {egl['age']} | CEFR: {egl['cefr']}
Writing strategy: {writing_strategy} | Plan: {methods_desc}
Key words from text: {', '.join(key_terms[:8])}
Text context: {text_summary[:300]}{curric}
</user_input>

**PACE Articulateness station rules:**
- Teacher is physically present at this station the entire time
- ONE writing strategy per unit (use the same strategy in every round): {writing_strategy}
- Writing is GUIDED, not independent — teacher models first, then students write
- Include a writing scaffold/template for every level

**Writing strategies and their requirements:**
- description: sensory details, vivid adjectives, clear structure
- narration: beginning/middle/end, characters, setting, problem/solution
- optimal_response: structured opinion with reason + evidence from text
- summarization: main ideas only, no copying, own words, logical order
- comparison: similarities and differences, organized structure
- argumentation: clear stance + 2-3 reasons + conclusion
- synthesis: combine information from multiple angles into a unified response

**Age-appropriate writing options for grade {grade} ({egl['cefr']}):** {', '.join(egl['methods_options'])}

**Rules:**
1. Task is guided and scaffolded — full support for all levels
2. Include: clear instruction + sentence-starters scaffold + guiding questions
3. Appropriate for age {egl['age']} and CEFR {egl['cefr']}
4. Include 3 difficulty levels (marked by color/symbol ONLY — no ability labels like "weak/strong/basic")

**Output format — JSON only (ALL values in English):**
{{
  "title": "Task title in English",
  "writing_strategy": "{writing_strategy}",
  "main_instruction": "Clear main instruction for the student",
  "context_prompt": "The question/topic to write about",
  "scaffold_template": "Writing template/scaffold (structure, sentence starters — teacher models this on the board)",
  "guiding_questions": [
    "Guiding question 1",
    "Guiding question 2",
    "Guiding question 3"
  ],
  "difficulty_levels": {{
    "green": "Level 1 — shorter task, full template with sentence starters provided",
    "yellow": "Level 2 — partial scaffold, student fills in key ideas",
    "red": "Level 3 — extension: more depth, longer response, creative elaboration"
  }},
  "words_range": "X-Y words",
  "lines_needed": 10,
  "success_criteria": ["criterion 1", "criterion 2", "criterion 3"],
  "model_answer": "A complete sample student response following the writing strategy structure, at appropriate CEFR level"
}}"""


def build_english_precision_prompt(subject: str, topic: str, grade: str,
                                    round_num: int, round_plan: Dict,
                                    key_terms: List[str]) -> str:
    egl = get_english_grade_level(grade)
    curric = _curric_note(grade)
    prec_plan = round_plan.get('precision', {})
    activity_type = prec_plan.get('activity_type', 'spelling and grammar')
    game_element = prec_plan.get('game_element', 'cards')
    precision_desc = prec_plan.get('description', '')

    return f"""Create a game-based language accuracy activity for the Precision station of a PACE English lesson.

**IMPORTANT: ALL output — every word, title, instruction, question, and label — must be in English.**

<user_input>
Subject: {subject} | Topic: {topic} | Round {round_num}
Grade: {grade} | Age: {egl['age']} | CEFR: {egl['cefr']}
Activity type: {activity_type} | Game element: {game_element} | Plan: {precision_desc}
Words from the text: {', '.join(key_terms[:12])}
Number of spelling words for this grade: {egl['dictation_words']}{curric}
</user_input>

**⚠️ PACE Iron Rule — Precision must be GAME-BASED:**
- Every activity MUST include a game, play, or competition element
- FORBIDDEN: plain fill-in-the-blank worksheets with no game element
- Required game formats: word wheel, sorting cards, memory match, dominoes, snakes-and-ladders, competition timer, cut-and-sort

**Language accuracy toolkit — choose a variety:**
- Spelling: words and sentences from the text
- Grammar: tenses (present/past/future), subject-verb agreement, articles
- Word forms: noun/verb/adjective/adverb transformations
- Punctuation: capital letters, full stops, commas, apostrophes
- Prepositions: in/on/at/by/with/for/to/from
- Singular/plural: regular and irregular forms
- Sentence ordering: unscramble sentences (cut-up strips game)
- Error correction: find and fix the mistake (competition — who finds it first?)
- Collocations: common word pairs from the topic
- Irregular verbs: sorting cards (base/past/past participle)

**Age-appropriate precision options for grade {grade} ({egl['cefr']}):** {', '.join(egl['precision_options'])}

**Rules:**
1. All words/sentences must come from the text read at the Conception station
2. Include {egl['dictation_words']} spelling words (pair dictation — one student dictates, one writes)
3. Include **2-3 different exercise types** — not only spelling
4. Every exercise must specify the GAME element explicitly
5. Variety: each round uses different exercise types from the previous round

**Output format — JSON only (ALL values in English):**
{{
  "title": "Activity title in English",
  "activity_type": "{activity_type}",
  "game_element": "{game_element}",
  "dictation_list": [
    {{"word": "word", "difficulty": "easy/medium/hard", "note": "note if needed"}}
  ],
  "exercises": [
    {{
      "type": "spelling/grammar/word-forms/punctuation/tenses/prepositions/ordering/error-correction",
      "title": "Exercise title",
      "game_instruction": "How the game element works (e.g. 'Race your partner — who finishes first?')",
      "instruction": "Instruction for the student",
      "items": [
        {{"question": "...", "answer": "..."}}
      ]
    }}
  ],
  "sentences_for_dictation": [
    "Sentence 1 from the text for pair dictation",
    "Sentence 2 from the text for pair dictation"
  ],
  "answer_key": "Full answer key"
}}"""


def build_english_vocabulary_prompt(subject: str, topic: str, grade: str,
                                     round_num: int, round_plan: Dict,
                                     key_terms: List[str], used_types: List[str]) -> str:
    egl = get_english_grade_level(grade)
    curric = _curric_note(grade)
    vocab_plan = round_plan.get('vocabulary', {})
    activity_type = vocab_plan.get('activity_type', 'physical_plasticine')
    is_physical = vocab_plan.get('physical_creation', vocab_plan.get('is_physical', True))
    vocab_desc = vocab_plan.get('description', '')

    physical_note = """
**⚠️ PACE Iron Rule — Enhancing Vocabulary requires PHYSICAL CREATION:**
Physical creation is mandatory — writing alone is NOT sufficient at this station.
Examples: sculpt a word in clay/plasticine, build a 3D model, create an illustrated dictionary, make a mobile, construct a poster with physical materials, act out vocabulary through movement.
The activity must involve the hands, body, or sensorimotor memory.
""" if is_physical else """
**Note:** If not physical, ensure the activity is highly visual and interactive (crossword, matching game, illustrated sort).
"""

    return f"""Create a vocabulary activity for the Enhancing Vocabulary station of a PACE English lesson.

**IMPORTANT: ALL output — every word, title, instruction, question, and label — must be in English.**

<user_input>
Subject: {subject} | Topic: {topic} | Round {round_num}
Grade: {grade} | Age: {egl['age']} | CEFR: {egl['cefr']}
Activity type: {activity_type} | Physical creation: {is_physical} | Plan: {vocab_desc}
Key words from text: {', '.join(key_terms[:12])}
Types already used: {', '.join(used_types) if used_types else 'none'}{curric}
</user_input>
{physical_note}

**PACE Vocabulary station principle:** "What is felt is remembered" — visual + auditory + tactile-kinesthetic memory

**Physical/tactile activity types (preferred):**
- physical_plasticine: sculpt a word/concept in clay — word list + step-by-step instructions
- physical_model: build a model/diagram — labels to print + construction steps
- physical_game: card game/memory/dominoes — board/cards to print and play
- physical_poster: build a vocabulary poster — layout guide + words to illustrate
- physical_clothesline: "washing line" — hang word cards in pairs (synonyms/antonyms)
- physical_simulation: role play/mime — roles + vocabulary to act out

**Printed activity types (when physical is not possible):**
- matching_cards: cut-and-match (word ↔ definition)
- sorting_table: sort words into categories (cut and paste)
- crossword_mini: mini crossword
- illustrated_dictionary: draw and label 6-8 new words with sentences
- definition_table: word | definition | example sentence | illustration box

**Rules:**
1. Always list the target vocabulary words with definitions
2. Include clear step-by-step instructions
3. Each round — different activity type (do not repeat: {', '.join(used_types) if used_types else 'none yet'})
4. Include a word bank if applicable

**Age-appropriate vocabulary options for grade {grade} ({egl['cefr']}):** {', '.join(egl['vocabulary_options'])}

**Output format — JSON only (ALL values in English):**
{{
  "title": "Activity title in English",
  "activity_type": "{activity_type}",
  "physical_creation": {str(is_physical).lower()},
  "instruction": "Clear step-by-step instruction for the student",
  "materials_needed": ["material 1", "material 2"],
  "words": [
    {{
      "word": "word/phrase",
      "definition": "short definition",
      "example": "example sentence",
      "category": "category (if relevant)",
      "partner": "synonym/antonym (if relevant)"
    }}
  ],
  "word_bank": ["word1", "word2"],
  "left_column": ["item1", "item2", "item3", "item4", "item5", "item6", "item7", "item8"],
  "right_column": ["pair1", "pair2", "pair3", "pair4", "pair5", "pair6", "pair7", "pair8"],
  "categories": ["category1", "category2", "category3"],
  "fill_sentences": [
    {{"sentence": "Sentence with a _____ gap", "answer": "the answer"}}
  ],
  "crossword_clues": [
    {{"direction": "across/down", "number": 1, "clue": "clue", "answer": "answer"}}
  ],
  "physical_steps": [
    "Step 1: ...",
    "Step 2: ...",
    "Step 3: ..."
  ],
  "answer_key": "Full answer key"
}}"""


def build_english_teacher_prep_prompt(subject: str, topic: str, grade: str,
                                       round_num: int, all_content: Dict) -> str:
    egl = get_english_grade_level(grade)
    curric = _curric_note(grade)
    comp = all_content.get('comprehension', {})
    meth = all_content.get('methods', {})
    prec = all_content.get('precision', {})
    vocab = all_content.get('vocabulary', {})
    is_physical_vocab = vocab.get('physical_creation', vocab.get('is_physical', False))

    return f"""Create a teacher preparation sheet for Round {round_num} of a PACE English lesson.

**IMPORTANT: ALL output — every word, title, instruction, question, and label — must be in English.**

<user_input>
Subject: {subject} | Topic: {topic} | Grade: {grade} | CEFR: {egl['cefr']} | Round {round_num}{curric}
</user_input>

**PACE round stations:**
- Conception: {comp.get('section_title', '')} ({len(comp.get('paragraphs', []))} paragraphs) — **ORAL ONLY, teacher NOT required here — students work in pairs independently**
- Articulateness: {meth.get('title', '')} — strategy: {meth.get('writing_strategy', meth.get('writing_type', ''))} — **teacher MUST be present at this station the entire time**
- Precision: {prec.get('title', '')} — {prec.get('activity_type', '')} — game element: {prec.get('game_element', '')}
- Enhancing Vocabulary: {vocab.get('title', '')} — {vocab.get('activity_type', '')} {'(physical activity — prepare materials in advance)' if is_physical_vocab else '(printed activity)'}

**Output format — JSON only (ALL values in English):**
{{
  "objectives": {{
    "knowledge": ["knowledge goal 1", "knowledge goal 2"],
    "skills": ["skill to be developed 1", "skill 2"],
    "values": ["value/habit 1"]
  }},
  "language_focus": ["main grammar/language focus 1", "language focus 2"],
  "materials": {{
    "conception": ["copies of the narrative text for each student", "..."],
    "articulateness": ["task sheet with scaffold", "writing checklist", "..."],
    "precision": ["game materials (cards/wheel/board)", "scissors if cutting required", "..."],
    "vocabulary": ["required materials — {', '.join(vocab.get('materials_needed', ['activity sheets']))}"]
  }},
  "timing": {{
    "conception": "15-20 minutes",
    "articulateness": "20-25 minutes",
    "precision": "15-20 minutes",
    "vocabulary": "15-20 minutes"
  }},
  "rotation_tip": "Instruction for rotating groups between stations",
  "teacher_notes": [
    "Conception station: fully oral — do not correct written work here, students speak to their partner",
    "Articulateness station: YOU must stay here — model the writing strategy on the board before students write",
    "Anticipated difficulty + suggested solution",
    "Extension for advanced students at any station"
  ],
  "differentiation": {{
    "struggling": "How to support struggling students at each station",
    "advanced": "Extension for strong students",
    "special_needs": "Adaptations for diverse learners"
  }},
  "self_check": [
    "Is every station fully independent (student can start anywhere)?",
    "Is the Conception station writing-free (oral only)?",
    "Does Precision have a game/play element?",
    "Does Enhancing Vocabulary include physical/tactile creation?",
    "Is differentiation built in at every station?"
  ]
}}"""
