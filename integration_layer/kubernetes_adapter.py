from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from core.system import AdrionCore


@dataclass
class KubernetesAdapter:
    """Converts toroidal decision outputs to deploy gate metadata."""

    core: AdrionCore

    def evaluate_deploy(self, deploy_context: Dict[str, Any]) -> Dict[str, Any]:
        result = self.core.process_decision(deploy_context, source="kubernetes")
        gate = "allow" if result.approved else "deny"
        return {
            "deploy_gate": gate,
            "annotations": {
                "adrion.decision": result.decision,
                "adrion.recommendation": result.recommendation,
                "adrion.zero.report": result.zero_symbolic_report,
                "adrion.ennead.report": result.ennead_symbolic_report,
                "adrion.guardian.weighted": f"{result.guardian_weighted_score:.4f}",
            },
            "summary": result.compressed_report,
        }
