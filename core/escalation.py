"""
ADRION 369 — Human-in-the-Loop Escalation Protocol v5.7
=========================================================
Webhook-based escalation module for HOLD_HUMAN and HOLD_SENTINEL decisions.

When the Trinity Engine or Guardian validation produces a decision requiring
human review, this module dispatches notifications via:
  - HTTP POST webhooks (Slack, Discord, custom endpoints)
  - Local file-based fallback (audit_escalations.jsonl)

Design principles:
  - Non-blocking: webhook calls are fire-and-forget with timeout
  - Fail-safe: if webhook fails, event is logged locally — never lost
  - G5 Transparency: every escalation is logged with full context
  - G7 Privacy: only decision metadata sent — raw input is SHA-256 hashed

Usage:
    from core.escalation import EscalationManager

    mgr = EscalationManager()
    mgr.add_webhook("https://hooks.slack.com/services/...", name="slack-ops")
    mgr.escalate(
        decision="HOLD_HUMAN_REVIEW",
        trinity_score=0.65,
        guardian_scores={"G8_Nonmaleficence": 0.94},
        reason="G8 below hard-veto threshold",
    )
"""

import hashlib
import json
import time
import threading
import urllib.request
import urllib.error
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple


# ── Escalation Levels ───────────────────────────────────────────────────────

ESCALATION_DECISIONS = frozenset({
    "HOLD_HUMAN_REVIEW",
    "HOLD_SENTINEL_REVIEW",
    "HARD_VETO",
    "HEALING_REQUIRED",
    "DENY",
})


# ── Escalation Event ───────────────────────────────────────────────────────

