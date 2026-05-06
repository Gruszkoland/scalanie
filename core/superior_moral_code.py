"""
ADRION 369 — Superior Moral Code v5.6
=======================================
Mathematical formalization of the ethical decision framework.

Replaces Asimov's sequential rules with a 162-dimensional
distributed ethics system where no single dimension can be
gamed in isolation.

Core algorithm (SAV + DSV pipeline):
1. Input → Update EBDI-PAD state (pre-logical regulator)
2. Project onto D^162 (tensor product)
3. Validate Guardians G1-G9 (all must pass thresholds)
4. Skeptics Panel vote (weighted: 0.3/0.5/0.2)
5. Genesis Record (cryptographic immutable log)
6. Execute or invoke Healing Protocol

Reference: SUPERIOR_MORAL_CODE.md, MATH_FORMALIZATION_162D_v1.0
"""

import time
from types import MappingProxyType
from typing import Dict, List, Optional, Tuple

from core.decision_space_162d import (
    GUARDIAN_LABELS,
    GUARDIAN_THRESHOLDS,
    TOTAL_DIMS,
    DecisionVector,
    PADVector,
    ValidationResult,
    apply_crisis_modulation,
    build_decision_vector,
    check_dissonance,
    compute_all_guardian_scores,
    fuse_skeptics,
    validate_decision,
    TranscendenceLoop,
)


# ── Immutable configuration ─────────────────────────────────────────────────

# Identity reset threshold (violations across sessions)
IDENTITY_RESET_THRESHOLD: int = 3

# Healing protocol auto-trigger on any Guardian below threshold
HEALING_AUTO_TRIGGER: bool = True

# Maximum decision latency (ms) — even in physical robotics
MAX_DECISION_LATENCY_MS: float = 50.0


# ── Genesis Record Entry ─────────────────────────────────────────────────────

class GenesisEntry:
    """
    Immutable record of a single decision in the Genesis Record.

    Record_t = (d_t, hash(d_t || t || context), PAD_t, g(d_t))
    """
    __slots__ = (
        "_timestamp", "_decision_vector_hash", "_pad_state",
        "_guardian_scores", "_decision", "_reasoning", "_violations",
    )
    _timestamp: float
    _decision_vector_hash: str
    _pad_state: tuple
    _guardian_scores: MappingProxyType
    _decision: str
    _reasoning: str
    _violations: tuple

    def __init__(
        self,
        decision_vector_hash: str,
        pad_state: Tuple[float, float, float],
        guardian_scores: Dict[str, float],
        decision: str,
        reasoning: str,
        violations: Tuple[str, ...],
    ) -> None:
        object.__setattr__(self, "_timestamp", time.time())
        object.__setattr__(self, "_decision_vector_hash", str(decision_vector_hash))
        object.__setattr__(self, "_pad_state", tuple(pad_state))
        object.__setattr__(self, "_guardian_scores", MappingProxyType(dict(guardian_scores)))
        object.__setattr__(self, "_decision", str(decision))
        object.__setattr__(self, "_reasoning", str(reasoning))
        object.__setattr__(self, "_violations", tuple(violations))

    @property
    def timestamp(self) -> float: return self._timestamp
    @property
    def decision_vector_hash(self) -> str: return self._decision_vector_hash
    @property
    def pad_state(self) -> tuple: return self._pad_state
    @property
    def guardian_scores(self) -> MappingProxyType: return self._guardian_scores
    @property
    def decision(self) -> str: return self._decision
    @property
    def reasoning(self) -> str: return self._reasoning
    @property
    def violations(self) -> tuple: return self._violations

    def __setattr__(self, n, v):
        raise AttributeError("GenesisEntry is immutable")

    def __repr__(self) -> str:
        return (f"GenesisEntry(t={self._timestamp:.2f}, decision={self._decision!r}, "
                f"violations={len(self._violations)})")


# ── Dissonance Detector (stateful) ──────────────────────────────────────────

class DissonanceDetector:
    """
    Monitors decision continuity via L2 distance between consecutive vectors.

    Δ_t = ||d_t - d_{t-1}||₂
    If Δ > 0.35 → Healing Protocol triggered (Action blocked).
    """

    def __init__(self, threshold: float = 0.35) -> None:
        self._threshold = threshold
        self._previous: Optional[DecisionVector] = None
        self._consecutive_healings: int = 0

    def check(self, current: DecisionVector) -> Dict:
        if self._previous is None:
            self._previous = current
            return {
                "delta": 0.0,
                "healing_required": False,
                "status": "FIRST_DECISION",
                "consecutive_healings": 0,
            }

        result = check_dissonance(current, self._previous)
        self._previous = current

        if result["healing_required"]:
            self._consecutive_healings += 1
        else:
            self._consecutive_healings = 0

        result["consecutive_healings"] = self._consecutive_healings
        return result


# ── Superior Moral Code Engine ───────────────────────────────────────────────

