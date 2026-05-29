import random

from core.observer import MetaObserver
from core.vortex import VortexEngine
from core.zero import ZeroRouter


def test_should_reach_resonance_target_in_random_decisions() -> None:
    random.seed(369)
    router = ZeroRouter()
    observer = MetaObserver(zero_router=router, resonance_floor=0.90, entropy_ceiling=0.10)
    engine = VortexEngine()

    accepted = 0
    resonance_values = []

    for _ in range(1000):
        jitter = random.uniform(-0.04, 0.04)
        base = max(0.0, min(1.0, 0.93 + jitter))
        snapshot = {
            "resonance_score": base,
            "entropy_level": max(0.0, 1.0 - base),
            "trinity_vector": (base, base, base),
        }
        observed = observer.observe_and_route(snapshot)
        routed = observed["routed_payload"]
        resonance = float(routed["resonance_score"])
        resonance_values.append(resonance)
        accepted += 1 if resonance >= 0.90 else 0
        engine.rotate(axis=(0.0, 1.0, 0.0), angle_rad=0.01, blend=0.5)

    avg_resonance = sum(resonance_values) / len(resonance_values)
    acceptance_ratio = accepted / 1000.0

    assert avg_resonance >= 0.92
    assert acceptance_ratio >= 0.95
