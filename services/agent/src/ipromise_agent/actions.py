"""Risk-ordered action planning with fail-closed publication gates."""

from __future__ import annotations

from .models import (
    ActionKind,
    ActionState,
    PlannedAction,
    VerificationReceipt,
    VerificationResult,
    Verdict,
)


class UnsafeActionPlan(ValueError):
    pass


def _receipt_proves_candidate(receipt: VerificationReceipt | None) -> bool:
    return bool(
        receipt
        and receipt.publishable
        and receipt.isolated
        and receipt.exact_tree_verified
        and receipt.baseline_control == VerificationResult.FAIL
        and receipt.candidate_control == VerificationResult.PASS
        and receipt.regression_suite == VerificationResult.PASS
    )


def plan_actions(
    *,
    run_id: str,
    verdict: Verdict,
    receipt: VerificationReceipt | None,
    consecutive_contradictions: int = 1,
    email_enabled: bool = False,
) -> list[PlannedAction]:
    proven = _receipt_proves_candidate(receipt)

    if verdict == Verdict.CONTRADICTED:
        pull_request = PlannedAction(
            id=f"{run_id}:pr",
            kind=ActionKind.PULL_REQUEST,
            state=ActionState.READY if proven else ActionState.BLOCKED,
            title="Remove overdue analytics profile during account deletion",
            reason=(
                "Isolated fail-before/pass-after receipt authorizes a draft PR"
                if proven
                else "Blocked until an isolated verifier proves the exact candidate tree"
            ),
            verified=proven,
        )
        issue = PlannedAction(
            id=f"{run_id}:issue",
            kind=ActionKind.ISSUE,
            state=(
                ActionState.SKIPPED
                if proven or (email_enabled and consecutive_contradictions >= 2)
                else ActionState.PLANNED
            ),
            title="Account deletion does not clear analytics profiles",
            reason=(
                "Draft PR is the selected response"
                if proven
                else "Email escalation supersedes issue creation"
                if email_enabled and consecutive_contradictions >= 2
                else "No verified repair is available."
            ),
            verified=False,
        )
        email_ready = email_enabled and consecutive_contradictions >= 2 and not proven
        email = PlannedAction(
            id=f"{run_id}:email",
            kind=ActionKind.EMAIL,
            state=ActionState.PLANNED if email_ready else ActionState.SKIPPED,
            title=(
                "Notify the configured owner"
                if email_ready
                else "Do not email on first detection"
            ),
            reason=(
                "Escalation threshold reached"
                if email_ready
                else "Email is disabled until an allowlisted recipient opts in"
                if not email_enabled
                else f"Email policy requires 2 consecutive contradictions; {consecutive_contradictions}/2"
            ),
            verified=False,
        )
    elif verdict == Verdict.INCONCLUSIVE:
        pull_request = _skipped(run_id, ActionKind.PULL_REQUEST, "No verified repair")
        issue = _skipped(
            run_id,
            ActionKind.ISSUE,
            "Required evidence was unavailable; iPromise abstained without dispatch",
        )
        email = _skipped(run_id, ActionKind.EMAIL, "No confirmed contradiction")
    else:
        reason = "No contradiction requires action"
        pull_request = _skipped(run_id, ActionKind.PULL_REQUEST, reason)
        issue = _skipped(run_id, ActionKind.ISSUE, reason)
        email = _skipped(run_id, ActionKind.EMAIL, reason)

    actions = [pull_request, issue, email]
    validate_action_plan(actions, receipt)
    return actions


def _skipped(run_id: str, kind: ActionKind, reason: str) -> PlannedAction:
    return PlannedAction(
        id=f"{run_id}:{kind.value}",
        kind=kind,
        state=ActionState.SKIPPED,
        title=f"No {kind.value.replace('_', ' ')} action",
        reason=reason,
        verified=False,
    )


def validate_action_plan(
    actions: list[PlannedAction], receipt: VerificationReceipt | None
) -> None:
    expected_order = [ActionKind.PULL_REQUEST, ActionKind.ISSUE, ActionKind.EMAIL]
    if [action.kind for action in actions] != expected_order:
        raise UnsafeActionPlan("Actions must remain ordered PR, issue, then email")

    for action in actions:
        if action.state in {ActionState.OPENED, ActionState.SENT}:
            raise UnsafeActionPlan("The planner cannot claim an external side effect")

    selected_states = {
        ActionState.PLANNED,
        ActionState.READY,
        ActionState.OPENED,
        ActionState.SENT,
    }
    if sum(action.state in selected_states for action in actions) > 1:
        raise UnsafeActionPlan("At most one external action route may be selected")

    pull_request = actions[0]
    if pull_request.state == ActionState.READY:
        if not pull_request.verified or not _receipt_proves_candidate(receipt):
            raise UnsafeActionPlan("A draft PR cannot be ready without complete proof")
    elif pull_request.verified:
        raise UnsafeActionPlan("A non-ready draft PR cannot be marked verified")