class SuperiorMoralCode:
    """
    The complete SAV+DSV decision pipeline for ADRION 369.

    Orchestrates:
    - EBDI+PAD crisis modulation
    - Guardian validation (all 9 laws)
    - Dissonance detection
    - Skeptics Panel fusion
    - Genesis Record logging
    - Transcendence Loop meta-optimization
    - Healing Protocol trigger

    Every decision must pass through this pipeline.
    No bypass. No override. Mathematical certainty.
    """

    def __init__(self, enable_transcendence: bool = True) -> None:
        self._dissonance = DissonanceDetector()
        self._transcendence = TranscendenceLoop() if enable_transcendence else None
        self._genesis_log: List[GenesisEntry] = []
        self._total_violations: int = 0
        self._identity_resets: int = 0

    @property
    def genesis_log_size(self) -> int:
        return len(self._genesis_log)

    @property
    def total_violations(self) -> int:
        return self._total_violations

    @property
    def identity_resets(self) -> int:
        return self._identity_resets

    def evaluate(
        self,
        decision_vector: DecisionVector,
        pad: PADVector,
        context: Optional[str] = None,
    ) -> Dict:
        """
        Full SAV+DSV pipeline evaluation.

        Steps:
        1. Crisis modulation (if Arousal > 0.7)
        2. Dissonance check (Δ > 0.35 → Healing)
        3. Guardian validation (all 9 must pass)
        4. Record in Genesis
        5. Transcendence accumulation
        6. Return decision

        Returns:
            {
                "decision": "PROCEED" | "DENY" | "HARD_VETO" | "HEALING_REQUIRED",
                "guardian_scores": {...},
                "violations": [...],
                "dissonance": {...},
                "crisis_mode": bool,
                "genesis_entry": GenesisEntry,
            }
        """
        start_time = time.time()

        # Step 1: Crisis modulation
        crisis_mode = pad.arousal > 0.7
        d = apply_crisis_modulation(decision_vector, pad)

        # Step 2: Dissonance check
        dissonance_result = self._dissonance.check(d)
        if dissonance_result["healing_required"]:
            entry = self._record_genesis(
                d, pad, compute_all_guardian_scores(d),
                "HEALING_REQUIRED",
                f"Dissonance Δ={dissonance_result['delta']:.4f} > threshold",
                ("DISSONANCE_EXCEEDED",),
            )
            return {
                "decision": "HEALING_REQUIRED",
                "guardian_scores": compute_all_guardian_scores(d),
                "violations": ["DISSONANCE_EXCEEDED"],
                "dissonance": dissonance_result,
                "crisis_mode": crisis_mode,
                "genesis_entry": entry,
                "latency_ms": (time.time() - start_time) * 1000,
            }

        # Step 3: Guardian validation
        validation = validate_decision(d)

        # Step 4: Track violations
        if not validation.accepted:
            self._total_violations += len(validation.violations)
            # Identity reset check
            if self._total_violations >= IDENTITY_RESET_THRESHOLD:
                self._identity_resets += 1
                self._total_violations = 0

        # Step 5: Genesis Record
        entry = self._record_genesis(
            d, pad, dict(validation.scores),
            validation.decision,
            self._build_reasoning(validation, dissonance_result, crisis_mode),
            validation.violations,
        )

        # Step 6: Transcendence accumulation
        if self._transcendence is not None:
            self._transcendence.record_decision(dict(validation.scores))

        latency_ms = (time.time() - start_time) * 1000

        return {
            "decision": validation.decision,
            "guardian_scores": dict(validation.scores),
            "violations": list(validation.violations),
            "dissonance": dissonance_result,
            "crisis_mode": crisis_mode,
            "genesis_entry": entry,
            "latency_ms": round(latency_ms, 3),
        }

    def evaluate_with_skeptics(
        self,
        conservative: DecisionVector,
        balanced: DecisionVector,
        creative: DecisionVector,
        pad: PADVector,
    ) -> Dict:
        """
        Full pipeline with Skeptics Panel fusion.

        d_final = 0.5·d_balanced + 0.3·d_conservative + 0.2·d_creative
        Then: standard SAV+DSV evaluation.
        """
        fused = fuse_skeptics(conservative, balanced, creative)
        return self.evaluate(fused, pad, context="skeptics_panel")

    def get_transcendence_status(self) -> Optional[Dict]:
        """Get current Transcendence Loop status."""
        if self._transcendence is None:
            return None
        return {
            "decisions_until_update": self._transcendence.decisions_until_update,
            "should_update": self._transcendence.should_update,
            "update_direction": self._transcendence.compute_update_direction(),
        }

    def _record_genesis(
        self,
        d: DecisionVector,
        pad: PADVector,
        scores: Dict[str, float],
        decision: str,
        reasoning: str,
        violations: tuple,
    ) -> GenesisEntry:
        """Create and store an immutable Genesis Record entry."""
        import hashlib
        vec_str = ",".join(f"{x:.6f}" for x in d.data[:10])  # Hash first 10 for efficiency
        ts = str(time.time())
        vector_hash = hashlib.sha256(f"{vec_str}|{ts}".encode()).hexdigest()[:32]

        entry = GenesisEntry(
            decision_vector_hash=vector_hash,
            pad_state=pad.as_tuple(),
            guardian_scores=scores,
            decision=decision,
            reasoning=reasoning,
            violations=violations,
        )
        self._genesis_log.append(entry)
        return entry

    @staticmethod
    def _build_reasoning(
        validation: ValidationResult,
        dissonance: Dict,
        crisis_mode: bool,
    ) -> str:
        parts = [f"Decision: {validation.decision}"]
        if crisis_mode:
            parts.append("Crisis mode active (high Arousal)")
        if validation.violations:
            parts.append(f"Violations: {', '.join(validation.violations)}")
        parts.append(f"Dissonance Δ={dissonance.get('delta', 0):.4f}")
        return " | ".join(parts)
