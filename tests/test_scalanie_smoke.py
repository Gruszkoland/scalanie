from core.observer import MetaObserver
from core.unity_field import UnityField
from core.vortex import VortexEngine
from core.zero import ZeroRouter
from guardians import EnneadCouncil


def test_should_complete_end_to_end_non_breaking_flow() -> None:
    router = ZeroRouter()
    observer = MetaObserver(zero_router=router)
    vortex = VortexEngine()
    unity = UnityField()
    council = EnneadCouncil(threshold=0.8)

    snapshot = vortex.rotate(axis=(0.0, 0.0, 1.0), angle_rad=0.05, blend=0.7)
    observed = observer.observe_and_route(
        {
            "resonance_score": snapshot.resonance_score,
            "entropy_level": snapshot.entropy_level,
            "trinity_vector": snapshot.trinity_vector,
        }
    )

    merged = unity.merge(
        zero={
            "resonance_score": observed["routed_payload"]["resonance_score"],
            "entropy_level": observed["routed_payload"]["entropy_level"],
        },
        observer={
            "resonance_score": observed["report"].resonance_score,
            "entropy_level": observed["report"].entropy_level,
        },
        vortex={
            "resonance_score": snapshot.resonance_score,
            "entropy_level": snapshot.entropy_level,
        },
    )

    result = council.evaluate(
        {
            "Unity": merged["resonance_score"],
            "Harmony": merged["resonance_score"],
            "Rhythm": merged["resonance_score"],
            "Causality": merged["resonance_score"],
            "Transparency": merged["resonance_score"],
            "Authenticity": merged["resonance_score"],
            "Privacy": 0.95,
            "Nonmaleficence": 0.95,
            "Sustainability": merged["resonance_score"],
        }
    )

    assert observed["zero_approved"] is True
    assert merged["resonance_score"] >= 0.85
    assert result["decision"] in {"PROCEED", "DENY"}
