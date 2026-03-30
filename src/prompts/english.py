from typing import Any, Dict, List
from ..config import get_english_grade_level


def build_english_roadmap_prompt(subject: str, topic: str, grade: str, rounds: int) -> str:
    egl = get_english_grade_level(grade)
    return f"""You are planning an English language learning unit using the Al-HaSadeh (station-rotation) method.

**Subject:** {subject} | **Topic:** {topic}
**Grade:** {grade} | **Age:** {egl['age']} | **CEFR Level:** {egl['cefr']}
**Number of rounds:** {rounds}

**IMPORTANT: ALL output — every word, title, instruction, question, and label — must be in English.**

**Station structure (same as Hebrew edition, but fully in English):**
1. **Comprehension Station** — rich reading text + oral discussion only (no writing)
2. **Methods Station** — structured, scaffolded writing task (teacher present)
3. **Precision Station** — spelling, grammar, vocabulary accuracy (technical language work)
4. **Vocabulary Station** — experiential activity (printed or hands-on)

**Iron rules:**
1. All 4 stations in every round are **fully independent** (student can start at any station)
2. Comprehension = reading text + oral discussion only, no writing required
3. Methods = structured writing — teacher is physically present here
4. Precision = technical language work (spelling, grammar, word forms — NOT comprehension questions)
5. Vocabulary = experiential and engaging — printed or hands-on
6. Progression across rounds: introduction → development → deepening → synthesis

**Writing types for Methods station:**
opinion paragraph, descriptive writing, narrative, summary, compare and contrast,
personal response, formal letter, dialogue writing, short poem, information report

**Activity types for Vocabulary station:**
Printed: matching_cards, sorting_table, dominoes, fill_in_poster, clothesline, idiom_cards, definition_table, crossword_mini
Physical/experiential: physical_plasticine, physical_model, physical_game, physical_poster, physical_simulation, physical_clothesline

**Age-appropriate options for grade {grade} ({egl['cefr']}):**
- Comprehension: {', '.join(egl['comprehension_options'])}
- Methods: {', '.join(egl['methods_options'])}
- Precision: {', '.join(egl['precision_options'])}
- Vocabulary: {', '.join(egl['vocabulary_options'])}

**Output format — JSON only (all values in English):**
{{
  "unit_title": "Unit title in English",
  "central_text_type": "text type",
  "language_focus": "main language/grammar focus of the unit",
  "learning_goals": {{
    "knowledge": ["knowledge goal 1", "knowledge goal 2"],
    "skills": ["skill 1", "skill 2"],
    "values": ["value/habit 1"]
  }},
  "rounds": [
    {{
      "round": 1,
      "comprehension": {{
        "text_type": "narrative/informational/dialogue/poem",
        "description": "brief description of the text",
        "discussion_focus": "main discussion question / conflict / theme"
      }},
      "methods": {{
        "writing_type": "writing type from the list",
        "description": "description of the task"
      }},
      "precision": {{
        "activity_type": "spelling/grammar/word-forms/punctuation/tenses/prepositions",
        "description": "description"
      }},
      "vocabulary": {{
        "activity_type": "activity type (printed or physical)",
        "is_physical": false,
        "description": "description"
      }}
    }}
  ]
}}"""


