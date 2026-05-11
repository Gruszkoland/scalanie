"""
tests/ecosystem/test_attention_economy.py
==========================================
Testy jednostkowe dla ecosystem/attention_economy.py.
Weryfikuje: stany trybu, markery frustracji, budżet, reset sesji.
"""

import pytest
from ecosystem.attention_economy import AttentionBudget, UserAction, AttentionMode


# ── Fixtures ──────────────────────────────────────────────────────────────────

def fresh_budget(max_cost: float = 100.0) -> AttentionBudget:
    return AttentionBudget(max_cost=max_cost)


# ── Testy ─────────────────────────────────────────────────────────────────────

class TestAttentionBudgetInit:
    """2.2.1 — Nowy AttentionBudget ma spent = 0 i tryb PRECISION."""

    def test_budget_starts_full(self):
        budget = fresh_budget()
        assert budget.spent == 0.0

    def test_mode_starts_precision(self):
        budget = fresh_budget()
        assert budget.get_current_mode() == "PRECISION"

    def test_frustration_markers_start_at_zero(self):
        budget = fresh_budget()
        assert budget.frustration_markers == 0

    def test_invalid_max_cost_raises(self):
        with pytest.raises(ValueError):
            AttentionBudget(max_cost=0)
        with pytest.raises(ValueError):
            AttentionBudget(max_cost=-10)


class TestFrustrationMarkers:
    """2.2.2 — Odrzucenia planów i inne akcje dodają markery."""

    def test_plan_rejection_adds_marker(self):
        budget = fresh_budget()
        budget.record_user_action(UserAction.PLAN_REJECTED)
        assert budget.frustration_markers == 1

    def test_step_failed_adds_marker(self):
        budget = fresh_budget()
        budget.record_user_action(UserAction.STEP_FAILED)
        assert budget.frustration_markers == 1

    def test_short_response_adds_marker(self):
        budget = fresh_budget()
        budget.record_user_action(UserAction.SHORT_RESPONSE)
        assert budget.frustration_markers == 1

    def test_long_silence_adds_marker(self):
        budget = fresh_budget()
        budget.record_user_action(UserAction.LONG_SILENCE)
        assert budget.frustration_markers == 1

    def test_plan_accepted_does_not_add_marker(self):
        budget = fresh_budget()
        budget.record_user_action(UserAction.PLAN_ACCEPTED)
        assert budget.frustration_markers == 0

    def test_step_completed_does_not_add_marker(self):
        budget = fresh_budget()
        budget.record_user_action(UserAction.STEP_COMPLETED)
        assert budget.frustration_markers == 0


class TestEmpathyMode:
    """2.2.3 — Trzy odrzucenia aktywują tryb EMPATHY."""

    def test_three_rejections_trigger_empathy(self):
        budget = fresh_budget()
        for _ in range(3):
            budget.record_user_action(UserAction.PLAN_REJECTED)
        assert budget.get_current_mode() == "EMPATHY"

    def test_two_rejections_stay_precision(self):
        budget = fresh_budget()
        budget.record_user_action(UserAction.PLAN_REJECTED)
        budget.record_user_action(UserAction.PLAN_REJECTED)
        assert budget.get_current_mode() == "PRECISION"

    def test_five_rejections_trigger_recovery(self):
        budget = fresh_budget()
        for _ in range(5):
            budget.record_user_action(UserAction.PLAN_REJECTED)
        assert budget.get_current_mode() == "RECOVERY"


