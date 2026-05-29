from guardians import EnneadCouncil


def test_should_deny_when_critical_guardian_fails() -> None:
    council = EnneadCouncil(threshold=0.8)
    scores = {
        "Unity": 0.9,
        "Harmony": 0.9,
        "Rhythm": 0.9,
        "Causality": 0.9,
        "Transparency": 0.9,
        "Authenticity": 0.9,
        "Privacy": 0.2,
        "Nonmaleficence": 0.95,
        "Sustainability": 0.9,
    }

    result = council.evaluate(scores)

    assert result["decision"] == "DENY"
    assert result["critical_veto"] is True


def test_should_proceed_when_all_scores_above_threshold() -> None:
    council = EnneadCouncil(threshold=0.8)
    scores = {k: 0.95 for k in (
        "Unity",
        "Harmony",
        "Rhythm",
        "Causality",
        "Transparency",
        "Authenticity",
        "Privacy",
        "Nonmaleficence",
        "Sustainability",
    )}

    result = council.evaluate(scores)

    assert result["decision"] == "PROCEED"
    assert result["violations"] == []
