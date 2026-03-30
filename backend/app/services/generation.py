"""
Generation service – wraps the core src/pipeline so the FastAPI layer
never needs to know about its internal structure.

The src/ package lives at the project root (one level above backend/).
We resolve that path once at module load and insert it into sys.path only
if it isn't there already, so repeated imports stay idempotent.
"""
import json
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

# ── resolve project root (backend/app/services → backend/app → backend → root)
_PROJECT_ROOT = Path(__file__).parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.pipeline import generate_all_rounds, generate_roadmap  # noqa: E402

from app.core.config import settings as _settings  # noqa: E402
from app.core.logging import get_logger  # noqa: E402

log = get_logger("app.services.generation")


class GenerationService:
    def __init__(self, output_base_dir: Path | None = None):
        self.output_base_dir = output_base_dir or Path("./generated_materials")
        self.output_base_dir.mkdir(exist_ok=True)

    # ── input helpers ─────────────────────────────────────────────────────────

    def _normalize_input(self, user_input: Dict[str, Any]) -> Dict[str, Any]:
        """Validate required fields and strip whitespace."""
        normalized = user_input.copy()
        for field in ("subject", "topic", "grade", "rounds"):
            if field not in normalized:
                raise ValueError(f"Missing required field: {field}")
        normalized["subject"] = normalized["subject"].strip()
        normalized["topic"] = normalized["topic"].strip()
        normalized["grade"] = normalized["grade"].strip()
        normalized["rounds"] = int(normalized["rounds"])
        return normalized

    def _get_output_directory(self, user_input: Dict[str, Any]) -> Path:
        """Return a unique timestamped directory for this generation."""
        subject = user_input["subject"].replace(" ", "_").replace("/", "_")
        topic = user_input["topic"].replace(" ", "_").replace("/", "_")
        grade = user_input["grade"]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = self.output_base_dir / f"{subject}_{topic}_{grade}_{timestamp}"
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

    # ── public API ────────────────────────────────────────────────────────────

    def generate_materials(self, user_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run the full generation pipeline and return a result dict.

        Returns a dict with ``status`` == "completed" or "failed".
        Persistence (DB, cache) is handled by the caller.
        """
        normalized = self._normalize_input(user_input)
        generation_id = str(uuid.uuid4())
        output_dir = self._get_output_directory(normalized)

        try:
            log.info("pipeline_start", generation_id=generation_id, subject=normalized["subject"], topic=normalized["topic"], grade=normalized["grade"], rounds=normalized["rounds"], output_dir=str(output_dir))
            roadmap = generate_roadmap(normalized, str(output_dir))
            log.info("pipeline_roadmap_done", generation_id=generation_id)
            results = generate_all_rounds(normalized, roadmap, str(output_dir))
            log.info("pipeline_all_rounds_done", generation_id=generation_id)

            response: Dict[str, Any] = {
                "generation_id": generation_id,
                "status": "completed",
                "input": normalized,
                "output_dir": str(output_dir),
                "roadmap": roadmap,
                "results": results,
                "generated_at": datetime.utcnow().isoformat() + "Z",
            }

            if results:
                response["files"] = {
                    "student_pdf": results.get("student_pdf"),
                    "teacher_pdf": results.get("teacher_pdf"),
                    "rounds": [
                        {
                            "round": i,
                            "comprehension": r.get("files", {}).get("comprehension"),
                            "methods": r.get("files", {}).get("methods"),
                            "precision": r.get("files", {}).get("precision"),
                            "vocabulary": r.get("files", {}).get("vocabulary"),
                            "student_pdf": r.get("files", {}).get("student_pdf"),
                            "teacher_pdf": r.get("files", {}).get("teacher_pdf"),
                            "answer_key": r.get("files", {}).get("answer_key"),
                            "teacher_prep": r.get("files", {}).get("teacher_prep"),
                        }
                        for i, r in enumerate(results.get("rounds", []), 1)
                    ],
                }

            return response

        except Exception as exc:
            log.error("pipeline_failed", generation_id=generation_id, error=str(exc), exc_info=True)
            return {
                "generation_id": generation_id,
                "status": "failed",
                "error": str(exc),
                "input": normalized,
                "generated_at": datetime.utcnow().isoformat() + "Z",
            }

    def get_generation_files(self, generation_result: Dict[str, Any]) -> List[Dict[str, str]]:
        """Extract all file entries from a completed generation result."""
        if generation_result.get("status") != "completed":
            return []

        files: List[Dict[str, str]] = []
        results = generation_result.get("results", {})

        for key, desc in (
            ("student_pdf", "Complete student materials (all rounds)"),
            ("teacher_pdf", "Complete teacher materials (all rounds)"),
        ):
            if results.get(key):
                files.append({"type": key, "path": results[key], "description": desc})

        for round_file in generation_result.get("files", {}).get("rounds", []):
            n = round_file["round"]
            for ftype, fdesc in (
                ("comprehension", "Comprehension station"),
                ("methods", "Methods station"),
                ("precision", "Precision station"),
                ("vocabulary", "Vocabulary station"),
                ("student_pdf", "Student materials"),
                ("teacher_pdf", "Teacher materials"),
                ("answer_key", "Answer key"),
                ("teacher_prep", "Teacher preparation"),
            ):
                if round_file.get(ftype):
                    files.append({
                        "type": f"round{n}_{ftype}",
                        "path": round_file[ftype],
                        "description": f"Round {n} – {fdesc}",
                    })

        return files


# ── dependency factory ────────────────────────────────────────────────────────

def create_generation_service() -> GenerationService:
    """FastAPI dependency factory – returns a ready GenerationService."""
    return GenerationService()