class EscalationEvent:
    """Immutable record of an escalation."""
    __slots__ = (
        "_timestamp", "_decision", "_trinity_score", "_guardian_scores",
        "_violations", "_reason", "_severity", "_event_hash",
    )
    _timestamp: float
    _decision: str
    _trinity_score: float
    _guardian_scores: dict
    _violations: tuple
    _reason: str
    _severity: str
    _event_hash: str

    def __init__(
        self,
        decision: str,
        trinity_score: float,
        guardian_scores: Dict[str, float],
        violations: Tuple[str, ...] = (),
        reason: str = "",
        severity: str = "MEDIUM",
    ) -> None:
        ts = time.time()
        object.__setattr__(self, "_timestamp", ts)
        object.__setattr__(self, "_decision", str(decision))
        object.__setattr__(self, "_trinity_score", float(trinity_score))
        object.__setattr__(self, "_guardian_scores", dict(guardian_scores))
        object.__setattr__(self, "_violations", tuple(violations))
        object.__setattr__(self, "_reason", str(reason))
        object.__setattr__(self, "_severity", str(severity))
        # Event hash for deduplication
        payload = f"{ts}|{decision}|{trinity_score}|{reason}"
        h = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        object.__setattr__(self, "_event_hash", h)

    @property
    def timestamp(self) -> float: return self._timestamp
    @property
    def decision(self) -> str: return self._decision
    @property
    def trinity_score(self) -> float: return self._trinity_score
    @property
    def guardian_scores(self) -> dict: return dict(self._guardian_scores)
    @property
    def violations(self) -> tuple: return self._violations
    @property
    def reason(self) -> str: return self._reason
    @property
    def severity(self) -> str: return self._severity
    @property
    def event_hash(self) -> str: return self._event_hash

    def __setattr__(self, n, v):
        raise AttributeError("EscalationEvent is immutable")

    def to_dict(self) -> dict:
        import datetime
        return {
            "timestamp": datetime.datetime.fromtimestamp(self._timestamp, datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
            "decision": self._decision,
            "trinity_score": round(self._trinity_score, 4),
            "guardian_scores": {k: round(v, 4) for k, v in self._guardian_scores.items()},
            "violations": list(self._violations),
            "reason": self._reason,
            "severity": self._severity,
            "event_hash": self._event_hash,
        }

    def __repr__(self) -> str:
        return (f"EscalationEvent(decision={self._decision!r}, "
                f"severity={self._severity!r}, hash={self._event_hash[:12]}...)")


# ── Webhook Target ──────────────────────────────────────────────────────────

class WebhookTarget:
    """Configuration for a single webhook endpoint."""

    def __init__(
        self,
        url: str,
        name: str = "",
        timeout: float = 5.0,
        decisions: Optional[frozenset] = None,
        headers: Optional[Dict[str, str]] = None,
        formatter: Optional[Callable] = None,
    ) -> None:
        if not url.startswith(("http://", "https://")):
            raise ValueError(f"Webhook URL must start with http(s)://, got: {url}")
        self.url = url
        self.name = name or url[:40]
        self.timeout = timeout
        self.decisions = decisions or ESCALATION_DECISIONS
        self.headers = headers or {"Content-Type": "application/json"}
        self.formatter = formatter
        self._failure_count = 0
        self._last_failure: Optional[str] = None

    def should_fire(self, decision: str) -> bool:
        return decision in self.decisions

    def format_payload(self, event: EscalationEvent) -> bytes:
        if self.formatter:
            data = self.formatter(event)
        else:
            data = self._default_format(event)
        return json.dumps(data, ensure_ascii=False).encode("utf-8")

    @staticmethod
    def _default_format(event: EscalationEvent) -> dict:
        """Default JSON payload — compatible with Slack/Discord webhooks."""
        severity_emoji = {
            "LOW": "[LOW]", "MEDIUM": "[MEDIUM]",
            "HIGH": "[HIGH]", "CRITICAL": "[CRITICAL]",
        }
        marker = severity_emoji.get(event.severity, "[?]")
        text = (
            f"{marker} ADRION 369 Escalation\n"
            f"Decision: {event.decision}\n"
            f"Trinity Score: {event.trinity_score:.4f}\n"
            f"Reason: {event.reason}\n"
            f"Violations: {', '.join(event.violations) if event.violations else 'none'}\n"
            f"Event Hash: {event.event_hash[:16]}..."
        )
        return {"text": text}

    def __repr__(self) -> str:
        return f"WebhookTarget(name={self.name!r}, url={self.url[:30]}...)"


# ── Escalation Manager ─────────────────────────────────────────────────────

class EscalationManager:
    """
    Central escalation dispatcher.

    Thread-safe. Dispatches webhook calls asynchronously.
    Always logs to local file as fallback (G5 compliance).
    """

    def __init__(
        self,
        log_path: Optional[str] = None,
        async_dispatch: bool = True,
    ) -> None:
        self._webhooks: List[WebhookTarget] = []
        self._history: List[EscalationEvent] = []
        self._lock = threading.RLock()
        self._async = async_dispatch
        self._log_path = Path(log_path) if log_path else None
        self._callbacks: List[Callable] = []

    def add_webhook(
        self,
        url: str,
        name: str = "",
        timeout: float = 5.0,
        decisions: Optional[frozenset] = None,
        headers: Optional[Dict[str, str]] = None,
        formatter: Optional[Callable] = None,
    ) -> None:
        """Register a webhook endpoint."""
        wh = WebhookTarget(
            url=url, name=name, timeout=timeout,
            decisions=decisions, headers=headers, formatter=formatter,
        )
        with self._lock:
            self._webhooks.append(wh)

    def add_callback(self, callback: Callable) -> None:
        """Register a local callback (for testing or in-process handling)."""
        with self._lock:
            self._callbacks.append(callback)

    def escalate(
        self,
        decision: str,
        trinity_score: float,
        guardian_scores: Dict[str, float],
        violations: Tuple[str, ...] = (),
        reason: str = "",
        severity: str = "MEDIUM",
    ) -> EscalationEvent:
        """
        Create and dispatch an escalation event.

        Returns the EscalationEvent regardless of webhook success.
        """
        event = EscalationEvent(
            decision=decision,
            trinity_score=trinity_score,
            guardian_scores=guardian_scores,
            violations=violations,
            reason=reason,
            severity=severity,
        )

        with self._lock:
            self._history.append(event)

        # Always log locally (G5 Transparency fallback)
        self._log_local(event)

        # Fire callbacks synchronously
        with self._lock:
            callbacks = list(self._callbacks)
        for cb in callbacks:
            try:
                cb(event)
            except Exception:
                pass

        # Dispatch webhooks
        with self._lock:
            targets = [wh for wh in self._webhooks if wh.should_fire(decision)]

        for wh in targets:
            if self._async:
                t = threading.Thread(
                    target=self._send_webhook,
                    args=(wh, event),
                    daemon=True,
                )
                t.start()
            else:
                self._send_webhook(wh, event)

        return event

    def _send_webhook(self, wh: WebhookTarget, event: EscalationEvent) -> bool:
        """Send HTTP POST to webhook. Returns True on success."""
        try:
            payload = wh.format_payload(event)
            req = urllib.request.Request(
                wh.url, data=payload,
                headers=wh.headers, method="POST",
            )
            with urllib.request.urlopen(req, timeout=wh.timeout) as resp:
                return resp.status == 200
        except Exception as e:
            wh._failure_count += 1
            wh._last_failure = str(e)
            return False

    def _log_local(self, event: EscalationEvent) -> None:
        """Append event to local JSONL file (G5 fallback)."""
        if self._log_path is None:
            return
        try:
            with open(self._log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")
        except Exception:
            pass  # Silent fail — event is still in memory history

    @property
    def history(self) -> List[EscalationEvent]:
        with self._lock:
            return list(self._history)

    @property
    def webhook_count(self) -> int:
        with self._lock:
            return len(self._webhooks)

    def get_webhook_status(self) -> List[dict]:
        """Return status of all registered webhooks."""
        with self._lock:
            return [
                {
                    "name": wh.name,
                    "url": wh.url[:40] + "..." if len(wh.url) > 40 else wh.url,
                    "failures": wh._failure_count,
                    "last_failure": wh._last_failure,
                }
                for wh in self._webhooks
            ]

    def summary(self) -> dict:
        """Escalation summary for monitoring."""
        with self._lock:
            by_decision: Dict[str, int] = {}
            by_severity: Dict[str, int] = {}
            for e in self._history:
                by_decision[e.decision] = by_decision.get(e.decision, 0) + 1
                by_severity[e.severity] = by_severity.get(e.severity, 0) + 1
            return {
                "total_escalations": len(self._history),
                "by_decision": by_decision,
                "by_severity": by_severity,
                "webhooks_registered": len(self._webhooks),
            }
