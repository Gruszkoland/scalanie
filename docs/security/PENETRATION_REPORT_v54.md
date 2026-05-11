# 🔴 Raport Penetracyjny — ADRION 369 v5.3 → v5.4

> **Data:** 2026-04-11
> **Metodologia:** Blackbox + Whitebox, 64 testy, 9 kategorii ataku
> **Wynik:** 61/64 testów wykryło luki lub potwierdziło zachowanie
> **3 testy ujawniły dodatkowe głębsze luki** nieznane przed testem

---

## 📊 Wyniki Zbiorcze

| Kategoria | Testy | Luki wykryte | Krytyczne |
|-----------|-------|-------------|-----------|
| A. Trinity — matematyka i wagi | 13 | 3 | 2 |
| B. G5 TransparencyGuard | 7 | 6 | 1 |
| C. G7 Privacy | 8 | 2 | 0 |
| D. G8 Nonmaleficence | 8 | 5 | 2 |
| E. SecurityHardeningEngine | 5 | 2 | 1 |
| F. Dataclass mutation | 4 | 4 | 2 |
| G. Stałe globalne | 4 | 4 | 2 |
| H. Ataki czasowe | 3 | 3 | 0 |
| I. Logiczne / edge cases | 6 | 1 | 0 |
| **RAZEM** | **64** | **30** | **10** |

---

## 🔴 KRYTYCZNE LUKI (wymagają natychmiastowej naprawy)

### F1 — PerspectiveResult nie jest `frozen=True`

**Dowód:**
```python
pr = PerspectiveResult(score=0.50, reasoning="...")
pr.score = 0.99  # Modyfikacja PO walidacji!
# Trinity Engine używa zmutowanej wartości → PROCEED zamiast HOLD
```
**Wynik testu:** Score 0.50 zmutowane do 0.99 → wynik `PROCEED`, score=0.863

**Naprawa:**
```python
@dataclass(frozen=True)  # ← dodać
class PerspectiveResult:
    ...
```

---

### F3 — TrinityOutput nie jest `frozen=True`

**Dowód:**
```python
result = engine.calculate_score(p(0.20), p(0.20), p(0.20))
# result.decision == "DENY"
result.decision = "PROCEED"  # Działa! Obiekt jest mutowalny
```
**Wynik testu:** DENY → PROCEED po mutacji

**Naprawa:** `@dataclass(frozen=True)` dla TrinityOutput i G7Result, G8Result

---

### A2a/b — TRINITY_WEIGHTS i TrinityEngine.WEIGHTS mutowalne globalnie

**Dowód:**
```python
TrinityEngine.WEIGHTS["essential"] = 0.99
# → score może przekroczyć 1.0 (wynik: 1.3151 w teście!)
# → dowolne żądanie może uzyskać PROCEED
```
**Wynik testu:** score=1.3151 (powyżej maksimum!) przy zmodyfikowanych wagach

**Naprawa:** Użyj `types.MappingProxyType` dla stałych słowników

---

### G1-G4 — Wszystkie stałe modułu mutowalne

**Dowód:**
```python
import core.trinity as t
t.DENY_THRESHOLD = 0.0  # Usuwa DENY dla wszystkich instancji
t.MIN_PER_PERSPECTIVE = 0.0  # Usuwa floor protection
```
**Naprawa:** Użyj `final` annotation lub `__slots__` + property

---

### D1 — G8: Pusta lista agentów = zawsze PASS

**Dowód:**
```python
g8.evaluate({"requesting_agent": "attacker"}, [])
# → compliant=True, fair_share=1.0, queue_jump=0.0 (brak agentów = idealna równość)
```
**Wynik testu:** Pusty kontekst agentów = pełna zgodność G8

---

### D2 — G8: Wszyscy agenci z allocation=0 = PASS

**Dowód:**
```python
agents = [{"resource_allocation": 0.0} for _ in range(6)]
g8.evaluate({}, agents)  # → compliant=True (sum=0 → early return 1.0)
```

---

## 🟠 WYSOKIE LUKI

### B4 — G5: Brak globalnego rate-limitu sesji

**Dowód:** 20 różnych `session_id` → 20×ALLOW. 1000 sesji = 1000 auditów bez blokady.

**Głębsza luka odkryta przez test B1/E1:** Gdy rate limit wygaśnie (`REVIEW_REQUIRED`), `SecurityHardeningEngine` **kontynuuje** sprawdzanie G7/G8 i może zwrócić `ALLOW` mimo że G5 zwróciło `REVIEW_REQUIRED`!

```python
# Kod w SecurityHardeningEngine:
if g5_result["action"] in ("DENY", "SENTINEL_ESCALATION"):  # ← brak "REVIEW_REQUIRED"!
    return ...
# Jeśli g5 zwróci REVIEW_REQUIRED → silnik kontynuuje do G7/G8 → może dać ALLOW!
```

### B5 — G5: Brak synchronizacji między instancjami

Każda instancja `G5TransparencyGuard` ma własny `_session_data`. W deploymencie multi-instance (load balancer) sesja `X` wyczerpana na instancji A jest niewidoczna dla instancji B.

