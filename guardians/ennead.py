from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List

GUARDIAN_NAMES = (
    "Unity",
    "Harmony",
    "Rhythm",
    "Causality",
    "Transparency",
    "Authenticity",
    "Privacy",
    "Nonmaleficence",
    "Sustainability",
)
CRITICAL_GUARDIANS = {"Privacy", "Nonmaleficence"}


@dataclass(frozen=True)
class GuardianVerdict:
    """Werdykt pojedynczego opiekuna."""

    guardian: str
    score: float
    passed: bool


class EnneadCouncil:
    """Rada 9 opiekunow z logika konsensusu i twardym veto."""

    def __init__(self, threshold: float = 0.8) -> None:
        self.threshold = threshold

    def evaluate(self, guardian_scores: Dict[str, float]) -> Dict[str, object]:
        verdicts: List[GuardianVerdict] = []
        for name in GUARDIAN_NAMES:
            score = float(guardian_scores.get(name, 0.0))
            verdicts.append(GuardianVerdict(name, score, score >= self.threshold))

        violations = [v.guardian for v in verdicts if not v.passed]
        critical_violation = any(v in CRITICAL_GUARDIANS for v in violations)
        decision = "DENY" if critical_violation or len(violations) >= 2 else "PROCEED"

        return {
            "decision": decision,
            "violations": violations,
            "critical_veto": critical_violation,
            "verdicts": verdicts,
        }

    @staticmethod
    def to_guardian_scores(values: Iterable[float]) -> Dict[str, float]:
        values_list = list(values)
        result: Dict[str, float] = {}
        for i, name in enumerate(GUARDIAN_NAMES):
            result[name] = float(values_list[i]) if i < len(values_list) else 0.0
        return result
