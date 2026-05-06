"""
ADRION 369 — Redis Backend for Multi-Instance Deployment v5.6
=============================================================
Provides Redis-backed storage for CVC (Cumulative Violation Counter)
and G5 session state, enabling horizontal scaling.

Falls back to in-memory storage when Redis is unavailable.

Usage:
    from core.redis_backend import RedisSessionStore, RedisCVCStore

    # With Redis
    session_store = RedisSessionStore(redis_url="redis://localhost:6379/0")
    cvc_store = RedisCVCStore(redis_url="redis://localhost:6379/0")

    # Without Redis (in-memory fallback — same behavior as v5.5)
    session_store = RedisSessionStore()
    cvc_store = RedisCVCStore()
"""

import time
import json
import threading
from typing import Dict, Optional, Protocol

# ── Storage Protocol ─────────────────────────────────────────────────────────

class SessionStore(Protocol):
    """Protocol for G5 session storage backends."""

    def get_session(self, sid: str) -> Optional[dict]: ...
    def set_session(self, sid: str, data: dict) -> None: ...
    def delete_session(self, sid: str) -> None: ...
    def session_count(self) -> int: ...
    def evict_expired(self, ttl: float) -> int: ...


class CVCStore(Protocol):
    """Protocol for CVC (Cumulative Violation Counter) storage backends."""

    def record_violations(self, session_id: str, count: int, window_hours: int) -> int: ...
    def get_violation_count(self, session_id: str, window_hours: int) -> int: ...
    def reset(self, session_id: str) -> None: ...


# ── In-Memory Implementations (default, compatible with v5.5) ──────────────

class InMemorySessionStore:
    """Thread-safe in-memory session store. Default for single-instance."""

    def __init__(self) -> None:
        self._sessions: Dict[str, dict] = {}
        self._lock = threading.RLock()

    def get_session(self, sid: str) -> Optional[dict]:
        with self._lock:
            return self._sessions.get(sid)

    def set_session(self, sid: str, data: dict) -> None:
        with self._lock:
            self._sessions[sid] = data

    def delete_session(self, sid: str) -> None:
        with self._lock:
            self._sessions.pop(sid, None)

    def session_count(self) -> int:
        with self._lock:
            return len(self._sessions)

    def evict_expired(self, ttl: float) -> int:
        now = time.time()
        evicted = 0
        with self._lock:
            expired = [
                sid for sid, data in self._sessions.items()
                if now - data.get("last_audit", data.get("created_at", 0)) > ttl
            ]
            for sid in expired:
                del self._sessions[sid]
                evicted += 1
        return evicted


class InMemoryCVCStore:
    """Thread-safe in-memory CVC store. Default for single-instance."""

    def __init__(self) -> None:
        self._counts: Dict[str, list] = {}
        self._lock = threading.RLock()

    def record_violations(self, session_id: str, count: int, window_hours: int) -> int:
        now = time.time()
        cutoff = now - window_hours * 3600
        with self._lock:
            history = self._counts.setdefault(session_id, [])
            history.extend([now] * count)
            self._counts[session_id] = [t for t in history if t > cutoff]
            return len(self._counts[session_id])

    def get_violation_count(self, session_id: str, window_hours: int) -> int:
        now = time.time()
        cutoff = now - window_hours * 3600
        with self._lock:
            history = [t for t in self._counts.get(session_id, []) if t > cutoff]
            return len(history)

    def reset(self, session_id: str) -> None:
        with self._lock:
            self._counts.pop(session_id, None)


# ── Redis Implementations ────────────────────────────────────────────────────

