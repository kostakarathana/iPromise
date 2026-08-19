from __future__ import annotations

import asyncio
from dataclasses import replace

import pytest

from ipromise_agent.cloudbuild_verifier import (
    CandidateFileEvidence,
    CheckResult,
    CloudBuildEvidence,
    VerificationDecision,
    VerificationFailureCode,
    VerificationOutcome,
    VerifiedCandidate,
)
from ipromise_agent.compiler import DeterministicDemonstrationCompiler
from ipromise_agent.firestore_store import FirestoreRunStore
from ipromise_agent.github import (
    GitHubPublicationRejected,
    GitHubPublishUncertain,
    PublishedIssue,
    PublishedPullRequest,
    RepositorySourceSnapshot,
)
from ipromise_agent.models import (
    ActionKind,
    ActionState,
    CreateRunRequest,
    GitHubRepository,
    RunStatus,
)
from ipromise_agent.remediation import ALLOWED_REMEDIATION_PATHS
from ipromise_agent.service import AuditService
from ipromise_agent.store import InMemoryRunStore

from conftest import FakeReferenceClient
from remediation_fixtures import locked_remediation_preimages


BASE_SHA = "a" * 40
REPOSITORY = GitHubRepository(
    id=101,
    full_name="kostakarathana/iPromise",
    default_branch="main",
    private=False,
    html_url="https://github.com/kostakarathana/iPromise",
)


class _Source:
    def __init__(self) -> None:
        self.calls = 0

    async def capture_repository_files(self, target, paths):
        self.calls += 1
        assert target == REPOSITORY
        assert paths == ALLOWED_REMEDIATION_PATHS
        preimages = locked_remediation_preimages()
        return RepositorySourceSnapshot(
            base_sha=BASE_SHA,
            files=tuple((path, preimages[path]) for path in paths),
        )


class _Verifier:
    def __init__(self, decision: VerificationDecision) -> None:
        self.decision = decision
        self.calls = 0

    async def verify(self, artifact):
        self.calls += 1
        if self.decision != VerificationDecision.VERIFIED:
            return VerificationOutcome(
                decision=self.decision,
                failure_code=(
                    VerificationFailureCode.SUBMISSION_FAILED
                    if self.decision == VerificationDecision.UNAVAILABLE
                    else VerificationFailureCode.CANDIDATE_MISMATCH
                ),
                detail="Verifier unavailable or candidate rejected.",
                baseline_control=CheckResult.NOT_RUN,
                candidate_control=CheckResult.NOT_RUN,
                regression_suite=CheckResult.NOT_RUN,
                exact_source_verified=False,
                exact_candidate_verified=False,
            )
        evidence = CloudBuildEvidence(
            build_id="build-1",
            build_name="projects/test/locations/global/builds/build-1",
            status="SUCCESS",
            log_url="https://console.cloud.google.com/cloud-build/builds/build-1",
            requested_source_url="https://github.com/kostakarathana/iPromise.git",
            resolved_source_url="https://github.com/kostakarathana/iPromise.git",
            requested_base_sha=artifact.base_sha,
            resolved_base_sha=artifact.base_sha,
            unified_diff_sha256=artifact.unified_diff_sha256,
            step_results=(),
        )
        candidate = VerifiedCandidate(
            schema_version="ipromise.verified-candidate.v1",
            repository_url="https://github.com/kostakarathana/iPromise.git",
            base_sha=artifact.base_sha,
            unified_diff_sha256=artifact.unified_diff_sha256,
            files=tuple(
                CandidateFileEvidence(
                    path=item.path,
                    preimage_sha256=item.preimage_sha256,
                    candidate_sha256=item.candidate_sha256,
                    content=item.content,
                )
                for item in artifact.candidate_files
            ),
            evidence=evidence,
        )
        return VerificationOutcome(
            decision=VerificationDecision.VERIFIED,
            failure_code=VerificationFailureCode.NONE,
            detail="Exact candidate verified.",
            baseline_control=CheckResult.EXPECTED_FAILURE,
            candidate_control=CheckResult.PASS,
            regression_suite=CheckResult.PASS,
            exact_source_verified=True,
            exact_candidate_verified=True,
            evidence=evidence,
            candidate=candidate,
        )


class _GitHub:
    def __init__(self, *, pr_failure: Exception | None = None) -> None:
        self.pr_failure = pr_failure
        self.pr_calls = 0
        self.issue_calls = 0

    async def selected_repository(self):
        return REPOSITORY

    async def publish_draft_pull_request(self, _run, _action, _candidate):
        self.pr_calls += 1
        if self.pr_failure is not None:
            failure = self.pr_failure
            self.pr_failure = None
            raise failure
        return PublishedPullRequest(
            url="https://github.com/kostakarathana/iPromise/pull/7",
            number=7,
            remote_id=700,
            branch="ipromise/promise-drift-1234",
            head_sha="b" * 40,
            base_sha=BASE_SHA,
            tree_sha="c" * 40,
            reconciled=self.pr_calls > 1,
        )

    async def publish_issue(self, _run, _action):
        self.issue_calls += 1
        return PublishedIssue(
            url="https://github.com/kostakarathana/iPromise/issues/8",
            number=8,
            remote_id=800,
        )


