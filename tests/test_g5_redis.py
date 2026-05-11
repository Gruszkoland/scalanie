"""
test_g5_redis.py — ADRION 369 B5-FIX: G5TransparencyGuard Redis backend tests
===============================================================================
Weryfikuje:
  1. Baseline in-memory — istniejące testy nadal przechodzą bez Redis
  2. Redis session store — sesja persystowana w Redis po classify_request
  3. Multi-instance sync — dwie instancje G5 współdzielą stan przez Redis
  4. Global limit Redis — atomowy INCR egzekwuje limit między instancjami
  5. Fallback in-memory — Redis niedostępny → graceful fallback
  6. TTL eviction — Redis EXPIRE zachowuje się poprawnie (session_ttl)
  7. Rate limit sync — cooldown persystowany w Redis (nie in-memory)
  8. Depth limit sync — audit_depth persystowany między instancjami
  9. AUDIT_REQUEST_PATTERNS — niemutowalne nawet z Redis backendem
 10. CVC integration — _CumulativeViolationCounter niezależny od Redis G5

Uruchomienie:
    pytest tests/test_g5_redis.py -v

Wymagania:
    pip install fakeredis redis pytest
"""

import time
import threading
import sys
import os
import importlib

import pytest
import fakeredis

# ── Ścieżka do modułu ────────────────────────────────────────────────────────

_STAGING = os.path.join(os.path.dirname(__file__), "..", "core")
if _STAGING not in sys.path:
    sys.path.insert(0, _STAGING)

# Dynamiczny import z lokalizacji staging — nie z zainstalowanego pakietu
import importlib.util as _ilu

_MOD_PATH = os.path.join(_STAGING, "security_hardening.py")
_spec = _ilu.spec_from_file_location("security_hardening", _MOD_PATH)
_mod  = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

G5TransparencyGuard        = _mod.G5TransparencyGuard
_CumulativeViolationCounter = _mod._CumulativeViolationCounter
SecurityHardeningEngine     = _mod.SecurityHardeningEngine


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def fake_redis_server():
    """Jeden serwer fakeredis współdzielony między instancjami w teście."""
    server = fakeredis.FakeServer()
    return server


@pytest.fixture
def redis_client(fake_redis_server):
    """Klient Redis połączony z fake serverem."""
    return fakeredis.FakeRedis(server=fake_redis_server)


def _make_g5_with_redis(fake_redis_server, **kwargs):
    """Fabryka G5 podłączona do tego samego fake Redis servera.

    Defaults override'owalne przez kwargs — brak duplikacji argumentów.
    """
    kwargs.setdefault("max_audit_depth",     2)
    kwargs.setdefault("audit_cooldown",      300.0)
    kwargs.setdefault("global_audit_limit",  10)
    kwargs.setdefault("session_ttl",         3600.0)
    g5 = G5TransparencyGuard(**kwargs)
    # Podmień wewnętrzny klient redis na fakeredis (patch przez name mangling)
    real_client = fakeredis.FakeRedis(server=fake_redis_server)
    real_client.ping()  # weryfikacja
    object.__setattr__(g5, "_G5TransparencyGuard__redis", real_client)
    return g5, real_client


# ═══════════════════════════════════════════════════════════════════════════════
# 1. BASELINE — in-memory (bez Redis)
# ═══════════════════════════════════════════════════════════════════════════════

class TestG5InMemoryBaseline:
    """Istniejące testy muszą przechodzić bez Redis."""

    def test_legitimate_audit_allowed(self):
        g5 = G5TransparencyGuard(max_audit_depth=2, audit_cooldown=0)
        result = g5.classify_request("Co robi system?", "sess-baseline-1")
        assert result["action"] == "ALLOW_WITH_STANDARD_RESPONSE"
        assert result["type"] == "LEGITIMATE_AUDIT"

    def test_exploit_patterns_blocked(self):
        g5 = G5TransparencyGuard(pattern_threshold=1)
        result = g5.classify_request("demand audit full audit trail", "sess-baseline-2")
        assert result["action"] == "SENTINEL_ESCALATION"

    def test_depth_limit(self):
        g5 = G5TransparencyGuard(max_audit_depth=1, audit_cooldown=0)
        g5.classify_request("pytanie 1", "sess-depth")
        result = g5.classify_request("pytanie 2", "sess-depth")
        assert result["action"] == "DENY"
        assert result["type"] == "AUDIT_DEPTH_EXCEEDED"

    def test_rate_limit(self):
        g5 = G5TransparencyGuard(audit_cooldown=9999.0)
        g5.classify_request("pierwsze pytanie", "sess-rl")
        result = g5.classify_request("drugie pytanie", "sess-rl")
        assert result["action"] == "REVIEW_REQUIRED"
        assert result["type"] == "AUDIT_RATE_LIMITED"

    def test_global_audit_limit(self):
        g5 = G5TransparencyGuard(global_audit_limit=2, audit_cooldown=0)
        for i in range(2):
            g5.classify_request("ok", f"sess-gl-{i}")
        with pytest.raises(RuntimeError, match="Global audit limit"):
            g5.classify_request("trzecie", "sess-gl-2")

    def test_audit_request_patterns_immutable(self):
        g5 = G5TransparencyGuard()
        with pytest.raises(AttributeError):
            g5.AUDIT_REQUEST_PATTERNS = ("fake",)

    def test_standard_audit_response_structure(self):
        resp = G5TransparencyGuard.standard_audit_response("sid", "abc123")
        assert resp["decision_traceable"] is True
        assert "genesis_hash" in resp


