from core.observer import MetaObserver


def test_should_escalate_when_low_resonance_or_high_entropy() -> None:
    observer = MetaObserver(resonance_floor=0.75, entropy_ceiling=0.25)
    cases = [
        {"resonance_score": 0.50, "entropy_level": 0.10, "trinity_vector": (0.5, 0.5, 0.5)},
        {"resonance_score": 0.90, "entropy_level": 0.40, "trinity_vector": (0.9, 0.9, 0.9)},
        {"resonance_score": 0.70, "entropy_level": 0.40, "trinity_vector": (0.7, 0.7, 0.7)},
    ]

    detections = sum(1 for c in cases if observer.analyze_snapshot(c).escalate_to_zero)

    assert detections == len(cases)


def test_should_keep_false_positive_rate_below_three_percent() -> None:
    observer = MetaObserver(resonance_floor=0.75, entropy_ceiling=0.25)
    stable_cases = [
        {"resonance_score": 0.88, "entropy_level": 0.12, "trinity_vector": (0.9, 0.88, 0.86)}
        for _ in range(100)
    ]

    false_positives = sum(1 for c in stable_cases if observer.analyze_snapshot(c).escalate_to_zero)
    false_positive_rate = false_positives / len(stable_cases)

    assert false_positive_rate <= 0.03
