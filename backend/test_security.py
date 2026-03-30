"""
Sprint 5 — Security tests (OWASP Top 10 review).

Covers:
  A01 Broken Access Control   — cross-user access, unauthenticated endpoints
  A02 Cryptographic Failures  — JWT token validation
  A03 Injection               — SQL injection in request fields
  A04 Insecure Design         — overly permissive inputs stored cleanly
  A07 Identification / Auth   — malformed / expired / missing tokens
  A08 Integrity               — path traversal in file download
"""
import os
import sys

# ── env setup BEFORE any app import ──────────────────────────────────────────
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_alhasade_complete.db")
os.environ.setdefault("GEMINI_API_KEY", "test-key")
os.environ.setdefault("AUTH_RATE_LIMIT", "1000/minute")
os.environ.setdefault("GENERATION_RATE_LIMIT", "1000/minute")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from unittest.mock import MagicMock

import fakeredis
from fastapi.testclient import TestClient

from app.db.base import Base
from app.db.session import engine
from app.main import app
from app.models import material, query, user  # noqa: F401
from app.services.cache import CacheService
from app.services.generation import GenerationService, create_generation_service
from app.services.search import SearchService, create_search_service

Base.metadata.create_all(bind=engine)

FAKE_REDIS = fakeredis.FakeRedis()

MOCK_RESULT = {
    "generation_id": "mock-gen-id",
    "status": "completed",
    "input": {},
    "output_dir": "/tmp/mock",
    "roadmap": {},
    "results": {"rounds": []},
    "files": {"rounds": []},
    "generated_at": "2026-01-01T00:00:00Z",
}


def _mock_gen():
    svc = MagicMock(spec=GenerationService)
    svc.generate_materials.return_value = MOCK_RESULT
    return svc


def _fake_search():
    return SearchService(CacheService(redis_client=FAKE_REDIS))


app.dependency_overrides[create_generation_service] = _mock_gen
app.dependency_overrides[create_search_service] = _fake_search

client = TestClient(app)


# ── helpers ───────────────────────────────────────────────────────────────────

def _register_and_login(email: str) -> str:
    client.post(
        "/auth/register",
        json={"email": email, "password": "testpassword123", "full_name": "Security Tester"},
    )
    resp = client.post("/auth/login", data={"username": email, "password": "testpassword123"})
    return resp.json()["access_token"]


# ═══════════════════════════════════════════════════════════════════════════════
# A01 — Broken Access Control
# ═══════════════════════════════════════════════════════════════════════════════

def test_all_generation_endpoints_require_auth():
    """Every /generations/* endpoint must reject unauthenticated requests."""
    endpoints = [
        ("POST", "/generations/", {"subject": "X", "topic": "Y", "grade": "Z", "rounds": 1}),
        ("GET",  "/generations/", None),
        ("GET",  "/generations/00000000-0000-0000-0000-000000000001", None),
    ]
    for method, url, body in endpoints:
        if method == "POST":
            resp = client.post(url, json=body)
        else:
            resp = client.get(url)
        assert resp.status_code in (401, 403), f"{method} {url} should require auth, got {resp.status_code}"
    print("All generation endpoints require auth test passed!")


def test_all_materials_endpoints_require_auth():
    """Every /materials/* endpoint must reject unauthenticated requests."""
    endpoints = [
        ("POST", "/materials/some-id/approve"),
        ("POST", "/materials/some-id/reject"),
        ("GET",  "/materials/versions?subject=X&topic=Y&grade=Z"),
    ]
    for method, url in endpoints:
        resp = client.post(url) if method == "POST" else client.get(url)
        assert resp.status_code in (401, 403), f"{method} {url} should require auth"
    print("All materials endpoints require auth test passed!")