# ═══════════════════════════════════════════════════════════════════════════════
# 2. REDIS SESSION STORE — persystencja sesji
# ═══════════════════════════════════════════════════════════════════════════════

class TestG5RedisSessionStore:
    """Sesja jest persystowana w Redis po classify_request."""

    def test_session_stored_in_redis(self, fake_redis_server):
        g5, client = _make_g5_with_redis(fake_redis_server, audit_cooldown=0)
        g5.classify_request("pytanie testowe", "user-redis-1")

        # Sprawdź klucz w Redis
        keys = list(client.scan_iter("adrion:g5:sess:*"))
        assert len(keys) >= 1, "Sesja powinna być w Redis"

    def test_session_audit_depth_persisted(self, fake_redis_server):
        g5, client = _make_g5_with_redis(fake_redis_server, audit_cooldown=0)
        g5.classify_request("q1", "user-depth-r")

        key = b"adrion:g5:sess:user-depth-r"
        data = client.hgetall(key)
        assert int(data.get(b"audit_depth", 0)) == 1

    def test_session_last_audit_persisted(self, fake_redis_server):
        g5, client = _make_g5_with_redis(fake_redis_server, audit_cooldown=0)
        before = time.time()
        g5.classify_request("q1", "user-la-r")
        after = time.time()

        key = b"adrion:g5:sess:user-la-r"
        data = client.hgetall(key)
        last_audit = float(data.get(b"last_audit", 0))
        assert before <= last_audit <= after

    def test_session_ttl_set(self, fake_redis_server):
        g5, client = _make_g5_with_redis(fake_redis_server, session_ttl=3600.0, audit_cooldown=0)
        g5.classify_request("q1", "user-ttl-r")

        key = b"adrion:g5:sess:user-ttl-r"
        ttl = client.ttl(key)
        assert 3590 <= ttl <= 3601, f"TTL should be ~3600, got {ttl}"

    def test_session_count_tracked_in_redis(self, fake_redis_server):
        g5, client = _make_g5_with_redis(fake_redis_server, audit_cooldown=0)
        g5.classify_request("q1", "user-cnt-1")
        g5.classify_request("q2", "user-cnt-2")

        count_key = b"adrion:g5:sess_count"
        assert int(client.get(count_key) or 0) == 2


# ═══════════════════════════════════════════════════════════════════════════════
# 3. MULTI-INSTANCE SYNC
# ═══════════════════════════════════════════════════════════════════════════════

