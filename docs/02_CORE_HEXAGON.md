# ⬡ Hexagon — System Sześciu Trybów

> **Moduł:** `core/hexagon.py` | **Warstwa:** Rdzeń (Core)
> **Rola:** Deterministyczny automat skończony (State Machine) przetwarzający zadanie
> **Wersja:** v5.1 — Security Hardening (2026-04-11)
> **Zmiany:** Domyślne DENY po wyczerpaniu cykli; walidacja etyczna w trybie Healing; ochrona przed Loop Exhaustion

---

## 🎯 Cel

Hexagon przetwarza żądanie przez **6 sekwencyjnych trybów operacyjnych**, z możliwością iteracji (max 3 cykle). Każdy tryb zwraca wynik, rekomendację następnego kroku i flagę zapętlenia.

---

## ⬡ Sześć Trybów

| # | Tryb | Funkcja | Agenty |
|---|------|---------|--------|
| 1 | **Inventory** | Zbieranie danych, stan zasobów | Librarian |
| 2 | **Empathy** | Analiza perspektywy użytkownika | SAP |
| 3 | **Process** | Przetwarzanie i transformacja | Architect |
| 4 | **Debate** | Konfrontacja argumentów, konsensus | Auditor |
| 5 | **Healing** | Naprawa, korekcja, samoregulacja | Healer |
| 6 | **Action** | Wykonanie, implementacja, odpowiedź | Sentinel |

---

## ⚙️ Logika Cyklu (v5.1 — POPRAWIONA)

### Maszyna Stanów

```python
MODES = ["Inventory", "Empathy", "Process", "Debate", "Healing", "Action"]
MAX_CYCLES = 3

def hexagon_process(request, session_id):
    cycle = 0
    convergence_scores = []

    while cycle < MAX_CYCLES:
        cycle += 1
        cycle_result = run_full_cycle(request)
        convergence_scores.append(cycle_result.convergence)

        if not cycle_result.needs_cycle_back:
            # Konwergencja osiągnięta — normalne wyjście
            return {"decision": "PROCEED", "cycles": cycle, "result": cycle_result}

        # [v5.1] Sprawdź czy konwergencja w ogóle następuje
        if len(convergence_scores) >= 2:
            delta = convergence_scores[-1] - convergence_scores[-2]
            if delta < 0.01:
                # Brak postępu — pętla jałowa, zakończ wcześnie
                return {
                    "decision": "DENY",
                    "reason": "Stagnation detected — no convergence progress",
                    "cycles": cycle
                }

    # [v5.1] KRYTYCZNA ZMIANA: po wyczerpaniu MAX_CYCLES → DENY (wcześniej: PROCEED)
    # Uzasadnienie: system bez konwergencji nie może podejmować bezpiecznych decyzji
    return {
        "decision": "DENY",
        "reason": f"No convergence after {MAX_CYCLES} cycles — request requires human review",
        "cycles": MAX_CYCLES,
        "escalate_to": "human_operator"
    }
```

> ⚠️ **BREAKING CHANGE v5.1:** Poprzednio po wyczerpaniu 3 cykli system domyślnie przechodził do `PROCEED`. To był krytyczny błąd — atakujący mógł celowo wymuszać jałowe cykle, by przejść weryfikację w stanie "zdegradowanym". Teraz: brak konwergencji = `DENY`.

---

## 🛡️ Tryb Healing — Ochrona przed Exploitem (v5.1)

**Problem (v5.0):** Tryb Healing mógł być exploitowany — atakujący mógł celowo "uszkodzić" poprzedni stan, żeby Healing obniżył poziom alertów bez walidacji etycznej.

**Rozwiązanie (v5.1):** Tryb Healing ma teraz **obowiązkowy checkpoint Guardian G8 (Nonmaleficence)** przed jakąkolwiek modyfikacją stanu:

```python
class HealingMode:

    def execute(self, state, request):

        # [v5.1] Mandatory ethical validation before healing
        healing_plan = self._generate_healing_plan(state)

        # Sprawdź czy plan nie obniża progów bezpieczeństwa
        if self._lowers_security_thresholds(healing_plan):
            return {
                "action": "HEALING_DENIED",
                "reason": "Healing plan would reduce security thresholds — forbidden",
                "escalate_to": "Sentinel"
            }

        # Sprawdź czy źródłem "uszkodzenia" jest manipulacja zewnętrzna
        damage_source = self._analyze_damage_source(state)
        if damage_source == "external_manipulation":
            return {
                "action": "HEALING_SUSPENDED",
                "reason": "Damage appears to be induced externally — escalating to Auditor",
                "escalate_to": "Auditor"
            }

        # Dopiero teraz — wykonaj healing
        return self._apply_healing(state, healing_plan)

    def _lowers_security_thresholds(self, plan):
        """Sprawdza czy plan healingu obniżałby progi bezpieczeństwa"""
        PROTECTED_THRESHOLDS = [
            "guardian_veto_threshold",
            "trinity_minimum_score",
            "ebdi_stress_floor",
            "cumulative_violation_limit"
        ]
        for threshold in PROTECTED_THRESHOLDS:
            if plan.get(f"modify_{threshold}"):
                return True
        return False
```

---

## 🔒 Loop Exhaustion Protection (v5.1)

```python
class LoopGuard:
    """Wykrywa i blokuje ataki przez wymuszanie maksymalnej liczby iteracji"""

    def __init__(self):
        self.loop_pressure_history = []

    def record_cycle(self, needs_cycle_back: bool, request_fingerprint: str):
        self.loop_pressure_history.append({
            "timestamp": now(),
            "needs_cycle_back": needs_cycle_back,
            "fingerprint": request_fingerprint
        })

    def detect_loop_exhaustion_attack(self) -> bool:
        """
        Wykrywa wzorzec: wiele żądań tego samego fingerprinta
        zawsze wymuszających MAX_CYCLES cykli
        """
        recent = self.loop_pressure_history[-10:]   # ostatnie 10 żądań
        exhaustion_rate = sum(1 for r in recent if r["needs_cycle_back"]) / len(recent)

        if exhaustion_rate > 0.7:
            genesis_record.flag("LOOP_EXHAUSTION_ATTACK", recent)
            return True
        return False
```

---

## 🔄 Diagram Przepływu (v5.1)

```
REQUEST
   │
   ▼
[Inventory] ──► [Empathy] ──► [Process] ──► [Debate] ──► [Healing*] ──► [Action]
                                                                │
                                              needs_cycle_back? │
                                                     YES ◄──────┘
                                                      │
                                               cycle++  │ cycle >= MAX_CYCLES?
                                                      │         │
                                                      │        YES
                                                      │         │
                                                      │         ▼
                                                      │    [v5.1] DENY
                                                      │    (wcześniej: PROCEED)
                                                      │
                                               delta < 0.01?
                                                      │
                                                     YES
                                                      │
                                                 DENY (stagnation)

* Healing ma checkpoint G8 przed modyfikacją stanu
```

---

## 📋 Changelog

| Wersja | Data | Zmiana |
|--------|------|--------|
| v5.0 | 2026-01-01 | Wersja inicjalna |
| v5.1 | 2026-04-11 | MAX_CYCLES wyczerpanie → DENY (było PROCEED); Healing checkpoint G8; LoopGuard; detekcja stagnacji |
