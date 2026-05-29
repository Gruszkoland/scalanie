from compression import CompressionStyleGuide, SeedEncoder


def test_should_generate_symbolic_and_hybrid_payload() -> None:
    style = CompressionStyleGuide.default()
    payload = {
        "resonance_score": 0.944,
        "entropy_level": 0.056,
        "trinity_vector": (0.95, 0.94, 0.94),
        "decision": "PROCEED",
        "approved": True,
    }

    symbolic = style.symbolic(payload)
    hybrid = style.hybrid(payload)

    assert "R:" in symbolic
    assert "E:" in symbolic
    assert "||" in hybrid


def test_should_reach_recommended_compression_ratio() -> None:
    style = CompressionStyleGuide.default()
    payload = {
        "resonance_score": 0.944,
        "entropy_level": 0.056,
        "trinity_vector": (0.95, 0.94, 0.94),
        "decision": "PROCEED",
        "approved": True,
    }

    original = (
        "resonance_score=0.944, entropy_level=0.056, trinity_vector=(0.95,0.94,0.94), "
        "decision=PROCEED, approved=True, recommendation=maintain_high_coherence"
    )
    compressed = style.symbolic(payload)
    ratio = style.compression_ratio(original, compressed)

    assert ratio >= 0.58


def test_should_encode_seed_deterministically() -> None:
    encoder = SeedEncoder()

    seed_a = encoder.encode("R:0.94|E:0.06")
    seed_b = encoder.encode("R:0.94|E:0.06")

    assert seed_a == seed_b
    assert seed_a.startswith("SEED-")
