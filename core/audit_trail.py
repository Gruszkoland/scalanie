"""
ADRION 369 — Blockchain-Ready Audit Trail v5.7
================================================
Immutable, hash-chained audit log for G5 Transparency compliance.

Each record links to the previous via SHA-256, creating a tamper-evident
chain identical in structure to a blockchain (without consensus — single
authority model suitable for PLC/SCADA compliance audits).

Record structure:
    {
        "seq":                 sequential index,
        "timestamp":           ISO 8601 UTC,
        "prev_hash":           SHA-256 of previous record (genesis: "0"*64),
        "record_hash":         SHA-256(prev_hash + payload),
        "version":             ADRION version string,
        "input_hash":          SHA-256 of raw input,
        "trinity_score":       float,
        "decision":            PROCEED|DENY|HOLD_*|HARD_VETO|HEALING_REQUIRED,
        "guardian_violations":  list of violated laws,
        "guardian_scores":     {G1..G9: float},
        "pad_state":           (P, A, D),
        "severity":            LOW|MEDIUM|HIGH|CRITICAL,
    }

Usage:
    from core.audit_trail import AuditChain

    chain = AuditChain(version="5.7.0")
    chain.append(input_data="user request", trinity_score=0.85,
                 decision="PROCEED", guardian_scores={...})
    chain.verify()  # True if chain is intact
    chain.export_json("audit_log.json")
"""

import hashlib
import json
import time
import threading
from pathlib import Path
from types import MappingProxyType
from typing import Dict, List, Optional, Tuple


# ── Genesis Hash (first block) ───────────────────────────────────────────────

GENESIS_PREV_HASH = "0" * 64


# ── Single Audit Record ─────────────────────────────────────────────────────