class _ConcurrentReconciledGitHub(_GitHub):
    def __init__(self) -> None:
        super().__init__()
        self.created_prs = 0
        self._arrived = asyncio.Event()
        self._lock = asyncio.Lock()

    async def publish_draft_pull_request(self, _run, _action, _candidate):
        self.pr_calls += 1
        if self.pr_calls == 2:
            self._arrived.set()
        await asyncio.wait_for(self._arrived.wait(), timeout=2)
        async with self._lock:
            reconciled = self.created_prs == 1
            if not reconciled:
                self.created_prs = 1
        return PublishedPullRequest(
            url="https://github.com/kostakarathana/iPromise/pull/7",
            number=7,
            remote_id=700,
            branch="ipromise/promise-drift-1234",
            head_sha="b" * 40,
            base_sha=BASE_SHA,
            tree_sha="c" * 40,
            reconciled=reconciled,
        )


class _FailOnceOnCompleteCheckpointStore(InMemoryRunStore):
    def __init__(self) -> None:
        super().__init__()
        self.failed = False

    async def save(self, run) -> None:
        if not self.failed and run.status == RunStatus.COMPLETE:
            self.failed = True
            raise RuntimeError("simulated final Firestore checkpoint outage")
        await super().save(run)


def _service(
    settings,
    *,
    verifier,
    github,
    source,
    actions_enabled=True,
    store=None,
):
    return AuditService(
        settings=replace(settings, github_actions_enabled=actions_enabled),
        store=store,
        reference_client=FakeReferenceClient(),
        compiler=DeterministicDemonstrationCompiler(),
        github_service=github,
        verifier=verifier,
        remediation_source=source,
    )


@pytest.mark.asyncio
async def test_verified_candidate_is_primary_idempotent_draft_pr(settings) -> None:
    verifier = _Verifier(VerificationDecision.VERIFIED)
    github = _GitHub()
    source = _Source()
    service = _service(
        settings, verifier=verifier, github=github, source=source
    )
    request = CreateRunRequest(idempotency_key="verified-pr-primary-001")

    first = await service.create_run(request)
    replay = await service.create_run(request)

    pull_request = next(
        action for action in first.actions if action.kind == ActionKind.PULL_REQUEST
    )
    issue = next(action for action in first.actions if action.kind == ActionKind.ISSUE)
    assert first.status == RunStatus.COMPLETE
    assert pull_request.state == ActionState.OPENED
    assert pull_request.url == "https://github.com/kostakarathana/iPromise/pull/7"
    assert pull_request.reason == (
        "Verified exact candidate published as a draft. "
        "The implemented publisher exposes no merge or deploy operation and creates "
        "draft pull requests only."
    )
    assert issue.state == ActionState.SKIPPED
    assert first.remediation is not None
    assert first.remediation.base_reference == BASE_SHA
    assert first.verification is not None
    assert first.verification.artifact_binding is not None
    assert replay.id == first.id
    assert source.calls == verifier.calls == github.pr_calls == 1
    assert github.issue_calls == 0

    encoded = FirestoreRunStore._encode(first)
    assert "verifiedCandidate" not in encoded["payload"]
    assert "artifactBinding" not in encoded["payload"]["verification"]
    restored = FirestoreRunStore._decode(encoded)
    assert restored.verified_candidate is not None
    assert restored.verified_candidate.candidate_hashes == (
        first.verified_candidate.candidate_hashes
    )
    assert restored.verification is not None
    assert restored.verification.artifact_binding is not None
    assert restored.verification.artifact_binding.binding_sha256 == (
        first.verification.artifact_binding.binding_sha256
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "decision",
    [VerificationDecision.UNAVAILABLE, VerificationDecision.REJECTED],
)
async def test_unavailable_or_rejected_verification_opens_issue_fallback(
    settings, decision
) -> None:
    verifier = _Verifier(decision)
    github = _GitHub()
    service = _service(
        settings, verifier=verifier, github=github, source=_Source()
    )

    run = await service.create_run(
        CreateRunRequest(idempotency_key=f"verifier-fallback-{decision.value}")
    )

    pull_request = next(
        action for action in run.actions if action.kind == ActionKind.PULL_REQUEST
    )
    issue = next(action for action in run.actions if action.kind == ActionKind.ISSUE)
    assert run.status == RunStatus.COMPLETE
    assert pull_request.state == ActionState.BLOCKED
    assert issue.state == ActionState.OPENED
    assert github.pr_calls == 0
    assert github.issue_calls == 1


@pytest.mark.asyncio
async def test_pr_safety_rejection_routes_to_issue(settings) -> None:
    github = _GitHub(
        pr_failure=GitHubPublicationRejected("default branch moved")
    )
    service = _service(
        settings,
        verifier=_Verifier(VerificationDecision.VERIFIED),
        github=github,
        source=_Source(),
    )

    run = await service.create_run(
        CreateRunRequest(idempotency_key="pr-rejection-fallback-01")
    )

    assert run.status == RunStatus.COMPLETE
    assert github.pr_calls == 1
    assert github.issue_calls == 1
    assert next(
        action for action in run.actions if action.kind == ActionKind.ISSUE
    ).state == ActionState.OPENED


