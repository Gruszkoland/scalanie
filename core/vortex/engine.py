from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
from typing import TYPE_CHECKING, Any, Dict, List, Tuple

from core.math import Quaternion, slerp_batch

if TYPE_CHECKING:
    from core.observer import MetaObserver
    from core.zero import ZeroRouter


@dataclass
class VortexSnapshot:
    """Snapshot stanu VortexEngine po rotacji."""

    orientation: Quaternion
    resonance_score: float
    entropy_level: float
    trinity_vector: Tuple[float, float, float]
    pulse_count: int
    observer_summary: str = ""


@dataclass
class VortexEngine:
    """Silnik rotacji stanow oparty na kwaternionach."""

    orientation: Quaternion = field(default_factory=Quaternion.identity)
    trinity_vector: Tuple[float, float, float] = (0.9, 0.9, 0.9)
    history: List[VortexSnapshot] = field(default_factory=list)
    zero_router: "ZeroRouter | None" = None
    meta_observer: "MetaObserver | None" = None
    pulse_count: int = 0

    def _resonance(self) -> float:
        return max(0.0, min(1.0, sum(self.trinity_vector) / 3.0))

    def _entropy(self) -> float:
        return max(0.0, min(1.0, 1.0 - self._resonance()))

    def _calculate_resonance_from_quaternion(self, q: Quaternion) -> float:
        coherence = abs(q.dot(Quaternion.identity()))
        trinity_resonance = self._resonance()
        return max(0.0, min(1.0, (coherence * 0.6) + (trinity_resonance * 0.4)))

    def _calculate_entropy_from_quaternion(self, q: Quaternion) -> float:
        return max(0.0, min(1.0, 1.0 - self._calculate_resonance_from_quaternion(q)))

    def _project_to_trinity(self, q: Quaternion) -> Tuple[float, float, float]:
        coherence = abs(q.dot(Quaternion.identity()))
        material = min(1.0, max(0.0, coherence))
        intellectual = min(1.0, max(0.0, coherence - (abs(q.y) * 0.15)))
        essential = min(1.0, max(0.0, coherence - (abs(q.z) * 0.15)))
        return (material, intellectual, essential)

    def bind_orchestrators(self, *, zero_router: "ZeroRouter", meta_observer: "MetaObserver") -> None:
        self.zero_router = zero_router
        self.meta_observer = meta_observer

    def _notify_observer(self, snapshot: VortexSnapshot) -> str:
        if self.meta_observer is None:
            return ""
        observed = self.meta_observer.observe(
            {
                "resonance_score": snapshot.resonance_score,
                "entropy_level": snapshot.entropy_level,
                "trinity_vector": snapshot.trinity_vector,
            }
        )
        report = observed["report"]
        return report.summary_symbolic

    def rotate_to_quaternion(self, target_quaternion: Quaternion, *, steps: int = 12) -> VortexSnapshot:
        path = slerp_batch(self.orientation, target_quaternion, steps=steps)
        final_snapshot: VortexSnapshot | None = None

        for q in path[1:]:
            self.pulse_count += 1
            projected = self._project_to_trinity(q)
            prev_m, prev_i, prev_e = self.trinity_vector
            trinity = (
                (prev_m * 0.7) + (projected[0] * 0.3),
                (prev_i * 0.7) + (projected[1] * 0.3),
                (prev_e * 0.7) + (projected[2] * 0.3),
            )
            self.orientation = q
            self.trinity_vector = trinity
            snapshot = VortexSnapshot(
                orientation=q,
                resonance_score=self._resonance(),
                entropy_level=self._entropy(),
                trinity_vector=trinity,
                pulse_count=self.pulse_count,
            )
            final_snapshot = snapshot

        if final_snapshot is None:
            final_snapshot = VortexSnapshot(
                orientation=self.orientation,
                resonance_score=self._resonance(),
                entropy_level=self._entropy(),
                trinity_vector=self.trinity_vector,
                pulse_count=self.pulse_count,
            )

        final_snapshot.observer_summary = self._notify_observer(final_snapshot)
        self.history.append(final_snapshot)
        return final_snapshot

    def rotate(self, *, axis: Tuple[float, float, float], angle_rad: float, blend: float = 1.0) -> VortexSnapshot:
        target = Quaternion.from_axis_angle(axis, angle_rad)
        blended = Quaternion.slerp(self.orientation, self.orientation * target, blend)
        return self.rotate_to_quaternion(blended, steps=1)

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
            m = min(0.99, m + step)
            i = min(0.99, i + step)
            e = min(0.99, e + step)
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

    def snapshot_dict(self) -> Dict[str, Any]:
        if not self.history:
            return {
                "resonance_score": self._resonance(),
                "entropy_level": self._entropy(),
                "trinity_vector": self.trinity_vector,
                "pulse_count": self.pulse_count,
            }
        latest = self.history[-1]
        return {
            "resonance_score": latest.resonance_score,
            "entropy_level": latest.entropy_level,
            "trinity_vector": latest.trinity_vector,
            "pulse_count": latest.pulse_count,
            "observer_summary": latest.observer_summary,
        }