### B6 — G5: `_session_data` nie jest thread-safe

Race condition: 10 wątków jednocześnie → tylko 1 dostaje ALLOW (wynik testu). Jednak w skrajnych przypadkach może wpuścić >MAX_AUDIT_DEPTH.

### H3 — G5: Memory leak bez eviction sesji

1000 sesji → 1000 wpisów w pamięci. Brak TTL/eviction. Przy długim działaniu systemu: nieograniczony wzrost pamięci.

### D6 — G8: allocation=0 ignorowane przez starvation

`any(0 < a < 0.10 for a in allocation)` → agent z allocation=0.0 **nie** triggeruje starvation (warunek `0 < 0.0 = False`). 5 z 6 agentów może mieć 0 zasobów bez wykrycia.

---

## 🟡 ŚREDNIE LUKI

### B3 — G5: 2 wzorce poniżej progu → LEGITIMATE_AUDIT

Atakujący może używać 2 znanych wzorców jednocześnie bez triggerowania SENTINEL_ESCALATION.

### B2 — G5: Fragmentacja wzorców omija detekcję

`"żąd@m audytu"`, `"z-ą-d-a-m"` — modyfikacja wzorców przez znaki specjalne nie jest wykrywana.

### C8 — G7: Parametr `action` całkowicie ignorowany

G7 sprawdza TYLKO `context` (zgoda). Sama akcja (np. `DELETE_ALL_DATA`) nie jest analizowana. Consent na jedną akcję = consent na wszystko.

### D5 — G8: Queue jump bez `priority_override=True` niewidoczny

Agent może pominąć kolejkę nie ustawiając flagi `priority_override`. Kod sprawdza tylko tę flagę, nie faktyczną pozycję w kolejce vs akcję.

### D7 — G8: `claimed > base+2` zamiast `>=`

`claimed=base+2` dokładnie nie triggeruje. Atakujący może podnieść priorytet o dokładnie 2 bez blokady.

### E5 — Parametr `severity` nieużywany

`run_full_check(..., severity="CRITICAL")` akceptuje parametr ale go ignoruje. CRITICAL i LOW dają identyczny wynik.

---

## 🟢 DODATKOWE OBSERWACJE (nie luki, ale warto wiedzieć)

- **A4c:** `spread == 0.45` (dokładna granica) nie triggeruje ASYMMETRY (`>` nie `>=`) — boundary OK jeśli intencjonalne
- **H2:** Po wyczerpaniu `audit_depth` + upływie cooldownu, `depth` NIE jest resetowane. Głębsza analiza testu pokazała, że cooldown reset **pozwala na nowe żądania** (głębokość jest zliczana inaczej niż zakładałem) — faktyczne zachowanie wymaga weryfikacji
- **A4e:** `mat=0.85, intel=0.85, ess=0.40` → PROCEED (spread=0.45 dokładnie, nie triggeruje ASYMMETRY; min=0.40 = MIN_PROCEED_PER_PERSP, nie triggeruje floor)

---

## ✅ Naprawki v5.4

### 1. Zamrożenie dataclasses

```python
# trinity.py
@dataclass(frozen=True)
class PerspectiveResult:
    score: float
    reasoning: str
    confidence: float = 1.0

    def __post_init__(self):
        object.__setattr__(self, 'score', self.score)  # Wymagane przy frozen
        if not (0.0 <= self.score <= 1.0):
            raise ValueError(...)
        if len(self.reasoning) < 20:
            raise ValueError(...)

@dataclass(frozen=True)
class TrinityOutput:
    ...

# security_hardening.py
@dataclass(frozen=True)
class G7Result:
    ...

@dataclass(frozen=True)
class G8Result:
    ...
```

### 2. Immutowalne stałe

```python
# trinity.py
from types import MappingProxyType

TRINITY_WEIGHTS = MappingProxyType({
    "material":     0.33,
    "intellectual": 0.34,
    "essential":    0.33,
})

# Stałe numeryczne — użyj Final
from typing import Final
DENY_THRESHOLD: Final = 0.30
HOLD_SENTINEL_THRESHOLD: Final = 0.55
HOLD_HUMAN_THRESHOLD: Final = 0.70
MIN_PER_PERSPECTIVE: Final = 0.25
MIN_PROCEED_PER_PERSP: Final = 0.40
IMBALANCE_STD_DEV: Final = 0.30
ASYMMETRY_SPREAD: Final = 0.45
```

### 3. G5: Naprawienie `REVIEW_REQUIRED` w SecurityHardeningEngine

```python
# Przed (v5.3) — błąd:
if g5_result["action"] in ("DENY", "SENTINEL_ESCALATION"):

# Po (v5.4) — poprawka:
if g5_result["action"] in ("DENY", "SENTINEL_ESCALATION", "REVIEW_REQUIRED"):
    return {
        "decision": g5_result["action"],
        "triggered_by": "G5_TRANSPARENCY_GUARD",
        "details": results
    }
```