def build_english_comprehension_prompt(subject: str, topic: str, grade: str,
                                        round_num: int, total_rounds: int,
                                        round_plan: Dict, prev_texts: List[str]) -> str:
    egl = get_english_grade_level(grade)
    prev = ""
    if prev_texts:
        prev = f"\n\n**Previous texts (do not repeat this content):**\n" + "\n".join(prev_texts[-2:])

    text_type = round_plan.get('comprehension', {}).get('text_type', 'narrative')
    text_desc = round_plan.get('comprehension', {}).get('description', '')
    disc_focus = round_plan.get('comprehension', {}).get('discussion_focus', 'conflict and values')

    return f"""Write a rich {text_type} text for the Comprehension Station of an Al-HaSadeh English lesson.

**IMPORTANT: ALL output — every word, title, instruction, question, and label — must be in English.**

**Subject:** {subject} | **Topic:** {topic}
**Grade:** {grade} | **Age:** {egl['age']} | **CEFR:** {egl['cefr']} | **Language level:** {egl['language']}
**Round {round_num} of {total_rounds}** | **Plan:** {text_desc}
**Discussion focus:** {disc_focus}
{prev}

**Age-appropriate comprehension activities:** {', '.join(egl['comprehension_options'])}

**⚠️ Critical rules:**
1. **Length: {egl['text_length']}** — do not shorten! This is a read-aloud text, it must be rich and engaging
2. **Do NOT include written questions in the text body** — the station is oral discussion only
3. Include 8-12 **key vocabulary words** — highlighted/bolded in the text
4. Divide into 4-6 paragraphs with subheadings
5. Each paragraph at least 60 words
6. Explain any new word in parentheses within the text
7. Stage: {'introduction — meet the characters/situation' if round_num == 1 else 'development — deepen the story/topic' if round_num < total_rounds else 'climax — conflict, resolution, conclusion'}
8. Language complexity must match CEFR {egl['cefr']} — use {egl['language']}

**Oral discussion questions (5 Ws + depth):**
Include 4-5 graded questions:
- Level 1: Who/What/When/Where (factual)
- Level 2: Why/How (analysis)
- Level 3: Opinion, dilemma, personal connection ("What would you do if...")

**Output format — JSON only (ALL values in English):**
{{
  "section_title": "Round title in English",
  "intro_sentence": "Engaging opening sentence (rhetorical question / intriguing situation)",
  "paragraphs": [
    {{
      "subtitle": "Subheading in English",
      "text": "Paragraph text (minimum 60 words, CEFR {egl['cefr']} level)",
      "key_terms": ["term1", "term2"]
    }}
  ],
  "all_key_terms": ["all key vocabulary words (8-12)"],
  "discussion_starters": [
    "Factual question (Who/What/When/Where)",
    "Analysis question (Why/How)",
    "Opinion/dilemma/values question",
    "Open-ended extension question",
    "Summary and reflection question"
  ]
}}"""


def build_english_methods_prompt(subject: str, topic: str, grade: str,
                                  round_num: int, round_plan: Dict,
                                  comprehension_text: Dict) -> str:
    egl = get_english_grade_level(grade)
    writing_type = round_plan.get('methods', {}).get('writing_type', 'opinion paragraph')
    methods_desc = round_plan.get('methods', {}).get('description', '')
    key_terms = comprehension_text.get('all_key_terms', [])

    text_summary = comprehension_text.get('section_title', '') + ": "
    for p in comprehension_text.get('paragraphs', [])[:2]:
        text_summary += p.get('text', '')[:200] + "... "

    return f"""Create a structured writing task for the Methods Station of an Al-HaSadeh English lesson.

**IMPORTANT: ALL output — every word, title, instruction, question, and label — must be in English.**

**Subject:** {subject} | **Topic:** {topic} | **Round {round_num}**
**Grade:** {grade} | **Age:** {egl['age']} | **CEFR:** {egl['cefr']}
**Writing type:** {writing_type} | **Plan:** {methods_desc}
**Key words from text:** {', '.join(key_terms[:8])}
**Text context:** {text_summary[:300]}

**Writing types and their requirements:**
- Opinion paragraph: clear stance + 2-3 reasons + conclusion
- Descriptive writing: sensory details + vivid adjectives + structure
- Narrative: beginning/middle/end, characters, setting, problem/solution
- Summary: main ideas only, no copying, own words
- Compare and contrast: similarities and differences, organized structure
- Personal response: personal connection + evidence from text
- Formal letter: greeting, body paragraphs, closing
- Information report: topic sentence, facts, conclusion

**Age-appropriate writing options for grade {grade} ({egl['cefr']}):** {', '.join(egl['methods_options'])}

**Rules:**
1. Task is structured and scaffolded — support for struggling students
2. Include: clear instruction + example/template + guiding questions
3. Appropriate for age {egl['age']} and CEFR {egl['cefr']}
4. Include 3 difficulty levels (traffic light: green/yellow/red) for the same task

**Output format — JSON only (ALL values in English):**
{{
  "title": "Task title in English",
  "writing_type": "{writing_type}",
  "main_instruction": "Clear main instruction for the student",
  "context_prompt": "The question/topic to write about",
  "scaffold_template": "Writing template/scaffold (title, structure, suggested opening sentences)",
  "guiding_questions": [
    "Guiding question 1",
    "Guiding question 2",
    "Guiding question 3"
  ],
  "difficulty_levels": {{
    "green": "Basic task (for struggling students) — short, full template provided",
    "yellow": "Regular task — partial independence",
    "red": "Extension for advanced students — creativity, depth, longer response"
  }},
  "words_range": "X-Y words",
  "lines_needed": 10,
  "success_criteria": ["criterion 1", "criterion 2", "criterion 3"]
}}"""


