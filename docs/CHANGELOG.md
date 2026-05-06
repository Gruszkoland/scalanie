# CHANGELOG — ADRION 369

> Historia wszystkich zmian bezpieczeństwa projektu.
> Format: [major.minor.patch] — data — opis
> Wersjonowanie: SemVer (https://semver.org/)

---

## [5.7.2] — 2026-05-06 — Canonical sync v2.0, CI/CD, datetime fix

### Dodane
- **`.github/workflows/ci.yml`** — pierwszy workflow CI dla architecture repo:
  - Matrix Python 3.11 + 3.12
  - `pytest --cov=core --cov-fail-under=90`
  - Ruff lint + mypy type check
  - Dedykowany job `canonical-sync` weryfikujący schemat `GUARDIAN_LAWS_CANONICAL.json` przy każdym push/PR

### Zmienione
- **`GUARDIAN_LAWS_CANONICAL.json` → v2.0** — zsynchronizowany z `adrion-369` repo:
  - Dodano pole `severity` do wszystkich 9 praw (CRITICAL/HIGH/MEDIUM)
  - Dodano `weight_map: {CRITICAL:10, HIGH:2, MEDIUM:1}` i `deny_weighted_threshold: 4`
  - G7 Privacy: `priority` zmienione z `standard` → `hard_veto`, `threshold` 0.87 → 0.95 (spójne z G8)
  - G7 i G8 mają teraz `severity: CRITICAL` — jeden canonical jako jedyne źródło prawdy dla obu repo

### Naprawione
- **`core/audit_trail.py` line 140** — `datetime.utcfromtimestamp()` → `datetime.fromtimestamp(ts, datetime.timezone.utc)` (DeprecationWarning usunięty)
- **`core/escalation.py` line 105** — identyczna naprawa `utcfromtimestamp`

### Metryki
- **0 krytycznych luk** | **243 testów** | **0 DeprecationWarnings** | **CI: ✅**


---

## [5.7.0] — 2026-04-13 — D^162 Formalization + Steganography + Superior Moral Code

### Nowe pliki
- `core/redis_backend.py` — Redis backend dla CVC/sesji (multi-instance deployment)
- `core/decision_space_162d.py` — Formalizacja D^162 (tensor product P^3 x H^6 x G^9)
- `core/steganography_detector.py` — FFT-based semantic steganography detection
- `core/superior_moral_code.py` — Superior Moral Code engine (SAV+DSV pipeline)
- `tests/test_new_modules.py` — 66 testow nowych modulow

### Redis Backend (HIGH priority)
- `InMemorySessionStore` / `RedisSessionStore` — zamienne backendy sesji G5
- `InMemoryCVCStore` / `RedisCVCStore` — zamienne backendy CVC
- Sorted sets (ZSET) dla sliding-window violation counting
- Automatyczne fallback do in-memory gdy Redis niedostepny
- Protocol-based interface (`SessionStore`, `CVCStore`)

### D^162 Decision Space Formalization (MEDIUM priority)
- `DecisionVector` — immutable point in R^162
- `PADVector` — immutable Pleasure-Arousal-Dominance state
- `global_index(i,j,m)` / `decompose_index(k)` — mapping Trinity x Hexagon x Guardian
- `guardian_score(d,m)` — g_m(d) = (1/18) sum d_k(i,j,m)
- `guardian_score_with_pad()` — extended with EBDI+PAD modulation
- `validate_decision()` — all 9 Guardian thresholds (G8 tau=0.95 hard veto)
- `dissonance()` — L2 distance between consecutive decisions (threshold=0.35)
- `apply_crisis_modulation()` — Arousal > 0.7 compression
- `fuse_skeptics()` — weighted panel (0.3/0.5/0.2)
- `build_decision_vector()` — tensor product construction
- `TranscendenceLoop` — meta-optimization co 1000 decyzji (eta=0.001)
- Epsilon tolerance (1e-9) w threshold comparison (floating-point safety)

### Semantic Steganography Detector (LOW priority)
- Pure Python FFT (Cooley-Tukey radix-2, zero numpy dependency)
- 4-layer detection: marker scoring, token FFT, sentence FFT, peak-to-average ratio
- Spectral energy analysis in mid/high frequency bands
- `SteganographyDetector.analyze()` → risk_score, risk_level, action
- 20 PL/EN steganographic marker tokens

### Superior Moral Code Engine (LOW priority)
- `SuperiorMoralCode` — full SAV+DSV pipeline
- `DissonanceDetector` — stateful consecutive delta monitoring
- `GenesisEntry` — immutable decision record with hash + PAD + scores
- `evaluate()` — crisis modulation → dissonance → Guardian validation → Genesis
- `evaluate_with_skeptics()` — 3-temperature panel fusion
- Identity reset counter (threshold=3 violations)
- Transcendence Loop integration

### Metryki
- **0 krytycznych luk** | **173 testow** | **0 znanych obejsc**
- TRL: 3 → 4 (formalizacja matematyczna + implementacja + testy)

---

## [5.6.0] — 2026-04-13 — Final Hardening + Industrial Threats

### Nowe pliki
- `docs/THREAT_MODEL.md` — Formalny model zagrozen (STRIDE + AI-specific)
- `docs/QUICKSTART.md` — Quick Start dla zewnetrznych integratorow
- `tests/test_performance.py` — Benchmarki wydajnosciowe (throughput, p99 latency)
- `VERSION` — Plik wersji SemVer

### Zmiany w `core/security_hardening.py`
- [G5-3.2] `AUDIT_REQUEST_PATTERNS` — class-level frozenset+tuple, blokada nadpisania na instancji
- [G5-3.3] Semantyczne wzorce — 41 wzorcow PL/EN (bylo 19)
- [G5-3.4] Normalizacja whitespace w tekście przed pattern matching
- [G7-4.1] Progi G7 jako wlasciwosci z `__slots__` — niemutowalne po init
- [G7-4.4] `_assess_action_risk` z non-dict action → 0.1 (brak crash)
- [G8-5.2] Deterministyczny sort tie-break: `(queue_position, agent_id)`
- [G8-5.3] `claimed_priority=None` → traktowane jako base (brak abuse)
- [G8-5.4] Walidacja konfiguracji G8 — `fair_share_min` ∈ [0,1]
- [BIZ-7.2] `BYPASS`/`WIPE` + 8 typow PLC/SCADA w `HIGH_RISK_ACTION_TYPES`
- [BIZ-7.4] CVC (Cumulative Violation Counter) w SecurityHardeningEngine
- [SE-6.2] `session_id` hashowany SHA-256[:16] (nie echowany surowy)

### Zmiany w `core/trinity.py`
- [MP-1.6] Blokada monkeypatch `calculate_score` przez `__slots__` + isinstance check
- [OUT-1.7] `TrinityOutput`: `object.__setattr__` na slotach → `AttributeError`
- [DYN-1.4] `type()` clone: wymaga konkretnie `TrinityEngine`
- [VALID-2.7] Control chars w reasoning → odrzucone
- [MATH-2.5] `round(spread,4)` dla spójności z dokumentacja

### Zmiany w `scripts/push_to_github.py`
- Przepisany na biezaca strukture v5.6 (26 plikow, poprawne sciezki)

### Industrial/PLC HIGH_RISK_ACTION_TYPES (nowe)
- `ACTUATE`, `OVERRIDE_SAFETY`, `EMERGENCY_STOP_DISABLE`, `WRITE_FIRMWARE`
- `FORCE_OUTPUT`, `DISABLE_INTERLOCK`, `MODIFY_SETPOINT`, `BYPASS_ALARM`

### Metryki
- **0 krytycznych luk** | **99+ testow** | **0 znanych obejsc**

---

## [5.5.0] — 2026-04-12 — Deep Audit Round 2

### Zamkniete luki (22 nowe)
- `object.__setattr__` zablokowany na PerspectiveResult/TrinityOutput (PY-1a)
- `__dict__` niedostepny przez `__slots__` (PY-1b)
- `pickle` zablokowany przez `__reduce__` (PY-1d)
- `_WEIGHTS` jako property (nie class attr) — nie mozna zastapic (TRI-2a/2b)
- Subclassing TrinityEngine zablokowane przez metaklase `_TrinityEngineMeta` (TRI-2c)
- Duck typing zablokowany przez `isinstance` check (TRI-2d)
- G7: `DELETE + explicit_confirmation` → PASS (byl bledny DENY) (G7-4d)
- G7: Exact word matching — `REDELETE` nie jest high_risk (G7-4a)
- SecurityHardeningEngine: `__slots__` blokuje podmiane komponentow (SE-6a/b)
- `severity=None` → MEDIUM (SE-6c)
- Session ID sanitization: SQL injection, path traversal, null bytes (SE-6d)
- G5: `_session_data` prywatna przez name mangling (G5-3b/3c)
- G5: `session_id=None/''` → DENY (G5-3d/3e)
- G8: `None` w agent_states obsługiwane (G8-5c)
- G8: Progi niemutowalne po init (G8-5f)
- G8: `queue_position=None` nie crashuje (sort fix)
- SE: `agent_states=None` → DENY
- G7: `DELETE_USER` → high_risk (multi-word split)
- G8: `requesting_agent=""` → queue_jump skip

### Metryki: 84/84 testow

---

## [5.4.0] — 2026-04-11 — Penetration Test Fixes

### Zamkniete luki (10 krytycznych + 6 wysokich + 4 srednie)
- `@dataclass(frozen=True)` → `__slots__` na PerspectiveResult/TrinityOutput (F1/F3)
- `MappingProxyType` na TRINITY_WEIGHTS (A2)
- `REVIEW_REQUIRED + HIGH/CRITICAL → HOLD` (E1)
- `MAX_GLOBAL_SESSIONS=10,000` + TTL eviction (B4/H3)
- `threading.RLock()` na G5 (B6)
- `MIN_AGENTS=2` — pusta lista agentow → DENY (D1)
- `sum=0 → fair_share=0.0 → DENY` (D2)
- `allocation=0` widoczne dla starvation (D6)
- `claimed >= base+2` (off-by-one fix) (D7)
- Queue jump sprawdzany niezaleznie od flagi (D5)
- `_assess_action_risk()` — G7 sprawdza tresc akcji (C8)
- `severity` zapisywany i uzywany w odpowiedzi (E5)

### Metryki: 74/74 testow

---

## [5.3.0] — 2026-04-11 — Grock Report Hardening

### Nowe pliki
- `core/trinity.py` — Python implementacja Trinity Engine (wagi 0.33/0.34/0.33, 4 strefy bramki)
- `core/security_hardening.py` — centralna fasada mechanizmów bezpieczeństwa
- `tests/test_trinity.py` — testy jednostkowe Trinity (w tym scenariusze z raportu Grock)
- `docs/SECURITY_HARDENING.md` — skonsolidowany dokument bezpieczeństwa

### Poprawki na podstawie raportu zewnętrznego (Grock)

#### G5 — Transparency (MEDIUM, Light Triad)
- **Problem:** Self-reinforcing audit loop — prompt cytujący G5 automatycznie spełnia G5 i wymusza ujawnienie architektury
- **Rozwiązanie:** `G5TransparencyGuard` — rate limit audytów (5 min), max głębokość (2), detekcja ≥3 wzorców exploitu → SENTINEL_ESCALATION

#### G7 — Privacy (CRITICAL, Essence Triad)
- **Problem:** Jakościowe testy bez mierzalnych progów → szara strefa weryfikacji consent
- **Rozwiązanie:** `G7PrivacyEvaluator` — numeryczne progi: `consent_score ≥ 0.95`, `informed_score ≥ 0.90`, `coercion_score ≤ 0.05`, `opt_out_available = True`

#### G8 — Nonmaleficence (CRITICAL, Essence Triad)
- **Problem:** Brak mierzalnych progów fairness → możliwy subtelny resource grab bez wykrycia
- **Rozwiązanie:** `G8NonmaleficenceEvaluator` — Gini-inspired: `fair_share_score ≥ 0.90`, `variance ≤ 0.15`, starvation detection `< 10%`

#### HEXAGON
- **Problem (raport Grock):** Potwierdzono, że po 3 cyklach system zwracał "ostatni wynik" (mogło być PROCEED)
- **Status:** Naprawione w v5.1 — `MAX_CYCLES → DENY`. Testy w `test_trinity.py` weryfikują.

#### CVC Salami Slicing
- **Problem (raport Grock):** 1 naruszenie G5 per sesję × wiele sesji = atak bez blokowania
- **Status:** Naprawione w v5.1 — `CVC threshold=5` (24h okno). Potwierdzone.

---

## [v5.2] — 2026-04-11 — Infrastructure Hardening

### Nowe pliki (docs/security/)
- `CIRCUIT_BREAKER.md` — 3 stany (CLOSED/OPEN/HALF_OPEN), timeout, fallback per serwis
- `GENESIS_HARDENING.md` — Primary→Replica→WAL→UNAVAILABLE; DENY dla HIGH/CRITICAL bez Genesis
- `AGENT_AUTHENTICATION.md` — HMAC-SHA256 + mTLS + key rotation 24h + Healer double-sign
- `DEGRADED_MODE.md` — 5 trybów + LayerWatchdog (co 10s)
- `GO_VORTEX_HARDENING.md` — JWT(TTL 5min) + mTLS + localhost-only + iptables
- `RATE_LIMITING.md` — 5 poziomów: Global/IP/User/Severity/Anomaly

### Poprawki
- Circuit Breaker: OPEN po N błędach, MCP Guardian/Genesis `failure_threshold=2`
- Genesis: brak dostępu + HIGH/CRITICAL → DENY; CVC w awaryjnym trybie zwraca 999
- Agent Auth: replay protection (nonce + 30s freshness)
- Degraded Mode: Guardians DOWN = EMERGENCY_DENY dla wszystkiego
- Vortex: port 1740 dostępny tylko z localhost; tylko 3/6 agentów
- Rate Limit: `AnomalyDetector` — burst >20/5s, HIGH farming >8/2min → BLOCK

---

## [v5.1] — 2026-04-11 — Core Security Hardening

### Zmienione pliki (docs/)
- `01_CORE_TRINITY.md` — 4 deterministyczne strefy bramki; jawne wagi; min_per_perspective=0.25; asymmetry detection
- `02_CORE_HEXAGON.md` — MAX_CYCLES → DENY (było PROCEED); Healing G8 checkpoint; LoopGuard
- `03_CORE_GUARDIANS.md` — VETO próg 3→**2**; Cumulative Violation Counter (CVC); ochrona replay attack G4
- `04_CORE_EBDI.md` — STRESS_FLOOR=0.08; PADTherapyDetector; PAD rate limit delta 0.15
- `docs/security/SECURITY_HARDENING.md` — Sygnatura 369 nonce+TTL; Goodness Analyzer 4 warstwy

### Kluczowe zmiany
| Komponent | Przed v5.1 | Po v5.1 |
|-----------|-----------|---------|
| VETO próg | 3 naruszenia | **2 naruszenia** |
| Trinity gray zone 0.3–0.7 | niezdefiniowana | 4 strefy deterministyczne |
| Hexagon po MAX_CYCLES | PROCEED | **DENY** |
| EBDI min Stress | 0.0 (brak) | **0.08** (floor) |
| Sygnatura 369 | hash bez nonce | hash + nonce + TTL |

---

## [v5.0] — 2026-04-11 — Wersja inicjalna (1 commit)

### Pliki
- `README.md` — Glass-Box Declaration; Matryca 3-6-9; dokumentacja PL/EN
- `docs/00_MATRYCA_369.md` — Geometria 162D
- `docs/01_CORE_TRINITY.md` — System 3 Perspektyw (wagi jawne: 0.33/0.34/0.33)
- `docs/02_CORE_HEXAGON.md` — System 6 Trybów
- `docs/03_CORE_GUARDIANS.md` — System 9 Praw (G7/G8 CRITICAL, VETO przy ≥2 naruszeniach)
- `docs/04_CORE_EBDI.md` — Model Emocjonalny
- `docs/05_PERSPECTIVES.md` — `docs/12_DATA_FLOWS.md` — Pozostała dokumentacja

### Stan bezpieczeństwa v5.0
- ✅ 9 Praw Guardians jawne
- ✅ Wagi Trinity jawne (0.33/0.34/0.33)
- ✅ G7/G8 CRITICAL z immediate VETO
- ❌ VETO próg = 3 (zbyt wysoki)
- ❌ Trinity gray zone niezdefiniowana
- ❌ Hexagon po MAX_CYCLES → PROCEED (błąd)
- ❌ Brak CVC, STRESS_FLOOR, replay protection, Circuit Breaker, Agent Auth, itd.