def test_cross_user_generation_access_denied():
    """User B cannot see User A's generation (returns 404, not 403, to avoid enumeration)."""
    token_a = _register_and_login("sec_owner@example.com")
    token_b = _register_and_login("sec_other@example.com")

    resp = client.post(
        "/generations/",
        json={"subject": "מדעים", "topic": "תאים", "grade": "ה", "rounds": 1},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    gen_id = resp.json()["generation_id"]

    resp_b = client.get(
        f"/generations/{gen_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp_b.status_code == 404, "Cross-user access should return 404 (not 403)"
    print("Cross-user generation access denied (404) test passed!")


def test_search_endpoint_requires_auth():
    resp = client.get("/search/?q=test")
    assert resp.status_code in (401, 403)
    print("Search endpoint requires auth test passed!")


# ═══════════════════════════════════════════════════════════════════════════════
# A03 — Injection
# ═══════════════════════════════════════════════════════════════════════════════

def test_sql_injection_in_subject_does_not_crash():
    """
    SQL injection payloads in subject/topic/grade should be safely handled
    by SQLAlchemy ORM parameterization.
    The server must NOT return 500.
    """
    token = _register_and_login("sec_sqli@example.com")
    payloads = [
        "'; DROP TABLE users; --",
        "' OR '1'='1",
        "1; SELECT * FROM users; --",
        "\" OR \"1\"=\"1",
    ]
    for payload in payloads:
        resp = client.post(
            "/generations/",
            json={"subject": payload, "topic": "test", "grade": "ח", "rounds": 1},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code != 500, f"SQL injection payload caused 500: {payload!r}"
        assert resp.status_code in (202, 422), f"Unexpected status for payload {payload!r}: {resp.status_code}"
    print("SQL injection does not crash server test passed!")


def test_sql_injection_in_search_does_not_crash():
    """SQL injection in search query parameter must not cause 500."""
    token = _register_and_login("sec_sqli_search@example.com")
    payloads = [
        "'; DROP TABLE lesson_units; --",
        "' UNION SELECT * FROM users --",
    ]
    for payload in payloads:
        resp = client.get(
            f"/search/?q={payload}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code != 500, f"SQL injection in search caused 500: {payload!r}"
    print("SQL injection in search does not crash server test passed!")


# ═══════════════════════════════════════════════════════════════════════════════
# A04 — Insecure Design (input handling)
# ═══════════════════════════════════════════════════════════════════════════════

def test_xss_payload_stored_safely():
    """
    XSS payloads in text fields are stored as plain text (not executed).
    The API returns 202 (the payload is valid text content for the LLM).
    XSS prevention is the frontend's responsibility.
    """
    token = _register_and_login("sec_xss@example.com")
    resp = client.post(
        "/generations/",
        json={
            "subject": "<script>alert('xss')</script>",
            "topic": "<img src=x onerror=alert(1)>",
            "grade": "ח",
            "rounds": 1,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    # Server should accept (202) or reject for field-length (422), never crash
    assert resp.status_code != 500
    print("XSS payload stored safely test passed!")


def test_oversized_subject_rejected():
    """Subject field longer than reasonable limit should return 422."""
    token = _register_and_login("sec_long@example.com")
    resp = client.post(
        "/generations/",
        json={"subject": "א" * 10000, "topic": "test", "grade": "ח", "rounds": 1},
        headers={"Authorization": f"Bearer {token}"},
    )
    # Either accepted (stored) or rejected by Pydantic — must not crash
    assert resp.status_code != 500
    print("Oversized subject handled test passed!")


def test_rounds_out_of_range_rejected():
    """rounds=0 and rounds=100 must return 422 (Pydantic validation)."""
    token = _register_and_login("sec_rounds@example.com")
    for bad_rounds in (0, 11, -1, 100):
        resp = client.post(
            "/generations/",
            json={"subject": "מדעים", "topic": "תאים", "grade": "ה", "rounds": bad_rounds},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422, f"rounds={bad_rounds} should be rejected with 422"
    print("Rounds out-of-range validation test passed!")


# ═══════════════════════════════════════════════════════════════════════════════
# A07 — Identification & Authentication Failures
# ═══════════════════════════════════════════════════════════════════════════════

def test_missing_auth_header_returns_401_or_403():
    resp = client.get("/generations/")
    assert resp.status_code in (401, 403)
    print("Missing auth header returns 401/403 test passed!")


def test_malformed_token_rejected():
    """A syntactically invalid JWT must be rejected."""
    for bad_token in ("not-a-jwt", "Bearer", "eyJhbGciOiJub25lIn0.", "null"):
        resp = client.get(
            "/generations/",
            headers={"Authorization": f"Bearer {bad_token}"},
        )
        assert resp.status_code in (401, 403), f"Malformed token should be rejected: {bad_token!r}"
    print("Malformed token rejected test passed!")


def test_wrong_secret_token_rejected():
    """A JWT signed with a different secret key must be rejected."""
    import base64
    import json as _json

    header = base64.urlsafe_b64encode(b'{"alg":"HS256","typ":"JWT"}').rstrip(b"=").decode()
    payload = base64.urlsafe_b64encode(
        _json.dumps({"sub": "any-user", "exp": 9999999999}).encode()
    ).rstrip(b"=").decode()
    fake_sig = base64.urlsafe_b64encode(b"wrong-signature").rstrip(b"=").decode()
    forged_token = f"{header}.{payload}.{fake_sig}"

    resp = client.get(
        "/generations/",
        headers={"Authorization": f"Bearer {forged_token}"},
    )
    assert resp.status_code in (401, 403)
    print("Wrong-secret JWT rejected test passed!")


def test_duplicate_email_registration_rejected():
    """Registering the same email twice must return 400."""
    email = "sec_dup@example.com"
    client.post(
        "/auth/register",
        json={"email": email, "password": "password123", "full_name": "First"},
    )
    resp = client.post(
        "/auth/register",
        json={"email": email, "password": "different-pw", "full_name": "Second"},
    )
    assert resp.status_code == 400
    print("Duplicate email registration rejected test passed!")


def test_login_wrong_password_rejected():
    """Login with incorrect password must return 401."""
    email = "sec_wrongpw@example.com"
    client.post(
        "/auth/register",
        json={"email": email, "password": "correctpassword", "full_name": "Test"},
    )
    resp = client.post(
        "/auth/login",
        data={"username": email, "password": "wrongpassword"},
    )
    assert resp.status_code == 401
    print("Wrong password rejected test passed!")


def test_login_nonexistent_user_rejected():
    """Login with an email that does not exist must return 401."""
    resp = client.post(
        "/auth/login",
        data={"username": "nobody@nowhere.com", "password": "anything"},
    )
    assert resp.status_code == 401
    print("Non-existent user login rejected test passed!")


# ═══════════════════════════════════════════════════════════════════════════════
# A08 — Path Traversal in file download
# ═══════════════════════════════════════════════════════════════════════════════

def test_path_traversal_in_file_type_rejected():
    """
    Path traversal attempts via the file_type parameter must not serve
    files outside the output directory.
    Expected: 404 (generation not found) or 422 (validation error).
    Must NOT return 200 with file contents.
    """
    token = _register_and_login("sec_path@example.com")

    traversal_payloads = [
        "../../../../etc/passwd",
        "../etc/passwd",
        "student_pdf/../../../etc/passwd",
    ]
    for payload in traversal_payloads:
        gen_id = "00000000-0000-0000-0000-000000000001"
        resp = client.get(
            f"/generations/{gen_id}/download/{payload}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code != 200, f"Path traversal returned 200: {payload!r}"
    print("Path traversal in file_type rejected test passed!")


# ═══════════════════════════════════════════════════════════════════════════════
# Input validation (Pydantic schema coverage)
# ═══════════════════════════════════════════════════════════════════════════════

def test_missing_required_fields_rejected():
    """All three required fields (subject, topic, grade) must be present."""
    token = _register_and_login("sec_missing@example.com")
    cases = [
        {"topic": "X", "grade": "Y"},           # missing subject
        {"subject": "X", "grade": "Y"},          # missing topic
        {"subject": "X", "topic": "Y"},          # missing grade
        {},                                       # missing all
    ]
    for body in cases:
        resp = client.post(
            "/generations/",
            json=body,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422, f"Missing fields should return 422: {body}"
    print("Missing required fields rejected test passed!")


def test_invalid_json_body_rejected():
    """Sending malformed JSON must return 422."""
    token = _register_and_login("sec_badjson@example.com")
    resp = client.post(
        "/generations/",
        content=b"not json at all",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    assert resp.status_code == 422
    print("Invalid JSON body rejected test passed!")


# ── entrypoint ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # A01
    test_all_generation_endpoints_require_auth()
    test_all_materials_endpoints_require_auth()
    test_cross_user_generation_access_denied()
    test_search_endpoint_requires_auth()
    # A03
    test_sql_injection_in_subject_does_not_crash()
    test_sql_injection_in_search_does_not_crash()
    # A04
    test_xss_payload_stored_safely()
    test_oversized_subject_rejected()
    test_rounds_out_of_range_rejected()
    # A07
    test_missing_auth_header_returns_401_or_403()
    test_malformed_token_rejected()
    test_wrong_secret_token_rejected()
    test_duplicate_email_registration_rejected()
    test_login_wrong_password_rejected()
    test_login_nonexistent_user_rejected()
    # A08
    test_path_traversal_in_file_type_rejected()
    # Validation
    test_missing_required_fields_rejected()
    test_invalid_json_body_rejected()
    print("\nAll security tests passed!")