class RedisSessionStore:
    """
    Redis-backed session store for multi-instance G5TransparencyGuard.

    Session data stored as JSON in Redis hash 'adrion369:g5:sessions'.
    TTL managed via Redis EXPIRE on individual keys.
    """

    PREFIX = "adrion369:g5:sess:"

    _fallback: Optional["InMemorySessionStore"]

    def __init__(self, redis_url: str = "", redis_client=None) -> None:
        self._redis = None
        if redis_client is not None:
            self._redis = redis_client
        elif redis_url:
            try:
                import redis
                self._redis = redis.Redis.from_url(redis_url, decode_responses=True)
                self._redis.ping()
            except Exception:
                self._redis = None

        if self._redis is None:
            self._fallback = InMemorySessionStore()
        else:
            self._fallback = None

    @property
    def is_redis(self) -> bool:
        return self._redis is not None

    def get_session(self, sid: str) -> Optional[dict]:
        if self._redis is None:
            assert self._fallback is not None
            return self._fallback.get_session(sid)
        raw = self._redis.get(self.PREFIX + sid)
        if raw is None:
            return None
        return json.loads(raw)

    def set_session(self, sid: str, data: dict) -> None:
        if self._redis is None:
            assert self._fallback is not None
            self._fallback.set_session(sid, data)
            return
        self._redis.set(self.PREFIX + sid, json.dumps(data))

    def set_session_with_ttl(self, sid: str, data: dict, ttl_seconds: int) -> None:
        if self._redis is None:
            assert self._fallback is not None
            self._fallback.set_session(sid, data)
            return
        self._redis.setex(self.PREFIX + sid, ttl_seconds, json.dumps(data))

    def delete_session(self, sid: str) -> None:
        if self._redis is None:
            assert self._fallback is not None
            self._fallback.delete_session(sid)
            return
        self._redis.delete(self.PREFIX + sid)

    def session_count(self) -> int:
        if self._redis is None:
            assert self._fallback is not None
            return self._fallback.session_count()
        keys = self._redis.keys(self.PREFIX + "*")
        return len(keys)

    def evict_expired(self, ttl: float) -> int:
        if self._redis is None:
            assert self._fallback is not None
            return self._fallback.evict_expired(ttl)
        # Redis handles TTL natively via EXPIRE/SETEX — no manual eviction needed
        return 0


class RedisCVCStore:
    """
    Redis-backed CVC store for multi-instance deployment.

    Uses Redis sorted sets (ZSET) with timestamps as scores
    for efficient sliding-window violation counting.

    Key pattern: adrion369:cvc:{session_id}
    """

    PREFIX = "adrion369:cvc:"

    _fallback: Optional["InMemoryCVCStore"]

    def __init__(self, redis_url: str = "", redis_client=None) -> None:
        self._redis = None
        if redis_client is not None:
            self._redis = redis_client
        elif redis_url:
            try:
                import redis
                self._redis = redis.Redis.from_url(redis_url, decode_responses=True)
                self._redis.ping()
            except Exception:
                self._redis = None

        if self._redis is None:
            self._fallback = InMemoryCVCStore()
        else:
            self._fallback = None

    @property
    def is_redis(self) -> bool:
        return self._redis is not None

    def record_violations(self, session_id: str, count: int, window_hours: int) -> int:
        if self._redis is None:
            assert self._fallback is not None
            return self._fallback.record_violations(session_id, count, window_hours)

        now = time.time()
        cutoff = now - window_hours * 3600
        key = self.PREFIX + session_id
        pipe = self._redis.pipeline()
        # Add new violations with current timestamp as score
        for i in range(count):
            pipe.zadd(key, {f"{now}:{i}": now})
        # Remove entries outside the window
        pipe.zremrangebyscore(key, "-inf", cutoff)
        # Count remaining
        pipe.zcard(key)
        # Set TTL on key to auto-cleanup
        pipe.expire(key, int(window_hours * 3600) + 60)
        results = pipe.execute()
        return results[-2]  # zcard result

    def get_violation_count(self, session_id: str, window_hours: int) -> int:
        if self._redis is None:
            assert self._fallback is not None
            return self._fallback.get_violation_count(session_id, window_hours)

        now = time.time()
        cutoff = now - window_hours * 3600
        key = self.PREFIX + session_id
        # Remove old entries and count
        self._redis.zremrangebyscore(key, "-inf", cutoff)
        return self._redis.zcard(key)

    def reset(self, session_id: str) -> None:
        if self._redis is None:
            assert self._fallback is not None
            self._fallback.reset(session_id)
            return
        self._redis.delete(self.PREFIX + session_id)
