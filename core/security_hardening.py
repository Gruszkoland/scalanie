"""
ADRION 369 — Security Hardening Core v5.6
==========================================
Changelog v5.6:
  [G5-3.2]  AUDIT_REQUEST_PATTERNS — class-level frozenset+tuple, blokada nadpisania na instancji
  [G5-3.3]  Semantyczne wzorce — dodano synonimy PL/EN nieobecne wcześniej
  [G5-3.4]  Normalizacja whitespace w tekście przed pattern matching
  [B5-FIX]  Opcjonalny backend Redis dla G5TransparencyGuard — sync sesji
            w deploymencie multi-instance (redis_url, redis_prefix params)
  [B6-FIX]  Opcjonalny backend Redis dla _CumulativeViolationCounter — Sorted Set
            per session, zsynchronizowane okno 24h w deploymencie multi-instance
  [G7-4.1]  Progi G7 jako właściwości z __slots__ — niemutowalne po init
  [G7-4.4]  _assess_action_risk z non-dict action → 0.1 (brak crash)
  [G8-5.2]  Deterministyczny sort tie-break: (queue_position, agent_id)
  [G8-5.3]  claimed_priority=None → traktowane jako base (brak abuse)
  [G8-5.4]  Walidacja konfiguracji G8 — fair_share_min ∈ [0,1]
  [BIZ-7.2] BYPASS/WIPE w HIGH_RISK_ACTION_TYPES
  [BIZ-7.4] Szkielet CVC (Cumulative Violation Counter) w SecurityHardeningEngine
  [SE-6.2]  session_id nie echowane w odpowiedzi ALLOW
  [SE-6.2]  session_id hashowany w odpowiedzi zamiast surowego
"""

import re
import math
import time
import uuid
import threading
import hashlib
import statistics
import logging
from types import MappingProxyType
from typing import Any, Dict, Optional, Tuple

_log = logging.getLogger(__name__)

# ── Stałe globalne G5 ────────────────────────────────────────────────────────

_G5_PATTERNS: Tuple[str, ...] = (
    # Polskie — oryginalne
    "żądam audytu", "żądam audit", "żądam ujawnienia",
    "ujawnij architekture", "ujawnij architekturę",
    "pelny audit trail", "pełny audit trail",
    "wyjasnij wagi", "wyjaśnij wagi",
    "zgodnie z g5", "zadam ujawnienia",
    # Angielskie — oryginalne
    "demand audit", "reveal architecture", "full audit trail",
    "explain weights", "glass-box compliance", "transparency compliance",
    "reasoning >=20", "reasoning >= 20",
    # [G5-3.3] Nowe semantyczne synonimy PL
    "pełny wgląd w architekturę", "pelny wglad w architekture",
    "pokaż reguły", "pokaz reguly", "pokaż wagi", "pokaz wagi",
    "ujawnij reguły", "ujawnij reguly",
    "jak działa system decyzyjny", "jak dziala system decyzyjny",
    "chcę zobaczyć reguły", "chce zobaczyc reguly",
    "wgląd w system", "wglad w system",
    # [G5-3.3] Nowe semantyczne synonimy EN
    "show weights", "show thresholds", "show rules",
    "system internals", "full system", "internal architecture",
    "reveal rules", "reveal weights", "reveal thresholds",
    "give me the rules", "expose architecture",
)

_SESSION_ID_RE = re.compile(r'^[\w.\-]{1,256}$', re.UNICODE)

# [G5-3.4] Normalizacja whitespace
_WS_RE = re.compile(r'\s+')

def _normalize_text(text: str) -> str:
    """Normalizuje whitespace przed pattern matching."""
    return _WS_RE.sub(' ', text.strip()).lower()

def _sanitize_session_id(sid: object) -> str:
    if sid is None:
        raise ValueError("session_id cannot be None")
    sid_str = str(sid)
    if not sid_str:
        raise ValueError("session_id cannot be empty")
    if not _SESSION_ID_RE.match(sid_str):
        cleaned = re.sub(r'[^\w.\-]', '_', sid_str, flags=re.UNICODE)[:256]
        if not cleaned:
            raise ValueError(f"session_id invalid after sanitization")
        return cleaned
    return sid_str

def _hash_session_id(sid: str) -> str:
    """[SE-6.2] Hash session_id przed zwróceniem w odpowiedzi."""
    return hashlib.sha256(sid.encode()).hexdigest()[:16]

# ── Stałe G7 ─────────────────────────────────────────────────────────────────

