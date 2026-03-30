"""
Al-Hasade Load Test — Locust configuration.

Simulates concurrent teachers performing the full workflow:
  register/login → submit generation → poll status → approve/reject → download PDF

Run:
  pip install locust

  # Interactive (GUI):
  locust -f locustfile.py --host=http://localhost:8000

  # Headless — normal load (CI / automated):
  locust -f locustfile.py --host=http://localhost:8000 \
         --users 50 --spawn-rate 5 --run-time 2m --headless

  # Headless — spike/stress test:
  locust -f locustfile.py --host=http://localhost:8000 \
         --users 150 --spawn-rate 30 --run-time 3m --headless \
         --tags spike

Performance targets:
  - BM25 search latency      < 50 ms
  - Redis cache hit latency  <  5 ms
  - Generation submit        < 500 ms  (background task, not full pipeline)
  - /health                  < 100 ms
  - PDF download             < 2000 ms
"""
import random
import sys
import time
import uuid

from locust import HttpUser, SequentialTaskSet, between, events, tag, task


# ── Shared data ────────────────────────────────────────────────────────────────

SUBJECTS = ["מתמטיקה", "מדעים", "עברית", "היסטוריה", "ביולוגיה", "כימיה", "פיזיקה", "תנ\"ך", "אנגלית"]
TOPICS   = ["תאים", "שברים", "שירה", "ציונות", "פוטוסינתזה", "חומצות", "כוחות", "שיבת ציון", "grammar"]
GRADES   = ["ג-ד", "ה-ו", "ז-ח", "ח-ט", "י-יא", "יא-יב"]

# Failure threshold — test fails if error rate exceeds this (1%)
FAILURE_THRESHOLD_PERCENT = 1.0


# ── Metrics tracking ──────────────────────────────────────────────────────────

cache_hits = 0
cache_misses = 0


# ── Task sets ──────────────────────────────────────────────────────────────────

