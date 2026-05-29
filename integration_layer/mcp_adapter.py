from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from core.system import AdrionCore


@dataclass
class McpAdapter:
    """Maps MCP-like envelopes to AdrionCore decision contract."""

    core: AdrionCore

    def from_mcp_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        payload = request.get("payload", {})
        source = str(request.get("source", "mcp"))
        result = self.core.process_decision(payload, source=f"mcp::{source}")
        return {
            "status": "ok" if result.approved else "blocked",
            "decision": result.decision,
            "recommendation": result.recommendation,
            "reports": {
                "zero": result.zero_symbolic_report,
                "ennead": result.ennead_symbolic_report,
                "hybrid": result.compressed_report,
            },
            "metrics": {
                "resonance_score": result.resonance_score,
                "entropy_level": result.entropy_level,
                "guardian_weighted_score": result.guardian_weighted_score,
            },
        }
