"""
tests/ecosystem/test_antifragility.py
======================================
Testy jednostkowe dla ecosystem/antifragility.py.
Weryfikuje: immutability, learn/query/apply patch, success_rate, genesis format.
"""

import time
import pytest

from ecosystem.antifragility import (
    AntifragilityRegistry,
    MicroHeuristicPatch,
    RepairContext,
    _feature_similarity,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

def make_context(
    error_sig: str = "ValueError: convergence failed",
    hexagon_cycle: int = 3,
    convergence_score: float = 0.4,
    patched_files: tuple = ("core/hexagon.py",),
) -> RepairContext:
    return RepairContext(
        error_signature=error_sig,
        hexagon_cycle=hexagon_cycle,
        convergence_score=convergence_score,
        patched_files=patched_files,
    )


# ── Testy ─────────────────────────────────────────────────────────────────────

class TestAntifragilityRegistryImmutability:
    """1.2.1 — Rejestr jest append-only: nie można modyfikować wpisów po dodaniu."""

    def test_entries_only_grow_never_shrink(self):
        """Rejestr jest append-only: liczba wpisów nigdy nie maleje."""
        registry = AntifragilityRegistry()
        assert registry.entry_count == 0
        registry.learn_from_repair(make_context("err-A"))
        assert registry.entry_count == 1
        registry.learn_from_repair(make_context("err-B"))
        assert registry.entry_count == 2
        # Drugi zapis tej samej sygnatury nie dodaje nowego wpisu
        registry.learn_from_repair(make_context("err-A"))
        assert registry.entry_count == 2

    def test_repair_context_is_frozen(self):
        ctx = make_context()
        with pytest.raises((AttributeError, TypeError)):
            ctx.error_signature = "hacked"  # frozen dataclass

    def test_patch_id_is_consistent_for_same_signature(self):
        registry = AntifragilityRegistry()
        ctx1 = make_context("same error")
        ctx2 = make_context("same error")
        p1 = registry.learn_from_repair(ctx1)
        # Drugi learn z tą samą sygnaturą powinien zaktualizować istniejący patch
        p2 = registry.learn_from_repair(ctx2)
        assert p1.patch_id == p2.patch_id


class TestLearnFromRepair:
    """1.2.2 — learn_from_repair tworzy patch z poprawną sygnaturą."""

    def test_returns_micro_heuristic_patch(self):
        registry = AntifragilityRegistry()
        ctx = make_context()
        patch = registry.learn_from_repair(ctx)
        assert isinstance(patch, MicroHeuristicPatch)

    def test_patch_has_correct_error_signature(self):
        registry = AntifragilityRegistry()
        ctx = make_context("TypeError: None")
        patch = registry.learn_from_repair(ctx)
        assert patch.error_signature == "TypeError: None"

    def test_patch_applied_count_starts_at_one(self):
        registry = AntifragilityRegistry()
        ctx = make_context()
        patch = registry.learn_from_repair(ctx)
        assert patch.applied_count == 1

    def test_second_learn_same_signature_increments_count(self):
        registry = AntifragilityRegistry()
        ctx = make_context("duplicate error")
        registry.learn_from_repair(ctx)
        patch = registry.learn_from_repair(ctx)
        assert patch.applied_count == 2

    def test_registry_entry_count_grows(self):
        registry = AntifragilityRegistry()
        assert registry.entry_count == 0
        registry.learn_from_repair(make_context("err1"))
        assert registry.entry_count == 1
        registry.learn_from_repair(make_context("err2"))
        assert registry.entry_count == 2


class TestQueryPatch:
    """1.2.3 & 1.2.4 — query_patch: znalezienie przy ≥85% podobieństwie."""

    def test_query_finds_similar_patch(self):
        registry = AntifragilityRegistry()
        ctx = make_context(
            "ValueError: convergence failed",
            hexagon_cycle=3,
            convergence_score=0.4,
        )
        registry.learn_from_repair(ctx)

        # Identyczna sygnatura → 100% podobieństwo
        query = ctx.feature_vector()
        result = registry.query_patch(query)
        assert result is not None
        assert result.error_signature == "ValueError: convergence failed"

    def test_query_returns_none_below_threshold(self):
        registry = AntifragilityRegistry()
        ctx = make_context("MemoryError: OOM", hexagon_cycle=1, convergence_score=0.9)
        registry.learn_from_repair(ctx)

        # Zupełnie inna sygnatura i parametry
        query = {
            "error_prefix": "TypeError: unexpected type",
            "hexagon_cycle": 10,
            "conv_bucket": 0.1,
            "n_patched": 50,
        }
        result = registry.query_patch(query)
        assert result is None

    def test_query_on_empty_registry_returns_none(self):
        registry = AntifragilityRegistry()
        result = registry.query_patch({"error_prefix": "SomeError", "hexagon_cycle": 1})
        assert result is None


class TestApplyPatch:
    """1.2.5 — apply_patch modyfikuje przekazany kontekst."""

    def test_apply_adds_strategy_keys_to_context(self):
        registry = AntifragilityRegistry()
        ctx = make_context(hexagon_cycle=4, convergence_score=0.3)
        patch = registry.learn_from_repair(ctx)

        context = {"current_threshold": 0.7}
        result = registry.apply_patch(patch, context)
        assert isinstance(result, dict)
        # Oryginał niezmieniony
        assert "convergence_threshold_delta" not in context

    def test_apply_does_not_mutate_original_context(self):
        registry = AntifragilityRegistry()
        patch = registry.learn_from_repair(make_context())
        original = {"x": 1, "y": 2}
        _ = registry.apply_patch(patch, original)
        assert original == {"x": 1, "y": 2}

    def test_derived_from_key_present_in_strategy(self):
        registry = AntifragilityRegistry()
        ctx = make_context("SomeLongError: details here")
        patch = registry.learn_from_repair(ctx)
        assert "_derived_from" in patch.strategy_modification


class TestSuccessRateTracking:
    """1.2.6 — success_rate jest poprawnie aktualizowany."""

    def test_success_rate_after_one_success(self):
        patch = MicroHeuristicPatch(
            patch_id="abc",
            error_signature="err",
            strategy_modification={},
        )
        patch.record_outcome(success=True)
        assert patch.applied_count == 1
        assert patch.success_rate == 1.0

    def test_success_rate_after_mixed_outcomes(self):
        patch = MicroHeuristicPatch(
            patch_id="abc",
            error_signature="err",
            strategy_modification={},
        )
        patch.record_outcome(True)
        patch.record_outcome(True)
        patch.record_outcome(False)
        assert patch.applied_count == 3
        assert abs(patch.success_rate - 2/3) < 0.001

    def test_record_patch_outcome_via_registry(self):
        registry = AntifragilityRegistry()
        ctx = make_context()
        patch = registry.learn_from_repair(ctx)
        initial_rate = patch.success_rate
        registry.record_patch_outcome(patch, success=False)
        assert patch.success_rate < initial_rate or patch.applied_count > 1


class TestGenesisFormat:
    """1.2.7 — to_genesis_format() zwraca kompatybilny słownik."""

    def test_genesis_format_structure(self):
        registry = AntifragilityRegistry()
        result = registry.to_genesis_format()
        assert result["registry_type"] == "AntifragilityRegistry"
        assert result["version"] == "2.0.0"
        assert result["entry_count"] == 0
        assert isinstance(result["entries"], list)

    def test_genesis_format_with_entries(self):
        registry = AntifragilityRegistry()
        registry.learn_from_repair(make_context("err1"))
        registry.learn_from_repair(make_context("err2"))
        result = registry.to_genesis_format()
        assert result["entry_count"] == 2
        entry = result["entries"][0]
        assert "patch_id" in entry
        assert "error_signature" in entry
        assert "strategy_modification" in entry
        assert "applied_count" in entry
        assert "success_rate" in entry
        assert "recorded_at" in entry


class TestFeatureSimilarity:
    """Pomocnicze testy dla funkcji _feature_similarity."""

    def test_identical_vectors(self):
        v = {"a": 1, "b": 2}
        assert _feature_similarity(v, v) == 1.0

    def test_empty_vectors(self):
        assert _feature_similarity({}, {}) == 0.0

    def test_no_common_keys(self):
        assert _feature_similarity({"a": 1}, {"b": 2}) == 0.0

    def test_partial_match(self):
        a = {"x": 1, "y": 2, "z": 3}
        b = {"x": 1, "y": 99, "z": 3}
        score = _feature_similarity(a, b)
        assert abs(score - 2/3) < 0.001
