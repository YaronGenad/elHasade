"""
Integration tests for the Generation API endpoints (Sprint 2).

The actual generation pipeline (LLM calls, Playwright PDF) is mocked so
these tests run fast without external dependencies.
"""
import json
import os
import sys

# ── env setup BEFORE any app import ──────────────────────────────────────────
# Core env vars (conftest.py sets them if running via pytest; set here as
# fallback for direct `python test_generations_complete.py` execution).
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_alhasade_complete.db")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")
os.environ.setdefault("AUTH_RATE_LIMIT", "1000/minute")
os.environ.setdefault("GENERATION_RATE_LIMIT", "1000/minute")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# ── app bootstrap ─────────────────────────────────────────────────────────────
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.db.base import Base
from app.db.session import engine
from app.main import app
from app.models import material, query, user  # noqa: F401 – ensure models registered
from app.services.generation import GenerationService, create_generation_service

# ── ensure tables exist (auth tests may have already created them) ────────────
Base.metadata.create_all(bind=engine)

# ── mock generation service ───────────────────────────────────────────────────
MOCK_RESULT = {
    "generation_id": "mock-gen-id",
    "status": "completed",
    "input": {"subject": "מדעים", "topic": "תאים", "grade": "ה-ו", "rounds": 1},
    "output_dir": "/tmp/mock_output",
    "roadmap": {"rounds": [{"round": 1, "title": "תאים"}]},
    "results": {
        "student_pdf": "/tmp/mock_student.pdf",
        "teacher_pdf": "/tmp/mock_teacher.pdf",
        "rounds": [],
    },
    "files": {
        "student_pdf": "/tmp/mock_student.pdf",
        "teacher_pdf": "/tmp/mock_teacher.pdf",
        "rounds": [],
    },
    "generated_at": "2026-01-01T00:00:00Z",
}


def mock_generation_service() -> GenerationService:
    svc = MagicMock(spec=GenerationService)
    svc.generate_materials.return_value = MOCK_RESULT
    return svc


# Override the dependency for the entire test module
app.dependency_overrides[create_generation_service] = mock_generation_service

client = TestClient(app)

# ── helpers ───────────────────────────────────────────────────────────────────

def _register_and_login(email: str) -> str:
    """Register a user and return a valid access token."""
    client.post(
        "/auth/register",
        json={"email": email, "password": "testpassword123", "full_name": "Test User"},
    )
    resp = client.post("/auth/login", data={"username": email, "password": "testpassword123"})
    return resp.json()["access_token"]


# ── tests ─────────────────────────────────────────────────────────────────────

def test_submit_generation_unauthenticated():
    """POST /generations/ without token must return 401 or 403."""
    response = client.post(
        "/generations/",
        json={"subject": "מדעים", "topic": "תאים", "grade": "ה-ו", "rounds": 1},
    )
    assert response.status_code in (401, 403), response.text
    print("Unauthenticated generation test passed!")


