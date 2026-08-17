from __future__ import annotations

import asyncio
from dataclasses import replace
import json
import logging

import httpx
import pytest

from ipromise_agent.compiler import (
    ClaimCompilationError,
    DeterministicDemonstrationCompiler,
)
from ipromise_agent.actions import plan_actions
from ipromise_agent.github import GitHubPublishUncertain, PublishedIssue
from ipromise_agent.models import (
    ActionKind,
    ActionState,
    CreateRunRequest,
    EvidenceResult,
    EventState,
    GitHubRepository,
    RunEvent,
    RunStatus,
    VerificationResult,
    Verdict,
    utc_now,
)
from ipromise_agent.service import AuditService
from ipromise_agent.store import InMemoryRunStore

from conftest import FakeReferenceClient, make_service


class _InvalidOutputAfterModelEventCompiler:
    async def compile(self, _capture):
        raise ClaimCompilationError(
            "Gemini returned no schema-valid claim",
            model_invoked=True,
            model="gemini-3.5-flash",
            framework="Google Agent Development Kit 2 Graph Workflow",
        )


class _ReconciledGitHub:
    def __init__(self, repository: GitHubRepository) -> None:
        self.repository = repository
        self.publish_calls = 0

    async def selected_repository(self):
        return self.repository

    async def publish_issue(self, _run, _action):
        self.publish_calls += 1
        return PublishedIssue(
            url="https://github.com/octocat/alpha/issues/17",
            number=17,
            remote_id=9001,
            reconciled=True,
        )


class _PausedGitHub(_ReconciledGitHub):
    def __init__(self, repository: GitHubRepository) -> None:
        super().__init__(repository)
        self.started = asyncio.Event()
        self.release = asyncio.Event()

    async def publish_issue(self, _run, _action):
        self.publish_calls += 1
        self.started.set()
        await self.release.wait()
        return PublishedIssue(
            url="https://github.com/octocat/alpha/issues/17",
            number=17,
            remote_id=9001,
            reconciled=False,
        )


class _UncertainThenReconciledGitHub(_ReconciledGitHub):
    async def publish_issue(self, _run, _action):
        self.publish_calls += 1
        if self.publish_calls == 1:
            raise GitHubPublishUncertain("GitHub did not confirm the issue outcome")
        return PublishedIssue(
            url="https://github.com/octocat/alpha/issues/17",
            number=17,
            remote_id=9001,
            reconciled=True,
        )


class _RetryingReferenceClient(FakeReferenceClient):
    def __init__(self, failures: int) -> None:
        super().__init__()
        self.failures = failures
        self.capture_calls = 0

    async def capture_privacy(self):
        self.capture_calls += 1
        if self.capture_calls <= self.failures:
            raise httpx.ConnectTimeout("temporary synthetic service failure")
        return await super().capture_privacy()


class _PausedReferenceClient(FakeReferenceClient):
    def __init__(self) -> None:
        super().__init__()
        self.capture_calls = 0
        self.started = asyncio.Event()
        self.release = asyncio.Event()

    async def capture_privacy(self):
        self.capture_calls += 1
        self.started.set()
        await self.release.wait()
        return await super().capture_privacy()


class _FailOnceAfterOpenedCheckpointStore(InMemoryRunStore):
    def __init__(self) -> None:
        super().__init__()
        self.failed = False

    async def save(self, run) -> None:
        if not self.failed and any(
            action.state == ActionState.OPENED for action in run.actions
        ):
            self.failed = True
            raise RuntimeError("simulated Firestore checkpoint outage")
        await super().save(run)


