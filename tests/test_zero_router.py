from core.zero import ZeroRouter


def test_should_force_to_zero_when_metrics_are_low() -> None:
    router = ZeroRouter()
    payload = {"resonance_score": 0.4, "entropy_level": 0.7}

    result = router.route(payload, auto_force_to_zero=True)

    assert result.approval.approved is True
    assert result.payload["resonance_score"] == 1.0
    assert result.payload["entropy_level"] == 0.0


def test_should_reject_without_force_when_metrics_are_low() -> None:
    router = ZeroRouter()
    payload = {"resonance_score": 0.4, "entropy_level": 0.7}

    result = router.route(payload, auto_force_to_zero=False)

    assert result.approval.approved is False
    assert result.approval.reason in {"LOW_RESONANCE", "HIGH_ENTROPY"}