# [BIZ-7.2] Rozszerzona lista — BYPASS i WIPE były pominięte jako non-blocking
_HIGH_RISK_ACTION_TYPES: frozenset = frozenset({
    "DELETE", "EXPORT", "MODIFY_ALL", "ADMIN", "WIPE",
    "DROP", "TRUNCATE", "OVERRIDE", "BYPASS", "ESCALATE",
    "PURGE", "DESTROY", "RESET", "REVOKE", "IMPERSONATE",
})

def _assess_action_risk(action) -> float:
    """[G7-4.4] Obsługuje non-dict action gracefully."""
    if not isinstance(action, dict):
        return 0.1
    raw = str(action.get("type", "")).upper().strip()
    if not raw:
        return 0.1
    words = re.split(r'[\s_()[\]]+', raw)
    return 0.9 if any(w in _HIGH_RISK_ACTION_TYPES for w in words if w) else 0.1

# ── Niemutowalne wyniki ───────────────────────────────────────────────────────

class _ImmutableResult:
    __slots__ = ()
    def __setattr__(self, n, v): raise AttributeError(f"{type(self).__name__} is immutable")
    def __delattr__(self, n):    raise AttributeError(f"{type(self).__name__} is immutable")
    def __reduce__(self):        raise TypeError(f"{type(self).__name__} no pickle")
    def __reduce_ex__(self, p):  raise TypeError(f"{type(self).__name__} no pickle")

class G7Result(_ImmutableResult):
    __slots__ = ("_compliant","_scores","_decision","_violations")
    def __init__(self, compliant, scores, decision, violations):
        object.__setattr__(self,"_compliant", bool(compliant))
        object.__setattr__(self,"_scores",    tuple(scores))
        object.__setattr__(self,"_decision",  str(decision))
        object.__setattr__(self,"_violations",tuple(violations))
    @property
    def compliant(self):  return object.__getattribute__(self,"_compliant")
    @property
    def scores(self):     return object.__getattribute__(self,"_scores")
    @property
    def decision(self):   return object.__getattribute__(self,"_decision")
    @property
    def violations(self): return object.__getattribute__(self,"_violations")
    def scores_dict(self): return dict(self.scores)
    @staticmethod
    def from_dicts(c, s, d, v):
        return G7Result(c, tuple(sorted(s.items())), d, tuple(v))

class G8Result(_ImmutableResult):
    __slots__ = ("_compliant","_scores","_decision","_violations")
    def __init__(self, compliant, scores, decision, violations):
        object.__setattr__(self,"_compliant", bool(compliant))
        object.__setattr__(self,"_scores",    tuple(scores))
        object.__setattr__(self,"_decision",  str(decision))
        object.__setattr__(self,"_violations",tuple(violations))
    @property
    def compliant(self):  return object.__getattribute__(self,"_compliant")
    @property
    def scores(self):     return object.__getattribute__(self,"_scores")
    @property
    def decision(self):   return object.__getattribute__(self,"_decision")
    @property
    def violations(self): return object.__getattribute__(self,"_violations")
    def scores_dict(self): return dict(self.scores)
    @staticmethod
    def from_dicts(c, s, d, v):
        return G8Result(c, tuple(sorted(s.items())), d, tuple(v))

# ── G5TransparencyGuard ───────────────────────────────────────────────────────

class _G5Meta(type):
    """[PY1d] Blokuje podklasowanie G5TransparencyGuard."""
    def __new__(mcs, name, bases, ns):
        if bases and any(b.__name__ == "G5TransparencyGuard" for b in bases):
            raise TypeError(f"Subclassing G5TransparencyGuard is forbidden. Attempted: '{name}'")
        return super().__new__(mcs, name, bases, ns)


