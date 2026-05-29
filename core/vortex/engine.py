from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
from typing import List, Tuple

from core.math import Quaternion


@dataclass
class VortexSnapshot:
    """Snapshot stanu VortexEngine po rotacji."""

    orientation: Quaternion
    resonance_score: float
    entropy_level: float
    trinity_vector: Tuple[float, float, float]


@dataclass
class VortexEngine:
    """Silnik rotacji stanow oparty na kwaternionach."""

    orientation: Quaternion = field(default_factory=Quaternion.identity)
    trinity_vector: Tuple[float, float, float] = (0.9, 0.9, 0.9)
    history: List[VortexSnapshot] = field(default_factory=list)

    def _resonance(self) -> float:
        return max(0.0, min(1.0, sum(self.trinity_vector) / 3.0))

    def _entropy(self) -> float:
        return max(0.0, min(1.0, 1.0 - self._resonance()))

    def rotate(self, *, axis: Tuple[float, float, float], angle_rad: float, blend: float = 1.0) -> VortexSnapshot:
        target = Quaternion.from_axis_angle(axis, angle_rad)
        blended = Quaternion.slerp(self.orientation, self.orientation * target, blend)
        self.orientation = blended
        snapshot = VortexSnapshot(
            orientation=self.orientation,
            resonance_score=self._resonance(),
            entropy_level=self._entropy(),
            trinity_vector=self.trinity_vector,
        )
        self.history.append(snapshot)
        return snapshot

    def apply_perturbation(self, delta: float) -> None:
        m, i, e = self.trinity_vector
        updated = (
            max(0.0, min(1.0, m - delta)),
            max(0.0, min(1.0, i - delta * 0.5)),
            max(0.0, min(1.0, e - delta * 0.25)),
        )
        self.trinity_vector = updated

    def stabilize(self, target: float = 0.92, step: float = 0.02) -> int:
        loops = 0
        m, i, e = self.trinity_vector
        while self._resonance() < target and loops < 1000:
            loops += 1
            m = min(1.0, m + step)
            i = min(1.0, i + step)
            e = min(1.0, e + step)
            self.trinity_vector = (m, i, e)
        return loops

    def benchmark_rotation(self, iterations: int = 10000) -> dict:
        start = perf_counter()
        for _ in range(iterations):
            self.rotate(axis=(0.0, 1.0, 0.0), angle_rad=0.01, blend=0.5)
        duration = perf_counter() - start
        avg_ms = (duration / iterations) * 1000.0
        throughput = iterations / duration if duration > 0 else float("inf")
        return {
            "iterations": iterations,
            "duration_s": duration,
            "avg_ms": avg_ms,
            "throughput_rps": throughput,
        }
