"""Idempotent orchestration of semantic and deterministic audit stages."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from uuid import uuid4

import httpx

from .actions import plan_actions
from .compiler import (
    AdkVertexClaimCompiler,
    ClaimCompilationError,
    ClaimCompiler,
    DeterministicDemonstrationCompiler,
)
from .config import Settings
from .control import AccountDeletionControl, can_bind_account_deletion
from .demo_client import HttpReferenceClient, ReferenceClient
from .github import (
    GitHubIntegrationError,
    GitHubPublishUncertain,
    GitHubService,
)
from .models import (
    ActionKind,
    ActionState,
    AuditRun,
    Claim,
    CreateRunRequest,
    EventState,
    Mode,
    PlannedAction,
    RunEvent,
    RunStatus,
    RuntimeInfo,
    GitHubRepository,
    Testability,
    Verdict,
    utc_now,
)
from .remediation import propose_bounded_remediation, unverified_mvp_receipt
from .source import CapturedSource, exact_quote_is_grounded
from .state_machine import fail_run, finish_stage, start_stage
from .store import InMemoryRunStore, RunStore


logger = logging.getLogger("ipromise.audit")
logger.setLevel(logging.INFO)

MAX_RUN_ATTEMPTS = 3
RUN_LEASE_SECONDS = 5 * 60
ACTION_LEASE_SECONDS = 5 * 60


class _ExternalActionCheckpointError(RuntimeError):
    """A confirmed external action could not be checkpointed on the run."""

    def __init__(self, *, issue_number: int, issue_url: str) -> None:
        super().__init__(
            f"GitHub issue #{issue_number} was confirmed, but its run checkpoint failed"
        )
        self.issue_number = issue_number
        self.issue_url = issue_url


class AuditService:
    def __init__(
        self,
        *,
        settings: Settings,
        store: RunStore | None = None,
        reference_client: ReferenceClient | None = None,
        compiler: ClaimCompiler | None = None,
        github_service: GitHubService | None = None,
    ) -> None:
        self.settings = settings
        if store is not None:
            self.store = store
        elif settings.state_backend == "firestore":
            from .firestore_store import FirestoreRunStore

            self.store = FirestoreRunStore(database=settings.firestore_database)
        else:
            self.store = InMemoryRunStore()
        self.reference_client = reference_client or HttpReferenceClient(
            base_url=settings.demo_base_url,
            token=settings.demo_token,
        )
        self.compiler = compiler or self._configured_compiler()
        self.github = github_service or GitHubService(settings)
        self.control = AccountDeletionControl(self.reference_client)
        self._create_lock = asyncio.Lock()
        self._executions: dict[str, asyncio.Task[AuditRun]] = {}

    def _configured_compiler(self) -> ClaimCompiler:
        if self.settings.compiler == "adk":
            return AdkVertexClaimCompiler(self.settings.gemini_model)
        return DeterministicDemonstrationCompiler()

    async def create_run(
        self, request: CreateRunRequest, *, idempotency_key: str | None = None
    ) -> AuditRun:
        if request.control_id != self.control.id:
            raise ValueError(
                f"Unsupported control_id; this MVP accepts only {self.control.id}"
            )
        key = idempotency_key or request.idempotency_key or f"auto:{uuid4().hex}"
        if len(key) < 8 or len(key) > 128:
            raise ValueError("Idempotency key must contain 8 to 128 characters")

        repository = await self.github.selected_repository()
        execution_owner = f"run_execution_{uuid4().hex}"
        async with self._create_lock:
            run, created = await self.store.reserve(
                key, lambda: self._new_run(key, repository)
            )
            task = self._executions.get(run.id)
            if task is not None and task.done():
                self._executions.pop(run.id, None)
                task = None

            operation: Callable[[AuditRun], Awaitable[AuditRun]] | None = None
            if task is None and run.status not in {
                RunStatus.COMPLETE,
                RunStatus.FAILED_SAFE,
            }:
                acquired = await self.store.acquire_run_lease(
                    run.id,
                    execution_owner,
                    lease_seconds=RUN_LEASE_SECONDS,
                )
                if acquired:
                    if created:
                        operation = self._execute
                    elif run.status == RunStatus.FAILED_RETRYABLE:
                        if self._attempt_count(run) < MAX_RUN_ATTEMPTS:
                            if self._failed_during_action_dispatch(run):
                                self._resume_action_dispatch(run)
                                await self.store.save(run)
                                operation = self._dispatch_and_complete
                            else:
                                self._reset_interrupted_run(run)
                                await self.store.save(run)
                                operation = self._execute
                    elif run.status == RunStatus.ROUTING_ACTION:
                        operation = self._dispatch_and_complete
                    elif run.status == RunStatus.VERIFYING and run.verification:
                        operation = self._route_and_complete
                    else:
                        self._reset_interrupted_run(run)
                        await self.store.save(run)
                        operation = self._execute

                    if operation is not None:
                        task = asyncio.create_task(
                            self._run_with_execution_lease(
                                run,
                                execution_owner,
                                operation,
                            )
                        )
                        self._executions[run.id] = task
                    else:
                        await self.store.release_run_lease(
                            run.id,
                            execution_owner,
                        )

        if task is not None:
            result = (await asyncio.shield(task)).model_copy(deep=True)
            self._log_receipt(result)
            return result
        stored = await self.store.get(run.id)
        if stored is None:  # defensive invariant; cannot occur with an atomic reserve
            raise RuntimeError("Reserved run disappeared")
        self._log_receipt(stored)
        return stored

    async def _run_with_execution_lease(
        self,
        run: AuditRun,
        owner: str,
        operation: Callable[[AuditRun], Awaitable[AuditRun]],
    ) -> AuditRun:
        try:
            try:
                return await operation(run)
            except _ExternalActionCheckpointError as exc:
                self._fail_retryable(
                    run,
                    detail=str(exc),
                    side_effects_uncertain=True,
                )
                # The GitHub service returned a verified receipt before the
                # run checkpoint failed. Keep it and replace the generic
                # uncertainty wording with the narrower, known outcome.
                recovery = (
                    "needs a retry before finalization"
                    if run.status == RunStatus.FAILED_RETRYABLE
                    else "requires operator reconciliation"
                )
                run.limitations[-1] = (
                    f"GitHub issue #{exc.issue_number} is confirmed at "
                    f"{exc.issue_url}, but the run checkpoint {recovery}."
                )
                await self.store.save(run)
                return run
        finally:
            try:
                await asyncio.shield(self.store.release_run_lease(run.id, owner))
            except Exception:
                logger.exception(
                    "Failed to release run execution lease",
                    extra={"runId": run.id},
                )

    async def get_run(self, run_id: str) -> AuditRun | None:
        return await self.store.get(run_id)

    async def latest_run(self) -> AuditRun | None:
        return await self.store.latest()

    async def list_runs(self, limit: int = 20) -> list[AuditRun]:
        return await self.store.list(limit)

    def _new_run(
        self, idempotency_key: str, repository: GitHubRepository | None
    ) -> AuditRun:
        now = utc_now()
        run_id = f"run_{uuid4().hex}"
        mode = Mode(self.settings.mode)
        deterministic = self.settings.compiler == "deterministic"
        run = AuditRun(
            id=run_id,
            mode=mode,
            status=RunStatus.RECEIVED,
            verdict=Verdict.PENDING,
            started_at=now,
            updated_at=now,
            claim=Claim(
                exact_quote="Claim capture not completed.",
                source_url=f"{self.settings.demo_base_url}/privacy",
                source_title="Source not captured",
                captured_at=now,
                content_hash="unavailable",
                qualifiers=[],
                testability=Testability.NOT_TESTABLE,
                control_id=None,
            ),
            events=[
                RunEvent(
                    id=f"{run_id}:event:01",
                    stage=RunStatus.RECEIVED.value,
                    state=EventState.SUCCEEDED,
                    title="Audit started",
                    detail="Trigger accepted",
                    at=now,
                    system="Run dispatcher",
                )
            ],
            actions=[],
            runtime=RuntimeInfo(
                agent_framework=(
                    "Deterministic local workflow · Google ADK not used"
                    if deterministic
                    else "Google Agent Development Kit 2 Graph Workflow"
                ),
                model_invocation_attempted=False,
                model_invoked=False,
                model=None,
                execution_target=self.settings.execution_target,
                cloud_run_revision=self.settings.cloud_run_revision,
            ),
            limitations=[
                "All user and store data in this run is synthetic.",
                "The verdict applies only to the configured two-store deletion control; it is not a legal-compliance conclusion.",
            ]
            + (
                []
                if self.settings.github_actions_enabled and repository is not None
                else [
                    "GitHub issue publication was not enabled with a selected repository for this run."
                ]
            )
            + (
                ["This local workflow did not use Gemini or Google ADK."]
                if deterministic
                else []
            ),
            repository=repository,
            idempotency_key=idempotency_key,
        )
        return run

    async def _execute(self, run: AuditRun) -> AuditRun:
        capture: CapturedSource | None = None
        try:
            start_stage(
                run,
                RunStatus.CAPTURING,
                title="Capture promise",
                detail="Read the configured privacy source",
                system="HTTP source capture",
            )
            await self.store.save(run)
            capture = await self.reference_client.capture_privacy()
            finish_stage(
                run,
                "Source captured",
            )
            await self.store.save(run)

            start_stage(
                run,
                RunStatus.COMPILING,
                title="Structure promise",
                detail="Match one narrow claim to its exact source",
                system=(
                    "Google ADK"
                    if self.settings.compiler == "adk"
                    else "Deterministic parser"
                ),
            )
            await self.store.save(run)
            if self.settings.compiler == "adk":
                run.runtime.model_invocation_attempted = True
            compilation = await self.compiler.compile(capture)
            run.runtime.agent_framework = compilation.framework
            run.runtime.model_invoked = compilation.model_invoked
            run.runtime.model = compilation.model
            run.claim = Claim(
                exact_quote=compilation.payload.exact_quote,
                source_url=capture.url,
                source_title=capture.title,
                captured_at=capture.captured_at,
                content_hash=capture.content_hash,
                actor=compilation.payload.actor,
                action=compilation.payload.action,
                object=compilation.payload.object,
                deadline_hours=compilation.payload.deadline_hours,
                qualifiers=compilation.payload.qualifiers,
                testability=compilation.payload.testability,
                control_id=None,
            )
            if not exact_quote_is_grounded(run.claim.exact_quote, capture):
                raise ClaimCompilationError(
                    "The compiled quote was not an exact substring of the captured source"
                )
            finish_stage(
                run,
                "Exact quote matched to source",
            )
            await self.store.save(run)

            start_stage(
                run,
                RunStatus.BINDING,
                title="Match control",
                detail="Only approved controls can run",
                system="Control registry",
            )
            if not can_bind_account_deletion(run.claim):
                run.verdict = Verdict.NOT_TESTED
                finish_stage(run, "No approved control matched; iPromise abstained")
                await self._route_and_complete(run)
                return run
            run.claim.control_id = self.control.id
            finish_stage(run, f"{self.control.id} matched")
            await self.store.save(run)

            start_stage(
                run,
                RunStatus.PROBING,
                title="Test account deletion",
                detail=(
                    "Synthetic request at T0 · worker at +1h · observation at +25h"
                ),
                system="Deterministic deletion control",
            )
            await self.store.save(run)
            control_outcome = await self.control.execute(run.id)
            run.synthetic_fixture_id = control_outcome.fixture_id
            run.evidence = control_outcome.evidence
            finish_stage(
                run,
                f"Evidence collected at +{control_outcome.virtual_elapsed_hours:.2f}h"
                if control_outcome.virtual_elapsed_hours is not None
                else "Required timing evidence was unavailable",
            )
            await self.store.save(run)

            start_stage(
                run,
                RunStatus.EVALUATING,
                title="Evaluate evidence",
                detail="Deterministic code evaluates PASS, FAIL, and UNKNOWN",
                system="Evidence gate",
            )
            run.verdict = control_outcome.verdict
            finish_stage(
                run,
                (
                    "Contradicted · analytics profile remained"
                    if run.verdict == Verdict.CONTRADICTED
                    else f"{run.verdict.value.title()} · scoped evidence recorded"
                ),
            )
            await self.store.save(run)

            if run.verdict == Verdict.CONTRADICTED:
                start_stage(
                    run,
                    RunStatus.REMEDIATING,
                    title="Propose repair",
                    detail="Only one approved source path may change",
                    system="Remediation policy",
                )
                run.remediation = propose_bounded_remediation(run)
                finish_stage(run, "One file edit proposed")
                await self.store.save(run)

                start_stage(
                    run,
                    RunStatus.VERIFYING,
                    title="Verify repair",
                    detail="Require isolated fail-before/pass-after proof",
                    system="Verification gate",
                )
                run.verification = unverified_mvp_receipt()
                finish_stage(
                    run,
                    "Not run · draft PR blocked",
                )
                await self.store.save(run)

            await self._route_and_complete(run)
            return run
        except _ExternalActionCheckpointError:
            raise
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            run.verdict = Verdict.INCONCLUSIVE
            self._fail_retryable(
                run,
                detail=f"Configured reference service was unavailable ({type(exc).__name__})",
            )
        except ClaimCompilationError as exc:
            if exc.framework:
                run.runtime.agent_framework = exc.framework
            run.runtime.model_invoked = exc.model_invoked
            run.runtime.model = exc.model
            run.verdict = Verdict.INCONCLUSIVE
            fail_run(
                run,
                RunStatus.FAILED_SAFE,
                detail=str(exc),
                retryable=False,
            )
        except Exception as exc:  # fail closed; no untrusted exception detail is exposed
            run.verdict = Verdict.INCONCLUSIVE
            fail_run(
                run,
                RunStatus.FAILED_SAFE,
                detail=f"Unexpected safe-stop ({type(exc).__name__})",
                retryable=False,
            )

        run.actions = plan_actions(
            run_id=run.id,
            verdict=run.verdict,
            receipt=run.verification,
        )
        await self.store.save(run)
        return run

    async def _route_and_complete(self, run: AuditRun) -> AuditRun:
        start_stage(
            run,
            RunStatus.ROUTING_ACTION,
            title="Select action",
            detail="Choose one allowed response",
            system="Action planner",
        )
        run.actions = plan_actions(
            run_id=run.id,
            verdict=run.verdict,
            receipt=run.verification,
        )
        await self.store.save(run)
        return await self._dispatch_and_complete(run)

    async def _dispatch_and_complete(self, run: AuditRun) -> AuditRun:
        if (
            run.events
            and run.events[-1].stage == RunStatus.ROUTING_ACTION.value
            and run.events[-1].state == EventState.SUCCEEDED
        ):
            await self._complete_run(run)
            return run
        opened_issue = next(
            (
                action
                for action in run.actions
                if action.kind == ActionKind.ISSUE
                and action.state == ActionState.OPENED
                and action.url is not None
            ),
            None,
        )
        if opened_issue is not None:
            finish_stage(run, "Confirmed GitHub issue receipt preserved")
            await self.store.save(run)
            await self._complete_run(run)
            return run

        selected_issue = next(
            (
                action
                for action in run.actions
                if action.kind == ActionKind.ISSUE
                and action.state == ActionState.PLANNED
            ),
            None,
        )
        if (
            selected_issue is not None
            and self.settings.github_actions_enabled
            and run.repository is not None
        ):
            return await self._dispatch_issue_with_lease(run, selected_issue)
        elif selected_issue is not None and run.repository is None:
            finish_stage(run, "Issue selected · connect a repository to dispatch")
        elif selected_issue is not None:
            finish_stage(run, "Issue selected · external actions are disabled")
        else:
            finish_stage(run, "No external action required")
        await self.store.save(run)

        await self._complete_run(run)
        return run

    async def _dispatch_issue_with_lease(
        self, run: AuditRun, selected_issue: PlannedAction
    ) -> AuditRun:
        owner = f"worker_{uuid4().hex}"
        acquired = await self.store.acquire_action_lease(
            run.id,
            selected_issue.id,
            owner,
            lease_seconds=ACTION_LEASE_SECONDS,
        )
        if not acquired:
            current = await self.store.get(run.id)
            return current if current is not None else run

        try:
            try:
                receipt = await self.github.publish_issue(run, selected_issue)
            except GitHubPublishUncertain as exc:
                self._fail_retryable(
                    run,
                    detail=str(exc),
                    side_effects_uncertain=True,
                )
                await self.store.save(run)
                return run
            except GitHubIntegrationError as exc:
                fail_run(
                    run,
                    RunStatus.FAILED_SAFE,
                    detail=str(exc),
                    retryable=False,
                )
                await self.store.save(run)
                return run
            selected_issue.state = ActionState.OPENED
            selected_issue.url = receipt.url
            selected_issue.reason = (
                "Existing marker-matched issue reconciled"
                if receipt.reconciled
                else "Evidence-backed issue created with a repository-scoped GitHub App token"
            )
            finish_stage(run, f"GitHub issue #{receipt.number} opened")
            try:
                await self.store.save(run)
            except Exception as exc:
                raise _ExternalActionCheckpointError(
                    issue_number=receipt.number,
                    issue_url=receipt.url,
                ) from exc
            await self._complete_run(run)
            return run
        finally:
            try:
                await asyncio.shield(
                    self.store.release_action_lease(
                        run.id, selected_issue.id, owner
                    )
                )
            except Exception:
                # A stale lease expires. Do not let lease cleanup overwrite a
                # confirmed remote receipt or a more informative safe-stop.
                logger.exception(
                    "Failed to release action lease",
                    extra={"runId": run.id, "actionId": selected_issue.id},
                )

    async def _complete_run(self, run: AuditRun) -> None:
        start_stage(
            run,
            RunStatus.COMPLETE,
            title="Audit complete",
            detail="Evidence and action recorded",
            system="iPromise",
        )
        finish_stage(run, "Audit record saved")
        await self.store.save(run)

    def _reset_interrupted_run(self, run: AuditRun) -> None:
        now = utc_now()
        if run.events and run.events[-1].state == EventState.RUNNING:
            run.events[-1].state = EventState.FAILED
            run.events[-1].detail = "Worker stopped before this stage completed"
        run.status = RunStatus.RECEIVED
        run.verdict = Verdict.PENDING
        run.evidence = []
        run.actions = []
        run.remediation = None
        run.verification = None
        run.synthetic_fixture_id = None
        run.updated_at = now
        run.events.append(
            RunEvent(
                id=f"{run.id}:event:{len(run.events) + 1:02d}",
                stage=RunStatus.RECEIVED.value,
                state=EventState.SUCCEEDED,
                title="Audit resumed",
                detail="Interrupted attempt restarted from a safe checkpoint",
                at=now,
                system="Run dispatcher",
            )
        )

    def _resume_action_dispatch(self, run: AuditRun) -> None:
        now = utc_now()
        run.status = RunStatus.ROUTING_ACTION
        run.updated_at = now
        run.events.append(
            RunEvent(
                id=f"{run.id}:event:{len(run.events) + 1:02d}",
                stage=RunStatus.ROUTING_ACTION.value,
                state=EventState.RUNNING,
                title="Action retry resumed",
                detail="Reconciling the existing action intent before any write",
                at=now,
                system="Run dispatcher",
            )
        )

    @staticmethod
    def _failed_during_action_dispatch(run: AuditRun) -> bool:
        issue_states = {
            action.state
            for action in run.actions
            if action.kind == ActionKind.ISSUE
        }
        return bool(
            ActionState.OPENED in issue_states
            or (
                run.events
                and run.events[-1].stage == RunStatus.ROUTING_ACTION.value
                and ActionState.PLANNED in issue_states
            )
        )

    @staticmethod
    def _attempt_count(run: AuditRun) -> int:
        attempt_titles = {"Audit started", "Audit resumed", "Action retry resumed"}
        return sum(event.title in attempt_titles for event in run.events)

    def _fail_retryable(
        self,
        run: AuditRun,
        *,
        detail: str,
        side_effects_uncertain: bool = False,
    ) -> None:
        attempts = self._attempt_count(run)
        exhausted = attempts >= MAX_RUN_ATTEMPTS
        fail_run(
            run,
            RunStatus.FAILED_SAFE if exhausted else RunStatus.FAILED_RETRYABLE,
            detail=(
                f"{detail}; retry budget exhausted after {attempts} attempts"
                if exhausted
                else detail
            ),
            retryable=not exhausted,
            side_effects_uncertain=side_effects_uncertain,
        )

    @staticmethod
    def _log_receipt(run: AuditRun) -> None:
        opened_action = next(
            (action for action in run.actions if action.state == ActionState.OPENED),
            None,
        )
        logger.info(
            json.dumps(
                {
                    "event": "ipromise.audit.receipt",
                    "runId": run.id,
                    "status": run.status.value,
                    "verdict": run.verdict.value,
                    "controlId": run.claim.control_id,
                    "model": run.runtime.model,
                    "modelInvoked": run.runtime.model_invoked,
                    "cloudRunRevision": run.runtime.cloud_run_revision,
                    "action": opened_action.kind.value if opened_action else None,
                    "actionState": opened_action.state.value if opened_action else None,
                },
                separators=(",", ":"),
                sort_keys=True,
            )
        )
