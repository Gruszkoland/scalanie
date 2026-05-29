from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class CompressionStyleGuide:
    """Reguly kompresji raportow: symbolic i hybrid."""

    symbolic_tokens: Dict[str, str]

    @staticmethod
    def default() -> "CompressionStyleGuide":
        return CompressionStyleGuide(
            symbolic_tokens={
                "resonance_score": "R",
                "entropy_level": "E",
                "trinity_vector": "T",
                "decision": "D",
                "approved": "A",
            }
        )

    def symbolic(self, payload: Dict[str, object]) -> str:
        parts = []
        for key, value in payload.items():
            token = self.symbolic_tokens.get(key, key[:1].upper())
            parts.append(f"{token}:{value}")
        return "|".join(parts)

    def hybrid(self, payload: Dict[str, object]) -> str:
        symbolic_blob = self.symbolic(payload)
        plain_blob = ", ".join(f"{k}={v}" for k, v in payload.items())
        return f"{symbolic_blob} || {plain_blob}"

    @staticmethod
    def compression_ratio(original: str, compressed: str) -> float:
        if not original:
            return 0.0
        return max(0.0, min(1.0, 1.0 - (len(compressed) / len(original))))
