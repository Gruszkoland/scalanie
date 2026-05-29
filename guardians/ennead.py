from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List

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
    reason: str
    recommendation: str


@dataclass(frozen=True)
class BaseGuardian:
    name: str
    threshold: float = 0.8
    weight: float = 1.0

    def evaluate(self, decision: Dict[str, Any]) -> GuardianVerdict:
        raise NotImplementedError


class GuardianOfUnity(BaseGuardian):
    def __init__(self) -> None:
        super().__init__(name="Unity", threshold=0.8, weight=1.15)

    def evaluate(self, decision: Dict[str, Any]) -> GuardianVerdict:
        score = float(decision.get("resonance_score", 0.0))
        passed = score >= self.threshold
        return GuardianVerdict(self.name, score, passed, "Koherencja systemu", "Synchronize" if not passed else "Proceed")


class GuardianOfHarmony(BaseGuardian):
    def __init__(self) -> None:
        super().__init__(name="Harmony", threshold=0.78, weight=1.1)

    def evaluate(self, decision: Dict[str, Any]) -> GuardianVerdict:
        trinity = tuple(float(x) for x in decision.get("trinity_vector", (0.0, 0.0, 0.0)))
        spread = max(trinity) - min(trinity) if trinity else 1.0
        score = max(0.0, min(1.0, 1.0 - spread))
        passed = score >= self.threshold
        return GuardianVerdict(self.name, score, passed, "Balans Trinity", "Rebalance Trinity" if not passed else "Proceed")


class GuardianOfRhythm(BaseGuardian):
    def __init__(self) -> None:
        super().__init__(name="Rhythm", threshold=0.75, weight=1.0)

    def evaluate(self, decision: Dict[str, Any]) -> GuardianVerdict:
        pulse = int(decision.get("pulse_count", 0))
        aligned = pulse % 3 == 0 or pulse % 9 == 0
        score = 0.9 if aligned else 0.72
        passed = score >= self.threshold
        return GuardianVerdict(self.name, score, passed, "Kadencja cyklu", "Adjust cadence" if not passed else "Proceed")


class GuardianOfCausality(BaseGuardian):
    def __init__(self) -> None:
        super().__init__(name="Causality", threshold=0.8, weight=1.1)

    def evaluate(self, decision: Dict[str, Any]) -> GuardianVerdict:
        has_source = bool(decision.get("source", ""))
        has_payload = bool(decision.get("payload", {}))
        score = 1.0 if has_source and has_payload else 0.6
        passed = score >= self.threshold
        return GuardianVerdict(self.name, score, passed, "Traceability", "Add source+payload" if not passed else "Proceed")


class GuardianOfTransparency(BaseGuardian):
    def __init__(self) -> None:
        super().__init__(name="Transparency", threshold=0.75, weight=1.0)

    def evaluate(self, decision: Dict[str, Any]) -> GuardianVerdict:
        report = str(decision.get("observer_summary", ""))
        score = 0.92 if report else 0.65
        passed = score >= self.threshold
        return GuardianVerdict(self.name, score, passed, "Observer report", "Provide symbolic report" if not passed else "Proceed")


class GuardianOfAuthenticity(BaseGuardian):
    def __init__(self) -> None:
        super().__init__(name="Authenticity", threshold=0.75, weight=1.0)

    def evaluate(self, decision: Dict[str, Any]) -> GuardianVerdict:
        entropy = float(decision.get("entropy_level", 1.0))
        score = max(0.0, min(1.0, 1.0 - entropy))
        passed = score >= self.threshold
        return GuardianVerdict(self.name, score, passed, "Signal integrity", "Reduce entropy" if not passed else "Proceed")


class GuardianOfPrivacy(BaseGuardian):
    def __init__(self) -> None:
        super().__init__(name="Privacy", threshold=0.9, weight=1.25)

    def evaluate(self, decision: Dict[str, Any]) -> GuardianVerdict:
        has_secret = bool(decision.get("has_secret", False))
        score = 0.95 if not has_secret else 0.2
        passed = score >= self.threshold
        return GuardianVerdict(self.name, score, passed, "Sensitive fields exposure", "Redact payload" if not passed else "Proceed")


