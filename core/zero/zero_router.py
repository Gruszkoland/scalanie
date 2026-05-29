from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional

from .zero_state import ZeroApproval, ZeroState


@dataclass
class ZeroDecision:
    """Wynik routingu przez Punkt Zero."""

    payload: Dict[str, Any]
    approval: ZeroApproval


class ZeroRouter:
    """Centralny router, przez który przechodzi kazda decyzja systemu."""

    def __init__(self, zero_state: Optional[ZeroState] = None) -> None:
        self.zero_state = zero_state or ZeroState()
        self.total_routed = 0
        self.total_forced = 0

    @staticmethod
    def _mean(values: Iterable[float]) -> float:
        values = list(values)
        if not values:
            return 0.0
        return sum(values) / len(values)

    def _extract_metrics(self, payload: Dict[str, Any]) -> Dict[str, float]:
        resonance = payload.get("resonance_score")
        entropy = payload.get("entropy_level")

        if resonance is None:
            trinity = payload.get("trinity_vector", (0.0, 0.0, 0.0))
            resonance = self._mean(float(x) for x in trinity)

        if entropy is None:
            guardians = payload.get("guardian_scores", {})
            if isinstance(guardians, dict) and guardians:
                entropy = 1.0 - self._mean(float(v) for v in guardians.values())
            else:
                entropy = 0.0

        return {
            "resonance_score": float(resonance),
            "entropy_level": float(entropy),
        }

    def route(self, payload: Dict[str, Any], *, auto_force_to_zero: bool = True) -> ZeroDecision:
        self.total_routed += 1
        metrics = self._extract_metrics(payload)
        approval = self.zero_state.evaluate(metrics)

        if approval.approved:
            return ZeroDecision(payload=payload, approval=approval)

        if auto_force_to_zero:
            repaired = dict(payload)
            repaired.update(self.force_to_zero(reason=approval.reason))
            forced_approval = self.zero_state.evaluate(repaired)
            return ZeroDecision(payload=repaired, approval=forced_approval)

        return ZeroDecision(payload=payload, approval=approval)

    def force_to_zero(self, reason: str = "MANUAL") -> Dict[str, float]:
        """Force reset to singular state used by observer and orchestrator."""
        _ = reason
        self.total_forced += 1
        return self.zero_state.force_to_zero()

    def get_system_health(self) -> Dict[str, float]:
        forced_ratio = (self.total_forced / self.total_routed) if self.total_routed else 0.0
        return {
            "total_routed": float(self.total_routed),
            "total_forced": float(self.total_forced),
            "forced_ratio": forced_ratio,
            "reset_counter": float(self.zero_state.reset_counter),
        }
