"""Benchmark prostego pipeline MetaObserver + ZeroRouter."""

from time import perf_counter

from core.observer import MetaObserver
from core.zero import ZeroRouter


def run_benchmark(iterations: int = 10000) -> dict:
    observer = MetaObserver(zero_router=ZeroRouter())
    start = perf_counter()
    for _ in range(iterations):
        observer.observe_and_route(
            {
                "resonance_score": 0.93,
                "entropy_level": 0.07,
                "trinity_vector": (0.93, 0.93, 0.93),
            }
        )
    duration = perf_counter() - start
    return {
        "iterations": iterations,
        "duration_s": duration,
        "throughput_rps": iterations / duration if duration > 0 else float("inf"),
    }


if __name__ == "__main__":
    result = run_benchmark()
    print(result)