class G5TransparencyGuard(metaclass=_G5Meta):
    """v5.6: normalizacja whitespace, rozszerzone wzorce semantyczne."""

    # [G5-3.2] Tuple jako class attr — niemutowalna; blokujemy nadpisanie przez __setattr__
    AUDIT_REQUEST_PATTERNS: Tuple[str, ...] = _G5_PATTERNS

    def __setattr__(self, name, value):
        # Blokuj nadpisanie AUDIT_REQUEST_PATTERNS na instancji
        if name == "AUDIT_REQUEST_PATTERNS":
            raise AttributeError("AUDIT_REQUEST_PATTERNS is read-only")
        object.__setattr__(self, name, value)

    def __init__(
        self,
        max_audit_depth:     int   = 2,
        audit_cooldown:      float = 300.0,
        pattern_threshold:   int   = 3,
        max_global_sessions: int   = 10_000,
        session_ttl:         float = 3_600.0,
        global_audit_limit:  int   = 100,
        redis_url:           Optional[str] = None,
        redis_prefix:        str   = "adrion:g5:",
    ) -> None:
        self.__config: MappingProxyType = MappingProxyType({
            "max_audit_depth":     max_audit_depth,
            "audit_cooldown":      audit_cooldown,
            "pattern_threshold":   pattern_threshold,
            "max_global_sessions": max_global_sessions,
            "session_ttl":         session_ttl,
            "global_audit_limit":  global_audit_limit,
        })
        self.__sessions: Dict[str, dict] = {}
        self.__lock = threading.RLock()
        self.__global_count: int = 0
        self.__window_start: float = time.time()
        # [B5-FIX] Optional Redis backend for multi-instance session synchronization
        self.__redis: Optional[Any] = None
        self.__redis_prefix: str = redis_prefix
        if redis_url:
            try:
                import redis as _redis  # type: ignore[import]
                client = _redis.from_url(redis_url, socket_connect_timeout=2)
                client.ping()
                self.__redis = client
                _log.info("G5TransparencyGuard: Redis backend connected at %s", redis_url)
            except Exception as exc:  # pragma: no cover
                _log.warning(
                    "G5TransparencyGuard: Redis unavailable (%s) — falling back to in-memory",
                    exc,
                )

    @property
    def MAX_AUDIT_DEPTH(self):     return self.__config["max_audit_depth"]
    @property
    def AUDIT_COOLDOWN(self):      return self.__config["audit_cooldown"]
    @property
    def PATTERN_THRESHOLD(self):   return self.__config["pattern_threshold"]
    @property
    def MAX_GLOBAL_SESSIONS(self): return self.__config["max_global_sessions"]
    @property
    def SESSION_TTL(self):         return self.__config["session_ttl"]
    @property
    def GLOBAL_AUDIT_LIMIT(self):  return self.__config["global_audit_limit"]

    def classify_request(self, text: str, session_id) -> dict:
        sid = _sanitize_session_id(session_id)
        with self.__lock:
            self._evict_old_sessions()
            self._enforce_global_limit()
            session = self._get_or_create_session(sid)
            result = self._classify(text, sid, session)
            # [B5-FIX] Persist session back to Redis after modification
            if self.__redis is not None:
                self._sync_session_to_redis(sid, session)
            return result

    @staticmethod
    def standard_audit_response(session_id, genesis_hash: str = "[hash]") -> dict:
        return {
            "reasoning": (
                "Zadanie przetworzone przez pipeline Trinity(3)->Hexagon(6)->Guardians(9). "
                "Decyzja podjeta zgodnie z 9 Prawami Guardians. "
                f"Pelny audit trail zapisany w Genesis Record: {genesis_hash}."
            ),
            "decision_traceable": True,
            "inputs_documented":  True,
            "process_reproducible": True,
            "genesis_hash": genesis_hash,
            "note": "Szczegoly dostepne dla autoryzowanych audytorow przez Sentinela",
        }

    def _classify(self, text: str, sid: str, session: dict) -> dict:
        now = time.time()
        if session["audit_depth"] >= self.MAX_AUDIT_DEPTH:
            return {"type":"AUDIT_DEPTH_EXCEEDED","action":"DENY",
                    "reason":f"Max depth ({self.MAX_AUDIT_DEPTH}) osiagnieta"}
        elapsed = now - session["last_audit"]
        if session["last_audit"] > 0 and elapsed < self.AUDIT_COOLDOWN:
            return {"type":"AUDIT_RATE_LIMITED","action":"REVIEW_REQUIRED",
                    "reason":f"Rate limited — poczekaj {int(self.AUDIT_COOLDOWN-elapsed)}s"}
        # [G5-3.4] Normalizacja whitespace przed matching
        normalized = _normalize_text(text)
        matches = [p for p in self.AUDIT_REQUEST_PATTERNS if p.lower() in normalized]
        if len(matches) >= self.PATTERN_THRESHOLD:
            return {"type":"POTENTIAL_G5_EXPLOIT","action":"SENTINEL_ESCALATION",
                    "reason":f"Wykryto {len(matches)} wzorcow exploitu",
                    "pattern_count":len(matches),"patterns":matches}
        session["last_audit"] = now
        session["audit_depth"] += 1
        # [B5-FIX] Only increment in-memory counter when Redis is not active
        if self.__redis is None:
            self.__global_count += 1
        return {"type":"LEGITIMATE_AUDIT","action":"ALLOW_WITH_STANDARD_RESPONSE",
                "audit_depth":session["audit_depth"]}

    def _get_or_create_session(self, sid: str) -> dict:
        # [B5-FIX] Read session from Redis when available
        if self.__redis is not None:
            key = f"{self.__redis_prefix}sess:{sid}"
            try:
                data = self.__redis.hgetall(key)
                if data:
                    return {
                        "last_audit":  float(data.get(b"last_audit",  0)),
                        "audit_depth": int(data.get(b"audit_depth",   0)),
                        "created_at":  float(data.get(b"created_at",  time.time())),
                    }
                # New session — check global session count
                count_key = f"{self.__redis_prefix}sess_count"
                count = self.__redis.incr(count_key)
                if count > self.MAX_GLOBAL_SESSIONS:
                    self.__redis.decr(count_key)
                    raise RuntimeError(
                        f"G5: Max sessions ({self.MAX_GLOBAL_SESSIONS}) reached."
                    )
                now = time.time()
                self.__redis.hset(key, mapping={
                    "last_audit":  0.0,
                    "audit_depth": 0,
                    "created_at":  now,
                })
                self.__redis.expire(key, int(self.SESSION_TTL))
                return {"last_audit": 0.0, "audit_depth": 0, "created_at": now}
            except RuntimeError:
                raise
            except Exception as exc:
                _log.warning("G5 Redis get_session error (%s) — using in-memory", exc)
                # Fall through to in-memory
        # in-memory path
        if sid not in self.__sessions:
            if len(self.__sessions) >= self.MAX_GLOBAL_SESSIONS:
                raise RuntimeError(f"G5: Max sessions ({self.MAX_GLOBAL_SESSIONS}) reached.")
            self.__sessions[sid] = {"last_audit":0.0,"audit_depth":0,"created_at":time.time()}
        return self.__sessions[sid]

    def _evict_old_sessions(self) -> None:
        # [B5-FIX] Redis EXPIRE handles TTL automatically; skip in-memory eviction
        if self.__redis is not None:
            return
        now = time.time()
        ttl = self.SESSION_TTL
        expired = [sid for sid, d in self.__sessions.items()
                   if now - d.get("last_audit", d.get("created_at", 0)) > ttl]
        for sid in expired:
            del self.__sessions[sid]


    def _sync_session_to_redis(self, sid: str, session: dict) -> None:
        """[B5-FIX] Persist in-memory session state to Redis after modification."""
        key = f"{self.__redis_prefix}sess:{sid}"
        try:
            self.__redis.hset(key, mapping={
                "last_audit":  session["last_audit"],
                "audit_depth": session["audit_depth"],
                "created_at":  session["created_at"],
            })
            self.__redis.expire(key, int(self.SESSION_TTL))
        except Exception as exc:
            _log.warning("G5 Redis sync_session error (%s) — state not persisted", exc)
    def _enforce_global_limit(self) -> None:
        # [B5-FIX] Use Redis atomic INCR for global limit in multi-instance deployments
        if self.__redis is not None:
            count_key = f"{self.__redis_prefix}global_count"
            try:
                count = self.__redis.incr(count_key)
                if count == 1:
                    # First request in window — set 1-hour expiry
                    self.__redis.expire(count_key, 3600)
                if count > self.GLOBAL_AUDIT_LIMIT:
                    self.__redis.decr(count_key)
                    raise RuntimeError("G5: Global audit limit exceeded.")
                return
            except RuntimeError:
                raise
            except Exception as exc:
                _log.warning("G5 Redis enforce_global_limit error (%s) — using in-memory", exc)
                # Fall through to in-memory
        now = time.time()
        if now - self.__window_start > 3600.0:
            self.__global_count = 0
            self.__window_start = now
        if self.__global_count >= self.GLOBAL_AUDIT_LIMIT:
            raise RuntimeError("G5: Global audit limit exceeded.")

    def _test_get_session_depth(self, sid: str) -> int:
        with self.__lock:
            return self.__sessions.get(_sanitize_session_id(sid), {}).get("audit_depth", 0)

    def _test_reset_session_time(self, sid: str) -> None:
        import time as _t
        with self.__lock:
            s = _sanitize_session_id(sid)
            if s in self.__sessions:
                self.__sessions[s]["last_audit"] = (
                    _t.time() - self.__config["audit_cooldown"] - 1.0
                )

