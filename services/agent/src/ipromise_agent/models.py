"""Shared, judge-visible wire models for the audit workflow."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


def _to_camel(value: str) -> str:
    first, *rest = value.split("_")
    return first + "".join(part.capitalize() for part in rest)


class WireModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=_to_camel,
        extra="forbid",
        populate_by_name=True,
    )


class Mode(StrEnum):
    CLOUD = "cloud"
    LOCAL = "local"
    DEMONSTRATION = "demonstration"


class RunStatus(StrEnum):
    RECEIVED = "RECEIVED"
    CAPTURING = "CAPTURING"
    COMPILING = "COMPILING"
    BINDING = "BINDING"
    PROBING = "PROBING"
    EVALUATING = "EVALUATING"
    REMEDIATING = "REMEDIATING"
    VERIFYING = "VERIFYING"
    ROUTING_ACTION = "ROUTING_ACTION"
    COMPLETE = "COMPLETE"
    FAILED_RETRYABLE = "FAILED_RETRYABLE"
    FAILED_SAFE = "FAILED_SAFE"


class Verdict(StrEnum):
    PENDING = "PENDING"
    SUPPORTED = "SUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    INCONCLUSIVE = "INCONCLUSIVE"
    NOT_TESTED = "NOT_TESTED"


class Testability(StrEnum):
    EXECUTABLE = "EXECUTABLE"
    PARTIAL = "PARTIAL"
    NOT_TESTABLE = "NOT_TESTABLE"


class EvidenceResult(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"


class EventState(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class ActionKind(StrEnum):
    PULL_REQUEST = "pull_request"
    ISSUE = "issue"
    EMAIL = "email"


class ActionState(StrEnum):
    PLANNED = "PLANNED"
    BLOCKED = "BLOCKED"
    READY = "READY"
    OPENED = "OPENED"
    SENT = "SENT"
    SKIPPED = "SKIPPED"


class VerificationResult(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_RUN = "NOT_RUN"


class GitHubRepository(WireModel):
    """A repository proven accessible through the installed GitHub App."""

    id: int = Field(gt=0)
    full_name: str = Field(min_length=3)
    default_branch: str = Field(min_length=1)
    private: bool
    archived: bool = False
    html_url: str


class GitHubIntegrationStatus(WireModel):
    configured: bool
    connected: bool
    actions_enabled: bool
    account_login: str | None = None
    repositories: list[GitHubRepository] = Field(default_factory=list)
    selected_repository: GitHubRepository | None = None


class GitHubInstallUrl(WireModel):
    url: str


class GitHubOAuthStartRequest(WireModel):
    installation_id: int = Field(gt=0)
    setup_action: str = Field(default="install", max_length=32)
    state: str = Field(min_length=20, max_length=256)


class GitHubOAuthCallbackRequest(WireModel):
    code: str = Field(min_length=8, max_length=512)
    state: str = Field(min_length=20, max_length=256)


class GitHubRepositorySelection(WireModel):
    repository_id: int = Field(gt=0)


class Claim(WireModel):
    exact_quote: str = Field(min_length=1)
    source_url: str
    source_title: str
    captured_at: datetime
    content_hash: str
    actor: str | None = None
    action: str | None = None
    object: str | None = None
    deadline_hours: int | None = Field(default=None, ge=0)
    qualifiers: list[str] = Field(default_factory=list)
    testability: Testability
    control_id: str | None = None


class Evidence(WireModel):
    id: str
    label: str
    expected: str
    observed: str
    result: EvidenceResult
    scope: str | None = None
    artifact_ref: str | None = None


class RunEvent(WireModel):
    id: str
    stage: str
    state: EventState
    title: str
    at: datetime
    detail: str | None = None
    system: str | None = None
    artifact_ref: str | None = None


class PlannedAction(WireModel):
    id: str
    kind: ActionKind
    state: ActionState
    title: str
    verified: bool
    reason: str | None = None
    url: str | None = None


class RuntimeInfo(WireModel):
    agent_framework: str
    model_invocation_attempted: bool
    model_invoked: bool
    model: str | None = None
    execution_target: str
    cloud_run_revision: str | None = None


class FileEdit(WireModel):
    path: str
    operation: str
    rationale: str
    content_preview: str


class RemediationProposal(WireModel):
    summary: str
    base_reference: str
    edits: list[FileEdit]
    generated_by: str


class VerificationReceipt(WireModel):
    verifier: str
    baseline_control: VerificationResult
    candidate_control: VerificationResult
    regression_suite: VerificationResult
    exact_tree_verified: bool
    isolated: bool
    publishable: bool
    detail: str


class AuditRun(WireModel):
    id: str = Field(min_length=8)
    mode: Mode
    status: RunStatus
    verdict: Verdict
    started_at: datetime
    updated_at: datetime
    claim: Claim
    evidence: list[Evidence] = Field(default_factory=list)
    events: list[RunEvent] = Field(default_factory=list)
    actions: list[PlannedAction] = Field(default_factory=list)
    runtime: RuntimeInfo
    limitations: list[str] = Field(default_factory=list)
    remediation: RemediationProposal | None = None
    verification: VerificationReceipt | None = None
    repository: GitHubRepository | None = None
    idempotency_key: str
    synthetic_fixture_id: str | None = None


class CreateRunRequest(WireModel):
    trigger: str = Field(default="manual", max_length=32)
    source: str = Field(default="api", max_length=32)
    control_id: str = Field(default="privacy.account_deletion.v1", max_length=64)
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=128)


class CompilationPayload(BaseModel):
    """Strict model output; source metadata is supplied by deterministic capture."""

    model_config = ConfigDict(extra="forbid")

    exact_quote: str = Field(min_length=1)
    actor: str = Field(min_length=1)
    action: str = Field(min_length=1)
    object: str = Field(min_length=1)
    deadline_hours: int | None = Field(default=None, ge=0)
    qualifiers: list[str] = Field(default_factory=list)
    testability: Testability


def utc_now() -> datetime:
    return datetime.now(UTC)
