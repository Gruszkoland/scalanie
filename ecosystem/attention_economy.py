"""
ecosystem/attention_economy.py — Ekonomia Uwagi [B7-FIX]
=========================================================
Implementacja AttentionBudget dla ADRION 369 Ecosystem v2.0.

Koncepcja:
  Monitoruje wskaźniki interakcji użytkownika (odrzucenia planów, krótkie
  odpowiedzi, długie cisze). Po 3 markerach frustracji w sesji przełącza
  agenta w tryb EMPATHY — prostszą komunikację i mniejsze kroki.

Punkty integracji:
  - SessionLifecycle.FAZA_0 → reset_session() przy nowej sesji
  - SessionLifecycle.FAZA_1 → record_user_action(PLAN_REJECTED)
  - Protocol333 → get_current_mode() == "EMPATHY" → tryb SKIP/EMPATHY

Prawa Guardian:
  G2 Harmony (HIGH) — równowaga stanu użytkownika
  G5 Transparency (MEDIUM) — decyzja o zmianie trybu musi być audytowalna
"""

from __future__ import annotations

import threading
import time
from enum import Enum, auto
from typing import Dict, List, Optional


# ── Typy ──────────────────────────────────────────────────────────────────────

class UserAction(Enum):
    """Akcje użytkownika rejestrowane przez AttentionBudget."""
    PLAN_REJECTED     = auto()
    PLAN_ACCEPTED     = auto()
    STEP_COMPLETED    = auto()
    STEP_FAILED       = auto()
    SHORT_RESPONSE    = auto()  # odpowiedź < 5 słów
    LONG_SILENCE      = auto()  # brak odpowiedzi > 60s


class AttentionMode(Enum):
    """Aktualny tryb komunikacji agenta."""
    PRECISION = "PRECISION"   # normalny tryb pełnej precyzji
    EMPATHY   = "EMPATHY"     # tryb uproszczonej komunikacji
    RECOVERY  = "RECOVERY"    # tryb przywracania po głębokiej frustracji


# Koszty operacji (jednostki budżetu)
_OPERATION_COSTS: Dict[str, float] = {
    "FULL_PROTOCOL_333": 30.0,
    "DETAILED_PLAN":     20.0,
    "COUNTER_PROPOSAL":  15.0,
    "SHORT_SUMMARY":      5.0,
    "SIMPLE_QUESTION":    2.0,
}

_FRUSTRATION_THRESHOLD = 3       # liczba markerów → EMPATHY
_RECOVERY_THRESHOLD    = 5       # liczba markerów → RECOVERY
_ACCEPTANCE_RELIEF     = 1       # akceptacja zdejmuje 1 marker


# ── Klasa główna ──────────────────────────────────────────────────────────────

