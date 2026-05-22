import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List

import structlog

from .gemini import call_gemini
from .exceptions import LLMAPIError, PDFRenderError, CostLimitExceededError
from .config import (
    is_stem, is_english, SAFE_NAME_MAX_LENGTH, DEFAULT_ROUNDS,
    GEMINI_FLASH_INPUT_COST_PER_1M, GEMINI_FLASH_OUTPUT_COST_PER_1M,
    GEMINI_MAX_COST_PER_GENERATION_USD,
)
from .images import ImageService

_PROVIDER_LABEL = "Gemini"
log = structlog.get_logger(__name__)
from .prompts import (
    build_roadmap_prompt,
    build_comprehension_prompt,
    build_methods_prompt,
    build_precision_prompt,
    build_vocabulary_prompt,
    build_teacher_prep_prompt,
    # STEAM edition
    build_stem_roadmap_prompt,
    build_stem_comprehension_prompt,
    build_stem_methods_prompt,
    build_stem_precision_prompt,
    build_stem_vocabulary_prompt,
    # English edition
    build_english_roadmap_prompt,
    build_english_comprehension_prompt,
    build_english_methods_prompt,
    build_english_precision_prompt,
    build_english_vocabulary_prompt,
    build_english_teacher_prep_prompt,
)
from .renderers import (
    render_roadmap,
    render_comprehension,
    render_methods,
    render_precision,
    render_vocabulary,
    render_teacher_prep,
    render_answer_key,
)
from .pdf import save_html, make_pdf_isolated as make_pdf


def generate_roadmap(user_input: Dict[str, Any], output_dir: str = "output") -> Dict[str, Any]:
    subject = user_input['subject']
    topic = user_input['topic']
    grade = user_input['grade']
    rounds = user_input.get('rounds', DEFAULT_ROUNDS)

    log.info("roadmap_start", topic=topic, subject=subject, grade=grade, rounds=rounds)

    provider = _PROVIDER_LABEL
    steam_mode = is_stem(subject)
    english_mode = is_english(subject)
    if steam_mode:
        mode_label = "STEAM"
    elif english_mode:
        mode_label = "English"
    else:
        mode_label = "Language"
    log.info("roadmap_calling_llm", provider=provider, mode=mode_label)
    if steam_mode:
        roadmap_prompt_fn = build_stem_roadmap_prompt
    elif english_mode:
        roadmap_prompt_fn = build_english_roadmap_prompt
    else:
        roadmap_prompt_fn = build_roadmap_prompt
    try:
        roadmap, roadmap_usage = call_gemini(roadmap_prompt_fn(subject, topic, grade, rounds))
        log.info("roadmap_llm_done", input_tokens=roadmap_usage["input_tokens"], output_tokens=roadmap_usage["output_tokens"])
    except Exception as exc:
        log.error("roadmap_llm_failed", topic=topic, error=str(exc))
        raise LLMAPIError(
            message=f"Failed to generate roadmap for '{topic}'",
            detail=str(exc),
        ) from exc

    try:
        os.makedirs(output_dir, exist_ok=True)
    except OSError as exc:
        log.error("output_dir_create_failed", output_dir=output_dir, error=str(exc))
        raise PDFRenderError(
            message=f"Cannot create output directory: {output_dir}",
            detail=str(exc),
        ) from exc

    safe_name = topic.replace(" ", "_").replace("/", "_")[:SAFE_NAME_MAX_LENGTH]
    roadmap_html = render_roadmap(topic, roadmap, english_mode=english_mode)
    roadmap_path = f"{output_dir}/{safe_name}_roadmap.html"
    try:
        save_html(roadmap_html, roadmap_path)
    except Exception as exc:
        log.error("roadmap_save_failed", path=roadmap_path, error=str(exc))
        raise PDFRenderError(
            message=f"Failed to save roadmap HTML: {roadmap_path}",
            detail=str(exc),
        ) from exc

    log.info("roadmap_complete", rounds_planned=len(roadmap.get('rounds', [])))

    roadmap['_meta'] = {
        'subject': subject,
        'topic': topic,
        'grade': grade,
        'safe_name': safe_name,
        'output_dir': output_dir,
        'usage': roadmap_usage,
    }
    return roadmap