class TestCanAfford:
    """2.2.4 — can_afford zwraca False przy wyczerpanym budżecie lub złym trybie."""

    def test_can_afford_when_budget_full(self):
        budget = fresh_budget()
        assert budget.can_afford("FULL_PROTOCOL_333") is True

    def test_cannot_afford_when_budget_exhausted(self):
        budget = fresh_budget(max_cost=1.0)
        assert budget.can_afford("FULL_PROTOCOL_333") is False

    def test_empathy_mode_blocks_expensive_operations(self):
        budget = fresh_budget()
        for _ in range(3):
            budget.record_user_action(UserAction.PLAN_REJECTED)
        # W trybie EMPATHY, operacje > 10 jednostek są niedostępne
        assert budget.can_afford("FULL_PROTOCOL_333") is False

    def test_empathy_mode_allows_cheap_operations(self):
        budget = fresh_budget()
        for _ in range(3):
            budget.record_user_action(UserAction.PLAN_REJECTED)
        assert budget.can_afford("SIMPLE_QUESTION") is True

    def test_recovery_mode_blocks_medium_operations(self):
        budget = fresh_budget()
        for _ in range(5):
            budget.record_user_action(UserAction.PLAN_REJECTED)
        assert budget.can_afford("COUNTER_PROPOSAL") is False

    def test_unknown_operation_uses_default_cost(self):
        budget = fresh_budget(max_cost=5.0)
        # Nieznana operacja ma koszt 10.0 → za droga przy max_cost=5.0
        result = budget.can_afford("UNKNOWN_OP")
        assert result is False


class TestSuggestDowngrade:
    """2.2.5 — suggest_downgrade() zwraca niepusty string z kontekstem trybu."""

    def test_suggest_downgrade_returns_nonempty_string(self):
        budget = fresh_budget()
        result = budget.suggest_downgrade()
        assert isinstance(result, str)
        assert len(result) > 10

    def test_suggest_downgrade_empathy_contains_empathy(self):
        budget = fresh_budget()
        for _ in range(3):
            budget.record_user_action(UserAction.PLAN_REJECTED)
        result = budget.suggest_downgrade()
        assert "EMPATHY" in result.upper()

    def test_suggest_downgrade_recovery_contains_recovery(self):
        budget = fresh_budget()
        for _ in range(5):
            budget.record_user_action(UserAction.PLAN_REJECTED)
        result = budget.suggest_downgrade()
        assert "RECOVERY" in result.upper()


class TestResetSession:
    """2.2.6 — reset_session() czyści budżet i przywraca tryb PRECISION."""

    def test_reset_clears_spent(self):
        budget = fresh_budget()
        budget.spend("DETAILED_PLAN")
        assert budget.spent > 0
        budget.reset_session()
        assert budget.spent == 0.0

    def test_reset_clears_frustration_markers(self):
        budget = fresh_budget()
        for _ in range(4):
            budget.record_user_action(UserAction.PLAN_REJECTED)
        budget.reset_session()
        assert budget.frustration_markers == 0

    def test_reset_restores_precision_mode(self):
        budget = fresh_budget()
        for _ in range(3):
            budget.record_user_action(UserAction.PLAN_REJECTED)
        assert budget.get_current_mode() == "EMPATHY"
        budget.reset_session()
        assert budget.get_current_mode() == "PRECISION"


class TestAcceptanceRelief:
    """2.2.7 — Akceptacja planu redukuje markery frustracji."""

    def test_acceptance_reduces_frustration_markers(self):
        budget = fresh_budget()
        budget.record_user_action(UserAction.PLAN_REJECTED)
        budget.record_user_action(UserAction.PLAN_REJECTED)
        assert budget.frustration_markers == 2
        budget.record_user_action(UserAction.PLAN_ACCEPTED)
        assert budget.frustration_markers == 1

    def test_acceptance_does_not_go_below_zero(self):
        budget = fresh_budget()
        budget.record_user_action(UserAction.PLAN_ACCEPTED)
        assert budget.frustration_markers == 0

    def test_three_rejections_one_acceptance_stays_in_precision(self):
        budget = fresh_budget()
        for _ in range(3):
            budget.record_user_action(UserAction.PLAN_REJECTED)
        assert budget.get_current_mode() == "EMPATHY"
        budget.record_user_action(UserAction.PLAN_ACCEPTED)
        # 3 - 1 = 2 markery → PRECISION
        assert budget.get_current_mode() == "PRECISION"


class TestSessionSummary:
    """Dodatkowy test: get_session_summary() zwraca spójny raport."""

    def test_session_summary_structure(self):
        budget = fresh_budget()
        budget.record_user_action(UserAction.PLAN_REJECTED)
        summary = budget.get_session_summary()
        assert summary["mode"] == "PRECISION"
        assert summary["spent"] == 0.0
        assert summary["frustration_markers"] == 1
        assert summary["action_count"] == 1
