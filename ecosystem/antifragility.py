"""
ecosystem/antifragility.py — Silnik Antykruchości [B7-FIX]
============================================================
Implementacja AntifragilityEngine dla ADRION 369 Ecosystem v2.0.

Koncepcja:
  Po każdej pętli naprawczej (SAV fail) wyciąga sygnaturę błędu i zapisuje
  ją w AntifragilityRegistry (append-only log wzorowany na GenesisRecord).
  Przy kolejnych zadaniach sprawdza, czy podobna sygnatura już istnieje,
  i aplikuje MicroHeuristicPatch — małą modyfikację strategii.

Punkty integracji z repo:
  - SuperiorMoralCode.sav_pipeline() → hook post_repair
  - GenesisRecord — wzorzec struktury immutable logu
  - Hexagon.MAX_CYCLES i convergence_scores jako dane wejściowe

Prawa Guardian odpowiadające modułowi:
  G4 Causality (HIGH) — każdy błąd musi mieć śledzalną przyczynę.
"""

from __future__ import annotations

import hashlib
import time
import threading
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


# ── Typy danych ───────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class RepairContext:
    """
    Kontekst zakończonej pętli naprawczej (SAV fail → SAV pass).

    Atrybuty:
        error_signature: str    — opis błędu (wyjątek lub klasa błędu)
        hexagon_cycle: int      — numer cyklu Hexagon przy którym wystąpił błąd
        convergence_score: float— wynik konwergencji ostatniego cyklu Hexagon
        patched_files: tuple    — pliki zmienione w pętli naprawczej
        timestamp: float        — Unix timestamp zakończenia naprawy
        extra: dict             — dodatkowe metadane (opcjonalne)
    """
    error_signature: str
    hexagon_cycle: int
    convergence_score: float
    patched_files: tuple = field(default_factory=tuple)
    timestamp: float = field(default_factory=time.time)
    extra: Dict[str, Any] = field(default_factory=dict)

    def feature_vector(self) -> Dict[str, Any]:
        """Ekstrahuje cechy do porównania sygnatur."""
        return {
            "error_prefix": self.error_signature[:64],
            "hexagon_cycle": self.hexagon_cycle,
            "conv_bucket": round(self.convergence_score, 1),
            "n_patched": len(self.patched_files),
        }


@dataclass
class MicroHeuristicPatch:
    """
    Mikro-łatka strategii wygenerowana przez AntifragilityEngine.

    Atrybuty:
        patch_id: str             — unikalny ID patcha (SHA-1 sygnatury)
        error_signature: str      — sygnatura błędu, dla której patch powstał
        strategy_modification: dict — modyfikacje do zastosowania w kontekście
        applied_count: int        — ile razy patch został zastosowany
        success_rate: float       — % pomyślnych zastosowań (0.0–1.0)
    """
    patch_id: str
    error_signature: str
    strategy_modification: Dict[str, Any]
    applied_count: int = 0
    success_rate: float = 0.0

    def record_outcome(self, success: bool) -> None:
        """Aktualizuje statystyki zastosowania patcha."""
        prev_successes = round(self.success_rate * self.applied_count)
        self.applied_count += 1
        new_successes = prev_successes + (1 if success else 0)
        self.success_rate = new_successes / self.applied_count


# ── Registry ──────────────────────────────────────────────────────────────────

_SIMILARITY_THRESHOLD = 0.85  # min pokrycie cech do uznania za "podobną" sygnaturę


def _signature_hash(signature: str) -> str:
    """SHA-1 sygnatury błędu jako ID patcha."""
    return hashlib.sha1(signature.encode("utf-8", errors="replace")).hexdigest()[:16]


def _feature_similarity(a: Dict[str, Any], b: Dict[str, Any]) -> float:
    """
    Oblicza podobieństwo między dwoma wektorami cech (0.0–1.0).
    Prosta metryka: ułamek kluczy o identycznej wartości.
    """
    if not a or not b:
        return 0.0
    common_keys = set(a.keys()) & set(b.keys())
    if not common_keys:
        return 0.0
    matches = sum(1 for k in common_keys if a[k] == b[k])
    return matches / len(common_keys)