class GuardianOfNonmaleficence(BaseGuardian):
    def __init__(self) -> None:
        super().__init__(name="Nonmaleficence", threshold=0.9, weight=1.3)

    def evaluate(self, decision: Dict[str, Any]) -> GuardianVerdict:
        risk = float(decision.get("risk_score", 0.0))
        score = max(0.0, min(1.0, 1.0 - risk))
        passed = score >= self.threshold
        return GuardianVerdict(self.name, score, passed, "Operational safety", "Escalate to Zero" if not passed else "Proceed")


class GuardianOfSustainability(BaseGuardian):
    def __init__(self) -> None:
        super().__init__(name="Sustainability", threshold=0.75, weight=1.0)

    def evaluate(self, decision: Dict[str, Any]) -> GuardianVerdict:
        load = float(decision.get("load_factor", 0.2))
        score = max(0.0, min(1.0, 1.0 - load))
        passed = score >= self.threshold
        return GuardianVerdict(self.name, score, passed, "Resource pressure", "Reduce load" if not passed else "Proceed")


class EnneadCouncil:
    """Rada 9 opiekunow z logika konsensusu i twardym veto."""

    def __init__(self, threshold: float = 0.8) -> None:
        self.threshold = threshold
        self.guardians: List[BaseGuardian] = [
            GuardianOfUnity(),
            GuardianOfHarmony(),
            GuardianOfRhythm(),
            GuardianOfCausality(),
            GuardianOfTransparency(),
            GuardianOfAuthenticity(),
            GuardianOfPrivacy(),
            GuardianOfNonmaleficence(),
            GuardianOfSustainability(),
        ]

    def evaluate(self, guardian_scores: Dict[str, float]) -> Dict[str, object]:
        """Compatibility path: evaluate map of guardian scores."""
        verdicts: List[GuardianVerdict] = []
        for name in GUARDIAN_NAMES:
            score = float(guardian_scores.get(name, 0.0))
            verdicts.append(
                GuardianVerdict(
                    guardian=name,
                    score=score,
                    passed=score >= self.threshold,
                    reason="Score map evaluation",
                    recommendation="Proceed" if score >= self.threshold else "Escalate",
                )
            )

        return self._finalize(verdicts)

    def evaluate_decision(self, decision: Dict[str, Any]) -> Dict[str, object]:
        """Production path: run all 9 guardians against one decision."""
        verdicts = [guardian.evaluate(decision) for guardian in self.guardians]
        return self._finalize(verdicts)

    def _finalize(self, verdicts: List[GuardianVerdict]) -> Dict[str, object]:

        violations = [v.guardian for v in verdicts if not v.passed]
        critical_violation = any(v in CRITICAL_GUARDIANS for v in violations)
        decision = "DENY" if critical_violation or len(violations) >= 2 else "PROCEED"
        weighted_numerator = 0.0
        weighted_denominator = 0.0
        for verdict in verdicts:
            weight = next((g.weight for g in self.guardians if g.name == verdict.guardian), 1.0)
            weighted_numerator += verdict.score * weight
            weighted_denominator += weight
        weighted_score = (weighted_numerator / weighted_denominator) if weighted_denominator else 0.0

        return {
            "decision": decision,
            "violations": violations,
            "critical_veto": critical_violation,
            "verdicts": verdicts,
            "weighted_score": weighted_score,
        }

    @staticmethod
    def to_guardian_scores(values: Iterable[float]) -> Dict[str, float]:
        values_list = list(values)
        result: Dict[str, float] = {}
        for i, name in enumerate(GUARDIAN_NAMES):
            result[name] = float(values_list[i]) if i < len(values_list) else 0.0
        return result
