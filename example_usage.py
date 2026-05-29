from __future__ import annotations

from core.system import AdrionCore


def main() -> None:
    core = AdrionCore()

    decision_payload = {
        "axis": (0.0, 1.0, 0.0),
        "angle_rad": 0.08,
        "blend": 0.65,
        "risk_score": 0.05,
        "load_factor": 0.18,
        "session_token": "SECRET_VALUE",
    }

    result = core.process_decision(decision_payload, source="example_usage")

    print("=== ADRION CORE RESULT ===")
    print(f"decision: {result.decision}")
    print(f"approved: {result.approved}")
    print(f"resonance_score: {result.resonance_score:.4f}")
    print(f"entropy_level: {result.entropy_level:.4f}")
    print(f"recommendation: {result.recommendation}")
    print(f"compressed_report: {result.compressed_report}")


if __name__ == "__main__":
    main()