def build_english_precision_prompt(subject: str, topic: str, grade: str,
                                    round_num: int, round_plan: Dict,
                                    key_terms: List[str]) -> str:
    egl = get_english_grade_level(grade)
    activity_type = round_plan.get('precision', {}).get('activity_type', 'spelling and grammar')
    precision_desc = round_plan.get('precision', {}).get('description', '')

    return f"""Create a language accuracy activity for the Precision Station of an Al-HaSadeh English lesson.

**IMPORTANT: ALL output — every word, title, instruction, question, and label — must be in English.**

**Subject:** {subject} | **Topic:** {topic} | **Round {round_num}**
**Grade:** {grade} | **Age:** {egl['age']} | **CEFR:** {egl['cefr']}
**Activity type:** {activity_type} | **Plan:** {precision_desc}
**Words from the text:** {', '.join(key_terms[:12])}
**Number of spelling words for this grade:** {egl['dictation_words']}

**Full language toolkit — choose a variety:**
- Spelling: words and sentences from the text
- Grammar: tenses (present/past/future), subject-verb agreement, articles
- Word forms: noun/verb/adjective/adverb transformations
- Punctuation: capital letters, full stops, commas, apostrophes
- Prepositions: in/on/at/by/with/for/to/from
- Singular/plural: regular and irregular forms
- Sentence types: statement/question/command/exclamation
- Sentence ordering: unscramble sentences
- Error correction: find and fix the mistake
- Collocations: common word pairs from the topic

**Age-appropriate precision options for grade {grade} ({egl['cefr']}):** {', '.join(egl['precision_options'])}

**Rules:**
1. All words/sentences must come from the text read at the Comprehension Station
2. Include {egl['dictation_words']} spelling words
3. Include **2-3 different exercise types** — not only spelling
4. All technical language work (NOT comprehension questions)
5. Variety: each round uses different exercise types from the previous round

**Output format — JSON only (ALL values in English):**
{{
  "title": "Activity title in English",
  "activity_type": "{activity_type}",
  "dictation_list": [
    {{"word": "word", "difficulty": "easy/medium/hard", "note": "note if needed"}}
  ],
  "exercises": [
    {{
      "type": "spelling/grammar/word-forms/punctuation/tenses/prepositions/ordering/error-correction",
      "title": "Exercise title",
      "instruction": "Instruction for the student",
      "items": [
        {{"question": "...", "answer": "..."}}
      ]
    }}
  ],
  "sentences_for_dictation": [
    "Sentence 1 from the text for dictation",
    "Sentence 2 from the text for dictation"
  ],
  "answer_key": "Full answer key"
}}"""