class AntifragilityRegistry:
    """
    Append-only log sygnatur błędów i wygenerowanych mikro-łatek.

    Wzorowany na GenesisRecord: immutable entries, thread-safe, exportowalny.
    Instancja jest thread-safe dzięki wewnętrznemu RLock.

    Użycie:
        registry = AntifragilityRegistry()
        patch = registry.learn_from_repair(repair_context)
        existing = registry.query_patch(task_signature)
        if existing:
            mods = existing.strategy_modification
    """
    __slots__ = ("_entries", "_lock")

    def __init__(self) -> None:
        object.__setattr__(self, "_entries", [])
        object.__setattr__(self, "_lock", threading.RLock())

    # ── Publiczne API ─────────────────────────────────────────────────────────

    def learn_from_repair(self, context: RepairContext) -> MicroHeuristicPatch:
        """
        Po zakończeniu pętli naprawczej: ekstrahuje sygnaturę błędu,
        zapisuje ją w rejestrze i generuje mikro-łatkę.

        Jeśli taka sygnatura już istnieje → aktualizuje istniejący patch.
        """
        sig = context.error_signature
        patch_id = _signature_hash(sig)

        with self._lock:
            existing = self._find_by_id(patch_id)
            if existing is not None:
                # Aktualizuj statystyki — naprawiono ponownie
                existing.record_outcome(success=True)
                return existing

            patch = MicroHeuristicPatch(
                patch_id=patch_id,
                error_signature=sig,
                strategy_modification=self._derive_strategy(context),
            )
            patch.record_outcome(success=True)
            self._entries.append({
                "patch": patch,
                "feature_vector": context.feature_vector(),
                "recorded_at": context.timestamp,
            })
            return patch

    def query_patch(self, task_signature: Dict[str, Any]) -> Optional[MicroHeuristicPatch]:
        """
        Przed Krok 2.5 (SAV): sprawdza, czy podobny błąd już wystąpił.
        Zwraca patch z najwyższym similarity jeśli ≥ threshold.
        """
        with self._lock:
            best_patch: Optional[MicroHeuristicPatch] = None
            best_score = 0.0

            for entry in self._entries:
                score = _feature_similarity(task_signature, entry["feature_vector"])
                if score >= _SIMILARITY_THRESHOLD and score > best_score:
                    best_score = score
                    best_patch = entry["patch"]

            return best_patch

    def apply_patch(self, patch: MicroHeuristicPatch, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Aplikuje strategy_modification do przekazanego kontekstu.
        Zwraca nowy słownik — oryginał jest niezmieniony.
        """
        result = dict(context)
        result.update(patch.strategy_modification)
        return result

    def record_patch_outcome(self, patch: MicroHeuristicPatch, success: bool) -> None:
        """Rejestruje wynik zastosowania patcha (do aktualizacji success_rate)."""
        with self._lock:
            patch.record_outcome(success)

    def to_genesis_format(self) -> Dict[str, Any]:
        """Eksportuje stan rejestru do formatu kompatybilnego z Genesis Record."""
        with self._lock:
            return {
                "registry_type": "AntifragilityRegistry",
                "version": "2.0.0",
                "entry_count": len(self._entries),
                "entries": [
                    {
                        "patch_id": e["patch"].patch_id,
                        "error_signature": e["patch"].error_signature,
                        "strategy_modification": e["patch"].strategy_modification,
                        "applied_count": e["patch"].applied_count,
                        "success_rate": e["patch"].success_rate,
                        "recorded_at": e["recorded_at"],
                    }
                    for e in self._entries
                ],
            }

    @property
    def entry_count(self) -> int:
        with self._lock:
            return len(self._entries)

    # ── Prywatne ──────────────────────────────────────────────────────────────

    def _find_by_id(self, patch_id: str) -> Optional[MicroHeuristicPatch]:
        """Szuka patcha po ID (bez locka — caller musi trzymać lock)."""
        for entry in self._entries:
            if entry["patch"].patch_id == patch_id:
                return entry["patch"]
        return None

    @staticmethod
    def _derive_strategy(context: RepairContext) -> Dict[str, Any]:
        """
        Generuje strategię naprawy na podstawie kontekstu błędu.

        Heurystyki:
        - Wysoki cykl Hexagon → podnieś próg konwergencji
        - Niska konwergencja → zwiększ ilość iteracji walidacji
        - Dużo zmodyfikowanych plików → wymuś dodatkowy snapshot RBC
        """
        strategy: Dict[str, Any] = {}

        if context.hexagon_cycle >= 3:
            strategy["convergence_threshold_delta"] = +0.05
        if context.convergence_score < 0.5:
            strategy["extra_validation_passes"] = 2
        if len(context.patched_files) > 5:
            strategy["force_rbc_snapshot"] = True

        # Zawsze dodaj surową sygnaturę do strategii (dla audytowalności)
        strategy["_derived_from"] = context.error_signature[:128]
        return strategy