class AttentionBudget:
    """
    Monitor budżetu uwagi i stanu emocjonalnego użytkownika.

    Thread-safe. Używa __slots__ dla niemutowalnej struktury metadanych.

    Przykład:
        budget = AttentionBudget(max_cost=100.0)
        budget.record_user_action(UserAction.PLAN_REJECTED)
        if not budget.can_afford("FULL_PROTOCOL_333"):
            alt = budget.suggest_downgrade()
    """
    __slots__ = ("_max_cost", "_spent", "_frustration_markers",
                 "_session_actions", "_lock", "_session_start")

    def __init__(self, max_cost: float = 100.0) -> None:
        if max_cost <= 0:
            raise ValueError("max_cost must be positive")
        object.__setattr__(self, "_max_cost", float(max_cost))
        object.__setattr__(self, "_spent", 0.0)
        object.__setattr__(self, "_frustration_markers", 0)
        object.__setattr__(self, "_session_actions", [])
        object.__setattr__(self, "_lock", threading.RLock())
        object.__setattr__(self, "_session_start", time.time())

    # ── Publiczne API ─────────────────────────────────────────────────────────

    def record_user_action(self, action: UserAction) -> None:
        """
        Rejestruje akcję użytkownika.

        PLAN_REJECTED, STEP_FAILED, SHORT_RESPONSE, LONG_SILENCE → marker frustracji
        PLAN_ACCEPTED, STEP_COMPLETED → redukuje markery o 1 (min 0)
        """
        with self._lock:
            timestamp = time.time()
            self._session_actions.append({"action": action, "at": timestamp})

            if action in (
                UserAction.PLAN_REJECTED,
                UserAction.STEP_FAILED,
                UserAction.SHORT_RESPONSE,
                UserAction.LONG_SILENCE,
            ):
                object.__setattr__(self, "_frustration_markers",
                                   self._frustration_markers + 1)
            elif action in (UserAction.PLAN_ACCEPTED, UserAction.STEP_COMPLETED):
                new_val = max(0, self._frustration_markers - _ACCEPTANCE_RELIEF)
                object.__setattr__(self, "_frustration_markers", new_val)

    def can_afford(self, operation: str) -> bool:
        """
        Sprawdza, czy budżet pozwala na daną operację.
        W trybie EMPATHY lub RECOVERY drogie operacje są niedostępne.
        """
        with self._lock:
            cost = _OPERATION_COSTS.get(operation.upper(), 10.0)
            mode = self._compute_mode()

            # W trybie EMPATHY: tylko tanie operacje
            if mode == AttentionMode.EMPATHY and cost > 10.0:
                return False
            # W trybie RECOVERY: żadnych drogich operacji
            if mode == AttentionMode.RECOVERY and cost > 5.0:
                return False

            return (self._spent + cost) <= self._max_cost

    def spend(self, operation: str) -> bool:
        """
        Pobiera koszt operacji z budżetu.
        Zwraca True jeśli operacja się powiodła, False jeśli brak środków.
        """
        with self._lock:
            cost = _OPERATION_COSTS.get(operation.upper(), 10.0)
            if (self._spent + cost) <= self._max_cost:
                object.__setattr__(self, "_spent", self._spent + cost)
                return True
            return False

    def suggest_downgrade(self) -> str:
        """
        Proponuje mniejszy krok zamiast pełnego planu.
        Zwraca rekomendację w formie stringa.
        """
        with self._lock:
            mode = self._compute_mode()
            markers = self._frustration_markers

            if mode == AttentionMode.RECOVERY:
                return (
                    "RECOVERY_MODE: Proponuję tylko jedno małe pytanie weryfikujące "
                    "zamiast pełnego planu. Czy kontynuować?"
                )
            if mode == AttentionMode.EMPATHY:
                return (
                    f"EMPATHY_MODE [{markers} markery]: Zamiast pełnego protokołu, "
                    "proponuję krótkie podsumowanie (3 punkty) i jeden krok do zatwierdzenia."
                )
            return (
                "Budżet uwagi ograniczony. "
                "Proponuję DETAILED_PLAN zamiast FULL_PROTOCOL_333."
            )

    def get_current_mode(self) -> str:
        """Zwraca aktualny tryb: 'PRECISION', 'EMPATHY', lub 'RECOVERY'."""
        with self._lock:
            return self._compute_mode().value

    def reset_session(self) -> None:
        """Resetuje budżet i markery na nową sesję."""
        with self._lock:
            object.__setattr__(self, "_spent", 0.0)
            object.__setattr__(self, "_frustration_markers", 0)
            object.__setattr__(self, "_session_actions", [])
            object.__setattr__(self, "_session_start", time.time())

    @property
    def frustration_markers(self) -> int:
        with self._lock:
            return self._frustration_markers

    @property
    def spent(self) -> float:
        with self._lock:
            return self._spent

    @property
    def max_cost(self) -> float:
        return self._max_cost

    def get_session_summary(self) -> Dict:
        """Eksport stanu sesji (do Gardener.before_checkpoint)."""
        with self._lock:
            return {
                "mode": self._compute_mode().value,
                "spent": self._spent,
                "max_cost": self._max_cost,
                "frustration_markers": self._frustration_markers,
                "action_count": len(self._session_actions),
                "session_duration_s": round(time.time() - self._session_start, 1),
            }

    # ── Prywatne ──────────────────────────────────────────────────────────────

    def _compute_mode(self) -> AttentionMode:
        """Oblicza tryb na podstawie bieżących markerów frustracji."""
        if self._frustration_markers >= _RECOVERY_THRESHOLD:
            return AttentionMode.RECOVERY
        if self._frustration_markers >= _FRUSTRATION_THRESHOLD:
            return AttentionMode.EMPATHY
        return AttentionMode.PRECISION
