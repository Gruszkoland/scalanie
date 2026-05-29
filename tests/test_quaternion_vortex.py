from core.math import Quaternion
from core.vortex import VortexEngine


def test_should_keep_quaternion_normalized_after_slerp() -> None:
    q1 = Quaternion.identity()
    q2 = Quaternion.from_axis_angle((0.0, 1.0, 0.0), 1.2)

    q_mid = Quaternion.slerp(q1, q2, 0.5)

    assert abs(q_mid.norm() - 1.0) < 1e-9


def test_should_meet_vortex_performance_thresholds() -> None:
    engine = VortexEngine()

    stats = engine.benchmark_rotation(iterations=10000)

    assert stats["avg_ms"] <= 0.8
    assert stats["throughput_rps"] >= 1200