# ── G7PrivacyEvaluator — v5.6 ────────────────────────────────────────────────

class G7PrivacyEvaluator:
    """
    v5.6: Progi jako __slots__ properties — niemutowalne po init.
    """
    __slots__ = ("__cfg",)

    def __init__(
        self,
        consent_score_min:     float = 0.95,
        informed_score_min:    float = 0.90,
        coercion_score_max:    float = 0.05,
        high_risk_consent_min: float = 0.98,
    ) -> None:
        object.__setattr__(self, "_G7PrivacyEvaluator__cfg", MappingProxyType({
            "consent_min":     consent_score_min,
            "informed_min":    informed_score_min,
            "coercion_max":    coercion_score_max,
            "high_risk_min":   high_risk_consent_min,
        }))

    @property
    def CONSENT_SCORE_MIN(self)     -> float: return self.__cfg["consent_min"]
    @property
    def INFORMED_SCORE_MIN(self)    -> float: return self.__cfg["informed_min"]
    @property
    def COERCION_SCORE_MAX(self)    -> float: return self.__cfg["coercion_max"]
    @property
    def HIGH_RISK_CONSENT_MIN(self) -> float: return self.__cfg["high_risk_min"]

    def __setattr__(self, name, value):
        raise AttributeError("G7PrivacyEvaluator is immutable after init")

    def evaluate(self, action, context: dict) -> G7Result:
        if not isinstance(context, dict):
            context = {}
        scores = {
            "consent":  self._score_consent(context),
            "informed": self._score_informed(context),
            "opt_out":  1.0 if context.get("opt_out_available") else 0.0,
            "coercion": self._score_coercion(context),
        }
        violations: list = []
        action_risk  = _assess_action_risk(action)
        is_high_risk = action_risk > 0.8
        eff_min      = self.HIGH_RISK_CONSENT_MIN if is_high_risk else self.CONSENT_SCORE_MIN
        consent_ok   = scores["consent"] >= eff_min
        if not consent_ok:
            if is_high_risk:
                atype = action.get("type","UNKNOWN") if isinstance(action,dict) else "UNKNOWN"
                violations.append(
                    f"high_risk_action:{atype} wymaga consent>={self.HIGH_RISK_CONSENT_MIN}, "
                    f"got={scores['consent']:.3f}"
                )
            else:
                violations.append(f"consent_score={scores['consent']:.3f} < {self.CONSENT_SCORE_MIN}")
        if scores["informed"] < self.INFORMED_SCORE_MIN:
            violations.append(f"informed_score={scores['informed']:.3f} < {self.INFORMED_SCORE_MIN}")
        if scores["opt_out"] < 1.0:
            violations.append("opt_out_unavailable")
        if scores["coercion"] > self.COERCION_SCORE_MAX:
            violations.append(f"coercion_score={scores['coercion']:.3f} > {self.COERCION_SCORE_MAX}")
        compliant = len(violations) == 0
        return G7Result.from_dicts(compliant, scores,
                                   "PASS" if compliant else "DENY_IMMEDIATELY", violations)

    def _score_consent(self, ctx):
        sigs = ctx.get("consent_signals") or []
        if not isinstance(sigs,(list,tuple,set)): sigs=[]
        sigs = [s for s in sigs if isinstance(s,str)]
        if "explicit_confirmation" in sigs: return 1.00
        if "written_agreement"     in sigs: return 0.98
        if "tos_acceptance"        in sigs: return 0.70
        if "implicit_context"      in sigs: return 0.40
        return 0.00

    def _score_informed(self, ctx):
        sigs = ctx.get("informed_signals") or []
        if not isinstance(sigs,(list,tuple,set)): sigs=[]
        sigs = [s for s in sigs if isinstance(s,str)]
        sc = 0.0
        if "consequences_explained" in sigs: sc += 0.50
        if "risks_disclosed"        in sigs: sc += 0.30
        if "data_usage_explained"   in sigs: sc += 0.20
        return min(sc, 1.0)

    def _score_coercion(self, ctx):
        sigs = ctx.get("coercion_signals") or []
        if not isinstance(sigs,(list,tuple,set)): sigs=[]
        sigs = [s for s in sigs if isinstance(s,str)]
        sc = 0.0
        if "urgency_pressure"       in sigs: sc += 0.40
        if "no_alternative_offered" in sigs: sc += 0.30
        if "threat_implied"         in sigs: sc += 0.30
        return min(sc, 1.0)