class TestG5MultiInstanceSync:
    """Dwie instancje G5 współdzielą stan przez Redis — kluczowy test B5."""

    def test_depth_shared_across_instances(self, fake_redis_server):
        """Instance A zapisuje audit_depth=1 → Instance B widzi depth=1 i blokuje."""
        g5_a, _ = _make_g5_with_redis(fake_redis_server, max_audit_depth=1, audit_cooldown=0)
        g5_b, _ = _make_g5_with_redis(fake_redis_server, max_audit_depth=1, audit_cooldown=0)

        # Instance A obsługuje pierwsze żądanie
        result_a = g5_a.classify_request("pytanie 1", "shared-user")
        assert result_a["action"] == "ALLOW_WITH_STANDARD_RESPONSE"

        # Instance B widzi depth=1 (od A) i blokuje
        result_b = g5_b.classify_request("pytanie 2", "shared-user")
        assert result_b["action"] == "DENY", (
            f"Multi-instance sync failed: B should see depth=1, got {result_b}"
        )
        assert result_b["type"] == "AUDIT_DEPTH_EXCEEDED"

    def test_rate_limit_shared_across_instances(self, fake_redis_server):
        """Instance A ustawia last_audit → Instance B widzi cooldown."""
        g5_a, _ = _make_g5_with_redis(fake_redis_server, audit_cooldown=9999.0)
        g5_b, _ = _make_g5_with_redis(fake_redis_server, audit_cooldown=9999.0)

        # A obsługuje pierwsze żądanie
        result_a = g5_a.classify_request("pierwsze", "rl-shared-user")
        assert result_a["action"] == "ALLOW_WITH_STANDARD_RESPONSE"

        # B powinno zobaczyć rate limit od A
        result_b = g5_b.classify_request("drugie", "rl-shared-user")
        assert result_b["action"] == "REVIEW_REQUIRED", (
            f"B should be rate-limited from A's session, got {result_b}"
        )

    def test_global_limit_shared_across_instances(self, fake_redis_server):
        """Global audit limit egzekwowany atomowo między instancjami."""
        g5_a, _ = _make_g5_with_redis(fake_redis_server, global_audit_limit=3, audit_cooldown=0)
        g5_b, _ = _make_g5_with_redis(fake_redis_server, global_audit_limit=3, audit_cooldown=0)

        # 3 żądania przez A (limit=3)
        for i in range(3):
            g5_a.classify_request("ok", f"sess-gl-multi-{i}")

        # B powinno dostać RuntimeError
        with pytest.raises(RuntimeError, match="Global audit limit"):
            g5_b.classify_request("ponad limit", "sess-gl-multi-extra")

    def test_concurrent_session_creation_safe(self, fake_redis_server):
        """Równoległe tworzenie sesji przez wiele wątków — brak race condition."""
        # global_audit_limit=100 żeby 20 równoległych żądań nie trafiło w limit
        g5, _ = _make_g5_with_redis(fake_redis_server, audit_cooldown=0, global_audit_limit=100)
        results = []
        errors = []

        def classify_worker(i):
            try:
                r = g5.classify_request(f"pytanie {i}", f"concurrent-sess-{i}")
                results.append(r)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=classify_worker, args=(i,)) for i in range(20)]
        for t in threads: t.start()
        for t in threads: t.join()

        assert not errors, f"Errors in concurrent test: {errors}"
        assert len(results) == 20


# ═══════════════════════════════════════════════════════════════════════════════
# 4. GLOBAL LIMIT via Redis INCR
# ═══════════════════════════════════════════════════════════════════════════════

class TestG5RedisGlobalLimit:
    """Atomowy Redis INCR dla global_audit_limit."""

    def test_global_count_in_redis(self, fake_redis_server):
        g5, client = _make_g5_with_redis(fake_redis_server, global_audit_limit=5, audit_cooldown=0)
        for i in range(3):
            g5.classify_request("ok", f"sess-glr-{i}")

        count_key = b"adrion:g5:global_count"
        assert int(client.get(count_key) or 0) == 3

    def test_global_count_decremented_on_limit_exceeded(self, fake_redis_server):
        g5, client = _make_g5_with_redis(fake_redis_server, global_audit_limit=2, audit_cooldown=0)
        g5.classify_request("ok", "sess-gld-0")
        g5.classify_request("ok", "sess-gld-1")

        with pytest.raises(RuntimeError):
            g5.classify_request("over", "sess-gld-2")

        count_key = b"adrion:g5:global_count"
        count = int(client.get(count_key) or 0)
        # Po DECR counter wrócił do 2 (= limit), nie przekroczył
        assert count == 2, f"Counter should be 2 after failed limit, got {count}"

    def test_global_count_ttl_set_on_first_request(self, fake_redis_server):
        g5, client = _make_g5_with_redis(fake_redis_server, global_audit_limit=10, audit_cooldown=0)
        g5.classify_request("ok", "sess-glt-0")

        count_key = b"adrion:g5:global_count"
        ttl = client.ttl(count_key)
        assert 3590 <= ttl <= 3601, f"Global count TTL should be ~3600, got {ttl}"


# ═══════════════════════════════════════════════════════════════════════════════
# 5. FALLBACK IN-MEMORY
# ═══════════════════════════════════════════════════════════════════════════════

