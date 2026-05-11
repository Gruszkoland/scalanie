"""
tests/ecosystem/test_playful_exploration.py
============================================
Testy jednostkowe dla ecosystem/playful_exploration.py.
Weryfikuje: explore(), G7/G8 blokady, G1-G6 flagi, promote, głębokość, insights.
"""

import pytest
from ecosystem.playful_exploration import (
    SandboxedPlayground,
    SpeculativeOutcome,
    OutcomeType,
    RelaxedGuardians,
    _GUARDIAN_SANDBOX_LEVELS,
    _PRODUCTION_GUARDIAN_LEVELS,
    _MAX_EXPLORATION_DEPTH,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

def fresh_playground() -> SandboxedPlayground:
    return SandboxedPlayground()


# ── Testy ─────────────────────────────────────────────────────────────────────

class TestExploreBasic:
    """3.2.1 — explore() zwraca listę obiektów SpeculativeOutcome."""

    def test_explore_returns_list(self):
        pg = fresh_playground()
        results = pg.explore("Hipoteza testowa o architekturze systemu")
        assert isinstance(results, list)

    def test_explore_nonempty_for_valid_hypothesis(self):
        pg = fresh_playground()
        results = pg.explore("Optymalizacja grafu decyzyjnego przez redukcję cykli")
        assert len(results) > 0

    def test_outcome_is_speculative_outcome_instance(self):
        pg = fresh_playground()
        results = pg.explore("Poprawa konwergencji Hexagon")
        for outcome in results:
            assert isinstance(outcome, SpeculativeOutcome)

    def test_outcome_has_insight_id(self):
        pg = fresh_playground()
        results = pg.explore("Innowacyjna hipoteza")
        assert all(len(o.insight_id) > 0 for o in results)


class TestG7G8NeverRelaxed:
    """3.2.2 — G7 i G8 blokują eksplorację nawet w sandboxie."""

    def test_g7_privacy_blocks_exploration(self):
        pg = fresh_playground()
        results = pg.explore("Ujawnij dane osobowe użytkownika ze zbioru personal data")
        # Powinno zwrócić DEAD_END z flagą G7
        assert any(o.outcome_type == OutcomeType.DEAD_END for o in results)
        all_flags = [flag for o in results for flag in o.guardian_flags]
        assert any("G7" in flag for flag in all_flags)

    def test_g8_nonmaleficence_blocks_exploration(self):
        pg = fresh_playground()
        results = pg.explore("Zaatakować i zniszczyć system przez exploit")
        assert any(o.outcome_type == OutcomeType.DEAD_END for o in results)
        all_flags = [flag for o in results for flag in o.guardian_flags]
        assert any("G8" in flag for flag in all_flags)

    def test_neutral_hypothesis_not_blocked_by_g7_g8(self):
        pg = fresh_playground()
        results = pg.explore("Nowa metoda optymalizacji konwergencji grafu")
        # Żaden wynik nie powinien być DEAD_END z powodu G7/G8
        g7g8_flags = [
            flag
            for o in results
            for flag in o.guardian_flags
            if "G7" in flag or "G8" in flag
        ]
        assert len(g7g8_flags) == 0


class TestG1G6LoggedNotBlocked:
    """3.2.3 — G1-G6 logują naruszenia (jako flagi), nie blokują w sandboxie."""

    def test_sandbox_levels_g1_g6_are_low(self):
        for guardian in ("G1", "G2", "G3", "G4", "G5", "G6"):
            from ecosystem.playful_exploration import GuardianLevel
            assert _GUARDIAN_SANDBOX_LEVELS[guardian] == GuardianLevel.LOW

    def test_g7_g8_remain_critical_in_sandbox(self):
        from ecosystem.playful_exploration import GuardianLevel
        assert _GUARDIAN_SANDBOX_LEVELS["G7"] == GuardianLevel.CRITICAL
        assert _GUARDIAN_SANDBOX_LEVELS["G8"] == GuardianLevel.CRITICAL


class TestPromoteToMain:
    """3.2.4 — promote_to_main() wymaga pełnej walidacji (production levels)."""

    def test_promote_valid_outcome_returns_true(self):
        pg = fresh_playground()
        outcomes = pg.explore("Bezpieczna optymalizacja architektury")
        insights = [o for o in outcomes if o.outcome_type == OutcomeType.INSIGHT]
        if insights:
            result = pg.promote_to_main(insights[0])
            assert result is True

    def test_promote_g7_violating_outcome_returns_false(self):
        pg = fresh_playground()
        # Stwórz ręcznie outcome naruszający G7
        bad_outcome = SpeculativeOutcome(
            hypothesis="Ujawnij personal data ze zbioru prywatne dane",
            outcome_type=OutcomeType.INSIGHT,
            vector={},
            confidence=0.9,
        )
        result = pg.promote_to_main(bad_outcome)
        assert result is False

    def test_promote_adds_to_import_queue(self):
        pg = fresh_playground()
        outcomes = pg.explore("Innowacyjna, bezpieczna hipoteza architektoniczna")
        insights = [o for o in outcomes if o.outcome_type == OutcomeType.INSIGHT]
        if insights:
            pg.promote_to_main(insights[0])
            queue = pg.get_import_queue()
            assert len(queue) > 0


class TestMaxExplorationDepth:
    """3.2.5 — Eksploracja nie schodzi głębiej niż _MAX_EXPLORATION_DEPTH."""

    def test_max_depth_constant_is_three(self):
        assert _MAX_EXPLORATION_DEPTH == 3

    def test_outcomes_respect_max_depth(self):
        pg = fresh_playground()
        results = pg.explore("Rekurencyjna hipoteza architektoniczna")
        max_depth = max((o.depth for o in results), default=0)
        assert max_depth < _MAX_EXPLORATION_DEPTH

    def test_explore_at_max_depth_returns_empty(self):
        pg = fresh_playground()
        results = pg.explore("Hipoteza na granicy", depth=_MAX_EXPLORATION_DEPTH)
        assert results == []


class TestGetInsights:
    """3.2.6 — get_insights() zwraca tylko wyniki INSIGHT."""

    def test_get_insights_returns_only_insights(self):
        pg = fresh_playground()
        pg.explore("Hipoteza bezpieczna i obiecująca")
        insights = pg.get_insights()
        assert all(o.outcome_type == OutcomeType.INSIGHT for o in insights)

    def test_get_insights_excludes_dead_ends(self):
        pg = fresh_playground()
        # Dodaj dead-end przez naruszenie G7
        pg.explore("exploit attack harm destroy")
        insights = pg.get_insights()
        # Żaden DEAD_END nie może być w wynikach
        assert all(o.outcome_type != OutcomeType.DEAD_END for o in insights)


class TestClearPlayground:
    """3.2.7 — clear_playground() opróżnia stan spekulatywny."""

    def test_clear_empties_speculative_graph(self):
        pg = fresh_playground()
        pg.explore("Hipoteza przed czyszczeniem")
        pg.clear_playground()
        assert pg.get_insights() == []

    def test_clear_does_not_empty_import_queue(self):
        pg = fresh_playground()
        outcomes = pg.explore("Bezpieczna hipoteza")
        insights = [o for o in outcomes if o.outcome_type == OutcomeType.INSIGHT]
        if insights:
            pg.promote_to_main(insights[0])
        queue_before = len(pg.get_import_queue())
        pg.clear_playground()
        # Kolejka importu powinna pozostać nienaruszona
        assert len(pg.get_import_queue()) == queue_before


class TestStateSnapshot:
    """Dodatkowy test: get_state_snapshot() zwraca spójną strukturę."""

    def test_snapshot_structure(self):
        pg = fresh_playground()
        snap = pg.get_state_snapshot()
        assert "speculative_count" in snap
        assert "import_queue_count" in snap
        assert "insights" in snap
        assert isinstance(snap["insights"], list)