@pytest.mark.asyncio
async def test_happy_path_finds_scoped_overdue_contradiction(settings) -> None:
    service, client = make_service(settings)

    run = await service.create_run(
        CreateRunRequest(idempotency_key="happy-path-0001")
    )

    assert run.status == RunStatus.COMPLETE
    assert run.verdict == Verdict.CONTRADICTED
    assert run.claim.control_id == "privacy.account_deletion.v1"
    assert run.claim.deadline_hours == 24
    assert run.runtime.model_invoked is False
    assert run.runtime.model is None
    assert client.seed_calls == 1
    assert client.process_calls == 1

    evidence = {item.id: item for item in run.evidence}
    assert evidence["synthetic-virtual-timeline"].result == EvidenceResult.PASS
    assert "T0+1.00h" in evidence["synthetic-virtual-timeline"].observed
    assert "T0+25.00h" in evidence["synthetic-virtual-timeline"].observed
    assert evidence["app-profile"].result == EvidenceResult.PASS
    assert evidence["analytics-profile"].result == EvidenceResult.FAIL

    assert [action.kind for action in run.actions] == [
        ActionKind.PULL_REQUEST,
        ActionKind.ISSUE,
        ActionKind.EMAIL,
    ]
    assert run.actions[0].state == ActionState.BLOCKED
    assert run.actions[0].verified is False
    assert run.verification is not None
    assert run.verification.candidate_control == VerificationResult.NOT_RUN
    assert run.verification.publishable is False


@pytest.mark.asyncio
async def test_missing_required_store_evidence_is_inconclusive(settings) -> None:
    service, _ = make_service(settings, analytics_exists=None)

    run = await service.create_run(
        CreateRunRequest(idempotency_key="missing-evidence-01")
    )

    assert run.status == RunStatus.COMPLETE
    assert run.verdict == Verdict.INCONCLUSIVE
    assert {item.result for item in run.evidence} == {
        EvidenceResult.PASS,
        EvidenceResult.UNKNOWN,
    }
    assert all(action.state != ActionState.READY for action in run.actions)
    assert run.remediation is None
    assert run.verification is None


@pytest.mark.asyncio
async def test_known_late_worker_is_a_contradiction_not_unknown(settings) -> None:
    service, _ = make_service(
        settings,
        analytics_exists=False,
        profile_exists=False,
        processing_elapsed_hours=25,
    )

    run = await service.create_run(
        CreateRunRequest(idempotency_key="late-worker-0001")
    )

    evidence = {item.id: item for item in run.evidence}
    assert run.verdict == Verdict.CONTRADICTED
    assert evidence["synthetic-virtual-timeline"].result == EvidenceResult.FAIL
    assert evidence["app-profile"].result == EvidenceResult.PASS
    assert evidence["analytics-profile"].result == EvidenceResult.PASS


@pytest.mark.asyncio
async def test_duplicate_trigger_executes_exactly_once(settings) -> None:
    service, client = make_service(settings)
    request = CreateRunRequest(idempotency_key="duplicate-key-001")

    first = await service.create_run(request)
    second = await service.create_run(request)

    assert first.id == second.id
    assert client.seed_calls == 1
    assert client.process_calls == 1
    assert len(await service.list_runs()) == 1


@pytest.mark.asyncio
async def test_distinct_instances_serialize_one_run_execution(settings) -> None:
    store = InMemoryRunStore()
    client = _PausedReferenceClient()
    first_service = AuditService(
        settings=settings,
        store=store,
        reference_client=client,
        compiler=DeterministicDemonstrationCompiler(),
    )
    second_service = AuditService(
        settings=settings,
        store=store,
        reference_client=client,
        compiler=DeterministicDemonstrationCompiler(),
    )
    request = CreateRunRequest(idempotency_key="distributed-duplicate-001")

    active = asyncio.create_task(first_service.create_run(request))
    await asyncio.wait_for(client.started.wait(), timeout=2)
    overlapping = await second_service.create_run(request)

    assert overlapping.status == RunStatus.CAPTURING
    assert client.capture_calls == 1
    assert client.seed_calls == 0

    client.release.set()
    completed = await active
    replay = await second_service.create_run(request)

    assert overlapping.id == completed.id == replay.id
    assert completed.status == RunStatus.COMPLETE
    assert replay.status == RunStatus.COMPLETE
    assert client.capture_calls == 1
    assert client.seed_calls == 1
    assert client.process_calls == 1


