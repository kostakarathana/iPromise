from __future__ import annotations

import pytest
from pydantic import ValidationError

from ipromise_agent.actions import UnsafeActionPlan, plan_actions, validate_action_plan
from ipromise_agent.models import (
    ActionState,
    CompilationPayload,
    Testability as ClaimTestability,
    VerificationReceipt,
    VerificationResult,
    Verdict,
    utc_now,
)
from ipromise_agent.source import exact_quote_is_grounded, parse_capture
from ipromise_demo.contract import DELETION_PROMISE


def test_exact_quote_grounding_rejects_semantic_or_punctuation_changes() -> None:
    capture = parse_capture(
        html=(
            '<html><body><p data-ipromise-claim="account-deletion">'
            f"{DELETION_PROMISE}</p></body></html>"
        ),
        url="https://synthetic.test/privacy",
        captured_at=utc_now(),
    )

    assert exact_quote_is_grounded(DELETION_PROMISE, capture) is True
    assert exact_quote_is_grounded(
        DELETION_PROMISE.replace("remove", "delete"), capture
    ) is False
    assert exact_quote_is_grounded(DELETION_PROMISE.rstrip("."), capture) is False
    assert exact_quote_is_grounded(DELETION_PROMISE + " Immediately.", capture) is False


def test_pr_stays_blocked_when_candidate_checks_did_not_run() -> None:
    receipt = VerificationReceipt(
        verifier="test gate",
        baseline_control=VerificationResult.FAIL,
        candidate_control=VerificationResult.NOT_RUN,
        regression_suite=VerificationResult.NOT_RUN,
        exact_tree_verified=False,
        isolated=False,
        publishable=False,
        detail="No candidate was executed",
    )

    actions = plan_actions(
        run_id="run_action_safety",
        verdict=Verdict.CONTRADICTED,
        receipt=receipt,
    )

    assert actions[0].state == ActionState.BLOCKED
    assert actions[0].verified is False
    actions[0].state = ActionState.READY
    actions[0].verified = True
    with pytest.raises(UnsafeActionPlan):
        validate_action_plan(actions, receipt)


def test_planner_never_claims_external_side_effects() -> None:
    actions = plan_actions(
        run_id="run_no_side_effects",
        verdict=Verdict.CONTRADICTED,
        receipt=None,
        consecutive_contradictions=2,
    )

    assert actions[2].state == ActionState.SKIPPED
    assert actions[1].state == ActionState.PLANNED
    selected_states = {
        ActionState.PLANNED,
        ActionState.READY,
        ActionState.OPENED,
        ActionState.SENT,
    }
    assert sum(action.state in selected_states for action in actions) == 1
    assert all(action.state not in {ActionState.OPENED, ActionState.SENT} for action in actions)

    opted_in = plan_actions(
        run_id="run_opted_in_email",
        verdict=Verdict.CONTRADICTED,
        receipt=None,
        consecutive_contradictions=2,
        email_enabled=True,
    )
    assert opted_in[1].state == ActionState.SKIPPED
    assert opted_in[2].state == ActionState.PLANNED


def test_inconclusive_evidence_never_dispatches_an_external_action() -> None:
    actions = plan_actions(
        run_id="run_inconclusive",
        verdict=Verdict.INCONCLUSIVE,
        receipt=None,
    )

    assert all(action.state == ActionState.SKIPPED for action in actions)


def test_compilation_payload_rejects_unknown_model_fields() -> None:
    with pytest.raises(ValidationError):
        CompilationPayload.model_validate(
            {
                "exact_quote": "A grounded promise.",
                "actor": "product",
                "action": "remove",
                "object": "profile",
                "deadline_hours": 24,
                "qualifiers": [],
                "testability": ClaimTestability.EXECUTABLE,
                "shell_command": "curl example.invalid",
            }
        )