def build_english_vocabulary_prompt(subject: str, topic: str, grade: str,
                                     round_num: int, round_plan: Dict,
                                     key_terms: List[str], used_types: List[str]) -> str:
    egl = get_english_grade_level(grade)
    activity_type = round_plan.get('vocabulary', {}).get('activity_type', 'matching_cards')
    is_physical = round_plan.get('vocabulary', {}).get('is_physical', False)
    vocab_desc = round_plan.get('vocabulary', {}).get('description', '')

    physical_note = """
**⚠️ Physical/experiential activity — guidelines:**
This station is hands-on. The product is:
1. Student instruction sheet (what to do, step by step)
2. Materials list (what needs to be prepared)
3. Word cards for printing and cutting (if needed)
The activity must involve body, hands, movement — "what is felt is remembered"
""" if is_physical else ""

    return f"""Create a vocabulary activity for the Vocabulary Station of an Al-HaSadeh English lesson.

**IMPORTANT: ALL output — every word, title, instruction, question, and label — must be in English.**

**Subject:** {subject} | **Topic:** {topic} | **Round {round_num}**
**Grade:** {grade} | **Age:** {egl['age']} | **CEFR:** {egl['cefr']}
**Activity type:** {activity_type} | **Plan:** {vocab_desc}
**Key words from text:** {', '.join(key_terms[:12])}
**Types already used:** {', '.join(used_types) if used_types else 'none'}
{physical_note}

**Station principle:** "What is felt is remembered" — visual + auditory + kinaesthetic memory

**Printed activity types:**
- matching_cards: cut-and-match cards (word ↔ definition)
- sorting_table: sorting table into categories (cut ↔ paste)
- dominoes: word dominoes for cutting
- fill_in_poster: poster with gaps to fill
- clothesline: connect pairs with a line (synonyms/antonyms)
- idiom_cards: idiom cards + meaning
- definition_table: word | definition | example sentence
- crossword_mini: mini crossword

**Physical/experiential activity types:**
- physical_plasticine: sculpt a word/concept in clay — includes instructions + word list
- physical_model: build a model/diagram — includes instructions + labels to print
- physical_game: card game/memory/dominoes/snakes and ladders — includes board/cards to print
- physical_poster: build a poster/display — includes guiding questions + layout
- physical_simulation: role play/simulation — includes roles + facilitation instructions
- physical_clothesline: "washing line" — hang word cards + pairs (synonyms/antonyms)

**Rules:**
1. Activity is experiential and varied — not just "write a sentence"
2. Words/phrases: from the text + new topic vocabulary
3. Include clear instructions + word bank if relevant
4. Each round — different type (do not repeat what was done)

**Age-appropriate vocabulary options for grade {grade} ({egl['cefr']}):** {', '.join(egl['vocabulary_options'])}

**Output format — JSON only (ALL values in English):**
{{
  "title": "Activity title in English",
  "activity_type": "activity type",
  "is_physical": {str(is_physical).lower()},
  "instruction": "Clear instruction for the student (step by step for physical)",
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
    comp = all_content.get('comprehension', {})
    meth = all_content.get('methods', {})
    prec = all_content.get('precision', {})
    vocab = all_content.get('vocabulary', {})
    is_physical_vocab = vocab.get('is_physical', False)

    return f"""Create a teacher preparation sheet for Round {round_num} of an Al-HaSadeh English lesson.

**IMPORTANT: ALL output — every word, title, instruction, question, and label — must be in English.**

**Subject:** {subject} | **Topic:** {topic} | **Grade:** {grade} | **CEFR:** {egl['cefr']} | **Round {round_num}**

**Round stations:**
- Comprehension: {comp.get('section_title', '')} ({len(comp.get('paragraphs', []))} paragraphs) — **oral station only, teacher NOT required here**
- Methods: {meth.get('title', '')} — {meth.get('writing_type', '')} — **teacher sits here**
- Precision: {prec.get('title', '')} — {prec.get('activity_type', '')}
- Vocabulary: {vocab.get('title', '')} — {vocab.get('activity_type', '')} {'(physical activity — materials preparation required)' if is_physical_vocab else '(printed)'}

**Output format — JSON only (ALL values in English):**
{{
  "objectives": {{
    "knowledge": ["knowledge to be gained 1", "knowledge to be gained 2"],
    "skills": ["skill to be developed 1", "skill 2"],
    "values": ["value/habit 1"]
  }},
  "language_focus": ["main grammar/language focus 1", "language focus 2"],
  "materials": {{
    "comprehension": ["copies of the text for each student", "..."],
    "methods": ["task sheet", "..."],
    "precision": ["exercise sheet", "..."],
    "vocabulary": ["required materials — especially for physical: {', '.join(vocab.get('materials_needed', ['activity sheets']))}"]
  }},
  "timing": {{
    "comprehension": "15-20 minutes",
    "methods": "20-25 minutes",
    "precision": "15-20 minutes",
    "vocabulary": "15-20 minutes"
  }},
  "rotation_tip": "Instruction for rotating groups between stations",
  "teacher_notes": [
    "Key point for comprehension station (oral only!)",
    "Key point for methods station (teacher here)",
    "Anticipated difficulty + suggested solution",
    "Suggestion for extension for advanced students"
  ],
  "differentiation": {{
    "struggling": "How to support struggling students at each station",
    "advanced": "Extension for strong students",
    "special_needs": "Adaptations for special education"
  }},
  "self_check": [
    "Is every station fully independent?",
    "Is the comprehension station writing-free?",
    "Is the vocabulary station hands-on/experiential?",
    "Is differentiation built in?"
  ]
}}"""
