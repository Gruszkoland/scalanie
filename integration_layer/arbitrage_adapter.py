from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from core.system import AdrionCore, AdrionResult

from arbitrage.hexagon import HexagonProcessor


@dataclass
class ArbitrageAdapter:
    """Bridge between legacy arbitrage hexagon pipeline and toroidal core."""

    core: AdrionCore

    def process(self, trinity_scores: Dict[str, float], *, source: str = "arbitrage_adapter") -> Dict[str, Any]:
        hexagon = HexagonProcessor().process(trinity_scores)
        core_result: AdrionResult = self.core.process_decision(
            {
                "resonance_score": float(hexagon.combined_score),
                "entropy_level": max(0.0, 1.0 - float(hexagon.combined_score)),
                "trinity_vector": (
                    float(trinity_scores.get("material", 0.0)),
                    float(trinity_scores.get("intellectual", 0.0)),
                    float(trinity_scores.get("essential", 0.0)),
                ),
                "risk_score": 0.25 if not hexagon.approved else 0.05,
                "load_factor": 0.35 if hexagon.total_duration_ms > 250 else 0.15,
            },
            source=source,
        )
        return {
            "hexagon": hexagon.to_dict(),
            "toroidal": {
                "decision": core_result.decision,
                "approved": core_result.approved,
                "resonance_score": core_result.resonance_score,
                "entropy_level": core_result.entropy_level,
                "zero_symbolic_report": core_result.zero_symbolic_report,
                "ennead_symbolic_report": core_result.ennead_symbolic_report,
                "compressed_report": core_result.compressed_report,
            },
        }