def generate_round(user_input: Dict[str, Any], roadmap: Dict[str, Any], round_num: int,
                   output_dir: str = "output",
                   prev_texts: List[str] | None = None) -> Dict[str, Any]:
    if prev_texts is None:
        prev_texts = []

    subject = user_input['subject']
    topic = user_input['topic']
    grade = user_input['grade']
    total_r = user_input.get('rounds', DEFAULT_ROUNDS)
    safe_name = roadmap.get('_meta', {}).get('safe_name', topic.replace(" ", "_")[:SAFE_NAME_MAX_LENGTH])

    rounds_list = roadmap.get('rounds', [])
    if round_num > len(rounds_list):
        log.warning("round_not_in_roadmap", round_num=round_num, available=len(rounds_list))
        return {}

    round_plan = rounds_list[round_num - 1]

    steam_mode = is_stem(subject)
    english_mode = is_english(subject)
    if steam_mode:
        mode_label = "STEAM"
    elif english_mode:
        mode_label = "English"
    else:
        mode_label = "Language"

    log.info("round_start", round=round_num, total=total_r, topic=topic, mode=mode_label)

    try:
        os.makedirs(output_dir, exist_ok=True)
    except OSError as exc:
        log.error("output_dir_create_failed", output_dir=output_dir, error=str(exc))
        raise PDFRenderError(
            message=f"Cannot create output directory: {output_dir}",
            detail=str(exc),
        ) from exc

    files = {}
    content = {}
    round_usage: Dict[str, int] = {"input_tokens": 0, "output_tokens": 0, "cached_tokens": 0}

    # Pre-fetch topic images (Pexels first, Imagen fallback); instant if cached
    if not english_mode:
        _img = ImageService()
        topic_images = {
            "comprehension": _img.fetch(topic, grade, "comprehension", round_num),
            "methods":       _img.fetch(topic, grade, "methods", round_num),
            "precision":     _img.fetch(topic, grade, "precision", round_num),
        }
        decorative_images = {
            "precision":   _img.fetch_decorative(topic, "precision", round_num),
            "vocabulary":  _img.fetch_decorative(topic, "vocabulary", round_num),
        }
        log.info("images_fetched", cached=[k for k, v in topic_images.items() if v],
                 decorative=[k for k, v in decorative_images.items() if v])
    else:
        topic_images = {"comprehension": None, "methods": None, "precision": None}
        decorative_images = {"precision": None, "vocabulary": None}

    # Accumulated cost so far across this generation (passed in from caller)
    accumulated_cost_usd: float = user_input.get('_accumulated_cost_usd', 0.0)

    def _call_llm(prompt, station_name: str) -> Dict[str, Any]:
        """Wrap call_gemini: accumulate usage, enforce cost cap, raise on LLM errors."""
        nonlocal accumulated_cost_usd
        log.info("llm_call_start", station=station_name, round=round_num, topic=topic, prompt_chars=len(prompt))
        try:
            result, usage = call_gemini(prompt)
        except Exception as exc:
            log.error("llm_call_failed", station=station_name, round=round_num, topic=topic, error=str(exc))
            raise LLMAPIError(
                message=f"LLM call failed at station '{station_name}' (round {round_num})",
                detail=str(exc),
            ) from exc

        round_usage["input_tokens"] += usage["input_tokens"]
        round_usage["output_tokens"] += usage["output_tokens"]
        round_usage["cached_tokens"] += usage["cached_tokens"]

        call_cost = (
            usage["input_tokens"] * GEMINI_FLASH_INPUT_COST_PER_1M / 1_000_000
            + usage["output_tokens"] * GEMINI_FLASH_OUTPUT_COST_PER_1M / 1_000_000
        )
        accumulated_cost_usd += call_cost

        if accumulated_cost_usd > GEMINI_MAX_COST_PER_GENERATION_USD:
            log.error(
                "cost_limit_exceeded",
                accumulated_cost_usd=round(accumulated_cost_usd, 4),
                limit=GEMINI_MAX_COST_PER_GENERATION_USD,
                station=station_name,
                round=round_num,
            )
            raise CostLimitExceededError(
                message=f"Generation cost ${accumulated_cost_usd:.4f} exceeded limit ${GEMINI_MAX_COST_PER_GENERATION_USD}",
                detail=f"Stopped at station '{station_name}', round {round_num}",
            )

        log.debug(
            "llm_call_cost",
            station=station_name,
            round=round_num,
            call_cost_usd=round(call_cost, 5),
            accumulated_usd=round(accumulated_cost_usd, 4),
        )
        return result

    def _save(html: str, path: str, station_name: str):
        """Wrap save_html with PDFRenderError context."""
        try:
            save_html(html, path)
        except Exception as exc:
            log.error("html_save_failed", station=station_name, path=path, error=str(exc))
            raise PDFRenderError(
                message=f"Failed to save HTML for '{station_name}': {path}",
                detail=str(exc),
            ) from exc

    def _render(station_name: str, fn, *args, **kwargs) -> str:
        """Call a renderer function and convert any exception to PDFRenderError."""
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            log.error("renderer_failed", station=station_name, round=round_num,
                      error_type=type(exc).__name__, error=str(exc))
            raise PDFRenderError(
                message=f"Renderer failed: {station_name} (round {round_num}): {type(exc).__name__}: {exc}",
                detail=str(exc),
            ) from exc

    # Station 1: Comprehension
    log.info("station_start", station="comprehension", step="1/4", round=round_num)
    if steam_mode:
        comp_prompt_fn = build_stem_comprehension_prompt
    elif english_mode:
        comp_prompt_fn = build_english_comprehension_prompt
    else:
        comp_prompt_fn = build_comprehension_prompt
    comp_data = _call_llm(comp_prompt_fn(
        subject, topic, grade, round_num, total_r, round_plan, prev_texts
    ), "comprehension")
    word_count = sum(len(p.get('text', '').split()) for p in comp_data.get('paragraphs', []))
    log.info("station_complete", station="comprehension", words=word_count, paragraphs=len(comp_data.get('paragraphs', [])))
    prev_texts.append(comp_data.get('section_title', '') + ": " + comp_data.get('intro_sentence', ''))
    content['comprehension'] = comp_data
    comp_html = _render("comprehension", render_comprehension, topic, round_num, comp_data, grade,
                        english_mode=english_mode, topic_image=topic_images["comprehension"])
    comp_path = f"{output_dir}/{safe_name}_round{round_num}_comprehension.html"
    _save(comp_html, comp_path, "comprehension")
    files['comprehension'] = comp_path

    # Station 2: Methods
    if steam_mode:
        meth_label = 'procedural thinking'
    elif english_mode:
        meth_label = 'English writing'
    else:
        meth_label = 'writing'
    log.info("station_start", station="methods", step="2/4", round=round_num, label=meth_label)
    if steam_mode:
        meth_prompt_fn = build_stem_methods_prompt
    elif english_mode:
        meth_prompt_fn = build_english_methods_prompt
    else:
        meth_prompt_fn = build_methods_prompt
    meth_data = _call_llm(meth_prompt_fn(
        subject, topic, grade, round_num, round_plan, comp_data
    ), "methods")
    log.info("station_complete", station="methods", writing_type=meth_data.get('writing_type', ''), levels=list(meth_data.get('difficulty_levels', {}).keys()))
    content['methods'] = meth_data
    meth_html = _render("methods", render_methods, topic, round_num, meth_data,
                        english_mode=english_mode, topic_image=topic_images["methods"])
    meth_path = f"{output_dir}/{safe_name}_round{round_num}_methods.html"
    _save(meth_html, meth_path, "methods")
    files['methods'] = meth_path

    # Station 3: Precision (language grammar / STEM hands-on / English accuracy)
    if steam_mode:
        prec_label = 'hands-on lab'
    elif english_mode:
        prec_label = 'English language accuracy tasks'
    else:
        prec_label = 'precision tasks (language)'
    log.info("station_start", station="precision", step="3/4", round=round_num, label=prec_label)
    key_terms = comp_data.get('all_key_terms', [])
    if steam_mode:
        prec_prompt_fn = build_stem_precision_prompt
    elif english_mode:
        prec_prompt_fn = build_english_precision_prompt
    else:
        prec_prompt_fn = build_precision_prompt
    prec_data = _call_llm(prec_prompt_fn(
        subject, topic, grade, round_num, round_plan, key_terms
    ), "precision")
    log.info("station_complete", station="precision", dictation_words=len(prec_data.get('dictation_list', [])), exercises=len(prec_data.get('exercises', [])))
    content['precision'] = prec_data
    prec_html = _render("precision", render_precision, topic, round_num, prec_data,
                        english_mode=english_mode, topic_image=topic_images["precision"],
                        decorative_image=decorative_images.get("precision"))
    prec_path = f"{output_dir}/{safe_name}_round{round_num}_precision.html"
    _save(prec_html, prec_path, "precision")
    files['precision'] = prec_path

    # Station 4: Vocabulary (language / STEAM bilingual games / English vocabulary)
    if steam_mode:
        vocab_label = 'game (STEAM bilingual)'
    elif english_mode:
        vocab_label = 'English vocabulary activity'
    else:
        vocab_label = 'activity'
    log.info("station_start", station="vocabulary", step="4/4", round=round_num, label=vocab_label)
    vocab_key = 'game_type' if steam_mode else 'activity_type'
    used_vocab_types = [r.get('vocabulary', {}).get(vocab_key, '') for r in rounds_list[:round_num - 1]]
    if steam_mode:
        vocab_prompt_fn = build_stem_vocabulary_prompt
    elif english_mode:
        vocab_prompt_fn = build_english_vocabulary_prompt
    else:
        vocab_prompt_fn = build_vocabulary_prompt
    vocab_data = _call_llm(vocab_prompt_fn(
        subject, topic, grade, round_num, round_plan, key_terms, used_vocab_types
    ), "vocabulary")
    log.info("station_complete", station="vocabulary", activity_type=vocab_data.get('activity_type', ''), title=vocab_data.get('title', ''))
    content['vocabulary'] = vocab_data
    vocab_html = _render("vocabulary", render_vocabulary, topic, round_num, vocab_data,
                         english_mode=english_mode,
                         decorative_image=decorative_images.get("vocabulary"))
    vocab_path = f"{output_dir}/{safe_name}_round{round_num}_vocabulary.html"
    _save(vocab_html, vocab_path, "vocabulary")
    files['vocabulary'] = vocab_path

    # Teacher Prep
    log.info("station_start", station="teacher_prep", round=round_num)
    teacher_prep_fn = build_english_teacher_prep_prompt if english_mode else build_teacher_prep_prompt
    teacher_data = _call_llm(teacher_prep_fn(subject, topic, grade, round_num, content), "teacher_prep")
    content['teacher'] = teacher_data
    teacher_html = _render("teacher_prep", render_teacher_prep, topic, round_num, teacher_data,
                           content, english_mode=english_mode)
    teacher_path = f"{output_dir}/{safe_name}_round{round_num}_teacher_prep.html"
    _save(teacher_html, teacher_path, "teacher_prep")
    files['teacher_prep'] = teacher_path

    # Answer Key
    log.info("station_start", station="answer_key", round=round_num)
    answers_html = _render("answer_key", render_answer_key, topic, round_num, prec_data,
                           vocab_data, meth_data, english_mode=english_mode)
    answers_path = f"{output_dir}/{safe_name}_round{round_num}_answer_key.html"
    _save(answers_html, answers_path, "answer_key")
    files['answer_key'] = answers_path

    # PDFs
    log.info("pdf_creation_start", round=round_num)
    student_files = [files['comprehension'], files['methods'], files['precision'], files['vocabulary']]
    student_pdf = f"{output_dir}/{safe_name}_round{round_num}_STUDENT.pdf"
    if not make_pdf(student_files, student_pdf, topic, f"סבב {round_num} — לתלמיד", subject=subject, grade=grade):
        log.warning("student_pdf_failed", round=round_num, path=student_pdf)
    files['student_pdf'] = student_pdf

    teacher_files = [files['teacher_prep']] + student_files + [files['answer_key']]
    teacher_pdf = f"{output_dir}/{safe_name}_round{round_num}_TEACHER.pdf"
    if not make_pdf(teacher_files, teacher_pdf, topic, f"סבב {round_num} — למורה", subject=subject, grade=grade):
        log.warning("teacher_pdf_failed", round=round_num, path=teacher_pdf)
    files['teacher_pdf'] = teacher_pdf

    log.info(
        "round_complete",
        round=round_num,
        output_dir=output_dir,
        input_tokens=round_usage["input_tokens"],
        output_tokens=round_usage["output_tokens"],
        accumulated_cost_usd=round(accumulated_cost_usd, 4),
    )

    return {
        'files': files,
        'content': content,
        'prev_texts': prev_texts,
        'usage': round_usage,
        '_accumulated_cost_usd': accumulated_cost_usd,
    }


