from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

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
    compressed_report: str
    recommendation: str


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

    def process_decision(self, payload: Dict[str, Any], *, source: str = "adrion_core") -> AdrionResult:
        safe_payload = self.shadow.redact(payload)
        axis = payload.get("axis", (0.0, 1.0, 0.0))
        angle_rad = float(payload.get("angle_rad", 0.05))
        blend = float(payload.get("blend", 0.7))

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
                "resonance_score": float(routed_payload.get("resonance_score", 0.0)),
                "entropy_level": float(routed_payload.get("entropy_level", 1.0)),
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

        compressed_report = self.style.hybrid(
            {
                "resonance_score": round(merged["resonance_score"], 4),
                "entropy_level": round(merged["entropy_level"], 4),
                "decision": decision,
                "approved": approved,
            }
        )

        recommendation = "Proceed"
        if not approved:
            recommendation = "Escalate to Zero"
            self.zero_router.force_to_zero(reason="ENNEAD_DENY")

        return AdrionResult(
            decision=decision,
            approved=approved,
            resonance_score=merged["resonance_score"],
            entropy_level=merged["entropy_level"],
            compressed_report=compressed_report,
            recommendation=recommendation,
        )
