from __future__ import annotations

from dataclasses import dataclass, field
from time import time
from typing import Any, Dict


@dataclass(frozen=True)
class ZeroApproval:
    """Niemutowalny wynik bramki Punktu Zero."""

    approved: bool
    resonance_score: float
    reason: str
    timestamp: float = field(default_factory=time)


@dataclass
class ZeroState:
    """Stan singularności i zasady akceptacji decyzji."""

    resonance_threshold: float = 0.90
    entropy_limit: float = 0.25
    reset_counter: int = 0

    def evaluate(self, metrics: Dict[str, Any]) -> ZeroApproval:
        resonance = float(metrics.get("resonance_score", 0.0))
        entropy = float(metrics.get("entropy_level", 0.0))

        if resonance >= self.resonance_threshold and entropy <= self.entropy_limit:
            return ZeroApproval(
                approved=True,
                resonance_score=resonance,
                reason="ZERO_APPROVED",
            )

        reason = "LOW_RESONANCE" if resonance < self.resonance_threshold else "HIGH_ENTROPY"
        return ZeroApproval(
            approved=False,
            resonance_score=resonance,
            reason=reason,
        )

    def force_to_zero(self) -> Dict[str, float]:
        self.reset_counter += 1
        return {
            "resonance_score": 1.0,
            "entropy_level": 0.0,
        }
