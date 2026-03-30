"""
Redis-backed cache service (Sprint 4.5 — revised key schema).

Key schema:
  unit:{subject}:{topic}:{grade}   JSON list of material IDs sorted by approval_count DESC  (7 days)
  hot:units:top50                  Sorted set — 50 most-requested topic keys (no TTL; capped by zremrangebyrank)
  gen:status:{job_id}              Async generation status dict (1 hour)
  query:{md5}                      Legacy: full generation result JSON for exact-hash cache hits (24 hours)
  material:{id}                    Material metadata JSON (7 days)

Removed from v1:
  bm25:index / bm25:query_ids      — replaced by Postgres tsvector
  user:{id}:history                — moved to Postgres only

All operations degrade gracefully when Redis is unavailable.
"""
import hashlib
import json
from typing import Any, Dict, List, Optional

import redis

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger("app.services.cache")

# ── TTLs ──────────────────────────────────────────────────────────────────────
UNIT_TTL = 7 * 24 * 3600       # 7 days  — unit ID lists
MATERIAL_TTL = 7 * 24 * 3600   # 7 days  — material metadata
QUERY_TTL = 24 * 3600          # 24 hours — legacy exact-hash cache
GEN_STATUS_TTL = 3600          # 1 hour  — async generation status


def _make_redis_client(url: str) -> Optional[redis.Redis]:
    try:
        client: redis.Redis = redis.from_url(
            url, decode_responses=False, socket_connect_timeout=2
        )
        client.ping()
        return client
    except (redis.RedisError, OSError) as exc:
        log.warning("redis_connect_failed", url=url, error=str(exc))
        return None