def generate_all_rounds(user_input: Dict[str, Any], roadmap: Dict[str, Any], output_dir: str = "output") -> Dict[str, Any]:
    total = user_input.get('rounds', DEFAULT_ROUNDS)
    all_results = []
    all_student_files = []
    all_teacher_files = []
    total_usage: Dict[str, int] = {"input_tokens": 0, "output_tokens": 0, "cached_tokens": 0}

    # Carry roadmap usage forward
    roadmap_usage = roadmap.get('_meta', {}).get('usage', {})
    for k in total_usage:
        total_usage[k] += roadmap_usage.get(k, 0)

    failed_rounds: List[int] = []
    results_by_round: Dict[int, Any] = {}
    cancel_event = threading.Event()

    def _run_round(round_num: int) -> Any:
        if cancel_event.is_set():
            return None
        inp = dict(user_input)
        inp['_accumulated_cost_usd'] = 0.0  # each round tracks its own cost vs per-round limit
        return generate_round(inp, roadmap, round_num, output_dir, prev_texts=[])

    workers = min(total, 4)
    log.info("parallel_rounds_start", total=total, workers=workers)
    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_map = {executor.submit(_run_round, i): i for i in range(1, total + 1)}
        for future in as_completed(future_map):
            rn = future_map[future]
            try:
                result = future.result()
                if result is None:
                    continue  # cancelled
                results_by_round[rn] = result
            except CostLimitExceededError as exc:
                cancel_event.set()
                log.error("round_failed", round=rn, total=total, error=str(exc),
                          error_type=type(exc).__name__, exc_info=True)
                failed_rounds.append(rn)
                all_results.append({"error": str(exc), "round": rn})
            except Exception as exc:
                log.error("round_failed", round=rn, total=total, error=str(exc),
                          error_type=type(exc).__name__, exc_info=True)
                failed_rounds.append(rn)
                all_results.append({"error": str(exc), "round": rn})

    # Collect results in round order for consistent PDF page ordering
    for i in range(1, total + 1):
        if i not in results_by_round:
            continue
        result = results_by_round[i]
        all_results.append(result)
        round_usage = result.get('usage', {})
        for k in total_usage:
            total_usage[k] += round_usage.get(k, 0)
        files = result.get('files', {})
        all_student_files.extend([
            files.get('comprehension', ''), files.get('methods', ''),
            files.get('precision', ''), files.get('vocabulary', '')
        ])
        all_teacher_files.extend([
            files.get('teacher_prep', ''), files.get('comprehension', ''),
            files.get('methods', ''), files.get('precision', ''),
            files.get('vocabulary', ''), files.get('answer_key', '')
        ])

    if failed_rounds and len(failed_rounds) == total:
        raise LLMAPIError(
            message=f"All {total} rounds failed",
            detail=f"Failed rounds: {failed_rounds}",
        )

    safe_name = roadmap.get('_meta', {}).get('safe_name', 'unit')
    topic = user_input['topic']

    log.info("full_unit_pdf_start", total_rounds=total)
    unit_student_pdf = f"{output_dir}/{safe_name}_FULL_STUDENT.pdf"
    subject = user_input.get('subject', '')
    grade = user_input.get('grade', '')
    if not make_pdf([f for f in all_student_files if f], unit_student_pdf, topic, f"יחידה מלאה — {total} סבבים — לתלמיד", subject=subject, grade=grade):
        log.warning("full_student_pdf_failed", path=unit_student_pdf)

    unit_teacher_pdf = f"{output_dir}/{safe_name}_FULL_TEACHER.pdf"
    if not make_pdf([f for f in all_teacher_files if f], unit_teacher_pdf, topic, f"יחידה מלאה — {total} סבבים — למורה", subject=subject, grade=grade):
        log.warning("full_teacher_pdf_failed", path=unit_teacher_pdf)

    total_cost_usd = (
        total_usage["input_tokens"] * GEMINI_FLASH_INPUT_COST_PER_1M / 1_000_000
        + total_usage["output_tokens"] * GEMINI_FLASH_OUTPUT_COST_PER_1M / 1_000_000
    )
    log.info(
        "all_rounds_complete",
        total=total,
        output_dir=output_dir,
        total_input_tokens=total_usage["input_tokens"],
        total_output_tokens=total_usage["output_tokens"],
        total_cost_usd=round(total_cost_usd, 4),
    )

    return {
        'rounds': all_results,
        'student_pdf': unit_student_pdf,
        'teacher_pdf': unit_teacher_pdf,
        'usage': total_usage,
        'cost_usd': round(total_cost_usd, 6),
    }