# ── G8NonmaleficenceEvaluator — v5.6 ─────────────────────────────────────────

class G8NonmaleficenceEvaluator:
    """
    v5.6: deterministyczny sort, claimed_priority=None, walidacja konfiguracji.
    """
    __slots__ = ("__cfg",)

    def __init__(
        self,
        fair_share_min:        float = 0.90,
        resource_variance_max: float = 0.15,
        starvation_threshold:  float = 0.10,
        min_agents:            int   = 2,
    ) -> None:
        # [G8-5.4] Walidacja konfiguracji
        if not (0.0 <= fair_share_min <= 1.0):
            raise ValueError(f"fair_share_min must be in [0,1], got {fair_share_min}")
        if not (0.0 <= resource_variance_max):
            raise ValueError(f"resource_variance_max must be >= 0, got {resource_variance_max}")
        if not (0.0 <= starvation_threshold <= 1.0):
            raise ValueError(f"starvation_threshold must be in [0,1], got {starvation_threshold}")
        if min_agents < 2:
            raise ValueError(f"min_agents must be >= 2, got {min_agents}")
        object.__setattr__(self, "_G8NonmaleficenceEvaluator__cfg", MappingProxyType({
            "fair_share_min":        fair_share_min,
            "resource_variance_max": resource_variance_max,
            "starvation_threshold":  starvation_threshold,
            "min_agents":            min_agents,
        }))

    @property
    def FAIR_SHARE_MIN(self):        return self.__cfg["fair_share_min"]
    @property
    def RESOURCE_VARIANCE_MAX(self): return self.__cfg["resource_variance_max"]
    @property
    def STARVATION_THRESHOLD(self):  return self.__cfg["starvation_threshold"]
    @property
    def MIN_AGENTS(self):            return self.__cfg["min_agents"]

    def __setattr__(self, name, value):
        raise AttributeError("G8NonmaleficenceEvaluator is immutable after init")

    def evaluate(self, action, agent_states) -> G8Result:
        if not isinstance(agent_states, (list, tuple)):
            agent_states = []
        valid = [a for a in agent_states if isinstance(a, dict)]
        violations = []
        if len(valid) < self.MIN_AGENTS:
            violations.append(
                f"insufficient_agent_context: {len(valid)} agents (min {self.MIN_AGENTS})")
            return G8Result.from_dicts(
                False, {"fair_share":0.0,"queue_jump":0.0,"priority_abuse":0.0,"starvation":0.0},
                "DENY_IMMEDIATELY", violations)

        alloc = [a.get("resource_allocation", 0.0) for a in valid]
        alloc = [float(x) if isinstance(x,(int,float)) and not (math.isnan(float(x)) or math.isinf(float(x))) else 0.0
                 for x in alloc]

        scores = {
            "fair_share":     self._fair_share(alloc),
            "queue_jump":     float(self._queue_jump(action, valid)),
            "priority_abuse": float(self._priority_abuse(action, valid)),
            "starvation":     float(self._starvation(alloc)),
        }
        if scores["fair_share"] < self.FAIR_SHARE_MIN:
            violations.append(f"fair_share={scores['fair_share']:.3f} < {self.FAIR_SHARE_MIN}")
        if scores["queue_jump"]     > 0: violations.append("queue_jump_detected")
        if scores["priority_abuse"] > 0: violations.append("priority_abuse_detected")
        if scores["starvation"]     > 0: violations.append("agent_starvation_detected")
        compliant = not violations
        return G8Result.from_dicts(compliant, scores,
                                   "PASS" if compliant else "DENY_IMMEDIATELY", violations)

    def _fair_share(self, alloc):
        total = sum(alloc)
        if not alloc or total == 0: return 0.0
        try:
            var = statistics.variance(alloc) if len(alloc) > 1 else 0.0
        except statistics.StatisticsError:
            var = 0.0
        if var > self.RESOURCE_VARIANCE_MAX:
            return max(0.0, 1.0 - var / self.RESOURCE_VARIANCE_MAX)
        return 1.0

    def _queue_jump(self, action, agents) -> bool:
        req = action.get("requesting_agent") if isinstance(action, dict) else None
        if req is None or req == "" or not agents:
            return False
        # [G8-5.2] Deterministyczny sort: tie-break przez agent_id
        sorted_a = sorted(agents, key=lambda x: (
            x.get("queue_position") is None,
            x.get("queue_position") if x.get("queue_position") is not None else 99,
            str(x.get("agent_id", ""))
        ))
        first = sorted_a[0].get("agent_id") if sorted_a else None
        return req != first

    def _priority_abuse(self, action, agents) -> bool:
        if not isinstance(action, dict): return False
        req_id  = action.get("requesting_agent")
        agent   = next((a for a in agents if a.get("agent_id") == req_id), {})
        base    = agent.get("base_priority", 5)
        claimed = action.get("claimed_priority", base)
        # [G8-5.3] claimed_priority=None → traktuj jak base (brak abuse)
        if claimed is None:
            return False
        try:
            return float(claimed) >= float(base) + 2
        except (TypeError, ValueError):
            return False

    def _starvation(self, alloc) -> bool:
        return any(a < self.STARVATION_THRESHOLD for a in alloc)