@pytest.mark.asyncio
async def test_terminal_run_emits_correlated_structured_receipt(
    settings, caplog
) -> None:
    service, _ = make_service(settings)

    with caplog.at_level(logging.INFO, logger="ipromise.audit"):
        run = await service.create_run(
            CreateRunRequest(idempotency_key="structured-log-001")
        )

    receipts = [
        json.loads(record.message)
        for record in caplog.records
        if record.name == "ipromise.audit"
        and '"event":"ipromise.audit.receipt"' in record.message
    ]
    assert receipts[-1]["runId"] == run.id
    assert receipts[-1]["status"] == "COMPLETE"
    assert receipts[-1]["verdict"] == "CONTRADICTED"
    assert receipts[-1]["controlId"] == "privacy.account_deletion.v1"


@pytest.mark.asyncio
async def test_failed_model_output_preserves_attempt_and_invocation_provenance(
    settings,
) -> None:
    cloud_settings = replace(settings, mode="cloud", compiler="adk")
    service = AuditService(
        settings=cloud_settings,
        reference_client=FakeReferenceClient(),
        compiler=_InvalidOutputAfterModelEventCompiler(),
    )

    run = await service.create_run(
        CreateRunRequest(idempotency_key="invalid-model-output-01")
    )

    assert run.status == RunStatus.FAILED_SAFE
    assert run.verdict == Verdict.INCONCLUSIVE
    assert run.runtime.model_invocation_attempted is True
    assert run.runtime.model_invoked is True
    assert run.runtime.model == "gemini-3.5-flash"
    assert all(action.state == ActionState.SKIPPED for action in run.actions)


@pytest.mark.asyncio
async def test_interrupted_nonterminal_run_restarts_from_safe_checkpoint(
    settings,
) -> None:
    store = InMemoryRunStore()
    first_service = AuditService(
        settings=settings,
        store=store,
        reference_client=FakeReferenceClient(),
        compiler=DeterministicDemonstrationCompiler(),
    )
    key = "interrupted-capture-01"
    interrupted = first_service._new_run(key, None)
    interrupted.status = RunStatus.CAPTURING
    interrupted.events.append(
        RunEvent(
            id=f"{interrupted.id}:event:02",
            stage=RunStatus.CAPTURING.value,
            state=EventState.RUNNING,
            title="Capture promise",
            detail="Worker stopped here",
            at=utc_now(),
        )
    )
    await store.reserve(key, lambda: interrupted)
    await store.save(interrupted)

    resumed_client = FakeReferenceClient()
    resumed = AuditService(
        settings=settings,
        store=store,
        reference_client=resumed_client,
        compiler=DeterministicDemonstrationCompiler(),
    )
    run = await resumed.create_run(CreateRunRequest(idempotency_key=key))

    assert run.status == RunStatus.COMPLETE
    assert run.verdict == Verdict.CONTRADICTED
    assert any(event.title == "Audit resumed" for event in run.events)
    assert resumed_client.process_calls == 1