class TestG5RedisFallback:
    """Gdy Redis niedostępny — graceful fallback do in-memory."""

    def test_unavailable_redis_falls_back(self):
        """redis_url wskazuje na niedostępny host → fallback in-memory."""
        # G5 przechwytuje ConnectionError/TimeoutError i ustawia __redis = None
        g5 = G5TransparencyGuard(
            redis_url="redis://127.0.0.1:9999",   # port nieużywany
            audit_cooldown=0,
        )
        # __redis powinno być None po nieudanym połączeniu
        redis_attr = object.__getattribute__(g5, "_G5TransparencyGuard__redis")
        assert redis_attr is None, "Redis should be None after failed connection"

        # Mimo to G5 powinno działać (in-memory)
        result = g5.classify_request("pytanie fallback", "sess-fallback-1")
        assert result["action"] == "ALLOW_WITH_STANDARD_RESPONSE"

    def test_no_redis_no_change_in_behavior(self):
        """G5 bez redis_url == G5 z niedostępnym redis — identyczne zachowanie."""
        g5_mem   = G5TransparencyGuard(audit_cooldown=0)
        g5_nordb = G5TransparencyGuard(redis_url=None, audit_cooldown=0)

        r1 = g5_mem.classify_request("pytanie", "s1")
        r2 = g5_nordb.classify_request("pytanie", "s1")

        assert r1["type"]   == r2["type"]
        assert r1["action"] == r2["action"]


# ═══════════════════════════════════════════════════════════════════════════════
# 6. TTL EVICTION
# ═══════════════════════════════════════════════════════════════════════════════

class TestG5RedisTTL:
    """Redis EXPIRE zarządza TTL sesji."""

    def test_session_expires_after_ttl(self, fake_redis_server):
        """Sesja jest przechowywana w Redis z prawidłowym TTL."""
        g5, client = _make_g5_with_redis(fake_redis_server, session_ttl=120.0, audit_cooldown=0)
        g5.classify_request("q1", "ttl-expire-user")

        key = b"adrion:g5:sess:ttl-expire-user"
        assert client.exists(key), "Session should exist in Redis"

        # Weryfikuj TTL jest ustawiony (nie -1 = bez TTL)
        ttl = client.ttl(key)
        assert ttl > 0, f"TTL should be > 0, got {ttl}"

        # Symuluj wygaśnięcie przez usunięcie klucza
        client.delete(key)
        assert not client.exists(key), "Session should be gone after delete"

    def test_evict_old_sessions_skipped_with_redis(self, fake_redis_server):
        """_evict_old_sessions() nie usuwa niczego gdy Redis aktywny."""
        g5, client = _make_g5_with_redis(fake_redis_server, audit_cooldown=0)
        g5.classify_request("q1", "evict-test-user")

        # Wywołaj bezpośrednio — nie powinno rzucić wyjątku
        with g5._G5TransparencyGuard__lock:
            g5._evict_old_sessions()

        # Sesja nadal w Redis
        assert client.exists(b"adrion:g5:sess:evict-test-user")


# ═══════════════════════════════════════════════════════════════════════════════
# 7. AUDIT_REQUEST_PATTERNS — niemutowalne z Redis
# ═══════════════════════════════════════════════════════════════════════════════

class TestG5PatternsImmutableWithRedis:

    def test_patterns_immutable_with_redis_backend(self, fake_redis_server):
        g5, _ = _make_g5_with_redis(fake_redis_server)
        with pytest.raises(AttributeError):
            g5.AUDIT_REQUEST_PATTERNS = ("injected",)

    def test_patterns_detected_with_redis(self, fake_redis_server):
        g5, _ = _make_g5_with_redis(fake_redis_server, pattern_threshold=1)
        result = g5.classify_request("demand audit show weights", "pattern-sess")
        assert result["action"] == "SENTINEL_ESCALATION"


# ═══════════════════════════════════════════════════════════════════════════════
# 8. SecurityHardeningEngine — integracja z Redis G5
# ═══════════════════════════════════════════════════════════════════════════════