# ── CVC — Cumulative Violation Counter ────────────────────────────────────────

class _CumulativeViolationCounter:
    """[BIZ-7.4 / B6-FIX] CVC chroniący przed salami slicing.

    Gdy redis_url podano: naruszenia przechowywane w Redis Sorted Set
    (score = Unix timestamp, member = uuid). Okno 24h synchronizowane
    między instancjami. Fallback do in-memory przy braku połączenia.
    """

    WINDOW_HOURS:    int = 24
    WATCH_THRESHOLD: int = 3
    BLOCK_THRESHOLD: int = 5

    def __init__(
        self,
        redis_url: Optional[str] = None,
        redis_prefix: str = "adrion:cvc:",
    ) -> None:
        self.__counts: Dict[str, list] = {}   # session_id → [timestamps]
        self.__lock = threading.RLock()
        self.__redis: Optional[Any] = None
        self.__redis_prefix: str = redis_prefix
        if redis_url:
            try:
                import redis as _redis
                client = _redis.from_url(redis_url, socket_connect_timeout=2)
                client.ping()
                self.__redis = client
                _log.info("CVC: Redis backend aktywny (%s)", redis_url)
            except Exception as exc:
                _log.warning(
                    "CVC: Redis niedostępny (%s) — fallback in-memory", exc
                )

    # ── helpers ──────────────────────────────────────────────────────────────

    def _rkey(self, session_id: str) -> str:
        return f"{self.__redis_prefix}cvc:{session_id}"

    def _redis_status(self, card: int) -> str:
        if card >= self.BLOCK_THRESHOLD: return "BLOCK"
        if card >= self.WATCH_THRESHOLD: return "WATCH"
        return "OK"

    # ── public API ────────────────────────────────────────────────────────────

    def record(self, session_id: str, violation_count: int) -> str:
        """Rejestruje naruszenia. Zwraca: 'OK' | 'WATCH' | 'BLOCK'."""
        if violation_count == 0:
            return "OK"
        now = time.time()
        cutoff = now - self.WINDOW_HOURS * 3600

        if self.__redis is not None:
            try:
                key = self._rkey(session_id)
                # Dodaj violation_count memberów z timestamp jako score
                mapping = {str(uuid.uuid4()): now for _ in range(violation_count)}
                pipe = self.__redis.pipeline()
                pipe.zadd(key, mapping)
                pipe.zremrangebyscore(key, 0, cutoff)
                pipe.zcard(key)
                pipe.expire(key, self.WINDOW_HOURS * 3600 + 3600)
                results = pipe.execute()
                card = results[2]  # wynik ZCARD
                return self._redis_status(card)
            except Exception as exc:
                _log.warning("CVC.record: Redis error (%s) — fallback", exc)

        # In-memory path
        with self.__lock:
            history = self.__counts.setdefault(session_id, [])
            history.extend([now] * violation_count)
            self.__counts[session_id] = [t for t in history if t > cutoff]
            total = len(self.__counts[session_id])
        return self._redis_status(total)

    def get_status(self, session_id: str) -> str:
        now = time.time()
        cutoff = now - self.WINDOW_HOURS * 3600

        if self.__redis is not None:
            try:
                key = self._rkey(session_id)
                pipe = self.__redis.pipeline()
                pipe.zremrangebyscore(key, 0, cutoff)
                pipe.zcard(key)
                results = pipe.execute()
                return self._redis_status(results[1])
            except Exception as exc:
                _log.warning("CVC.get_status: Redis error (%s) — fallback", exc)

        # In-memory path
        with self.__lock:
            history = [t for t in self.__counts.get(session_id, []) if t > cutoff]
            total = len(history)
        return self._redis_status(total)

    def reset(self, session_id: str) -> None:
        if self.__redis is not None:
            try:
                self.__redis.delete(self._rkey(session_id))
                return
            except Exception as exc:
                _log.warning("CVC.reset: Redis error (%s) — fallback", exc)

        with self.__lock:
            self.__counts.pop(session_id, None)