@pytest.mark.asyncio
async def test_interrupted_issue_dispatch_reconciles_before_completion(
    settings,
) -> None:
    configured = replace(settings, github_actions_enabled=True)
    repository = GitHubRepository(
        id=101,
        full_name="octocat/alpha",
        default_branch="main",
        private=True,
        html_url="https://github.com/octocat/alpha",
    )
    github = _ReconciledGitHub(repository)
    store = InMemoryRunStore()
    service = AuditService(
        settings=configured,
        store=store,
        reference_client=FakeReferenceClient(),
        compiler=DeterministicDemonstrationCompiler(),
        github_service=github,
    )
    key = "interrupted-routing-01"
    interrupted = service._new_run(key, repository)
    interrupted.status = RunStatus.ROUTING_ACTION
    interrupted.verdict = Verdict.CONTRADICTED
    interrupted.actions = plan_actions(
        run_id=interrupted.id,
        verdict=interrupted.verdict,
        receipt=None,
    )
    interrupted.events.append(
        RunEvent(
            id=f"{interrupted.id}:event:02",
            stage=RunStatus.ROUTING_ACTION.value,
            state=EventState.RUNNING,
            title="Select action",
            detail="Publishing",
            at=utc_now(),
        )
    )
    await store.reserve(key, lambda: interrupted)
    await store.save(interrupted)

    run = await service.create_run(CreateRunRequest(idempotency_key=key))

    issue = next(action for action in run.actions if action.kind == ActionKind.ISSUE)
    assert run.status == RunStatus.COMPLETE
    assert issue.state == ActionState.OPENED
    assert issue.url == "https://github.com/octocat/alpha/issues/17"
    assert "reconciled" in (issue.reason or "").lower()
    assert github.publish_calls == 1


@pytest.mark.asyncio
async def test_retryable_run_resumes_same_identity_with_a_bounded_budget(settings) -> None:
    reference = _RetryingReferenceClient(failures=2)
    service = AuditService(
        settings=settings,
        reference_client=reference,
        compiler=DeterministicDemonstrationCompiler(),
    )
    request = CreateRunRequest(idempotency_key="bounded-retry-resume-01")

    first = await service.create_run(request)
    second = await service.create_run(request)
    third = await service.create_run(request)

    assert first.status == RunStatus.FAILED_RETRYABLE
    assert second.status == RunStatus.FAILED_RETRYABLE
    assert third.status == RunStatus.COMPLETE
    assert first.id == second.id == third.id
    assert reference.capture_calls == 3
    assert sum(event.title == "Audit resumed" for event in third.events) == 2


@pytest.mark.asyncio
async def test_retry_budget_exhaustion_fails_safe_and_stops_reexecution(settings) -> None:
    reference = _RetryingReferenceClient(failures=99)
    service = AuditService(
        settings=settings,
        reference_client=reference,
        compiler=DeterministicDemonstrationCompiler(),
    )
    request = CreateRunRequest(idempotency_key="bounded-retry-stop-01")

    await service.create_run(request)
    await service.create_run(request)
    exhausted = await service.create_run(request)
    replay = await service.create_run(request)

    assert exhausted.status == RunStatus.FAILED_SAFE
    assert replay.status == RunStatus.FAILED_SAFE
    assert replay.id == exhausted.id
    assert reference.capture_calls == 3
    assert "retry budget exhausted after 3 attempts" in exhausted.events[-1].detail


@pytest.mark.asyncio
async def test_action_lease_serializes_publishers_sharing_a_store(settings) -> None:
    configured = replace(settings, github_actions_enabled=True)
    repository = GitHubRepository(
        id=101,
        full_name="octocat/alpha",
        default_branch="main",
        private=True,
        html_url="https://github.com/octocat/alpha",
    )
    github = _PausedGitHub(repository)
    store = InMemoryRunStore()
    first_service = AuditService(
        settings=configured,
        store=store,
        reference_client=FakeReferenceClient(),
        compiler=DeterministicDemonstrationCompiler(),
        github_service=github,
    )
    second_service = AuditService(
        settings=configured,
        store=store,
        reference_client=FakeReferenceClient(),
        compiler=DeterministicDemonstrationCompiler(),
        github_service=github,
    )
    key = "shared-store-action-lease-01"
    routing = first_service._new_run(key, repository)
    routing.status = RunStatus.ROUTING_ACTION
    routing.verdict = Verdict.CONTRADICTED
    routing.actions = plan_actions(
        run_id=routing.id,
        verdict=routing.verdict,
        receipt=None,
    )
    routing.events.append(
        RunEvent(
            id=f"{routing.id}:event:02",
            stage=RunStatus.ROUTING_ACTION.value,
            state=EventState.RUNNING,
            title="Select action",
            detail="Publishing",
            at=utc_now(),
        )
    )
    await store.reserve(key, lambda: routing)
    await store.save(routing)
    first_copy = await store.get(routing.id)
    second_copy = await store.get(routing.id)
    assert first_copy is not None and second_copy is not None

    publisher = asyncio.create_task(first_service._dispatch_and_complete(first_copy))
    await github.started.wait()
    non_holder = await second_service._dispatch_and_complete(second_copy)
    github.release.set()
    await publisher

    stored = await store.get(routing.id)
    assert non_holder.status == RunStatus.ROUTING_ACTION
    assert stored is not None and stored.status == RunStatus.COMPLETE
    assert github.publish_calls == 1


