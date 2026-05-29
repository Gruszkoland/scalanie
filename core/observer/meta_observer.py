from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Tuple

from compression import CompressionStyleGuide

from core.zero import ZeroRouter


@dataclass(frozen=True)
class ObserverReport:
    """Raport obserwatora z decyzja o eskalacji."""

    resonance_score: float
    entropy_level: float
    trinity_vector: Tuple[float, float, float]
    escalate_to_zero: bool
    summary_symbolic: str


class MetaObserver:
    """Modul samoobserwacji koherencji systemu."""

    def __init__(
        self,
        *,
        resonance_floor: float = 0.75,
        entropy_ceiling: float = 0.25,
        zero_router: ZeroRouter | None = None,
        compression_style: CompressionStyleGuide | None = None,
        force_resonance_floor: float | None = None,
        force_entropy_ceiling: float | None = None,
    ) -> None:
        self.resonance_floor = resonance_floor
        self.entropy_ceiling = entropy_ceiling
        self.force_resonance_floor = (
            force_resonance_floor
            if force_resonance_floor is not None
            else 0.0
        )
        self.force_entropy_ceiling = (
            force_entropy_ceiling
            if force_entropy_ceiling is not None
            else 1.0
        )
        self.zero_router = zero_router or ZeroRouter()
        self.compression_style = compression_style or CompressionStyleGuide.default()

    @staticmethod
    def _normalize_trinity(trinity_vector: Any) -> Tuple[float, float, float]:
        try:
            values = tuple(float(x) for x in trinity_vector)
        except TypeError as exc:
            raise ValueError("trinity_vector musi byc iterowalny") from exc
        if len(values) != 3:
            raise ValueError("trinity_vector musi miec dokladnie 3 skladowe")
        return values  # type: ignore[return-value]

    def analyze_snapshot(self, snapshot: Dict[str, Any]) -> ObserverReport:
        trinity = self._normalize_trinity(snapshot.get("trinity_vector", (0.0, 0.0, 0.0)))
        resonance = float(snapshot.get("resonance_score", sum(trinity) / 3.0))
        entropy = float(snapshot.get("entropy_level", max(0.0, 1.0 - resonance)))

        escalate = resonance < self.resonance_floor or entropy > self.entropy_ceiling
        symbolic = self.compression_style.symbolic(
            {
                "resonance_score": round(resonance, 3),
                "entropy_level": round(entropy, 3),
                "trinity_vector": tuple(round(x, 3) for x in trinity),
                "decision": "ESCALATE" if escalate else "STABLE",
            }
        )

        return ObserverReport(
            resonance_score=resonance,
            entropy_level=entropy,
            trinity_vector=trinity,
            escalate_to_zero=escalate,
            summary_symbolic=symbolic,
        )

    def observe_and_route(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        report = self.analyze_snapshot(snapshot)
        if report.escalate_to_zero:
            severe = (
                report.resonance_score < self.force_resonance_floor
                and report.entropy_level > self.force_entropy_ceiling
            )
            routed = self.zero_router.route(dict(snapshot), auto_force_to_zero=severe)
            routed_payload = routed.payload
            zero_approved = routed.approval.approved

            if not severe and not routed.approval.approved:
                # Soft correction improves coherence without hard reset.
                corrected = dict(snapshot)
                corrected["resonance_score"] = max(report.resonance_score, self.resonance_floor)
                corrected["entropy_level"] = min(report.entropy_level, self.entropy_ceiling)
                routed_payload = corrected
                zero_approved = True

            return {
                "report": report,
                "routed_payload": routed_payload,
                "zero_approved": zero_approved,
            }
        return {
            "report": report,
            "routed_payload": snapshot,
            "zero_approved": True,
        }

    def observe(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """Backward-compatible alias used by orchestration modules."""
        return self.observe_and_route(snapshot)