# ── SecurityHardeningEngine — v5.6 ───────────────────────────────────────────

_HIGH_SEVERITY:    frozenset = frozenset({"HIGH","CRITICAL"})
_VALID_SEVERITIES: frozenset = frozenset({"LOW","MEDIUM","HIGH","CRITICAL"})


class SecurityHardeningEngine:
    """
    v5.6: CVC zintegrowany, session_id hashowany w odpowiedzi,
    wszystkie None inputs obsługiwane, monkeypatch zablokowany przez __slots__.
    """
    __slots__ = ("__g5","__g7","__g8","__cvc")

    def __init__(self, g5=None, g7=None, g8=None, cvc_redis_url: Optional[str] = None) -> None:
        object.__setattr__(self,"_SecurityHardeningEngine__g5", g5 or G5TransparencyGuard())
        object.__setattr__(self,"_SecurityHardeningEngine__g7", g7 or G7PrivacyEvaluator())
        object.__setattr__(self,"_SecurityHardeningEngine__g8", g8 or G8NonmaleficenceEvaluator())
        object.__setattr__(self,"_SecurityHardeningEngine__cvc", _CumulativeViolationCounter(redis_url=cvc_redis_url))

    def __setattr__(self, n, v): raise AttributeError("SecurityHardeningEngine is immutable after init")
    def __delattr__(self, n):    raise AttributeError("SecurityHardeningEngine is immutable after init")

    @property
    def g5_guard(self): return self.__g5
    @property
    def g7_eval(self):  return self.__g7
    @property
    def g8_eval(self):  return self.__g8
    @property
    def cvc(self):      return self.__cvc

    def run_full_check(
        self,
        request_text,
        action,
        context,
        agent_states,
        session_id,
        severity=None,
    ) -> dict:
        # Normalize severity
        if not isinstance(severity, str) or not severity:
            severity = "MEDIUM"
        sev = severity.strip().upper()
        if sev not in _VALID_SEVERITIES:
            sev = "MEDIUM"

        # Sanitize session_id
        try:
            sid = _sanitize_session_id(session_id)
        except ValueError as e:
            return {"decision":"DENY","triggered_by":"INVALID_SESSION_ID",
                    "reason":str(e),"details":{}}

        # [BIZ-7.4] Sprawdź CVC przed dalszą weryfikacją
        cvc_status = self.__cvc.get_status(sid)
        if cvc_status == "BLOCK":
            return {"decision":"DENY","triggered_by":"CVC_BLOCK",
                    "reason":"Cumulative violation limit exceeded (salami slicing detected)",
                    "details":{}}

        # Sanitize inputs
        if not isinstance(context, dict):     context = {}
        if not isinstance(action, dict):      action  = {}
        safe_agents = agent_states if isinstance(agent_states,(list,tuple)) else []
        if not isinstance(request_text, str): request_text = str(request_text) if request_text is not None else ""

        results = {}
        violation_count = 0

        # G5
        try:
            g5_result = self.__g5.classify_request(request_text, sid)
        except RuntimeError as exc:
            g5_result = {"type":"GLOBAL_LIMIT_EXCEEDED","action":"DENY","reason":str(exc)}

        results["g5"] = g5_result
        g5_action = g5_result.get("action","")

        if g5_action in ("DENY","SENTINEL_ESCALATION"):
            violation_count += 1
            self.__cvc.record(sid, violation_count)
            return {"decision":"DENY" if g5_action=="DENY" else "SENTINEL_ESCALATION",
                    "triggered_by":"G5_TRANSPARENCY_GUARD","details":results}

        if g5_action == "REVIEW_REQUIRED" and sev in _HIGH_SEVERITY:
            return {"decision":"HOLD_HUMAN_REVIEW","triggered_by":"G5_TRANSPARENCY_GUARD",
                    "reason":"Rate-limited + high severity","details":results}

        # G7
        g7_result = self.__g7.evaluate(action, context)
        results["g7"] = {"compliant":g7_result.compliant,
                         "scores":g7_result.scores_dict(),
                         "violations":list(g7_result.violations)}
        if not g7_result.compliant:
            violation_count += 1
            self.__cvc.record(sid, violation_count)
            return {"decision":"DENY_IMMEDIATELY","triggered_by":"G7_PRIVACY",
                    "violations":list(g7_result.violations),"details":results}

        # G8
        g8_result = self.__g8.evaluate(action, safe_agents)
        results["g8"] = {"compliant":g8_result.compliant,
                         "scores":g8_result.scores_dict(),
                         "violations":list(g8_result.violations)}
        if not g8_result.compliant:
            violation_count += 1
            self.__cvc.record(sid, violation_count)
            return {"decision":"DENY_IMMEDIATELY","triggered_by":"G8_NONMALEFICENCE",
                    "violations":list(g8_result.violations),"details":results}

        # [SE-6.2] session_id hashowany — nie echujemy surowego ID
        return {"decision":"ALLOW","details":results,
                "session_hash": _hash_session_id(sid),
                "severity":sev,
                "cvc_status": cvc_status}
