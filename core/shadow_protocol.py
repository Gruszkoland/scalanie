from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass
class ShadowProtocol:
    """Protokol cienia: maskowanie metadanych i plan resilience."""

    mask_char: str = "*"

    def redact(self, payload: Dict[str, object]) -> Dict[str, object]:
        redacted: Dict[str, object] = {}
        for key, value in payload.items():
            if "token" in key.lower() or "secret" in key.lower():
                redacted[key] = self.mask_char * 8
            else:
                redacted[key] = value
        return redacted

    def resilience_hint(self, resonance_score: float) -> str:
        if resonance_score >= 0.92:
            return "STEALTH_STABLE"
        if resonance_score >= 0.80:
            return "STEALTH_MONITOR"
        return "STEALTH_ESCALATE_TO_ZERO"
