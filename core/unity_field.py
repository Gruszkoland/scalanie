from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass
class UnityField:
    """Pole unifikacji metryk z wielu warstw systemu."""

    def merge(self, *, zero: Dict[str, float], observer: Dict[str, float], vortex: Dict[str, float]) -> Dict[str, float]:
        resonance = (zero.get("resonance_score", 0.0) + observer.get("resonance_score", 0.0) + vortex.get("resonance_score", 0.0)) / 3.0
        entropy = (zero.get("entropy_level", 0.0) + observer.get("entropy_level", 0.0) + vortex.get("entropy_level", 0.0)) / 3.0
        return {
            "resonance_score": max(0.0, min(1.0, resonance)),
            "entropy_level": max(0.0, min(1.0, entropy)),
        }
