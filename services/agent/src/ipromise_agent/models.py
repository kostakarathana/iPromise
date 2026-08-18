"""Shared, judge-visible wire models for the audit workflow."""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, model_validator


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
    _artifact_binding: "VerificationArtifactBinding | None" = PrivateAttr(
        default=None
    )

    verifier: str
    baseline_control: VerificationResult
    candidate_control: VerificationResult
    regression_suite: VerificationResult
    exact_tree_verified: bool
    isolated: bool
    publishable: bool
    detail: str
    build_id: str | None = None
    log_url: str | None = None

    @property
    def artifact_binding(self) -> "VerificationArtifactBinding | None":
        return self._artifact_binding

    def checkpoint_artifact_binding(
        self, binding: "VerificationArtifactBinding | None"
    ) -> None:
        self._artifact_binding = binding


class VerificationArtifactBinding(WireModel):
    """Tamper-evident link from a receipt to exact source, bytes, and build."""

    schema_version: str = Field(pattern=r"^ipromise\.verification-binding\.v1$")
    repository_url: str = Field(min_length=12, max_length=2_000)
    base_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    unified_diff_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    preimage_hashes: dict[str, str] = Field(min_length=1, max_length=16)
    candidate_hashes: dict[str, str] = Field(min_length=1, max_length=16)
    build_id: str = Field(min_length=1, max_length=256)
    build_name: str = Field(min_length=1, max_length=1_000)
    log_url: str = Field(min_length=12, max_length=2_000)
    binding_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @staticmethod
    def _digest(payload: dict[str, Any]) -> str:
        canonical = json.dumps(
            payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @classmethod
    def create(
        cls,
        *,
        repository_url: str,
        base_sha: str,
        unified_diff_sha256: str,
        preimage_hashes: dict[str, str],
        candidate_hashes: dict[str, str],
        build_id: str,
        build_name: str,
        log_url: str,
    ) -> "VerificationArtifactBinding":
        payload = {
            "schemaVersion": "ipromise.verification-binding.v1",
            "repositoryUrl": repository_url,
            "baseSha": base_sha,
            "unifiedDiffSha256": unified_diff_sha256,
            "preimageHashes": dict(preimage_hashes),
            "candidateHashes": dict(candidate_hashes),
            "buildId": build_id,
            "buildName": build_name,
            "logUrl": log_url,
        }
        return cls.model_validate(
            {**payload, "bindingSha256": cls._digest(payload)}
        )

    @model_validator(mode="after")
    def validate_binding(self) -> "VerificationArtifactBinding":
        if set(self.preimage_hashes) != set(self.candidate_hashes):
            raise ValueError("Verification binding file paths do not match")
        for mapping in (self.preimage_hashes, self.candidate_hashes):
            for path, digest in mapping.items():
                if not path or len(path) > 1_000:
                    raise ValueError("Verification binding contains an invalid path")
                if (
                    len(digest) != 64
                    or any(
                        character not in "0123456789abcdef"
                        for character in digest
                    )
                ):
                    raise ValueError("Verification binding contains an invalid SHA-256")
        payload = self.model_dump(mode="json", by_alias=True)
        supplied = payload.pop("bindingSha256")
        if supplied != self._digest(payload):
            raise ValueError("Verification artifact binding digest does not match")
        return self


class VerifiedCandidateFileCheckpoint(WireModel):
    """One verifier-authenticated file retained only for action recovery."""

    path: str = Field(min_length=1, max_length=1_000)
    preimage_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    candidate_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    content_base64: str = Field(min_length=1, max_length=16 * 1024 * 1024)

    @model_validator(mode="after")
    def validate_exact_bytes(self) -> "VerifiedCandidateFileCheckpoint":
        try:
            content = base64.b64decode(self.content_base64, validate=True)
        except (ValueError, binascii.Error) as exc:
            raise ValueError(
                "Verified candidate content must be canonical base64"
            ) from exc
        if base64.b64encode(content).decode("ascii") != self.content_base64:
            raise ValueError("Verified candidate content must use canonical base64")
        if hashlib.sha256(content).hexdigest() != self.candidate_sha256:
            raise ValueError("Verified candidate bytes do not match their SHA-256")
        return self

    @property
    def content(self) -> bytes:
        return base64.b64decode(self.content_base64, validate=True)


class VerifiedCandidateCheckpoint(WireModel):
    """Minimal byte-exact publisher input, separate from the public run wire."""

    schema_version: str = Field(pattern=r"^ipromise\.verified-candidate\.v1$")
    repository_url: str = Field(min_length=12, max_length=2_000)
    base_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    unified_diff_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    files: list[VerifiedCandidateFileCheckpoint] = Field(min_length=1, max_length=16)

    @model_validator(mode="after")
    def validate_unique_paths(self) -> "VerifiedCandidateCheckpoint":
        paths = [item.path for item in self.files]
        if len(paths) != len(set(paths)):
            raise ValueError("Verified candidate paths must be unique")
        return self

    @classmethod
    def from_verified_candidate(
        cls, candidate: Any
    ) -> "VerifiedCandidateCheckpoint":
        tree = candidate.candidate_tree
        preimages = candidate.preimage_hashes
        candidates = candidate.candidate_hashes
        if set(tree) != set(preimages) or set(tree) != set(candidates):
            raise ValueError("Verified candidate path maps do not match")
        return cls(
            schema_version="ipromise.verified-candidate.v1",
            repository_url=candidate.repository_url,
            base_sha=candidate.base_sha,
            unified_diff_sha256=candidate.unified_diff_sha256,
            files=[
                VerifiedCandidateFileCheckpoint(
                    path=path,
                    preimage_sha256=preimages[path],
                    candidate_sha256=candidates[path],
                    content_base64=base64.b64encode(tree[path]).decode("ascii"),
                )
                for path in sorted(tree)
            ],
        )

    @property
    def candidate_tree(self) -> dict[str, bytes]:
        return {item.path: item.content for item in self.files}

    @property
    def preimage_hashes(self) -> dict[str, str]:
        return {item.path: item.preimage_sha256 for item in self.files}

    @property
    def candidate_hashes(self) -> dict[str, str]:
        return {item.path: item.candidate_sha256 for item in self.files}


class AuditRun(WireModel):
    _verified_candidate: VerifiedCandidateCheckpoint | None = PrivateAttr(default=None)

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

    @property
    def verified_candidate(self) -> VerifiedCandidateCheckpoint | None:
        return self._verified_candidate

    def checkpoint_verified_candidate(
        self, candidate: VerifiedCandidateCheckpoint | None
    ) -> None:
        self._verified_candidate = candidate


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
