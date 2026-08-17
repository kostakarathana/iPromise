"""Approved deterministic control for the canonical deletion promise."""

from __future__ import annotations

from dataclasses import dataclass

from .demo_client import ReferenceClient
from .models import Claim, Evidence, EvidenceResult, Testability, Verdict


CONTROL_ID = "privacy.account_deletion.v1"
CONTROL_SCOPE = (
    "One synthetic canary in the configured reference app; app profile and "
    "analytics profile only; observed after the disclosed 24-hour deadline."
)


@dataclass(frozen=True, slots=True)
class ControlOutcome:
    verdict: Verdict
    evidence: list[Evidence]
    fixture_id: str
    virtual_elapsed_hours: float | None


def can_bind_account_deletion(claim: Claim) -> bool:
    """Bind semantic model output only to this narrow, preapproved control."""

    quote = claim.exact_quote.casefold()
    required_fragments = (
        "delete your account",
        "profile",
        "analytics system",
        "within 24 hours",
    )
    return (
        claim.testability == Testability.EXECUTABLE
        and claim.deadline_hours == 24
        and all(fragment in quote for fragment in required_fragments)
    )


def calculate_verdict(evidence: list[Evidence]) -> Verdict:
    """An explicit failure proves contradiction; missing required data abstains."""

    results = {item.result for item in evidence}
    if EvidenceResult.FAIL in results:
        return Verdict.CONTRADICTED
    if not evidence or EvidenceResult.UNKNOWN in results:
        return Verdict.INCONCLUSIVE
    if results == {EvidenceResult.PASS}:
        return Verdict.SUPPORTED
    return Verdict.INCONCLUSIVE


class AccountDeletionControl:
    id = CONTROL_ID

    def __init__(self, client: ReferenceClient) -> None:
        self._client = client

    async def execute(self, run_id: str) -> ControlOutcome:
        fixture = await self._client.seed_account(run_id)
        processed = await self._client.process_deletion(fixture.account_id)
        state = await self._client.inspect_account(fixture.account_id)

        elapsed = state.virtual_observation_elapsed_hours
        deadline_crossed = elapsed is not None and elapsed > 24
        processing_elapsed = processed.virtual_processing_elapsed_hours
        processing_time_valid = processing_elapsed >= 0
        if not deadline_crossed or not processing_time_valid:
            timeline_result = EvidenceResult.UNKNOWN
        elif processing_elapsed <= 24:
            timeline_result = EvidenceResult.PASS
        else:
            timeline_result = EvidenceResult.FAIL
        deadline_evidence = Evidence(
            id="synthetic-virtual-timeline",
            label="Deletion timeline",
            expected="Worker runs by T0+24h; evidence observed after T0+24h",
            observed=(
                "Worker replayed at "
                f"T0+{processing_elapsed:.2f}h; "
                f"observation occurred at T0+{elapsed:.2f}h"
                if elapsed is not None
                else "Deletion-request timestamp or elapsed time was unavailable"
            ),
            result=timeline_result,
            scope=f"synthetic_accounts/{fixture.account_id}",
        )

        evidence = [
            deadline_evidence,
            _record_evidence(
                evidence_id="app-profile",
                label="App profile",
                exists=state.profile_exists if deadline_crossed else None,
                scope=f"profiles/{fixture.account_id}",
            ),
            _record_evidence(
                evidence_id="analytics-profile",
                label="Analytics profile",
                exists=state.analytics_profile_exists if deadline_crossed else None,
                scope=f"analytics_profiles/{fixture.account_id}",
            ),
        ]
        return ControlOutcome(
            verdict=calculate_verdict(evidence),
            evidence=evidence,
            fixture_id=fixture.account_id,
            virtual_elapsed_hours=elapsed,
        )


def _record_evidence(
    *, evidence_id: str, label: str, exists: bool | None, scope: str
) -> Evidence:
    if exists is None:
        result = EvidenceResult.UNKNOWN
        observed = "Required store evidence was unavailable"
    elif exists:
        result = EvidenceResult.FAIL
        observed = "1 active record at +25h"
    else:
        result = EvidenceResult.PASS
        observed = "No active record at +25h"
    return Evidence(
        id=evidence_id,
        label=label,
        expected="Removed within 24h",
        observed=observed,
        result=result,
        scope=scope,
    )