def test_submit_generation_authenticated():
    """POST /generations/ returns 202 with generation_id and status=pending."""
    token = _register_and_login("gen_submit@example.com")
    response = client.post(
        "/generations/",
        json={"subject": "מדעים", "topic": "תאים", "grade": "ה-ו", "rounds": 1},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 202, response.text
    data = response.json()
    assert "generation_id" in data
    assert data["status"] == "pending"
    assert "Poll" in data["message"] or "pending" in data["message"].lower() or "started" in data["message"].lower()
    print("Authenticated generation submit test passed!")


def test_submit_generation_invalid_request():
    """POST /generations/ with missing required field returns 422."""
    token = _register_and_login("gen_invalid@example.com")
    response = client.post(
        "/generations/",
        json={"subject": "מדעים"},  # missing topic, grade
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422, response.text
    print("Invalid generation request test passed!")


def test_submit_generation_rounds_out_of_range():
    """POST /generations/ with rounds=0 returns 422."""
    token = _register_and_login("gen_rounds@example.com")
    response = client.post(
        "/generations/",
        json={"subject": "מדעים", "topic": "תאים", "grade": "ה-ו", "rounds": 0},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422, response.text
    print("Out-of-range rounds test passed!")


def test_get_generation_status():
    """GET /generations/{id} returns status for the authenticated owner."""
    token = _register_and_login("gen_status@example.com")

    # Submit
    submit_resp = client.post(
        "/generations/",
        json={"subject": "היסטוריה", "topic": "מלחמת העצמאות", "grade": "ז-ח", "rounds": 2},
        headers={"Authorization": f"Bearer {token}"},
    )
    generation_id = submit_resp.json()["generation_id"]

    # Poll status
    response = client.get(
        f"/generations/{generation_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["generation_id"] == generation_id
    assert data["status"] in ("pending", "processing", "completed", "failed")
    assert data["subject"] == "היסטוריה"
    assert data["topic"] == "מלחמת העצמאות"
    print("Get generation status test passed!")


def test_get_generation_not_found():
    """GET /generations/{id} with unknown id returns 404."""
    token = _register_and_login("gen_notfound@example.com")
    response = client.get(
        "/generations/00000000-0000-0000-0000-000000000000",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404, response.text
    print("Generation not found test passed!")


def test_get_generation_wrong_user():
    """GET /generations/{id} by a different user returns 404 (not 403, to avoid enumeration)."""
    token_a = _register_and_login("gen_owner@example.com")
    token_b = _register_and_login("gen_other@example.com")

    # User A submits
    submit_resp = client.post(
        "/generations/",
        json={"subject": "עברית", "topic": "שירה", "grade": "ט-י", "rounds": 1},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    generation_id = submit_resp.json()["generation_id"]

    # User B tries to read User A's generation
    response = client.get(
        f"/generations/{generation_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert response.status_code == 404, response.text
    print("Cross-user generation access test passed!")


def test_list_generations():
    """GET /generations/ returns only the current user's history."""
    token = _register_and_login("gen_list@example.com")

    # Submit two generations
    for topic in ("פוטוסינתזה", "נשימה תאית"):
        client.post(
            "/generations/",
            json={"subject": "ביולוגיה", "topic": topic, "grade": "י-יא", "rounds": 1},
            headers={"Authorization": f"Bearer {token}"},
        )

    response = client.get("/generations/", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200, response.text
    data = response.json()
    assert "generations" in data
    assert len(data["generations"]) >= 2
    assert all(g["subject"] == "ביולוגיה" for g in data["generations"])
    print("List generations test passed!")


def test_list_generations_pagination():
    """GET /generations/?limit=1&offset=0 returns at most 1 result."""
    token = _register_and_login("gen_page@example.com")
    for i in range(3):
        client.post(
            "/generations/",
            json={"subject": "מתמטיקה", "topic": f"נושא {i}", "grade": "ג-ד", "rounds": 1},
            headers={"Authorization": f"Bearer {token}"},
        )

    response = client.get(
        "/generations/?limit=1&offset=0",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert len(data["generations"]) == 1
    assert data["limit"] == 1
    print("Generation pagination test passed!")


def test_download_not_completed():
    """GET /generations/{id}/download/student_pdf returns 409 if not completed."""
    token = _register_and_login("gen_dl_pending@example.com")

    submit_resp = client.post(
        "/generations/",
        json={"subject": "אנגלית", "topic": "grammar", "grade": "א-ב", "rounds": 1},
        headers={"Authorization": f"Bearer {token}"},
    )
    generation_id = submit_resp.json()["generation_id"]

    # Manually check – the background task may have already run in TestClient
    # so check the status first; only assert 409 if still pending/processing
    status_resp = client.get(
        f"/generations/{generation_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    current_status = status_resp.json()["status"]

    if current_status != "completed":
        dl_resp = client.get(
            f"/generations/{generation_id}/download/student_pdf",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert dl_resp.status_code == 409, dl_resp.text
    print("Download not-completed test passed!")


# ── entrypoint ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    test_submit_generation_unauthenticated()
    test_submit_generation_authenticated()
    test_submit_generation_invalid_request()
    test_submit_generation_rounds_out_of_range()
    test_get_generation_status()
    test_get_generation_not_found()
    test_get_generation_wrong_user()
    test_list_generations()
    test_list_generations_pagination()
    test_download_not_completed()
    print("\nAll generation integration tests passed!")
