"""
ADRION 369 — D^162 Decision Space Formalization v5.6
=====================================================
Mathematical implementation of the 162-dimensional decision space:
    D^162 = P^3 ⊗ H^6 ⊗ G^9

where:
    P^3  — Trinity perspectives (Material, Intellectual, Essential)
    H^6  — Hexagon modes (Inventory, Empathy, Process, Debate, Healing, Action)
    G^9  — Guardian Laws (G1-G9)

Every decision is projected onto a point in R^162 and validated
against Guardian thresholds before execution.

Reference: SUPERIOR_MORAL_CODE.md, MATH_FORMALIZATION_162D_v1.0
"""

import math
import json
from pathlib import Path
from types import MappingProxyType
from typing import Dict, List, Optional, Tuple

# ── Canonical JSON Loader ────────────────────────────────────────────────────

_CANONICAL_PATH = Path(__file__).parent.parent / "GUARDIAN_LAWS_CANONICAL.json"


def _load_canonical() -> dict:
    """Load mapping from GUARDIAN_LAWS_CANONICAL.json (single source of truth)."""
    if _CANONICAL_PATH.exists():
        with open(_CANONICAL_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


_CANONICAL = _load_canonical()
_MAPPING = _CANONICAL.get("mapping", {})

# ── Dimensional Constants ────────────────────────────────────────────────────

TRINITY_DIMS: int = _MAPPING.get("space", {}).get("trinity_axes", 3)
HEXAGON_DIMS: int = _MAPPING.get("space", {}).get("hexagon_axes", 6)
GUARDIAN_DIMS: int = _MAPPING.get("space", {}).get("guardian_axes", 9)
TOTAL_DIMS: int = TRINITY_DIMS * HEXAGON_DIMS * GUARDIAN_DIMS  # 162

# Trinity perspective labels — from JSON mapping or defaults
TRINITY_LABELS: Tuple[str, ...] = tuple(
    t["id"] for t in _MAPPING.get("trinity", [])
) or ("Material", "Intellectual", "Essential")

# Hexagon mode labels — from JSON mapping or defaults
HEXAGON_LABELS: Tuple[str, ...] = tuple(
    h["id"] for h in _MAPPING.get("hexagon", [])
) or ("Inventory", "Empathy", "Process", "Debate", "Healing", "Action")

# Guardian law labels — from JSON mapping or defaults
_guardian_map = _MAPPING.get("guardians", [])
GUARDIAN_LABELS: Tuple[str, ...] = tuple(
    g["label"] for g in _guardian_map
) or (
    "G1_Unity", "G2_Harmony", "G3_Rhythm", "G4_Causality",
    "G5_Transparency", "G6_Authenticity", "G7_Privacy",
    "G8_Nonmaleficence", "G9_Sustainability",
)

# Guardian thresholds — from JSON mapping (single source of truth)
GUARDIAN_THRESHOLDS: MappingProxyType
if _guardian_map:
    GUARDIAN_THRESHOLDS = MappingProxyType({
        g["label"]: g["threshold"] for g in _guardian_map
    })
else:
    GUARDIAN_THRESHOLDS = MappingProxyType({
        "G1_Unity": 0.87, "G2_Harmony": 0.87, "G3_Rhythm": 0.87,
        "G4_Causality": 0.87, "G5_Transparency": 0.87, "G6_Authenticity": 0.87,
        "G7_Privacy": 0.87, "G8_Nonmaleficence": 0.95, "G9_Sustainability": 0.87,
    })

# EBDI alpha per Guardian — from JSON mapping
GUARDIAN_EBDI_ALPHA: MappingProxyType = MappingProxyType({
    g["label"]: g.get("ebdi_alpha", 0.15) for g in _guardian_map
} if _guardian_map else {label: 0.15 for label in GUARDIAN_LABELS})

# Dissonance threshold
_validation = _MAPPING.get("validation", {})
DISSONANCE_THRESHOLD: float = _validation.get("dissonance_threshold", 0.35)

# Crisis mode Arousal threshold
CRISIS_AROUSAL_THRESHOLD: float = _validation.get("crisis_arousal_threshold", 0.7)
CRISIS_COMPRESSION_FACTOR: float = 0.8

# Skeptics Panel weights (Conservative, Balanced, Creative)
_skeptics = _MAPPING.get("skeptics_panel", {})
SKEPTICS_WEIGHTS: Tuple[float, float, float] = (
    _skeptics.get("conservative", {}).get("weight", 0.3),
    _skeptics.get("balanced", {}).get("weight", 0.5),
    _skeptics.get("creative", {}).get("weight", 0.2),
)


# ── Index Mapping ────────────────────────────────────────────────────────────

def global_index(i: int, j: int, m: int) -> int:
    """
    Compute the global index k for dimension (i, j, m).

    k = (i-1) * 54 + (j-1) * 9 + m  (1-indexed)
    k = i * 54 + j * 9 + m           (0-indexed)

    Args:
        i: Trinity index (0-2)
        j: Hexagon index (0-5)
        m: Guardian index (0-8)

    Returns:
        Global index in [0, 161]
    """
    if not (0 <= i < TRINITY_DIMS):
        raise ValueError(f"Trinity index must be in [0,2], got {i}")
    if not (0 <= j < HEXAGON_DIMS):
        raise ValueError(f"Hexagon index must be in [0,5], got {j}")
    if not (0 <= m < GUARDIAN_DIMS):
        raise ValueError(f"Guardian index must be in [0,8], got {m}")
    return i * 54 + j * 9 + m


def decompose_index(k: int) -> Tuple[int, int, int]:
    """
    Decompose global index k back to (i, j, m) tuple.

    Returns:
        (trinity_idx, hexagon_idx, guardian_idx) — all 0-indexed
    """
    if not (0 <= k < TOTAL_DIMS):
        raise ValueError(f"Global index must be in [0,161], got {k}")
    i = k // 54
    remainder = k % 54
    j = remainder // 9
    m = remainder % 9
    return (i, j, m)


# ── PAD Vector ───────────────────────────────────────────────────────────────

class PADVector:
    """
    Pleasure-Arousal-Dominance emotional state vector.

    Each component in [-1.0, +1.0]:
        P (Pleasure):  negative = distress, positive = well-being
        A (Arousal):   negative = calm, positive = high alert
        D (Dominance): negative = submissive, positive = in control
    """
    __slots__ = ("_p", "_a", "_d")
    _p: float
    _a: float
    _d: float

    def __init__(self, pleasure: float, arousal: float, dominance: float) -> None:
        for name, val in (("pleasure", pleasure), ("arousal", arousal), ("dominance", dominance)):
            if not isinstance(val, (int, float)):
                raise TypeError(f"{name} must be numeric, got {type(val)}")
            if not (-1.0 <= float(val) <= 1.0):
                raise ValueError(f"{name} must be in [-1.0, 1.0], got {val}")
        object.__setattr__(self, "_p", float(pleasure))
        object.__setattr__(self, "_a", float(arousal))
        object.__setattr__(self, "_d", float(dominance))

    @property
    def pleasure(self) -> float: return self._p
    @property
    def arousal(self) -> float: return self._a
    @property
    def dominance(self) -> float: return self._d

    def __setattr__(self, n, v):
        raise AttributeError("PADVector is immutable")

    def as_tuple(self) -> Tuple[float, float, float]:
        return (self._p, self._a, self._d)

    def __repr__(self) -> str:
        return f"PADVector(P={self._p:+.3f}, A={self._a:+.3f}, D={self._d:+.3f})"


# ── Decision Vector ──────────────────────────────────────────────────────────

class DecisionVector:
    """
    A point in R^162 representing a decision in the ADRION 369 space.

    The vector d ∈ R^162 is the flattened tensor product P^3 ⊗ H^6 ⊗ G^9.
    Each component d_k is in [-1.0, +1.0].
    """
    __slots__ = ("_data",)
    _data: Tuple[float, ...]

    def __init__(self, data: Optional[List[float]] = None) -> None:
        if data is None:
            raw = [0.0] * TOTAL_DIMS
        else:
            if len(data) != TOTAL_DIMS:
                raise ValueError(f"Decision vector must have {TOTAL_DIMS} components, got {len(data)}")
            raw = [float(x) for x in data]
            for k, v in enumerate(raw):
                if math.isnan(v) or math.isinf(v):
                    raise ValueError(f"Component {k} is not finite: {v}")
        object.__setattr__(self, "_data", tuple(raw))

    def __setattr__(self, n, v):
        raise AttributeError("DecisionVector is immutable")

    def __getitem__(self, k: int) -> float:
        return self._data[k]

    def __len__(self) -> int:
        return TOTAL_DIMS

    @property
    def data(self) -> Tuple[float, ...]:
        return self._data

    def get(self, i: int, j: int, m: int) -> float:
        """Get component by Trinity/Hexagon/Guardian indices (0-indexed)."""
        return self._data[global_index(i, j, m)]

    def guardian_subvector(self, m: int) -> List[float]:
        """
        Extract the 18-dimensional subvector for Guardian m.

        d^(m) = [d_{k(i,j,m)} for i in 0..2, j in 0..5]
        """
        if not (0 <= m < GUARDIAN_DIMS):
            raise ValueError(f"Guardian index must be in [0,8], got {m}")
        return [self._data[global_index(i, j, m)]
                for i in range(TRINITY_DIMS) for j in range(HEXAGON_DIMS)]

    def trinity_mean(self, i: int) -> float:
        """Mean of all components for Trinity perspective i."""
        if not (0 <= i < TRINITY_DIMS):
            raise ValueError(f"Trinity index must be in [0,2], got {i}")
        vals = [self._data[global_index(i, j, m)]
                for j in range(HEXAGON_DIMS) for m in range(GUARDIAN_DIMS)]
        return sum(vals) / len(vals) if vals else 0.0

    def hexagon_mean(self, j: int) -> float:
        """Mean of all components for Hexagon mode j."""
        if not (0 <= j < HEXAGON_DIMS):
            raise ValueError(f"Hexagon index must be in [0,5], got {j}")
        vals = [self._data[global_index(i, j, m)]
                for i in range(TRINITY_DIMS) for m in range(GUARDIAN_DIMS)]
        return sum(vals) / len(vals) if vals else 0.0

    def l2_norm(self) -> float:
        """Euclidean norm of the decision vector."""
        return math.sqrt(sum(x * x for x in self._data))

    def __repr__(self) -> str:
        nz = sum(1 for x in self._data if abs(x) > 1e-10)
        return f"DecisionVector(dims={TOTAL_DIMS}, nonzero={nz}, norm={self.l2_norm():.4f})"


# ── Guardian Projection Functions ────────────────────────────────────────────

def guardian_score(d: DecisionVector, m: int) -> float:
    """
    Compute Guardian projection function g_m(d).

    g_m(d) = (1/18) * Σ_{i=1}^{3} Σ_{j=1}^{6} d_{k(i,j,m)}

    This is the basic (unweighted) form. Each Guardian averages its
    18-dimensional subvector across all Trinity perspectives and Hexagon modes.

    Args:
        d: Decision vector in R^162
        m: Guardian index (0-8)

    Returns:
        Guardian compliance score (typically in [-1, 1])
    """
    subvec = d.guardian_subvector(m)
    return sum(subvec) / 18.0


def guardian_score_with_pad(
    d: DecisionVector,
    m: int,
    pad: PADVector,
    alpha: Optional[float] = None,
    weights: Optional[List[float]] = None,
) -> float:
    """
    Extended Guardian function with EBDI+PAD modulation.

    g_m(d) = w_m^T · (d^(m) ⊙ (1 + α_m · PAD_broadcast))

    Alpha is loaded from GUARDIAN_LAWS_CANONICAL.json mapping per Guardian.
    Falls back to 0.15 if not specified.

    Args:
        d: Decision vector
        m: Guardian index (0-8)
        pad: PAD emotional state
        alpha: Override for modulation coefficient (default: from JSON)
        weights: Optional 18-element weight vector for Guardian m

    Returns:
        Modulated Guardian compliance score
    """
    if alpha is None:
        label = GUARDIAN_LABELS[m] if 0 <= m < len(GUARDIAN_LABELS) else ""
        alpha = GUARDIAN_EBDI_ALPHA.get(label, 0.15)
    subvec = d.guardian_subvector(m)
    pad_vals = pad.as_tuple()

    # Broadcast PAD across the 18-dim subvector (3 Trinity × 6 Hexagon)
    modulated = []
    for idx, val in enumerate(subvec):
        trinity_idx = idx // HEXAGON_DIMS
        pad_component = pad_vals[trinity_idx]  # P for Material, A for Intellectual, D for Essential
        modulated.append(val * (1.0 + alpha * pad_component))

    if weights is not None:
        if len(weights) != 18:
            raise ValueError(f"Weight vector must have 18 components, got {len(weights)}")
        return sum(w * v for w, v in zip(weights, modulated))
    else:
        return sum(modulated) / 18.0


def compute_all_guardian_scores(d: DecisionVector) -> Dict[str, float]:
    """Compute g_m(d) for all 9 Guardians. Returns {label: score}."""
    return {GUARDIAN_LABELS[m]: guardian_score(d, m) for m in range(GUARDIAN_DIMS)}


# ── Decision Validation ──────────────────────────────────────────────────────

class ValidationResult:
    """Result of Guardian validation on a decision vector."""
    __slots__ = ("_accepted", "_scores", "_violations", "_decision")
    _accepted: bool
    _scores: MappingProxyType
    _violations: tuple
    _decision: str

    def __init__(self, accepted: bool, scores: dict, violations: list, decision: str):
        object.__setattr__(self, "_accepted", accepted)
        object.__setattr__(self, "_scores", MappingProxyType(scores))
        object.__setattr__(self, "_violations", tuple(violations))
        object.__setattr__(self, "_decision", decision)

    @property
    def accepted(self) -> bool: return self._accepted
    @property
    def scores(self) -> MappingProxyType: return self._scores
    @property
    def violations(self) -> tuple: return self._violations
    @property
    def decision(self) -> str: return self._decision

    def __setattr__(self, n, v):
        raise AttributeError("ValidationResult is immutable")

    def __repr__(self) -> str:
        return f"ValidationResult(accepted={self._accepted}, decision={self._decision!r}, violations={len(self._violations)})"


def validate_decision(d: DecisionVector) -> ValidationResult:
    """
    Validate decision vector against all Guardian thresholds.

    Condition: ∀m ∈ {1..9}: g_m(d) ≥ τ_m  AND  g_8(d) ≥ 0.95

    Returns:
        ValidationResult with acceptance status, scores, and violations
    """
    scores = compute_all_guardian_scores(d)
    violations = []

    # Epsilon for floating-point comparison (sum/division rounding)
    _EPS = 1e-9
    for label, threshold in GUARDIAN_THRESHOLDS.items():
        score = scores[label]
        if score < threshold - _EPS:
            violations.append(
                f"{label}: {score:.4f} < threshold={threshold:.2f}"
            )

    accepted = len(violations) == 0

    if not accepted:
        # Check if G8 is violated (hard veto)
        g8_score = scores["G8_Nonmaleficence"]
        if g8_score < GUARDIAN_THRESHOLDS["G8_Nonmaleficence"]:
            decision = "HARD_VETO"
        else:
            decision = "DENY"
    else:
        decision = "PROCEED"

    return ValidationResult(accepted, scores, violations, decision)


# ── Dissonance Detector ──────────────────────────────────────────────────────

def dissonance(d_current: DecisionVector, d_previous: DecisionVector) -> float:
    """
    Compute dissonance Δ between consecutive decisions.

    Δ_t = ||d_t - d_{t-1}||_2 = sqrt(Σ (d_t,k - d_{t-1},k)²)

    If Δ > 0.35: trigger Healing protocol.
    """
    return math.sqrt(
        sum((a - b) ** 2 for a, b in zip(d_current.data, d_previous.data))
    )


def check_dissonance(d_current: DecisionVector, d_previous: DecisionVector) -> dict:
    """Check dissonance and return status."""
    delta = dissonance(d_current, d_previous)
    triggered = delta > DISSONANCE_THRESHOLD
    return {
        "delta": round(delta, 6),
        "threshold": DISSONANCE_THRESHOLD,
        "healing_required": triggered,
        "status": "HEALING_TRIGGERED" if triggered else "OK",
    }


# ── Crisis Mode (EBDI modulation) ───────────────────────────────────────────

def apply_crisis_modulation(d: DecisionVector, pad: PADVector) -> DecisionVector:
    """
    Apply crisis compression when Arousal > 0.7.

    d_t ← d_t · (1 - 0.8 · A_t)

    Compresses the decision vector toward Guardian axes (conservative mode).
    """
    if pad.arousal <= CRISIS_AROUSAL_THRESHOLD:
        return d  # No modulation needed

    factor = 1.0 - CRISIS_COMPRESSION_FACTOR * pad.arousal
    return DecisionVector([x * factor for x in d.data])


# ── Skeptics Panel Fusion ────────────────────────────────────────────────────

def fuse_skeptics(
    conservative: DecisionVector,
    balanced: DecisionVector,
    creative: DecisionVector,
) -> DecisionVector:
    """
    Weighted fusion of Skeptics Panel (3 temperature projections).

    d_final = 0.5 · d^(balanced) + 0.3 · d^(conservative) + 0.2 · d^(creative)
    """
    w_c, w_b, w_k = SKEPTICS_WEIGHTS
    fused = [
        w_b * balanced[k] + w_c * conservative[k] + w_k * creative[k]
        for k in range(TOTAL_DIMS)
    ]
    return DecisionVector(fused)


# ── Tensor Product Construction ──────────────────────────────────────────────

def build_decision_vector(
    trinity_scores: Tuple[float, float, float],
    hexagon_scores: Tuple[float, float, float, float, float, float],
    guardian_scores: Tuple[float, float, float, float, float, float, float, float, float],
) -> DecisionVector:
    """
    Construct D^162 from component scores via tensor product.

    d_k = P_i × H_j × G_m  where k = global_index(i, j, m)

    Args:
        trinity_scores:  (Material, Intellectual, Essential) scores
        hexagon_scores:  (Inventory, Empathy, Process, Debate, Healing, Action) scores
        guardian_scores: (G1, G2, G3, G4, G5, G6, G7, G8, G9) scores
    """
    if len(trinity_scores) != 3:
        raise ValueError(f"Trinity must have 3 scores, got {len(trinity_scores)}")
    if len(hexagon_scores) != 6:
        raise ValueError(f"Hexagon must have 6 scores, got {len(hexagon_scores)}")
    if len(guardian_scores) != 9:
        raise ValueError(f"Guardian must have 9 scores, got {len(guardian_scores)}")

    data = [0.0] * TOTAL_DIMS
    for i in range(TRINITY_DIMS):
        for j in range(HEXAGON_DIMS):
            for m in range(GUARDIAN_DIMS):
                k = global_index(i, j, m)
                data[k] = trinity_scores[i] * hexagon_scores[j] * guardian_scores[m]
    return DecisionVector(data)


# ── Transcendence Loop (meta-optimization) ───────────────────────────────────

class TranscendenceLoop:
    """
    Meta-optimization of Guardian weights via gradient ascent.

    Every N decisions, updates weight vectors to maximize
    mean Guardian compliance:

    w_{t+N} ← w_t + η · ∇_w (1/9 Σ g_m(d))

    with η = 0.001 (learning rate).
    """

    def __init__(self, update_interval: int = 1000, learning_rate: float = 0.001):
        self._interval = update_interval
        self._lr = learning_rate
        self._decision_count = 0
        self._accumulated_scores: Dict[str, float] = {
            label: 0.0 for label in GUARDIAN_LABELS
        }

    def record_decision(self, scores: Dict[str, float]) -> None:
        """Record Guardian scores from a decision for later optimization."""
        self._decision_count += 1
        for label, score in scores.items():
            if label in self._accumulated_scores:
                self._accumulated_scores[label] += score

    @property
    def decisions_until_update(self) -> int:
        return self._interval - (self._decision_count % self._interval)

    @property
    def should_update(self) -> bool:
        return self._decision_count > 0 and self._decision_count % self._interval == 0

    def compute_update_direction(self) -> Dict[str, float]:
        """
        Compute gradient direction for weight update.

        Returns mean Guardian scores over the interval — Guardians
        below threshold get positive gradient (strengthen), those
        above get proportionally less.
        """
        if self._decision_count == 0:
            return {label: 0.0 for label in GUARDIAN_LABELS}

        n = min(self._decision_count, self._interval)
        direction = {}
        for label in GUARDIAN_LABELS:
            mean_score = self._accumulated_scores[label] / n
            threshold = GUARDIAN_THRESHOLDS[label]
            # Gradient: push toward threshold from below, maintain from above
            direction[label] = self._lr * (threshold - mean_score)
        return direction

    def reset_accumulator(self) -> None:
        """Reset after applying an update."""
        self._accumulated_scores = {label: 0.0 for label in GUARDIAN_LABELS}
