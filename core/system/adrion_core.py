from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, cast

from compression import CompressionStyleGuide
from guardians import EnneadCouncil

from core.observer import MetaObserver
from core.shadow_protocol import ShadowProtocol
from core.unity_field import UnityField
from core.vortex import VortexEngine
from core.zero import ZeroRouter


@dataclass(frozen=True)
class AdrionResult:
    decision: str
    approved: bool
    resonance_score: float
    entropy_level: float
    zero_symbolic_report: str
    ennead_symbolic_report: str
    compressed_report: str
    recommendation: str
    guardian_weighted_score: float


class AdrionCore:
    """Centralny integrator: Zero + Vortex + Observer + Ennead."""

    def __init__(self) -> None:
        self.zero_router = ZeroRouter()
        self.style = CompressionStyleGuide.default()
        self.meta_observer = MetaObserver(zero_router=self.zero_router, compression_style=self.style)
        self.vortex = VortexEngine()
        self.vortex.bind_orchestrators(zero_router=self.zero_router, meta_observer=self.meta_observer)
        self.ennead = EnneadCouncil()
        self.unity = UnityField()
        self.shadow = ShadowProtocol()

    @staticmethod
    def _ensure_tuple3(values: Any, fallback: tuple[float, float, float]) -> tuple[float, float, float]:
        try:
            parsed = tuple(float(v) for v in values)
        except TypeError:
            return fallback
        return parsed if len(parsed) == 3 else fallback

    def process_decision(self, payload: Dict[str, Any], *, source: str = "adrion_core") -> AdrionResult:
        # All decisions enter through AdrionCore and are pre-checked by ZeroRouter.
        safe_payload = self.shadow.redact(payload)
        axis = self._ensure_tuple3(payload.get("axis", (0.0, 1.0, 0.0)), (0.0, 1.0, 0.0))
        angle_rad = float(payload.get("angle_rad", 0.05))
        blend = float(payload.get("blend", 0.7))

        incoming = {
            "resonance_score": float(payload.get("resonance_score", 0.9)),
            "entropy_level": float(payload.get("entropy_level", 0.1)),
            "trinity_vector": self._ensure_tuple3(payload.get("trinity_vector", (0.9, 0.9, 0.9)), (0.9, 0.9, 0.9)),
        }
        pre_zero = self.zero_router.route(incoming, auto_force_to_zero=False)

        vortex_snapshot = self.vortex.rotate(axis=axis, angle_rad=angle_rad, blend=blend)

        observed = self.meta_observer.observe(
            {
                "resonance_score": vortex_snapshot.resonance_score,
                "entropy_level": vortex_snapshot.entropy_level,
                "trinity_vector": vortex_snapshot.trinity_vector,
            }
        )
        report = observed["report"]
        routed_payload = observed["routed_payload"]

        merged = self.unity.merge(
            zero={
                "resonance_score": float(pre_zero.payload.get("resonance_score", routed_payload.get("resonance_score", 0.0))),
                "entropy_level": float(pre_zero.payload.get("entropy_level", routed_payload.get("entropy_level", 1.0))),
            },
            observer={
                "resonance_score": report.resonance_score,
                "entropy_level": report.entropy_level,
            },
            vortex={
                "resonance_score": vortex_snapshot.resonance_score,
                "entropy_level": vortex_snapshot.entropy_level,
            },
        )

        decision_context = {
            "source": source,
            "payload": safe_payload,
            "resonance_score": merged["resonance_score"],
            "entropy_level": merged["entropy_level"],
            "trinity_vector": vortex_snapshot.trinity_vector,
            "pulse_count": vortex_snapshot.pulse_count,
            "observer_summary": report.summary_symbolic,
            "has_secret": any("token" in k.lower() or "secret" in k.lower() for k in safe_payload),
            "risk_score": float(payload.get("risk_score", merged["entropy_level"])),
            "load_factor": float(payload.get("load_factor", 0.2)),
        }

        council_result = self.ennead.evaluate_decision(decision_context)
        decision = str(council_result["decision"])
        approved = decision == "PROCEED"
        weighted_score_raw = council_result.get("weighted_score", 0.0)
        weighted_score = float(cast(float, weighted_score_raw))
        hard_block = bool(cast(bool, council_result.get("hard_block", False)))

        post_zero = self.zero_router.route(
            {
                "resonance_score": merged["resonance_score"],
                "entropy_level": merged["entropy_level"],
                "trinity_vector": vortex_snapshot.trinity_vector,
            },
            auto_force_to_zero=not approved,
        )
        final_resonance = float(post_zero.payload.get("resonance_score", merged["resonance_score"]))
        final_entropy = float(post_zero.payload.get("entropy_level", merged["entropy_level"]))
        final_approved = approved and post_zero.approval.approved

        zero_symbolic_report = self.style.symbolic(
            {
                "resonance_score": round(final_resonance, 4),
                "entropy_level": round(final_entropy, 4),
                "approved": final_approved,
                "decision": "ZERO_APPROVED" if post_zero.approval.approved else "ZERO_BLOCKED",
            }
        )
        ennead_symbolic_report = self.style.symbolic(
            {
                "decision": decision,
                "approved": approved,
                "guardian_weighted": round(weighted_score, 4),
                "critical_veto": bool(cast(bool, council_result.get("critical_veto", False))),
                "hard_block": hard_block,
            }
        )

        compressed_report = self.style.hybrid(
            {
                "resonance_score": round(final_resonance, 4),
                "entropy_level": round(final_entropy, 4),
                "decision": decision,
                "approved": final_approved,
                "observer_summary": report.summary_symbolic,
                "guardian_weighted": round(weighted_score, 4),
                "zero_report": zero_symbolic_report,
                "ennead_report": ennead_symbolic_report,
            }
        )

        recommendation = "Proceed"
        if not final_approved:
            recommendation = "Escalate to Zero"
            self.zero_router.force_to_zero(reason="ENNEAD_DENY")

        return AdrionResult(
            decision=decision,
            approved=final_approved,
            resonance_score=final_resonance,
            entropy_level=final_entropy,
            zero_symbolic_report=zero_symbolic_report,
            ennead_symbolic_report=ennead_symbolic_report,
            compressed_report=compressed_report,
            recommendation=recommendation,
            guardian_weighted_score=weighted_score,
        )