class CacheService:
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        if redis_client is not None:
            self._client: Optional[redis.Redis] = redis_client
        else:
            self._client = _make_redis_client(settings.REDIS_URL)

    @property
    def available(self) -> bool:
        return self._client is not None

    # ── key helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def query_hash(subject: str, topic: str, grade: str, rounds: int) -> str:
        """Stable MD5 hash for exact-match cache key."""
        normalized = (
            f"{subject.lower().strip()}"
            f"|{topic.lower().strip()}"
            f"|{grade.lower().strip()}"
            f"|{rounds}"
        )
        return hashlib.md5(normalized.encode("utf-8")).hexdigest()

    @staticmethod
    def _unit_key(subject: str, topic: str, grade: str) -> str:
        return (
            f"unit:{subject.lower().strip()}"
            f":{topic.lower().strip()}"
            f":{grade.lower().strip()}"
        )

    # ── unit ID list cache ────────────────────────────────────────────────────

    def get_unit_ids(self, subject: str, topic: str, grade: str) -> Optional[List[str]]:
        """Return cached list of material IDs sorted by approval_count DESC, or None."""
        if not self.available:
            return None
        try:
            raw = self._client.get(self._unit_key(subject, topic, grade))
            return json.loads(raw) if raw else None
        except redis.RedisError as exc:
            log.warning("cache_get_unit_ids_failed", key=self._unit_key(subject, topic, grade), error=str(exc))
            return None
        except (json.JSONDecodeError, TypeError) as exc:
            log.warning("cache_get_unit_ids_decode_failed", key=self._unit_key(subject, topic, grade), error=str(exc))
            return None

    def set_unit_ids(
        self, subject: str, topic: str, grade: str, ids: List[str]
    ) -> bool:
        """Store material ID list for this subject/topic/grade."""
        if not self.available:
            return False
        try:
            self._client.setex(
                self._unit_key(subject, topic, grade),
                UNIT_TTL,
                json.dumps(ids).encode("utf-8"),
            )
            return True
        except redis.RedisError as exc:
            log.warning("cache_set_unit_ids_failed", key=self._unit_key(subject, topic, grade), error=str(exc))
            return False

    def invalidate_unit_ids(self, subject: str, topic: str, grade: str) -> bool:
        """Remove cached unit list so next request re-queries the DB."""
        if not self.available:
            return False
        try:
            self._client.delete(self._unit_key(subject, topic, grade))
            return True
        except redis.RedisError as exc:
            log.warning("cache_invalidate_unit_ids_failed", key=self._unit_key(subject, topic, grade), error=str(exc))
            return False

    # ── hot units sorted set ──────────────────────────────────────────────────

    def update_hot_units(self, subject: str, topic: str, grade: str) -> None:
        """Increment score for this topic in the hot:units:top50 sorted set."""
        if not self.available:
            return
        try:
            key = (
                f"{subject.lower().strip()}"
                f":{topic.lower().strip()}"
                f":{grade.lower().strip()}"
            )
            self._client.zincrby("hot:units:top50", 1, key)
            # Keep only top 50
            self._client.zremrangebyrank("hot:units:top50", 0, -51)
        except redis.RedisError as exc:
            log.warning("cache_update_hot_units_failed", error=str(exc))

    # ── async generation status ───────────────────────────────────────────────

    def get_gen_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        if not self.available:
            return None
        try:
            raw = self._client.get(f"gen:status:{job_id}")
            return json.loads(raw) if raw else None
        except redis.RedisError as exc:
            log.warning("cache_get_gen_status_failed", job_id=job_id, error=str(exc))
            return None
        except (json.JSONDecodeError, TypeError) as exc:
            log.warning("cache_get_gen_status_decode_failed", job_id=job_id, error=str(exc))
            return None

    def set_gen_status(self, job_id: str, status_data: Dict[str, Any]) -> bool:
        if not self.available:
            return False
        try:
            self._client.setex(
                f"gen:status:{job_id}",
                GEN_STATUS_TTL,
                json.dumps(status_data, default=str).encode("utf-8"),
            )
            return True
        except redis.RedisError as exc:
            log.warning("cache_set_gen_status_failed", job_id=job_id, error=str(exc))
            return False

    # ── legacy exact-hash query cache ─────────────────────────────────────────
    # Kept for backward compatibility; may be removed in Sprint 5.

    def get_cached_query(self, query_hash: str) -> Optional[Dict[str, Any]]:
        if not self.available:
            return None
        try:
            raw = self._client.get(f"query:{query_hash}")
            return json.loads(raw) if raw else None
        except redis.RedisError as exc:
            log.warning("cache_get_query_failed", query_hash=query_hash, error=str(exc))
            return None
        except (json.JSONDecodeError, TypeError) as exc:
            log.warning("cache_get_query_decode_failed", query_hash=query_hash, error=str(exc))
            return None

    def cache_query(self, query_hash: str, result: Dict[str, Any]) -> bool:
        if not self.available:
            return False
        try:
            self._client.setex(
                f"query:{query_hash}",
                QUERY_TTL,
                json.dumps(result, default=str).encode("utf-8"),
            )
            return True
        except redis.RedisError as exc:
            log.warning("cache_set_query_failed", query_hash=query_hash, error=str(exc))
            return False

    def invalidate_query(self, query_hash: str) -> bool:
        if not self.available:
            return False
        try:
            self._client.delete(f"query:{query_hash}")
            return True
        except redis.RedisError as exc:
            log.warning("cache_invalidate_query_failed", query_hash=query_hash, error=str(exc))
            return False

    # ── material metadata cache ───────────────────────────────────────────────

    def get_cached_material(self, material_id: str) -> Optional[Dict[str, Any]]:
        if not self.available:
            return None
        try:
            raw = self._client.get(f"material:{material_id}")
            return json.loads(raw) if raw else None
        except redis.RedisError as exc:
            log.warning("cache_get_material_failed", material_id=material_id, error=str(exc))
            return None
        except (json.JSONDecodeError, TypeError) as exc:
            log.warning("cache_get_material_decode_failed", material_id=material_id, error=str(exc))
            return None

    def cache_material(self, material_id: str, content: Dict[str, Any]) -> bool:
        if not self.available:
            return False
        try:
            self._client.setex(
                f"material:{material_id}",
                MATERIAL_TTL,
                json.dumps(content, default=str).encode("utf-8"),
            )
            return True
        except redis.RedisError as exc:
            log.warning("cache_set_material_failed", material_id=material_id, error=str(exc))
            return False
