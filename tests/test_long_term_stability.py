from time import perf_counter

from core.observer import MetaObserver
from core.vortex import VortexEngine
from core.zero import ZeroRouter


def test_should_stabilize_under_chaos_within_time_budget() -> None:
    router = ZeroRouter()
    observer = MetaObserver(zero_router=router, resonance_floor=0.55, entropy_ceiling=0.45)
    engine = VortexEngine()

    total_cycles = 5000
    forced_resets = 0

    start = perf_counter()
    for i in range(total_cycles):
        if i % 17 == 0:
            engine.apply_perturbation(0.03)
        else:
            engine.apply_perturbation(0.002)

        snapshot = engine.rotate(axis=(1.0, 0.0, 0.0), angle_rad=0.01, blend=0.5)
        observed = observer.observe_and_route(
            {
                "resonance_score": snapshot.resonance_score,
                "entropy_level": snapshot.entropy_level,
                "trinity_vector": snapshot.trinity_vector,
            }
        )
        routed = observed["routed_payload"]
        if routed.get("resonance_score") == 1.0 and routed.get("entropy_level") == 0.0:
            forced_resets += 1

        if i % 100 == 0:
            engine.stabilize(target=0.92, step=0.05)

    duration = perf_counter() - start
    final_recovery_start = perf_counter()
    engine.stabilize(target=0.90, step=0.03)
    recovery_time = perf_counter() - final_recovery_start

    assert duration <= 8.0
    assert recovery_time <= 8.0
    assert (forced_resets / total_cycles) <= 0.02