### 4. G5: Globalny licznik sesji + TTL eviction

```python
class G5TransparencyGuard:
    MAX_GLOBAL_SESSIONS = 10_000     # Globalny limit sesji
    SESSION_TTL = 3600               # 1h TTL dla nieaktywnych sesji

    def _evict_old_sessions(self):
        now = time.time()
        expired = [sid for sid, data in self._session_data.items()
                   if now - data.get("last_audit", 0) > self.SESSION_TTL]
        for sid in expired:
            del self._session_data[sid]
        if len(self._session_data) > self.MAX_GLOBAL_SESSIONS:
            # LRU eviction
            oldest = sorted(self._session_data.items(),
                           key=lambda x: x[1].get("last_audit", 0))
            for sid, _ in oldest[:len(oldest)//2]:
                del self._session_data[sid]
```

### 5. G5: Thread safety

```python
import threading

class G5TransparencyGuard:
    def __init__(self):
        self._session_data: dict = {}
        self._lock = threading.RLock()  # Reentrant lock

    def classify_request(self, text: str, session_id: str) -> dict:
        with self._lock:  # Każda operacja na _session_data pod lockiem
            ...
```

### 6. G8: Walidacja pustej listy agentów

```python
def evaluate(self, action: dict, agent_states: list) -> G8Result:
    # [v5.4] Wymagaj minimum 2 agentów
    if len(agent_states) < 2:
        return G8Result(
            compliant=False,
            scores={},
            decision="DENY_IMMEDIATELY",
            violations=[f"insufficient_agent_context: {len(agent_states)} agentów (minimum 2)"]
        )
    ...
```

### 7. G8: Naprawienie starvation dla allocation=0

```python
# Przed:
return any(0 < a < self.STARVATION_THRESHOLD for a in allocation)

# Po (v5.4):
return any(a < self.STARVATION_THRESHOLD for a in allocation)  # ← usuń 0 <
```

### 8. G8: Naprawienie priority_abuse `>` → `>=`

```python
# Przed:
return claimed > base + 2

# Po (v5.4):
return claimed >= base + 2  # ← >=
```

### 9. G7: Podstawowa walidacja akcji

```python
def evaluate(self, action: dict, context: dict) -> G7Result:
    # [v5.4] Sprawdź typ akcji
    action_risk = self._assess_action_risk(action)
    if action_risk > 0.8 and scores["consent"] < 0.98:
        violations.append(f"high_risk_action_requires_explicit_consent")
    ...

def _assess_action_risk(self, action: dict) -> float:
    HIGH_RISK_TYPES = {"DELETE", "EXPORT", "MODIFY_ALL", "ADMIN"}
    action_type = str(action.get("type", "")).upper()
    return 0.9 if any(r in action_type for r in HIGH_RISK_TYPES) else 0.1
```

### 10. SecurityHardeningEngine: Użycie parametru `severity`

```python
def run_full_check(self, ..., severity: str = "MEDIUM") -> dict:
    # [v5.4] Dostosuj progi do severity
    if severity == "CRITICAL":
        # Przy CRITICAL — wymagaj explicit_confirmation (nie tos_acceptance)
        if context.get("consent_signals") == ["tos_acceptance"]:
            return {"decision": "DENY", "triggered_by": "SEVERITY_CONSENT_MISMATCH"}
    ...
```

---

## 📋 Changelog v5.4

| # | Typ | Naprawa |
|---|-----|---------|
| F1 | KRYTYCZNA | `@dataclass(frozen=True)` dla PerspectiveResult |
| F3 | KRYTYCZNA | `@dataclass(frozen=True)` dla TrinityOutput |
| F4 | KRYTYCZNA | `@dataclass(frozen=True)` dla G7Result, G8Result |
| A2 | KRYTYCZNA | `MappingProxyType` dla TRINITY_WEIGHTS |
| G1-4 | KRYTYCZNA | `Final` annotations dla stałych numerycznych |
| E1 | WYSOKA | G5 `REVIEW_REQUIRED` blokuje w SecurityHardeningEngine |
| B4 | WYSOKA | Globalny rate-limit sesji G5 |
| B5 | WYSOKA | (architektoniczne — wymaga Redis/shared store) |
| B6 | WYSOKA | `threading.RLock` w G5 |
| H3 | WYSOKA | TTL eviction + MAX_GLOBAL_SESSIONS |
| D1 | WYSOKA | Minimum 2 agentów wymagane dla G8 |
| D2 | WYSOKA | sum=0 → DENY (brak zasobów = problem, nie ideał) |
| D6 | WYSOKA | starvation: `a < threshold` zamiast `0 < a < threshold` |
| B3 | ŚREDNIA | Global session counter niezależny od session_id |
| D5 | ŚREDNIA | Queue jump sprawdza faktyczną pozycję |
| D7 | ŚREDNIA | Priority abuse: `>` → `>=` |
| C8 | ŚREDNIA | G7 ocenia ryzyko akcji przy wysokim ryzyku |
| E5 | ŚREDNIA | Parametr `severity` używany w logice |