class AuditRecord:
    """
    Immutable, hash-linked audit record.
    Once created, no field can be modified.
    """
    __slots__ = (
        "_seq", "_timestamp", "_prev_hash", "_record_hash",
        "_version", "_input_hash", "_trinity_score", "_decision",
        "_guardian_violations", "_guardian_scores", "_pad_state", "_severity",
    )
    _seq: int
    _timestamp: float
    _prev_hash: str
    _record_hash: str
    _version: str
    _input_hash: str
    _trinity_score: float
    _decision: str
    _guardian_violations: tuple
    _guardian_scores: MappingProxyType
    _pad_state: tuple
    _severity: str

    def __init__(
        self,
        seq: int,
        prev_hash: str,
        version: str,
        input_hash: str,
        trinity_score: float,
        decision: str,
        guardian_violations: Tuple[str, ...],
        guardian_scores: Dict[str, float],
        pad_state: Tuple[float, float, float],
        severity: str,
        timestamp: Optional[float] = None,
        record_hash: Optional[str] = None,
    ) -> None:
        ts = timestamp if timestamp is not None else time.time()
        object.__setattr__(self, "_seq", int(seq))
        object.__setattr__(self, "_timestamp", float(ts))
        object.__setattr__(self, "_prev_hash", str(prev_hash))
        object.__setattr__(self, "_version", str(version))
        object.__setattr__(self, "_input_hash", str(input_hash))
        object.__setattr__(self, "_trinity_score", float(trinity_score))
        object.__setattr__(self, "_decision", str(decision))
        object.__setattr__(self, "_guardian_violations", tuple(guardian_violations))
        object.__setattr__(self, "_guardian_scores", MappingProxyType(dict(guardian_scores)))
        object.__setattr__(self, "_pad_state", tuple(pad_state))
        object.__setattr__(self, "_severity", str(severity))

        if record_hash is not None:
            object.__setattr__(self, "_record_hash", str(record_hash))
        else:
            object.__setattr__(self, "_record_hash", self._compute_hash())

    def _compute_hash(self) -> str:
        """SHA-256(prev_hash + canonical payload)."""
        payload = (
            f"{self._prev_hash}|{self._seq}|{self._timestamp}|{self._version}|"
            f"{self._input_hash}|{self._trinity_score}|{self._decision}|"
            f"{','.join(self._guardian_violations)}|"
            f"{','.join(f'{k}={v}' for k, v in sorted(self._guardian_scores.items()))}|"
            f"{self._pad_state}|{self._severity}"
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def verify(self) -> bool:
        """Verify that record_hash matches the computed hash."""
        return self._record_hash == self._compute_hash()

    # Properties (read-only)
    @property
    def seq(self) -> int: return self._seq
    @property
    def timestamp(self) -> float: return self._timestamp
    @property
    def prev_hash(self) -> str: return self._prev_hash
    @property
    def record_hash(self) -> str: return self._record_hash
    @property
    def version(self) -> str: return self._version
    @property
    def input_hash(self) -> str: return self._input_hash
    @property
    def trinity_score(self) -> float: return self._trinity_score
    @property
    def decision(self) -> str: return self._decision
    @property
    def guardian_violations(self) -> tuple: return self._guardian_violations
    @property
    def guardian_scores(self) -> MappingProxyType: return self._guardian_scores
    @property
    def pad_state(self) -> tuple: return self._pad_state
    @property
    def severity(self) -> str: return self._severity

    @property
    def timestamp_iso(self) -> str:
        import datetime
        return datetime.datetime.fromtimestamp(self._timestamp, datetime.timezone.utc).isoformat().replace("+00:00", "Z")

    def __setattr__(self, n, v):
        raise AttributeError("AuditRecord is immutable")

    def to_dict(self) -> dict:
        return {
            "seq": self._seq,
            "timestamp": self.timestamp_iso,
            "prev_hash": self._prev_hash,
            "record_hash": self._record_hash,
            "version": self._version,
            "input_hash": self._input_hash,
            "trinity_score": round(self._trinity_score, 4),
            "decision": self._decision,
            "guardian_violations": list(self._guardian_violations),
            "guardian_scores": {k: round(v, 4) for k, v in self._guardian_scores.items()},
            "pad_state": list(self._pad_state),
            "severity": self._severity,
        }

    def __repr__(self) -> str:
        return (f"AuditRecord(seq={self._seq}, decision={self._decision!r}, "
                f"hash={self._record_hash[:12]}...)")


# ── Audit Chain ──────────────────────────────────────────────────────────────

class AuditChain:
    """
    Blockchain-ready hash chain of audit records.

    Thread-safe. Each new record links to the previous via SHA-256.
    Provides full chain verification to detect any tampering.
    """

    def __init__(self, version: str = "5.7.0") -> None:
        self._version = version
        self._chain: List[AuditRecord] = []
        self._lock = threading.RLock()

    @property
    def length(self) -> int:
        with self._lock:
            return len(self._chain)

    @property
    def last_hash(self) -> str:
        with self._lock:
            return self._chain[-1].record_hash if self._chain else GENESIS_PREV_HASH

    def append(
        self,
        input_data: str,
        trinity_score: float,
        decision: str,
        guardian_scores: Dict[str, float],
        guardian_violations: Tuple[str, ...] = (),
        pad_state: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        severity: str = "MEDIUM",
    ) -> AuditRecord:
        """
        Append a new record to the chain.

        Args:
            input_data: Raw input text (hashed, not stored in plaintext)
            trinity_score: Computed Trinity Score
            decision: Final decision string
            guardian_scores: All 9 Guardian scores
            guardian_violations: List of violated Guardian labels
            pad_state: (Pleasure, Arousal, Dominance) tuple
            severity: LOW|MEDIUM|HIGH|CRITICAL

        Returns:
            The newly created AuditRecord
        """
        input_hash = hashlib.sha256(input_data.encode("utf-8")).hexdigest()

        with self._lock:
            prev_hash = self._chain[-1].record_hash if self._chain else GENESIS_PREV_HASH
            seq = len(self._chain)

            record = AuditRecord(
                seq=seq,
                prev_hash=prev_hash,
                version=self._version,
                input_hash=input_hash,
                trinity_score=trinity_score,
                decision=decision,
                guardian_violations=guardian_violations,
                guardian_scores=guardian_scores,
                pad_state=pad_state,
                severity=severity,
            )
            self._chain.append(record)
            return record

    def verify(self) -> bool:
        """
        Verify the entire chain.

        Checks:
        1. Each record's hash matches its computed hash (no tampering)
        2. Each record's prev_hash matches the previous record's hash (chain integrity)
        3. First record's prev_hash is the genesis hash

        Returns:
            True if chain is intact, False if any tampering detected
        """
        with self._lock:
            if not self._chain:
                return True

            # Check genesis
            if self._chain[0].prev_hash != GENESIS_PREV_HASH:
                return False

            for i, record in enumerate(self._chain):
                # Verify record self-hash
                if not record.verify():
                    return False
                # Verify chain linkage
                if i > 0 and record.prev_hash != self._chain[i - 1].record_hash:
                    return False

            return True

    def get_record(self, seq: int) -> Optional[AuditRecord]:
        with self._lock:
            if 0 <= seq < len(self._chain):
                return self._chain[seq]
            return None

    def get_records_by_decision(self, decision: str) -> List[AuditRecord]:
        with self._lock:
            return [r for r in self._chain if r.decision == decision]

    def get_violation_history(self) -> List[AuditRecord]:
        with self._lock:
            return [r for r in self._chain if r.guardian_violations]

    def export_json(self, path: str) -> None:
        """Export entire chain to JSON file (for compliance audits)."""
        with self._lock:
            data = {
                "version": self._version,
                "chain_length": len(self._chain),
                "chain_valid": self.verify(),
                "records": [r.to_dict() for r in self._chain],
            }
        p = Path(path)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def export_records(self) -> List[dict]:
        """Return chain as list of dicts."""
        with self._lock:
            return [r.to_dict() for r in self._chain]

    def summary(self) -> dict:
        """Chain summary for monitoring."""
        with self._lock:
            decisions: Dict[str, int] = {}
            violations_total = 0
            for r in self._chain:
                decisions[r.decision] = decisions.get(r.decision, 0) + 1
                violations_total += len(r.guardian_violations)

            return {
                "chain_length": len(self._chain),
                "chain_valid": self.verify(),
                "last_hash": self.last_hash[:16] + "...",
                "decisions": decisions,
                "total_violations": violations_total,
                "version": self._version,
            }
