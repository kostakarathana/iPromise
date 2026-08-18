"""Fail-closed Cloud Build verification for one byte-exact remediation.

The candidate is not allowed to supply commands, a build configuration, or a
test harness.  This module creates the complete Cloud Build request inline,
fetches one public repository at one full commit SHA, executes a hidden control
before and after materialising the approved candidate bytes, and runs the
reference SaaS regression suite.  A successful result remains bound to the
exact bytes that a separate GitHub publisher may upload.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import re
import time
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol
from urllib.parse import urlparse

from .models import (
    VerificationArtifactBinding,
    VerificationReceipt,
    VerificationResult,
)
from .remediation import (
    ALLOWED_REMEDIATION_PATHS,
    BoundedRemediationArtifact,
    CandidateFile,
    EXPECTED_CANDIDATE_SHA256,
    EXPECTED_PREIMAGE_SHA256,
    EXPECTED_UNIFIED_DIFF_SHA256,
)


PUBLIC_REPOSITORY_URL = "https://github.com/kostakarathana/iPromise.git"
GIT_BUILDER_IMAGE = (
    "gcr.io/cloud-builders/git@sha256:"
    "3040f78b726c7134c1af38131567287157cc23d6453fd2f1a0eab955cc43ddc2"
)
PYTHON_BUILDER_IMAGE = (
    "python:3.12-slim-bookworm@sha256:"
    "a116514e19457bcb7af7efe9c3dd0b9b71e85b317694e7882a1c52aa15a78134"
)
UV_VERSION = "0.12.1"
REQUIRED_STEP_IDS = (
    "source-integrity",
    "install-locked-dependencies",
    "baseline-hidden-control",
    "materialize-candidate",
    "candidate-hidden-control",
    "demo-saas-regression",
    "candidate-integrity",
)
TERMINAL_BUILD_STATUSES = frozenset(
    {"SUCCESS", "FAILURE", "INTERNAL_ERROR", "TIMEOUT", "CANCELLED", "EXPIRED"}
)
_FULL_SHA = re.compile(r"[0-9a-f]{40}\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_PROJECT_ID = re.compile(r"[a-z][a-z0-9-]{4,28}[a-z0-9]\Z")
_LOCATION = re.compile(r"(?:global|[a-z]+(?:-[a-z0-9]+)+)\Z")


class VerificationDecision(StrEnum):
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    UNAVAILABLE = "UNAVAILABLE"


class VerificationFailureCode(StrEnum):
    NONE = "NONE"
    INVALID_ARTIFACT = "INVALID_ARTIFACT"
    SUBMISSION_FAILED = "SUBMISSION_FAILED"
    POLL_FAILED = "POLL_FAILED"
    DEADLINE_EXCEEDED = "DEADLINE_EXCEEDED"
    SOURCE_MISMATCH = "SOURCE_MISMATCH"
    BASELINE_MISMATCH = "BASELINE_MISMATCH"
    CANDIDATE_MISMATCH = "CANDIDATE_MISMATCH"
    CANDIDATE_CONTROL_FAILED = "CANDIDATE_CONTROL_FAILED"
    REGRESSION_FAILED = "REGRESSION_FAILED"
    BUILD_FAILED = "BUILD_FAILED"
    BUILD_INTERNAL_ERROR = "BUILD_INTERNAL_ERROR"
    BUILD_CANCELLED = "BUILD_CANCELLED"
    BUILD_EXPIRED = "BUILD_EXPIRED"
    EVIDENCE_INCOMPLETE = "EVIDENCE_INCOMPLETE"


class CheckResult(StrEnum):
    EXPECTED_FAILURE = "EXPECTED_FAILURE"
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_RUN = "NOT_RUN"


class VerifierConfigurationError(ValueError):
    """The verifier cannot run safely with the supplied infrastructure config."""


class VerifierArtifactError(ValueError):
    """The candidate does not match the bounded remediation contract."""


@dataclass(frozen=True, slots=True)
class CloudBuildVerifierConfig:
    project_id: str
    service_account: str
    location: str = "australia-southeast1"
    repository_url: str = PUBLIC_REPOSITORY_URL
    build_timeout_seconds: int = 600
    queue_ttl_seconds: int = 120
    overall_timeout_seconds: float = 750.0
    rpc_timeout_seconds: float = 15.0
    poll_interval_seconds: float = 2.0

    def __post_init__(self) -> None:
        if _PROJECT_ID.fullmatch(self.project_id) is None:
            raise VerifierConfigurationError("project_id is not a valid Google Cloud project ID")
        if _LOCATION.fullmatch(self.location) is None:
            raise VerifierConfigurationError("location is not a valid Cloud Build location")
        if self.repository_url != PUBLIC_REPOSITORY_URL:
            raise VerifierConfigurationError(
                f"repository_url must exactly equal {PUBLIC_REPOSITORY_URL}"
            )
        expected_prefix = f"projects/{self.project_id}/serviceAccounts/"
        if not self.service_account.startswith(expected_prefix):
            raise VerifierConfigurationError(
                "service_account must be a resource in the configured project"
            )
        service_account_email = self.service_account.removeprefix(expected_prefix)
        if not service_account_email.endswith(
            f"@{self.project_id}.iam.gserviceaccount.com"
        ):
            raise VerifierConfigurationError(
                "service_account must use a project-owned IAM service account"
            )
        if not 60 <= self.build_timeout_seconds <= 900:
            raise VerifierConfigurationError("build timeout must be between 60 and 900 seconds")
        if not 10 <= self.queue_ttl_seconds <= 600:
            raise VerifierConfigurationError("queue TTL must be between 10 and 600 seconds")
        if not self.build_timeout_seconds <= self.overall_timeout_seconds <= 1200:
            raise VerifierConfigurationError(
                "overall timeout must cover the build timeout and be at most 1200 seconds"
            )
        if not 1 <= self.rpc_timeout_seconds <= 60:
            raise VerifierConfigurationError("RPC timeout must be between 1 and 60 seconds")
        if not 0.05 <= self.poll_interval_seconds <= 30:
            raise VerifierConfigurationError(
                "poll interval must be between 0.05 and 30 seconds"
            )

    @property
    def parent(self) -> str:
        return f"projects/{self.project_id}/locations/{self.location}"


@dataclass(frozen=True, slots=True)
class BuildSubmission:
    build_id: str
    build_name: str


@dataclass(frozen=True, slots=True)
class BuildStepSnapshot:
    id: str
    status: str


@dataclass(frozen=True, slots=True)
class BuildSnapshot:
    build_id: str
    build_name: str
    status: str
    log_url: str | None
    resolved_source_url: str | None
    resolved_revision: str | None
    steps: tuple[BuildStepSnapshot, ...]
    status_detail: str | None = None


class CloudBuildGateway(Protocol):
    async def submit(self, build: Mapping[str, Any]) -> BuildSubmission: ...

    async def get(self, build_name: str) -> BuildSnapshot: ...

    async def cancel(self, build_name: str) -> None: ...


@dataclass(frozen=True, slots=True)
class CandidateFileEvidence:
    path: str
    preimage_sha256: str
    candidate_sha256: str
    content: bytes


@dataclass(frozen=True, slots=True)
class CloudBuildEvidence:
    build_id: str
    build_name: str
    status: str
    log_url: str | None
    requested_source_url: str
    resolved_source_url: str | None
    requested_base_sha: str
    resolved_base_sha: str | None
    unified_diff_sha256: str
    step_results: tuple[BuildStepSnapshot, ...]


@dataclass(frozen=True, slots=True)
class VerifiedCandidate:
    """Exact publication bytes plus the cloud receipt that proved them."""

    schema_version: str
    repository_url: str
    base_sha: str
    unified_diff_sha256: str
    files: tuple[CandidateFileEvidence, ...]
    evidence: CloudBuildEvidence

    @property
    def candidate_tree(self) -> dict[str, bytes]:
        return {item.path: item.content for item in self.files}

    @property
    def preimage_hashes(self) -> dict[str, str]:
        return {item.path: item.preimage_sha256 for item in self.files}

    @property
    def candidate_hashes(self) -> dict[str, str]:
        return {item.path: item.candidate_sha256 for item in self.files}


@dataclass(frozen=True, slots=True)
class VerificationOutcome:
    decision: VerificationDecision
    failure_code: VerificationFailureCode
    detail: str
    baseline_control: CheckResult
    candidate_control: CheckResult
    regression_suite: CheckResult
    exact_source_verified: bool
    exact_candidate_verified: bool
    evidence: CloudBuildEvidence | None = None
    candidate: VerifiedCandidate | None = None

    @property
    def publishable(self) -> bool:
        return (
            self.decision == VerificationDecision.VERIFIED
            and self.failure_code == VerificationFailureCode.NONE
            and self.baseline_control == CheckResult.EXPECTED_FAILURE
            and self.candidate_control == CheckResult.PASS
            and self.regression_suite == CheckResult.PASS
            and self.exact_source_verified
            and self.exact_candidate_verified
            and self.candidate is not None
        )

    def to_verification_receipt(self) -> VerificationReceipt:
        """Translate to the existing run wire receipt without inflating claims."""

        baseline = (
            VerificationResult.FAIL
            if self.baseline_control == CheckResult.EXPECTED_FAILURE
            else VerificationResult.NOT_RUN
        )
        candidate = (
            VerificationResult.PASS
            if self.candidate_control == CheckResult.PASS
            else VerificationResult.FAIL
            if self.candidate_control == CheckResult.FAIL
            else VerificationResult.NOT_RUN
        )
        regression = (
            VerificationResult.PASS
            if self.regression_suite == CheckResult.PASS
            else VerificationResult.FAIL
            if self.regression_suite == CheckResult.FAIL
            else VerificationResult.NOT_RUN
        )
        evidence_log_url = (
            self.evidence.log_url if self.evidence is not None else None
        )
        if evidence_log_url is not None:
            parsed_log_url = urlparse(evidence_log_url)
            if parsed_log_url.scheme != "https" or not parsed_log_url.hostname:
                evidence_log_url = None
        verifier = "Google Cloud Build red-before/green-after gate"
        receipt = VerificationReceipt(
            verifier=verifier,
            baseline_control=baseline,
            candidate_control=candidate,
            regression_suite=regression,
            exact_tree_verified=self.exact_candidate_verified,
            isolated=self.evidence is not None,
            publishable=self.publishable,
            detail=self.detail,
            build_id=self.evidence.build_id if self.evidence is not None else None,
            log_url=evidence_log_url,
        )
        if self.publishable and self.candidate is not None and self.evidence is not None:
            if self.evidence.log_url is None:
                raise ValueError("A publishable verification requires a durable log URL")
            receipt.checkpoint_artifact_binding(
                VerificationArtifactBinding.create(
                    repository_url=self.candidate.repository_url,
                    base_sha=self.candidate.base_sha,
                    unified_diff_sha256=self.candidate.unified_diff_sha256,
                    preimage_hashes=self.candidate.preimage_hashes,
                    candidate_hashes=self.candidate.candidate_hashes,
                    build_id=self.evidence.build_id,
                    build_name=self.evidence.build_name,
                    log_url=self.evidence.log_url,
                )
            )
        return receipt


class VerifierBackend(Protocol):
    async def verify(
        self, artifact: BoundedRemediationArtifact
    ) -> VerificationOutcome: ...


_TRUSTED_CONTROL = r'''from __future__ import annotations

import sys

from ipromise_demo.store import SyntheticStore

mode = sys.argv[1]
store = SyntheticStore()
fixture = store.seed("run_cloudbuild_hidden_control", 25)
before = store.inspect(fixture.account_id)
processed = store.process_deletion(fixture.account_id)
after = store.inspect(fixture.account_id)

common = (
    before.profile_exists is True
    and before.analytics_profile_exists is True
    and processed is not None
    and processed.virtual_processing_elapsed_hours <= 24
    and after.virtual_observation_elapsed_hours is not None
    and after.virtual_observation_elapsed_hours > 24
    and after.profile_exists is False
)
if not common:
    print("IPROMISE_CONTROL_ERROR reason=fixture_or_timeline_invariant")
    raise SystemExit(40)

if mode == "baseline":
    if after.analytics_profile_exists is not True:
        print("IPROMISE_CONTROL_ERROR reason=baseline_did_not_leave_analytics_residual")
        raise SystemExit(41)
    print("IPROMISE_CONTROL_RESULT result=FAIL reason=analytics_residual_after_25h")
elif mode == "candidate":
    if after.analytics_profile_exists is not False:
        print("IPROMISE_CONTROL_ERROR reason=candidate_left_analytics_residual")
        raise SystemExit(42)
    print("IPROMISE_CONTROL_RESULT result=PASS reason=both_owned_stores_removed")
else:
    print("IPROMISE_CONTROL_ERROR reason=unknown_mode")
    raise SystemExit(43)
'''


_MATERIALIZE_CANDIDATE = r'''from __future__ import annotations

import base64
import difflib
import hashlib
import os
import sys
from pathlib import Path, PurePosixPath

root = Path(os.environ.get("IPROMISE_VERIFIER_WORKSPACE", "/workspace")).resolve()
expected_diff = base64.b64decode(sys.argv[1], validate=True)
expected_diff_hash = sys.argv[2]
raw = sys.argv[3:]
if len(raw) == 0 or len(raw) % 4:
    print("IPROMISE_CANDIDATE_ERROR reason=invalid_materialization_arguments")
    raise SystemExit(50)

expected_paths = (
    "apps/demo_saas/src/ipromise_demo/store.py",
    "apps/demo_saas/tests/test_app.py",
)
entries = []
for index in range(0, len(raw), 4):
    path, preimage_hash, candidate_hash, encoded_candidate = raw[index:index + 4]
    pure_path = PurePosixPath(path)
    if pure_path.is_absolute() or ".." in pure_path.parts:
        print("IPROMISE_CANDIDATE_ERROR reason=unsafe_path")
        raise SystemExit(51)
    target = (root / pure_path).resolve()
    if root not in target.parents or target.is_symlink() or not target.is_file():
        print("IPROMISE_CANDIDATE_ERROR reason=non_regular_target")
        raise SystemExit(52)
    preimage = target.read_bytes()
    candidate = base64.b64decode(encoded_candidate, validate=True)
    if hashlib.sha256(preimage).hexdigest() != preimage_hash:
        print("IPROMISE_CANDIDATE_ERROR reason=preimage_hash_mismatch")
        raise SystemExit(53)
    if hashlib.sha256(candidate).hexdigest() != candidate_hash:
        print("IPROMISE_CANDIDATE_ERROR reason=candidate_hash_mismatch")
        raise SystemExit(54)
    entries.append((path, target, preimage, candidate, candidate_hash))

if tuple(path for path, *_ in entries) != expected_paths:
    print("IPROMISE_CANDIDATE_ERROR reason=path_set_mismatch")
    raise SystemExit(55)

chunks = []
for path, _, preimage, candidate, _ in entries:
    try:
        before = preimage.decode("utf-8")
        after = candidate.decode("utf-8")
    except UnicodeDecodeError:
        print("IPROMISE_CANDIDATE_ERROR reason=non_utf8_candidate")
        raise SystemExit(56)
    chunks.extend(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
            lineterm="\n",
        )
    )
observed_diff = "".join(chunks).encode("utf-8")
if observed_diff != expected_diff:
    print("IPROMISE_CANDIDATE_ERROR reason=canonical_diff_mismatch")
    raise SystemExit(57)
if hashlib.sha256(observed_diff).hexdigest() != expected_diff_hash:
    print("IPROMISE_CANDIDATE_ERROR reason=canonical_diff_hash_mismatch")
    raise SystemExit(58)

for _, target, _, candidate, candidate_hash in entries:
    temporary = target.with_name(f".ipromise-{candidate_hash}.tmp")
    temporary.write_bytes(candidate)
    os.replace(temporary, target)
    if hashlib.sha256(target.read_bytes()).hexdigest() != candidate_hash:
        print("IPROMISE_CANDIDATE_ERROR reason=post_write_hash_mismatch")
        raise SystemExit(59)

print(f"IPROMISE_CANDIDATE_RESULT result=MATERIALIZED diff_sha256={expected_diff_hash}")
'''


def _validate_artifact(artifact: BoundedRemediationArtifact) -> None:
    if not isinstance(artifact, BoundedRemediationArtifact):
        raise VerifierArtifactError("artifact must be a BoundedRemediationArtifact")
    if artifact.schema_version != "ipromise.bounded-remediation.v1":
        raise VerifierArtifactError("unsupported bounded remediation schema")
    if _FULL_SHA.fullmatch(artifact.base_sha) is None:
        raise VerifierArtifactError("base SHA must be a full lowercase Git commit SHA")
    diff_bytes = artifact.unified_diff.encode("utf-8")
    if hashlib.sha256(diff_bytes).hexdigest() != artifact.unified_diff_sha256:
        raise VerifierArtifactError("unified diff digest does not match its bytes")
    if len(base64.b64encode(diff_bytes)) > 4000:
        raise VerifierArtifactError(
            "base64-encoded unified diff exceeds the Cloud Build input bound"
        )
    paths = tuple(item.path for item in artifact.candidate_files)
    if paths != ALLOWED_REMEDIATION_PATHS:
        raise VerifierArtifactError("candidate file order and path set must equal the allowlist")
    for item in artifact.candidate_files:
        if not isinstance(item, CandidateFile):
            raise VerifierArtifactError("candidate_files contains an unsupported entry")
        if _SHA256.fullmatch(item.preimage_sha256) is None:
            raise VerifierArtifactError(f"invalid preimage digest for {item.path}")
        if _SHA256.fullmatch(item.candidate_sha256) is None:
            raise VerifierArtifactError(f"invalid candidate digest for {item.path}")
        if hashlib.sha256(item.content).hexdigest() != item.candidate_sha256:
            raise VerifierArtifactError(f"candidate digest mismatch for {item.path}")
    if artifact.candidate_tree != {
        item.path: item.content for item in artifact.candidate_files
    }:
        raise VerifierArtifactError("candidate tree bytes do not match candidate_files")
    if artifact.preimage_hashes != {
        item.path: item.preimage_sha256 for item in artifact.candidate_files
    }:
        raise VerifierArtifactError("preimage hash map does not match candidate_files")
    if artifact.candidate_hashes != {
        item.path: item.candidate_sha256 for item in artifact.candidate_files
    }:
        raise VerifierArtifactError("candidate hash map does not match candidate_files")
    if artifact.preimage_hashes != EXPECTED_PREIMAGE_SHA256:
        raise VerifierArtifactError(
            "preimage hashes do not match the locked vulnerable snapshot"
        )
    if artifact.candidate_hashes != EXPECTED_CANDIDATE_SHA256:
        raise VerifierArtifactError(
            "candidate hashes do not match the one approved remediation template"
        )
    if artifact.unified_diff_sha256 != EXPECTED_UNIFIED_DIFF_SHA256:
        raise VerifierArtifactError(
            "unified diff does not match the one approved remediation template"
        )


def build_trusted_cloud_build(
    config: CloudBuildVerifierConfig,
    artifact: BoundedRemediationArtifact,
) -> dict[str, Any]:
    """Return the complete inline build; the candidate contributes no commands."""

    _validate_artifact(artifact)
    source_env = [f"IPROMISE_BASE_SHA={artifact.base_sha}"]
    for index, item in enumerate(artifact.candidate_files, start=1):
        source_env.extend(
            (
                f"IPROMISE_PATH_{index}={item.path}",
                f"IPROMISE_PREIMAGE_SHA256_{index}={item.preimage_sha256}",
            )
        )
    materialize_args = [
        "-c",
        _MATERIALIZE_CANDIDATE,
        base64.b64encode(artifact.unified_diff.encode("utf-8")).decode("ascii"),
        artifact.unified_diff_sha256,
    ]
    for item in artifact.candidate_files:
        materialize_args.extend(
            (
                item.path,
                item.preimage_sha256,
                item.candidate_sha256,
                base64.b64encode(item.content).decode("ascii"),
            )
        )

    candidate_env: list[str] = []
    for index, item in enumerate(artifact.candidate_files, start=1):
        candidate_env.extend(
            (
                f"IPROMISE_PATH_{index}={item.path}",
                f"IPROMISE_CANDIDATE_SHA256_{index}={item.candidate_sha256}",
            )
        )

    return {
        "source": {
            "git_source": {
                "url": config.repository_url,
                "revision": artifact.base_sha,
            }
        },
        "steps": [
            {
                "name": GIT_BUILDER_IMAGE,
                "id": "source-integrity",
                "entrypoint": "bash",
                "env": source_env,
                "args": [
                    "-ceu",
                    (
                        'actual="$$(git rev-parse HEAD)"\n'
                        'test "$$actual" = "$$IPROMISE_BASE_SHA"\n'
                        'test -z "$$(git status --porcelain --untracked-files=all)"\n'
                        'test -f "$$IPROMISE_PATH_1" && test ! -L "$$IPROMISE_PATH_1"\n'
                        'test -f "$$IPROMISE_PATH_2" && test ! -L "$$IPROMISE_PATH_2"\n'
                        'test "$$(sha256sum "$$IPROMISE_PATH_1" | cut -d " " -f 1)" = '
                        '"$$IPROMISE_PREIMAGE_SHA256_1"\n'
                        'test "$$(sha256sum "$$IPROMISE_PATH_2" | cut -d " " -f 1)" = '
                        '"$$IPROMISE_PREIMAGE_SHA256_2"\n'
                        'printf "IPROMISE_SOURCE_RESULT result=PASS base_sha=%s\\n" '
                        '"$$actual"'
                    ),
                ],
                "timeout": "30s",
            },
            {
                "name": PYTHON_BUILDER_IMAGE,
                "id": "install-locked-dependencies",
                "entrypoint": "bash",
                "args": [
                    "-ceu",
                    (
                        f"python -m pip install --disable-pip-version-check --no-cache-dir "
                        f"uv=={UV_VERSION}\n"
                        "uv sync --project apps/demo_saas --locked --extra dev"
                    ),
                ],
                "timeout": "240s",
            },
            {
                "name": PYTHON_BUILDER_IMAGE,
                "id": "baseline-hidden-control",
                "entrypoint": "/workspace/apps/demo_saas/.venv/bin/python",
                "args": ["-c", _TRUSTED_CONTROL, "baseline"],
                "timeout": "30s",
            },
            {
                "name": PYTHON_BUILDER_IMAGE,
                "id": "materialize-candidate",
                "entrypoint": "python",
                "env": ["IPROMISE_VERIFIER_WORKSPACE=/workspace"],
                "args": materialize_args,
                "timeout": "30s",
            },
            {
                "name": PYTHON_BUILDER_IMAGE,
                "id": "candidate-hidden-control",
                "entrypoint": "/workspace/apps/demo_saas/.venv/bin/python",
                "args": ["-c", _TRUSTED_CONTROL, "candidate"],
                "timeout": "30s",
            },
            {
                "name": PYTHON_BUILDER_IMAGE,
                "id": "demo-saas-regression",
                "entrypoint": "/workspace/apps/demo_saas/.venv/bin/python",
                "args": ["-m", "pytest", "apps/demo_saas/tests"],
                "timeout": "180s",
            },
            {
                "name": GIT_BUILDER_IMAGE,
                "id": "candidate-integrity",
                "entrypoint": "bash",
                "env": candidate_env,
                "args": [
                    "-ceu",
                    (
                        'changed="$$(git diff --name-only --diff-filter=ACDMRTUXB)"\n'
                        'expected="$$(printf "%s\\n%s" "$$IPROMISE_PATH_1" '
                        '"$$IPROMISE_PATH_2")"\n'
                        'test "$$changed" = "$$expected"\n'
                        'git diff --check\n'
                        'test "$$(sha256sum "$$IPROMISE_PATH_1" | cut -d " " -f 1)" = '
                        '"$$IPROMISE_CANDIDATE_SHA256_1"\n'
                        'test "$$(sha256sum "$$IPROMISE_PATH_2" | cut -d " " -f 1)" = '
                        '"$$IPROMISE_CANDIDATE_SHA256_2"\n'
                        'printf "IPROMISE_CANDIDATE_RESULT result=PASS files=2\\n"'
                    ),
                ],
                "timeout": "30s",
            },
        ],
        "timeout": f"{config.build_timeout_seconds}s",
        "queue_ttl": f"{config.queue_ttl_seconds}s",
        "options": {
            "logging": "CLOUD_LOGGING_ONLY",
            "source_provenance_hash": ["SHA256"],
        },
        "service_account": config.service_account,
        "tags": [
            "ipromise-verifier",
            f"base-{artifact.base_sha[:12]}",
            f"candidate-{artifact.unified_diff_sha256[:12]}",
        ],
    }


class GoogleCloudBuildGateway:
    """Thin async boundary around the official Google Cloud Build client."""

    def __init__(
        self,
        config: CloudBuildVerifierConfig,
        *,
        client: Any | None = None,
    ) -> None:
        self._config = config
        if client is None:
            try:
                from google.cloud.devtools import cloudbuild_v1
            except ImportError as exc:  # pragma: no cover - packaging guard
                raise VerifierConfigurationError(
                    "Install the agent's google dependency extra to use Cloud Build"
                ) from exc
            client = cloudbuild_v1.CloudBuildClient()
        self._client = client

    @staticmethod
    def _types() -> Any:
        from google.cloud.devtools import cloudbuild_v1

        return cloudbuild_v1

    async def submit(self, build: Mapping[str, Any]) -> BuildSubmission:
        types = self._types()
        request = types.CreateBuildRequest(
            parent=self._config.parent,
            project_id=self._config.project_id,
            build=types.Build(build),
        )
        operation = await asyncio.to_thread(
            self._client.create_build,
            request=request,
            timeout=self._config.rpc_timeout_seconds,
        )
        metadata = getattr(operation, "metadata", None)
        submitted = getattr(metadata, "build", None)
        build_id = str(getattr(submitted, "id", "") or "")
        build_name = str(getattr(submitted, "name", "") or "")
        if not build_id:
            raise RuntimeError("Cloud Build submission returned no build ID")
        if not build_name:
            build_name = f"{self._config.parent}/builds/{build_id}"
        return BuildSubmission(build_id=build_id, build_name=build_name)

    async def get(self, build_name: str) -> BuildSnapshot:
        types = self._types()
        response = await asyncio.to_thread(
            self._client.get_build,
            request=types.GetBuildRequest(name=build_name),
            timeout=self._config.rpc_timeout_seconds,
        )
        return self._snapshot(response)

    async def cancel(self, build_name: str) -> None:
        types = self._types()
        await asyncio.to_thread(
            self._client.cancel_build,
            request=types.CancelBuildRequest(name=build_name),
            timeout=self._config.rpc_timeout_seconds,
        )

    @classmethod
    def _snapshot(cls, build: Any) -> BuildSnapshot:
        source_provenance = getattr(build, "source_provenance", None)
        resolved = getattr(source_provenance, "resolved_git_source", None)
        return BuildSnapshot(
            build_id=str(getattr(build, "id", "") or ""),
            build_name=str(getattr(build, "name", "") or ""),
            status=cls._enum_name(getattr(build, "status", None), build.Status),
            log_url=str(getattr(build, "log_url", "") or "") or None,
            resolved_source_url=(
                str(getattr(resolved, "url", "") or "") or None
            ),
            resolved_revision=(
                str(getattr(resolved, "revision", "") or "") or None
            ),
            steps=tuple(
                BuildStepSnapshot(
                    id=str(getattr(step, "id", "") or ""),
                    status=cls._enum_name(
                        getattr(step, "status", None), build.Status
                    ),
                )
                for step in getattr(build, "steps", ())
            ),
            status_detail=str(getattr(build, "status_detail", "") or "") or None,
        )

    @staticmethod
    def _enum_name(value: Any, enum_type: Any) -> str:
        try:
            return str(enum_type(value).name)
        except (TypeError, ValueError):
            name = getattr(value, "name", None)
            return str(name or value or "STATUS_UNKNOWN")


class CloudBuildVerifier:
    def __init__(
        self,
        config: CloudBuildVerifierConfig,
        *,
        gateway: CloudBuildGateway | None = None,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self.config = config
        self.gateway = gateway or GoogleCloudBuildGateway(config)
        self._clock = clock
        self._sleep = sleep

    async def verify(
        self, artifact: BoundedRemediationArtifact
    ) -> VerificationOutcome:
        try:
            build = build_trusted_cloud_build(self.config, artifact)
        except (VerifierArtifactError, UnicodeError) as exc:
            return self._outcome(
                VerificationDecision.REJECTED,
                VerificationFailureCode.INVALID_ARTIFACT,
                f"Candidate rejected before execution: {exc}",
            )

        try:
            submission = await asyncio.wait_for(
                self.gateway.submit(build),
                timeout=self.config.rpc_timeout_seconds,
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            return self._outcome(
                VerificationDecision.UNAVAILABLE,
                VerificationFailureCode.SUBMISSION_FAILED,
                "Cloud Build submission failed before a build receipt was returned.",
            )

        deadline = self._clock() + self.config.overall_timeout_seconds
        last_snapshot: BuildSnapshot | None = None
        try:
            while True:
                remaining = deadline - self._clock()
                if remaining <= 0:
                    return await self._cancelled_timeout(submission, artifact, last_snapshot)
                try:
                    last_snapshot = await asyncio.wait_for(
                        self.gateway.get(submission.build_name),
                        timeout=min(self.config.rpc_timeout_seconds, remaining),
                    )
                except asyncio.TimeoutError:
                    return await self._cancelled_timeout(submission, artifact, last_snapshot)
                except Exception:
                    evidence = self._evidence(artifact, last_snapshot, submission)
                    return self._outcome(
                        VerificationDecision.UNAVAILABLE,
                        VerificationFailureCode.POLL_FAILED,
                        "Cloud Build status could not be retrieved; publication remains blocked.",
                        evidence=evidence,
                    )
                if last_snapshot.status in TERMINAL_BUILD_STATUSES:
                    return self._interpret(artifact, submission, last_snapshot)
                await self._sleep(
                    min(self.config.poll_interval_seconds, max(0.0, remaining))
                )
        except asyncio.CancelledError:
            try:
                await asyncio.shield(
                    asyncio.wait_for(
                        self.gateway.cancel(submission.build_name),
                        timeout=self.config.rpc_timeout_seconds,
                    )
                )
            except Exception:
                pass
            raise

    async def _cancelled_timeout(
        self,
        submission: BuildSubmission,
        artifact: BoundedRemediationArtifact,
        snapshot: BuildSnapshot | None,
    ) -> VerificationOutcome:
        try:
            await asyncio.wait_for(
                self.gateway.cancel(submission.build_name),
                timeout=self.config.rpc_timeout_seconds,
            )
        except Exception:
            pass
        return self._outcome(
            VerificationDecision.UNAVAILABLE,
            VerificationFailureCode.DEADLINE_EXCEEDED,
            "Cloud Build verification exceeded its bounded deadline and was cancelled.",
            evidence=self._evidence(artifact, snapshot, submission),
        )

    def _interpret(
        self,
        artifact: BoundedRemediationArtifact,
        submission: BuildSubmission,
        snapshot: BuildSnapshot,
    ) -> VerificationOutcome:
        evidence = self._evidence(artifact, snapshot, submission)
        step_states = {item.id: item.status for item in snapshot.steps}
        baseline = self._baseline_result(step_states)
        candidate = self._pass_result(step_states, "candidate-hidden-control")
        regression = self._pass_result(step_states, "demo-saas-regression")

        if snapshot.status == "TIMEOUT":
            return self._outcome(
                VerificationDecision.UNAVAILABLE,
                VerificationFailureCode.DEADLINE_EXCEEDED,
                "Cloud Build timed out; candidate publication remains blocked.",
                baseline,
                candidate,
                regression,
                evidence=evidence,
            )
        if snapshot.status == "INTERNAL_ERROR":
            return self._outcome(
                VerificationDecision.UNAVAILABLE,
                VerificationFailureCode.BUILD_INTERNAL_ERROR,
                "Cloud Build reported an internal error.",
                baseline,
                candidate,
                regression,
                evidence=evidence,
            )
        if snapshot.status == "CANCELLED":
            return self._outcome(
                VerificationDecision.UNAVAILABLE,
                VerificationFailureCode.BUILD_CANCELLED,
                "Cloud Build was cancelled before verification completed.",
                baseline,
                candidate,
                regression,
                evidence=evidence,
            )
        if snapshot.status == "EXPIRED":
            return self._outcome(
                VerificationDecision.UNAVAILABLE,
                VerificationFailureCode.BUILD_EXPIRED,
                "Cloud Build expired in the queue before verification completed.",
                baseline,
                candidate,
                regression,
                evidence=evidence,
            )

        failed_step = next(
            (
                step_id
                for step_id in REQUIRED_STEP_IDS
                if step_states.get(step_id) in {"FAILURE", "TIMEOUT", "CANCELLED"}
            ),
            None,
        )
        if snapshot.status != "SUCCESS":
            decision, code, detail = self._failed_step_outcome(failed_step)
            return self._outcome(
                decision,
                code,
                detail,
                baseline,
                candidate,
                regression,
                evidence=evidence,
            )

        if set(step_states) != set(REQUIRED_STEP_IDS) or any(
            step_states.get(step_id) != "SUCCESS" for step_id in REQUIRED_STEP_IDS
        ):
            return self._outcome(
                VerificationDecision.UNAVAILABLE,
                VerificationFailureCode.EVIDENCE_INCOMPLETE,
                "Cloud Build succeeded without a complete trusted step receipt.",
                baseline,
                candidate,
                regression,
                evidence=evidence,
            )
        if (
            snapshot.resolved_source_url != self.config.repository_url
            or snapshot.resolved_revision != artifact.base_sha
        ):
            return self._outcome(
                VerificationDecision.REJECTED,
                VerificationFailureCode.SOURCE_MISMATCH,
                "Cloud Build source provenance did not match the requested repository and base SHA.",
                baseline,
                candidate,
                regression,
                evidence=evidence,
            )
        if not self._valid_log_url(snapshot.log_url):
            return self._outcome(
                VerificationDecision.UNAVAILABLE,
                VerificationFailureCode.EVIDENCE_INCOMPLETE,
                "Cloud Build returned no durable HTTPS log reference.",
                baseline,
                candidate,
                regression,
                exact_source_verified=True,
                evidence=evidence,
            )

        files = tuple(
            CandidateFileEvidence(
                path=item.path,
                preimage_sha256=item.preimage_sha256,
                candidate_sha256=item.candidate_sha256,
                content=item.content,
            )
            for item in artifact.candidate_files
        )
        verified_candidate = VerifiedCandidate(
            schema_version="ipromise.verified-candidate.v1",
            repository_url=self.config.repository_url,
            base_sha=artifact.base_sha,
            unified_diff_sha256=artifact.unified_diff_sha256,
            files=files,
            evidence=evidence,
        )
        return self._outcome(
            VerificationDecision.VERIFIED,
            VerificationFailureCode.NONE,
            (
                "Cloud Build proved the expected analytics-residual baseline, the exact "
                "candidate bytes, the green hidden control, and the full demo SaaS regression."
            ),
            CheckResult.EXPECTED_FAILURE,
            CheckResult.PASS,
            CheckResult.PASS,
            exact_source_verified=True,
            exact_candidate_verified=True,
            evidence=evidence,
            candidate=verified_candidate,
        )

    @staticmethod
    def _valid_log_url(log_url: str | None) -> bool:
        if not log_url:
            return False
        parsed = urlparse(log_url)
        return parsed.scheme == "https" and bool(parsed.hostname)

    @staticmethod
    def _baseline_result(step_states: Mapping[str, str]) -> CheckResult:
        state = step_states.get("baseline-hidden-control")
        if state == "SUCCESS":
            return CheckResult.EXPECTED_FAILURE
        if state in {"FAILURE", "TIMEOUT", "CANCELLED"}:
            return CheckResult.FAIL
        return CheckResult.NOT_RUN

    @staticmethod
    def _pass_result(step_states: Mapping[str, str], step_id: str) -> CheckResult:
        state = step_states.get(step_id)
        if state == "SUCCESS":
            return CheckResult.PASS
        if state in {"FAILURE", "TIMEOUT", "CANCELLED"}:
            return CheckResult.FAIL
        return CheckResult.NOT_RUN

    @staticmethod
    def _failed_step_outcome(
        step_id: str | None,
    ) -> tuple[VerificationDecision, VerificationFailureCode, str]:
        logical_failures = {
            "source-integrity": (
                VerificationFailureCode.SOURCE_MISMATCH,
                "The fetched source did not match the exact repository preimages or base SHA.",
            ),
            "baseline-hidden-control": (
                VerificationFailureCode.BASELINE_MISMATCH,
                "The hidden baseline control did not fail for the expected analytics-residual reason.",
            ),
            "materialize-candidate": (
                VerificationFailureCode.CANDIDATE_MISMATCH,
                "Candidate bytes, preimages, or canonical unified diff did not match.",
            ),
            "candidate-hidden-control": (
                VerificationFailureCode.CANDIDATE_CONTROL_FAILED,
                "The hidden deletion control did not pass against the candidate.",
            ),
            "demo-saas-regression": (
                VerificationFailureCode.REGRESSION_FAILED,
                "The full demo SaaS regression suite failed against the candidate.",
            ),
            "candidate-integrity": (
                VerificationFailureCode.CANDIDATE_MISMATCH,
                "The final candidate working tree did not match the verified byte hashes.",
            ),
        }
        if step_id in logical_failures:
            code, detail = logical_failures[step_id]
            return VerificationDecision.REJECTED, code, detail
        return (
            VerificationDecision.UNAVAILABLE,
            VerificationFailureCode.BUILD_FAILED,
            "Cloud Build failed outside the trusted control gates.",
        )

    def _evidence(
        self,
        artifact: BoundedRemediationArtifact,
        snapshot: BuildSnapshot | None,
        submission: BuildSubmission,
    ) -> CloudBuildEvidence:
        return CloudBuildEvidence(
            build_id=(snapshot.build_id if snapshot else submission.build_id),
            build_name=(snapshot.build_name if snapshot else submission.build_name),
            status=(snapshot.status if snapshot else "STATUS_UNKNOWN"),
            log_url=(snapshot.log_url if snapshot else None),
            requested_source_url=self.config.repository_url,
            resolved_source_url=(snapshot.resolved_source_url if snapshot else None),
            requested_base_sha=artifact.base_sha,
            resolved_base_sha=(snapshot.resolved_revision if snapshot else None),
            unified_diff_sha256=artifact.unified_diff_sha256,
            step_results=(snapshot.steps if snapshot else ()),
        )

    @staticmethod
    def _outcome(
        decision: VerificationDecision,
        failure_code: VerificationFailureCode,
        detail: str,
        baseline_control: CheckResult = CheckResult.NOT_RUN,
        candidate_control: CheckResult = CheckResult.NOT_RUN,
        regression_suite: CheckResult = CheckResult.NOT_RUN,
        *,
        exact_source_verified: bool = False,
        exact_candidate_verified: bool = False,
        evidence: CloudBuildEvidence | None = None,
        candidate: VerifiedCandidate | None = None,
    ) -> VerificationOutcome:
        return VerificationOutcome(
            decision=decision,
            failure_code=failure_code,
            detail=detail,
            baseline_control=baseline_control,
            candidate_control=candidate_control,
            regression_suite=regression_suite,
            exact_source_verified=exact_source_verified,
            exact_candidate_verified=exact_candidate_verified,
            evidence=evidence,
            candidate=candidate,
        )


def build_spec_contains_no_secrets(build: Mapping[str, Any]) -> bool:
    """Defensive assertion helper for deployment checks and tests."""

    forbidden_keys = {"secret_env", "available_secrets", "secrets", "kms_key_name"}

    def walk(value: Any) -> bool:
        if isinstance(value, Mapping):
            for key, child in value.items():
                if str(key).casefold() in forbidden_keys:
                    return False
                if not walk(child):
                    return False
        elif isinstance(value, (list, tuple)):
            return all(walk(child) for child in value)
        return True

    return walk(build)


def build_spec_fingerprint(build: Mapping[str, Any]) -> str:
    """Stable digest for audit logs without serialising candidate bytes again."""

    canonical = json.dumps(build, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
