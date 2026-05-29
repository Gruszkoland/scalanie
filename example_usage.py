from __future__ import annotations

from core.system import AdrionCore, AdrionResult


def print_result(label: str, result: AdrionResult) -> None:
    print(f"=== {label} ===")
    print(f"decision: {result.decision}")
    print(f"approved: {result.approved}")
    print(f"resonance_score: {result.resonance_score:.4f}")
    print(f"entropy_level: {result.entropy_level:.4f}")
    print(f"guardian_weighted_score: {result.guardian_weighted_score:.4f}")
    print(f"recommendation: {result.recommendation}")
    print(f"zero_symbolic_report: {result.zero_symbolic_report}")
    print(f"ennead_symbolic_report: {result.ennead_symbolic_report}")
    print(f"compressed_report: {result.compressed_report}")
    print()


def main() -> None:
    core = AdrionCore()

    stable_payload = {
        "axis": (0.0, 1.0, 0.0),
        "angle_rad": 0.08,
        "blend": 0.65,
        "resonance_score": 0.94,
        "entropy_level": 0.06,
        "trinity_vector": (0.95, 0.93, 0.92),
        "risk_score": 0.05,
        "load_factor": 0.18,
        "session_token": "SECRET_VALUE",
    }
    risky_payload = {
        "axis": (1.0, 0.0, 0.0),
        "angle_rad": 0.45,
        "blend": 1.0,
        "resonance_score": 0.62,
        "entropy_level": 0.48,
        "trinity_vector": (0.63, 0.55, 0.49),
        "risk_score": 0.24,
        "load_factor": 0.41,
        "api_secret": "VERY_SECRET",
    }

    stable_result = core.process_decision(stable_payload, source="example_usage/stable")
    risky_result = core.process_decision(risky_payload, source="example_usage/risky")

    print_result("FLOW 1: STABLE", stable_result)
    print_result("FLOW 2: RISKY", risky_result)
    print(f"ZeroRouter health: {core.zero_router.get_system_health()}")


if __name__ == "__main__":
    main()