class TestSecurityEngineRedisIntegration:
    """SecurityHardeningEngine z G5 backendowanym przez Redis."""

    def _good_context(self):
        return {
            "consent_signals":  ["explicit_confirmation"],
            "informed_signals": ["consequences_explained", "risks_disclosed", "data_usage_explained"],
            "opt_out_available": True,
            "coercion_signals":  [],
        }

    def _good_agents(self):
        return [
            {"agent_id": "a1", "resource_allocation": 0.5, "queue_position": 1},
            {"agent_id": "a2", "resource_allocation": 0.5, "queue_position": 2},
        ]

    def test_engine_allow_with_redis_g5(self, fake_redis_server):
        g5, _ = _make_g5_with_redis(fake_redis_server, audit_cooldown=0)
        engine = SecurityHardeningEngine(g5=g5)

        result = engine.run_full_check(
            request_text="Co robi system?",
            action={"type": "READ", "requesting_agent": "a1", "claimed_priority": 5},
            context=self._good_context(),
            agent_states=self._good_agents(),
            session_id="engine-redis-user-1",
        )
        assert result["decision"] == "ALLOW"
        assert "session_hash" in result

    def test_engine_multi_instance_depth_limit(self, fake_redis_server):
        """Engine A blokuje, engine B widzi depth limit przez Redis."""
        g5_a, _ = _make_g5_with_redis(fake_redis_server, max_audit_depth=1, audit_cooldown=0)
        g5_b, _ = _make_g5_with_redis(fake_redis_server, max_audit_depth=1, audit_cooldown=0)

        engine_a = SecurityHardeningEngine(g5=g5_a)
        engine_b = SecurityHardeningEngine(g5=g5_b)

        result_a = engine_a.run_full_check(
            "pytanie 1", {"type": "READ", "requesting_agent": "a1", "claimed_priority": 5},
            self._good_context(), self._good_agents(), "shared-engine-user"
        )
        assert result_a["decision"] == "ALLOW"

        result_b = engine_b.run_full_check(
            "pytanie 2", {"type": "READ", "requesting_agent": "a1", "claimed_priority": 5},
            self._good_context(), self._good_agents(), "shared-engine-user"
        )
        assert result_b["decision"] == "DENY", (
            f"Engine B should deny due to shared Redis depth limit, got: {result_b}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# 9. CVC — niezależny od Redis G5
# ═══════════════════════════════════════════════════════════════════════════════

class TestCVCIndependentFromRedis:
    """_CumulativeViolationCounter działa niezależnie od Redis G5."""

    def test_cvc_ok_watch_block(self):
        cvc = _CumulativeViolationCounter()
        assert cvc.record("u1", 1) == "OK"
        assert cvc.record("u1", 1) == "OK"
        assert cvc.record("u1", 1) == "WATCH"
        assert cvc.record("u1", 1) == "WATCH"
        assert cvc.record("u1", 1) == "BLOCK"

    def test_cvc_reset(self):
        cvc = _CumulativeViolationCounter()
        cvc.record("u2", 5)
        assert cvc.get_status("u2") == "BLOCK"
        cvc.reset("u2")
        assert cvc.get_status("u2") == "OK"

    def test_cvc_zero_violations_noop(self):
        cvc = _CumulativeViolationCounter()
        assert cvc.record("u3", 0) == "OK"
        assert cvc.get_status("u3") == "OK"

    def test_cvc_with_redis_g5_engine_block(self, fake_redis_server):
        """CVC blokuje po przekroczeniu threshold niezależnie od G5 Redis."""
        g5, _ = _make_g5_with_redis(fake_redis_server, pattern_threshold=1, audit_cooldown=0)
        engine = SecurityHardeningEngine(g5=g5)

        cvc = engine.cvc

        # Wstrzyknij violation_count bezpośrednio do CVC
        cvc.record("cvc-test-user", 3)
        cvc.record("cvc-test-user", 2)
        assert cvc.get_status("cvc-test-user") == "BLOCK"

        result = engine.run_full_check(
            "pytanie", {"type": "READ"}, {}, [], "cvc-test-user"
        )
        assert result["decision"] == "DENY"
        assert result["triggered_by"] == "CVC_BLOCK"


# ═══════════════════════════════════════════════════════════════════════════════
# 10. CVC Redis backend — B6-FIX
# ═══════════════════════════════════════════════════════════════════════════════

class TestCVCRedisBackend:
    """[B6-FIX] _CumulativeViolationCounter z Redis Sorted Set backend."""

    @pytest.fixture
    def cvc_server(self):
        return fakeredis.FakeServer()

    def _make_cvc(self, server, **kwargs):
        """Tworzy CVC z fakeredis podłączonym przez monkey-patch."""
        cvc = _CumulativeViolationCounter(**kwargs)
        # Podmień wewnętrzny klient przez name-mangling
        client = fakeredis.FakeRedis(server=server)
        object.__setattr__(cvc, "_CumulativeViolationCounter__redis", client)
        return cvc, client

    # ── Podstawowe operacje ───────────────────────────────────────────────────

    def test_cvc_redis_ok_watch_block(self, cvc_server):
        """record() zwraca prawidłowy status przez Redis Sorted Set."""
        cvc, _ = self._make_cvc(cvc_server)
        assert cvc.record("r1", 1) == "OK"
        assert cvc.record("r1", 1) == "OK"
        assert cvc.record("r1", 1) == "WATCH"   # 3 naruszenia = WATCH
        assert cvc.record("r1", 1) == "WATCH"
        assert cvc.record("r1", 1) == "BLOCK"   # 5 naruszeń = BLOCK

    def test_cvc_redis_get_status(self, cvc_server):
        """get_status() odczytuje poprawny status z Redis."""
        cvc, _ = self._make_cvc(cvc_server)
        cvc.record("r2", 3)
        assert cvc.get_status("r2") == "WATCH"
        cvc.record("r2", 2)
        assert cvc.get_status("r2") == "BLOCK"

    def test_cvc_redis_reset(self, cvc_server):
        """reset() usuwa klucz Redis (DEL)."""
        cvc, client = self._make_cvc(cvc_server)
        cvc.record("r3", 5)
        assert cvc.get_status("r3") == "BLOCK"
        cvc.reset("r3")
        assert cvc.get_status("r3") == "OK"
        # Klucz powinien być nieobecny w Redis
        assert client.exists(b"adrion:cvc:cvc:r3") == 0

    def test_cvc_redis_zero_noop(self, cvc_server):
        """record(session, 0) nie tworzy żadnego wpisu w Redis."""
        cvc, client = self._make_cvc(cvc_server)
        result = cvc.record("r4", 0)
        assert result == "OK"
        assert client.exists(b"adrion:cvc:cvc:r4") == 0

    # ── Multi-instance sync ───────────────────────────────────────────────────

    def test_cvc_redis_multi_instance_sync(self, cvc_server):
        """Dwa CVC instancje współdzielą okno przez ten sam Redis server."""
        cvc_a, _ = self._make_cvc(cvc_server)
        cvc_b, _ = self._make_cvc(cvc_server)

        # Instancja A rejestruje 4 naruszenia
        cvc_a.record("shared-user", 4)
        # Instancja B widzi stan (już WATCH)
        assert cvc_b.get_status("shared-user") == "WATCH"
        # Instancja B dodaje 1 → BLOCK
        assert cvc_b.record("shared-user", 1) == "BLOCK"
        # Instancja A też widzi BLOCK
        assert cvc_a.get_status("shared-user") == "BLOCK"

    def test_cvc_redis_ttl_set(self, cvc_server):
        """Redis key ma ustawiony TTL po operacji record."""
        cvc, client = self._make_cvc(cvc_server)
        cvc.record("ttl-user", 1)
        key = b"adrion:cvc:cvc:ttl-user"
        ttl = client.ttl(key)
        # TTL = WINDOW_HOURS * 3600 + 3600 = 25 * 3600 = 90000s
        assert ttl > 0, f"TTL should be > 0, got {ttl}"
        assert ttl <= 90000, f"TTL should be <= 90000s, got {ttl}"

    # ── Fallback ──────────────────────────────────────────────────────────────

    def test_cvc_redis_fallback_on_unavailable(self):
        """Niedostępny Redis → __redis=None → in-memory fallback."""
        cvc = _CumulativeViolationCounter(redis_url="redis://127.0.0.1:9998")
        redis_attr = object.__getattribute__(cvc, "_CumulativeViolationCounter__redis")
        assert redis_attr is None, "Should fallback to None on unavailable Redis"
        # In-memory nadal działa
        assert cvc.record("fallback-user", 3) == "WATCH"
        assert cvc.get_status("fallback-user") == "WATCH"

    # ── Engine integration ────────────────────────────────────────────────────

    def test_engine_cvc_redis_blocks_via_engine(self, cvc_server):
        """SecurityHardeningEngine blokuje przez CVC Redis po przekroczeniu BLOCK."""
        engine = SecurityHardeningEngine()
        cvc = engine.cvc
        # Podmień redis w CVC engine na fakeredis
        client = fakeredis.FakeRedis(server=cvc_server)
        object.__setattr__(cvc, "_CumulativeViolationCounter__redis", client)

        cvc.record("engine-cvc-user", 5)  # BLOCK threshold
        assert cvc.get_status("engine-cvc-user") == "BLOCK"

        result = engine.run_full_check(
            "pytanie", {"type": "READ"}, {}, [], "engine-cvc-user"
        )
        assert result["decision"] == "DENY"
        assert result["triggered_by"] == "CVC_BLOCK"