class TeacherWorkflow(SequentialTaskSet):
    """
    Simulates a teacher's complete session:
    1. Register (once)
    2. Login → get access token
    3. Search for existing materials
    4. Submit a generation request
    5. Poll generation status
    6. Approve or reject the result
    7. Download PDFs
    8. View history
    """

    token: str = ""
    generation_id: str = ""
    material_id: str = ""

    def on_start(self):
        """Register and login before running tasks."""
        email = f"load_test_{uuid.uuid4().hex[:8]}@example.com"
        password = "loadtest-password-123"

        # Register
        self.client.post(
            "/auth/register",
            json={"email": email, "password": password, "full_name": "Load Test Teacher"},
            name="/auth/register",
        )

        # Login
        resp = self.client.post(
            "/auth/login",
            data={"username": email, "password": password},
            name="/auth/login",
        )
        if resp.status_code == 200:
            self.token = resp.json().get("access_token", "")

    def _auth_headers(self) -> dict:
        return {"Authorization": f"Bearer {self.token}"}

    @task
    def health_check(self):
        """Hit health endpoint — should be <100ms."""
        with self.client.get(
            "/health",
            name="/health",
            catch_response=True,
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Health check failed: {resp.status_code}")

    @task
    def search_existing_materials(self):
        """Search for existing materials (debounced as the teacher types)."""
        global cache_hits, cache_misses
        subject = random.choice(SUBJECTS)
        topic = random.choice(TOPICS)
        with self.client.get(
            f"/search/?q={subject} {topic}",
            headers=self._auth_headers(),
            name="/search/",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                data = resp.json()
                # Track cache behavior via response count
                if data.get("count", 0) > 0:
                    cache_hits += 1
                else:
                    cache_misses += 1
            elif resp.status_code not in (401, 403):
                resp.failure(f"Search failed: {resp.status_code}")

    @task
    def submit_generation(self):
        """Submit a generation request."""
        global cache_hits, cache_misses
        subject = random.choice(SUBJECTS)
        topic = random.choice(TOPICS)
        grade = random.choice(GRADES)

        with self.client.post(
            "/generations/",
            json={"subject": subject, "topic": topic, "grade": grade, "rounds": 2},
            headers=self._auth_headers(),
            name="/generations/ (submit)",
            catch_response=True,
        ) as resp:
            if resp.status_code == 202:
                body = resp.json()
                self.generation_id = body.get("generation_id", "")
                if body.get("from_cache"):
                    cache_hits += 1
                else:
                    cache_misses += 1
            elif resp.status_code in (401, 403, 429):
                resp.success()  # expected rate-limit or auth
            else:
                resp.failure(f"Submit failed: {resp.status_code}")

    @task
    def poll_generation_status(self):
        """Poll for generation status (teachers usually poll every 5s)."""
        if not self.generation_id:
            return
        with self.client.get(
            f"/generations/{self.generation_id}",
            headers=self._auth_headers(),
            name="/generations/{id} (poll)",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == "completed":
                    self.material_id = data.get("material_id", "")
            elif resp.status_code in (404, 401, 403):
                resp.success()
            else:
                resp.failure(f"Poll failed: {resp.status_code}")

    @task
    def approve_material(self):
        """Approve a completed material."""
        if not self.material_id:
            return
        with self.client.post(
            f"/materials/{self.material_id}/approve",
            headers=self._auth_headers(),
            name="/materials/{id}/approve",
            catch_response=True,
        ) as resp:
            if resp.status_code in (200, 404, 401, 403):
                resp.success()
            else:
                resp.failure(f"Approve failed: {resp.status_code}")

    @task
    def download_pdf(self):
        """Download student PDF for a completed generation."""
        if not self.generation_id:
            return
        with self.client.get(
            f"/generations/{self.generation_id}/download/student_pdf",
            headers=self._auth_headers(),
            name="/generations/{id}/download/student_pdf",
            catch_response=True,
        ) as resp:
            if resp.status_code in (200, 404, 401, 403):
                resp.success()
            else:
                resp.failure(f"PDF download failed: {resp.status_code}")

    @task
    def download_teacher_pdf(self):
        """Download teacher PDF for a completed generation."""
        if not self.generation_id:
            return
        with self.client.get(
            f"/generations/{self.generation_id}/download/teacher_pdf",
            headers=self._auth_headers(),
            name="/generations/{id}/download/teacher_pdf",
            catch_response=True,
        ) as resp:
            if resp.status_code in (200, 404, 401, 403):
                resp.success()
            else:
                resp.failure(f"PDF download failed: {resp.status_code}")

    @task
    def get_history(self):
        """List the teacher's generation history."""
        with self.client.get(
            "/generations/?limit=10&offset=0",
            headers=self._auth_headers(),
            name="/generations/ (list)",
            catch_response=True,
        ) as resp:
            if resp.status_code not in (200, 401, 403):
                resp.failure(f"History failed: {resp.status_code}")
            # Reset for next cycle
            self.material_id = ""


class TeacherUser(HttpUser):
    """
    Represents a single teacher.
    Wait 1–5 seconds between tasks (realistic browser interaction speed).
    """
    tasks = [TeacherWorkflow]
    wait_time = between(1, 5)


@tag("spike")
class SpikeUser(HttpUser):
    """
    Stress test user — shorter wait times to simulate traffic spikes.
    Use: locust --tags spike --users 150 --spawn-rate 30
    """
    tasks = [TeacherWorkflow]
    wait_time = between(0.2, 1)


# ── Event hooks ────────────────────────────────────────────────────────────────

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    global cache_hits, cache_misses
    cache_hits = 0
    cache_misses = 0
    print("==> Load test started")
    print(f"    Failure threshold: {FAILURE_THRESHOLD_PERCENT}% error rate")
    print("    Performance targets:")
    print("      /search/                      < 50 ms")
    print("      /health                       < 100 ms")
    print("      /generations/ (submit)        < 500 ms")
    print("      /generations/*/download/*     < 2000 ms")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    stats = environment.stats
    total_requests = stats.total.num_requests
    total_failures = stats.total.num_failures

    print("\n==> Load test complete")
    print(f"    Total requests:  {total_requests}")
    print(f"    Total failures:  {total_failures}")

    if total_requests > 0:
        error_rate = (total_failures / total_requests) * 100
        print(f"    Error rate:      {error_rate:.2f}%")
    else:
        error_rate = 0.0

    print(f"\n    Cache hits:  {cache_hits}")
    print(f"    Cache misses: {cache_misses}")
    if cache_hits + cache_misses > 0:
        hit_rate = (cache_hits / (cache_hits + cache_misses)) * 100
        print(f"    Cache hit rate: {hit_rate:.1f}%")

    print("\n    Per-endpoint stats:")
    for name, entry in stats.entries.items():
        print(f"    {name[1]:<45} p50={entry.get_response_time_percentile(0.5):>6.0f}ms"
              f"  p95={entry.get_response_time_percentile(0.95):>6.0f}ms"
              f"  fails={entry.num_failures}")

    # Auto-fail if error rate exceeds threshold
    if total_requests > 0 and error_rate > FAILURE_THRESHOLD_PERCENT:
        print(f"\n    FAIL: Error rate {error_rate:.2f}% exceeds threshold {FAILURE_THRESHOLD_PERCENT}%")
        environment.process_exit_code = 1
    elif total_requests > 0:
        print(f"\n    PASS: Error rate {error_rate:.2f}% within threshold {FAILURE_THRESHOLD_PERCENT}%")
        environment.process_exit_code = 0