@pytest.mark.asyncio
async def test_uncertain_action_outcome_is_truthful_and_resumes_by_reconciliation(
    settings,
) -> None:
    configured = replace(settings, github_actions_enabled=True)
    repository = GitHubRepository(
        id=101,
        full_name="octocat/alpha",
        default_branch="main",
        private=True,
        html_url="https://github.com/octocat/alpha",
    )
    github = _UncertainThenReconciledGitHub(repository)
    service = AuditService(
        settings=configured,
        reference_client=FakeReferenceClient(),
        compiler=DeterministicDemonstrationCompiler(),
        github_service=github,
    )
    request = CreateRunRequest(idempotency_key="uncertain-action-resume-01")

    uncertain = await service.create_run(request)
    resumed = await service.create_run(request)

    assert uncertain.status == RunStatus.FAILED_RETRYABLE
    assert "external-action outcome is uncertain" in uncertain.limitations[-1]
    assert "without external side effects" not in uncertain.limitations[-1]
    assert resumed.status == RunStatus.COMPLETE
    assert resumed.id == uncertain.id
    issue = next(action for action in resumed.actions if action.kind == ActionKind.ISSUE)
    assert issue.state == ActionState.OPENED
    assert "reconciled" in (issue.reason or "").lower()
    assert github.publish_calls == 2


@pytest.mark.asyncio
async def test_confirmed_issue_survives_run_checkpoint_failure_without_republication(
    settings,
) -> None:
    configured = replace(settings, github_actions_enabled=True)
    repository = GitHubRepository(
        id=101,
        full_name="octocat/alpha",
        default_branch="main",
        private=True,
        html_url="https://github.com/octocat/alpha",
    )
    github = _ReconciledGitHub(repository)
    reference = FakeReferenceClient()
    service = AuditService(
        settings=configured,
        store=_FailOnceAfterOpenedCheckpointStore(),
        reference_client=reference,
        compiler=DeterministicDemonstrationCompiler(),
        github_service=github,
    )
    request = CreateRunRequest(idempotency_key="confirmed-action-checkpoint-loss-01")

    checkpoint_failed = await service.create_run(request)
    recovered = await service.create_run(request)

    failed_issue = next(
        action
        for action in checkpoint_failed.actions
        if action.kind == ActionKind.ISSUE
    )
    recovered_issue = next(
        action for action in recovered.actions if action.kind == ActionKind.ISSUE
    )
    assert checkpoint_failed.status == RunStatus.FAILED_RETRYABLE
    assert checkpoint_failed.verdict == Verdict.CONTRADICTED
    assert failed_issue.state == ActionState.OPENED
    assert failed_issue.url == "https://github.com/octocat/alpha/issues/17"
    assert "is confirmed" in checkpoint_failed.limitations[-1]
    assert "without external side effects" not in checkpoint_failed.limitations[-1]
    assert recovered.status == RunStatus.COMPLETE
    assert recovered.id == checkpoint_failed.id
    assert recovered_issue.state == ActionState.OPENED
    assert recovered_issue.url == failed_issue.url
    assert github.publish_calls == 1
    assert reference.seed_calls == 1
    assert reference.process_calls == 1