@pytest.mark.asyncio
async def test_uncertain_pr_resumes_from_verified_checkpoint(settings) -> None:
    verifier = _Verifier(VerificationDecision.VERIFIED)
    github = _GitHub(pr_failure=GitHubPublishUncertain("outcome unknown"))
    source = _Source()
    service = _service(
        settings, verifier=verifier, github=github, source=source
    )
    request = CreateRunRequest(idempotency_key="uncertain-pr-recovery-01")

    uncertain = await service.create_run(request)
    recovered = await service.create_run(request)

    assert uncertain.status == RunStatus.FAILED_RETRYABLE
    assert recovered.status == RunStatus.COMPLETE
    assert recovered.id == uncertain.id
    assert source.calls == 1
    assert verifier.calls == 1
    assert github.pr_calls == 2
    assert github.issue_calls == 0


@pytest.mark.asyncio
async def test_verifier_runs_with_external_actions_disabled(settings) -> None:
    verifier = _Verifier(VerificationDecision.VERIFIED)
    github = _GitHub()
    source = _Source()
    service = _service(
        settings,
        verifier=verifier,
        github=github,
        source=source,
        actions_enabled=False,
    )

    run = await service.create_run(
        CreateRunRequest(idempotency_key="verify-before-actions-rollout-01")
    )

    assert run.status == RunStatus.COMPLETE
    assert run.verification is not None and run.verification.publishable is True
    assert source.calls == verifier.calls == 1
    assert github.pr_calls == github.issue_calls == 0
    pull_request = next(
        action for action in run.actions if action.kind == ActionKind.PULL_REQUEST
    )
    assert pull_request.state == ActionState.BLOCKED
    assert pull_request.reason == (
        "Verified draft PR publication is disabled for this run; "
        "no external action was attempted."
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("decision", "expected_kind"),
    [
        (VerificationDecision.VERIFIED, ActionKind.PULL_REQUEST),
        (VerificationDecision.UNAVAILABLE, ActionKind.ISSUE),
    ],
)
async def test_final_checkpoint_failure_retries_without_republishing(
    settings, decision, expected_kind
) -> None:
    verifier = _Verifier(decision)
    github = _GitHub()
    source = _Source()
    reference = FakeReferenceClient()
    service = AuditService(
        settings=replace(settings, github_actions_enabled=True),
        store=_FailOnceOnCompleteCheckpointStore(),
        reference_client=reference,
        compiler=DeterministicDemonstrationCompiler(),
        github_service=github,
        verifier=verifier,
        remediation_source=source,
    )
    request = CreateRunRequest(
        idempotency_key=f"final-checkpoint-{expected_kind.value}-01"
    )

    checkpoint_failed = await service.create_run(request)
    recovered = await service.create_run(request)

    action = next(
        item for item in recovered.actions if item.kind == expected_kind
    )
    assert checkpoint_failed.status == RunStatus.FAILED_RETRYABLE
    assert checkpoint_failed.verdict.value == "CONTRADICTED"
    assert "receipt is confirmed" in checkpoint_failed.limitations[-1]
    assert recovered.status == RunStatus.COMPLETE
    assert recovered.id == checkpoint_failed.id
    assert action.state == ActionState.OPENED
    assert source.calls == verifier.calls == 1
    assert reference.seed_calls == reference.process_calls == 1
    assert github.pr_calls == (1 if expected_kind == ActionKind.PULL_REQUEST else 0)
    assert github.issue_calls == (1 if expected_kind == ActionKind.ISSUE else 0)


@pytest.mark.asyncio
async def test_concurrent_distinct_runs_reconcile_one_pr_without_issue(settings) -> None:
    github = _ConcurrentReconciledGitHub()
    first_service = _service(
        settings,
        verifier=_Verifier(VerificationDecision.VERIFIED),
        github=github,
        source=_Source(),
    )
    second_service = _service(
        settings,
        verifier=_Verifier(VerificationDecision.VERIFIED),
        github=github,
        source=_Source(),
    )

    first, second = await asyncio.gather(
        first_service.create_run(
            CreateRunRequest(idempotency_key="concurrent-distinct-run-01")
        ),
        second_service.create_run(
            CreateRunRequest(idempotency_key="concurrent-distinct-run-02")
        ),
    )

    first_pr = next(
        action for action in first.actions if action.kind == ActionKind.PULL_REQUEST
    )
    second_pr = next(
        action for action in second.actions if action.kind == ActionKind.PULL_REQUEST
    )
    assert first.status == second.status == RunStatus.COMPLETE
    assert first.id != second.id
    assert first_pr.state == second_pr.state == ActionState.OPENED
    assert first_pr.url == second_pr.url
    assert github.created_prs == 1
    assert github.pr_calls == 2
    assert github.issue_calls == 0
