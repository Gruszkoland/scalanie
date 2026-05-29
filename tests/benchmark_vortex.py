"""Benchmark VortexEngine zgodny z kryteriami akceptacji."""

from core.vortex import VortexEngine


def run_benchmark(iterations: int = 10000) -> dict:
    engine = VortexEngine()
    return engine.benchmark_rotation(iterations=iterations)


if __name__ == "__main__":
    result = run_benchmark()
    print(result)
