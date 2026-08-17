"""Bounded proposal and truthful, non-publishable MVP verification receipt."""

from __future__ import annotations

from .models import (
    AuditRun,
    FileEdit,
    RemediationProposal,
    VerificationReceipt,
    VerificationResult,
)


ALLOWED_REMEDIATION_PATH = "apps/demo_saas/src/ipromise_demo/store.py"


def propose_bounded_remediation(run: AuditRun) -> RemediationProposal:
    """Return data, never commands; this approved template cannot widen its path."""

    return RemediationProposal(
        summary="Remove the matching analytics profile while processing account deletion.",
        base_reference="not-captured-in-first-mvp",
        edits=[
            FileEdit(
                path=ALLOWED_REMEDIATION_PATH,
                operation="insert_bounded_statement",
                rationale=(
                    "The virtual worker removed the app profile at T0+1h, but the "
                    "synthetic analytics profile remained active at T0+25h."
                ),
                content_preview="self._analytics_profiles.pop(account_id, None)",
            )
        ],
        generated_by="deterministic approved remediation template",
    )


def unverified_mvp_receipt() -> VerificationReceipt:
    """Record observed red evidence without fabricating an unexecuted green build."""

    return VerificationReceipt(
        verifier="MVP verification gate (candidate execution not configured)",
        baseline_control=VerificationResult.FAIL,
        candidate_control=VerificationResult.NOT_RUN,
        regression_suite=VerificationResult.NOT_RUN,
        exact_tree_verified=False,
        isolated=False,
        publishable=False,
        detail=(
            "The live synthetic baseline contradicted the promise. No candidate patch "
            "was executed in an isolated verifier, so publication remains blocked."
        ),
    )
