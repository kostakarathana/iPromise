from __future__ import annotations

import base64
import hashlib
import os
import shutil
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from ipromise_agent.cloudbuild_verifier import (
    PUBLIC_REPOSITORY_URL,
    REQUIRED_STEP_IDS,
    _MATERIALIZE_CANDIDATE,
    _TRUSTED_CONTROL,
    BuildSnapshot,
    BuildStepSnapshot,
    BuildSubmission,
    CheckResult,
    CloudBuildVerifier,
    CloudBuildVerifierConfig,
    VerificationDecision,
    VerificationFailureCode,
    build_spec_contains_no_secrets,
    build_trusted_cloud_build,
)
from ipromise_agent.models import VerificationResult
from ipromise_agent.remediation import (
    ALLOWED_REMEDIATION_PATHS,
    BoundedRemediationArtifact,
    CandidateFile,
    build_bounded_remediation_artifact,
)
from remediation_fixtures import locked_remediation_preimages


BASE_SHA = "a" * 40
PROJECT_ID = "ipromise-test-2026"
SERVICE_ACCOUNT = (
    f"projects/{PROJECT_ID}/serviceAccounts/"
    f"ipromise-verifier@{PROJECT_ID}.iam.gserviceaccount.com"
)


def _artifact() -> BoundedRemediationArtifact:
    return build_bounded_remediation_artifact(
        base_reference=BASE_SHA,
        preimages=locked_remediation_preimages(),
    )


def _config(**overrides) -> CloudBuildVerifierConfig:
    values = {
        "project_id": PROJECT_ID,
        "service_account": SERVICE_ACCOUNT,
        "build_timeout_seconds": 60,
        "queue_ttl_seconds": 10,
        "overall_timeout_seconds": 60.0,
        "rpc_timeout_seconds": 1.0,
        "poll_interval_seconds": 0.05,
    }
    values.update(overrides)
    return CloudBuildVerifierConfig(**values)


def _steps(*, failure: str | None = None) -> tuple[BuildStepSnapshot, ...]:
    steps = []
    failed = False
    for step_id in REQUIRED_STEP_IDS:
        if step_id == failure:
            steps.append(BuildStepSnapshot(id=step_id, status="FAILURE"))
            failed = True
        elif failed:
            steps.append(BuildStepSnapshot(id=step_id, status="STATUS_UNKNOWN"))
        else:
            steps.append(BuildStepSnapshot(id=step_id, status="SUCCESS"))
    return tuple(steps)


def _snapshot(
    *,
    status: str = "SUCCESS",
    failure: str | None = None,
    source_url: str | None = PUBLIC_REPOSITORY_URL,
    revision: str | None = BASE_SHA,
    log_url: str | None = "https://console.cloud.google.com/cloud-build/builds/build-1",
) -> BuildSnapshot:
    return BuildSnapshot(
        build_id="build-1",
        build_name=f"projects/{PROJECT_ID}/locations/australia-southeast1/builds/build-1",
        status=status,
        log_url=log_url,
        resolved_source_url=source_url,
        resolved_revision=revision,
        steps=_steps(failure=failure),
    )


class FakeGateway:
    def __init__(self, snapshots: list[BuildSnapshot]) -> None:
        self.snapshots = snapshots
        self.submitted: list[dict] = []
        self.cancelled: list[str] = []

    async def submit(self, build) -> BuildSubmission:
        self.submitted.append(dict(build))
        return BuildSubmission(
            build_id="build-1",
            build_name=(
                f"projects/{PROJECT_ID}/locations/"
                "australia-southeast1/builds/build-1"
            ),
        )

    async def get(self, build_name: str) -> BuildSnapshot:
        assert build_name.endswith("/build-1")
        if len(self.snapshots) > 1:
            return self.snapshots.pop(0)
        return self.snapshots[0]

    async def cancel(self, build_name: str) -> None:
        self.cancelled.append(build_name)


class ManualClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    async def sleep(self, duration: float) -> None:
        self.now += duration


def test_trusted_build_is_pinned_bounded_and_contains_no_secrets() -> None:
    artifact = _artifact()
    build = build_trusted_cloud_build(_config(), artifact)

    assert build["source"] == {
        "git_source": {
            "url": PUBLIC_REPOSITORY_URL,
            "revision": BASE_SHA,
        }
    }
    assert build["service_account"] == SERVICE_ACCOUNT
    assert build["timeout"] == "60s"
    assert build["queue_ttl"] == "10s"
    assert build["options"] == {
        "logging": "CLOUD_LOGGING_ONLY",
        "source_provenance_hash": ["SHA256"],
    }
    assert tuple(step["id"] for step in build["steps"]) == REQUIRED_STEP_IDS
    assert all("@sha256:" in step["name"] for step in build["steps"])
    assert all(int(step["timeout"].removesuffix("s")) <= 240 for step in build["steps"])
    assert build_spec_contains_no_secrets(build) is True
    assert "available_secrets" not in str(build).casefold()
    assert "secret_env" not in str(build).casefold()

    materialize = next(
        step for step in build["steps"] if step["id"] == "materialize-candidate"
    )
    args = materialize["args"]
    assert base64.b64decode(args[2], validate=True) == artifact.unified_diff.encode()
    for item in artifact.candidate_files:
        encoded_index = args.index(item.candidate_sha256) + 1
        assert base64.b64decode(args[encoded_index], validate=True) == item.content


def test_trusted_build_is_accepted_by_official_cloud_build_message() -> None:
    cloudbuild_v1 = pytest.importorskip("google.cloud.devtools.cloudbuild_v1")

    message = cloudbuild_v1.Build(build_trusted_cloud_build(_config(), _artifact()))

    assert message.source.git_source.url == PUBLIC_REPOSITORY_URL
    assert message.source.git_source.revision == BASE_SHA
    assert [step.id for step in message.steps] == list(REQUIRED_STEP_IDS)
    assert message.service_account == SERVICE_ACCOUNT


async def test_success_returns_exact_candidate_and_publishable_receipt() -> None:
    artifact = _artifact()
    working = replace(_snapshot(), status="WORKING", log_url=None, steps=())
    gateway = FakeGateway([working, _snapshot()])
    clock = ManualClock()
    verifier = CloudBuildVerifier(
        _config(), gateway=gateway, clock=clock, sleep=clock.sleep
    )

    outcome = await verifier.verify(artifact)

    assert outcome.decision == VerificationDecision.VERIFIED
    assert outcome.failure_code == VerificationFailureCode.NONE
    assert outcome.publishable is True
    assert outcome.baseline_control == CheckResult.EXPECTED_FAILURE
    assert outcome.candidate_control == CheckResult.PASS
    assert outcome.regression_suite == CheckResult.PASS
    assert outcome.exact_source_verified is True
    assert outcome.exact_candidate_verified is True
    assert outcome.evidence is not None
    assert outcome.evidence.build_id == "build-1"
    assert outcome.evidence.log_url is not None
    assert outcome.evidence.resolved_base_sha == BASE_SHA
    assert outcome.candidate is not None
    assert outcome.candidate.base_sha == artifact.base_sha
    assert outcome.candidate.unified_diff_sha256 == artifact.unified_diff_sha256
    assert outcome.candidate.candidate_tree == artifact.candidate_tree
    assert outcome.candidate.preimage_hashes == artifact.preimage_hashes
    assert outcome.candidate.candidate_hashes == artifact.candidate_hashes
    receipt = outcome.to_verification_receipt()
    assert receipt.baseline_control == VerificationResult.FAIL
    assert receipt.candidate_control == VerificationResult.PASS
    assert receipt.regression_suite == VerificationResult.PASS
    assert receipt.exact_tree_verified is True
    assert receipt.isolated is True
    assert receipt.publishable is True
    assert receipt.build_id == "build-1"
    assert receipt.log_url == (
        "https://console.cloud.google.com/cloud-build/builds/build-1"
    )
    assert receipt.model_dump(by_alias=True)["buildId"] == "build-1"
    assert receipt.model_dump(by_alias=True)["logUrl"] == receipt.log_url
    assert receipt.artifact_binding is not None
    assert receipt.artifact_binding.repository_url == PUBLIC_REPOSITORY_URL
    assert receipt.artifact_binding.base_sha == artifact.base_sha
    assert receipt.artifact_binding.unified_diff_sha256 == (
        artifact.unified_diff_sha256
    )
    assert receipt.artifact_binding.preimage_hashes == artifact.preimage_hashes
    assert receipt.artifact_binding.candidate_hashes == artifact.candidate_hashes


async def test_tampered_candidate_fails_before_cloud_submission() -> None:
    artifact = _artifact()
    first, second = artifact.candidate_files
    tampered = CandidateFile(
        path=first.path,
        preimage_sha256=first.preimage_sha256,
        candidate_sha256=first.candidate_sha256,
        content=first.content + b"# tampered\n",
    )
    invalid = BoundedRemediationArtifact(
        schema_version=artifact.schema_version,
        base_reference=artifact.base_reference,
        candidate_files=(tampered, second),
        unified_diff=artifact.unified_diff,
        unified_diff_sha256=artifact.unified_diff_sha256,
    )
    gateway = FakeGateway([_snapshot()])
    verifier = CloudBuildVerifier(_config(), gateway=gateway)

    outcome = await verifier.verify(invalid)

    assert outcome.decision == VerificationDecision.REJECTED
    assert outcome.failure_code == VerificationFailureCode.INVALID_ARTIFACT
    assert outcome.publishable is False
    assert gateway.submitted == []


async def test_coherently_rehashed_alternate_template_is_rejected_preflight() -> None:
    artifact = _artifact()
    first, second = artifact.candidate_files
    alternate_content = first.content + b"# internally coherent but unapproved\n"
    alternate = CandidateFile(
        path=first.path,
        preimage_sha256=first.preimage_sha256,
        candidate_sha256=hashlib.sha256(alternate_content).hexdigest(),
        content=alternate_content,
    )
    alternate_diff = artifact.unified_diff + "+# internally coherent but unapproved\n"
    invalid = BoundedRemediationArtifact(
        schema_version=artifact.schema_version,
        base_reference=artifact.base_reference,
        candidate_files=(alternate, second),
        unified_diff=alternate_diff,
        unified_diff_sha256=hashlib.sha256(alternate_diff.encode()).hexdigest(),
    )
    gateway = FakeGateway([_snapshot()])
    verifier = CloudBuildVerifier(_config(), gateway=gateway)

    outcome = await verifier.verify(invalid)

    assert outcome.decision == VerificationDecision.REJECTED
    assert outcome.failure_code == VerificationFailureCode.INVALID_ARTIFACT
    assert "approved remediation template" in outcome.detail
    assert gateway.submitted == []


@pytest.mark.parametrize(
    ("failed_step", "expected_code"),
    [
        ("source-integrity", VerificationFailureCode.SOURCE_MISMATCH),
        ("baseline-hidden-control", VerificationFailureCode.BASELINE_MISMATCH),
        ("materialize-candidate", VerificationFailureCode.CANDIDATE_MISMATCH),
        (
            "candidate-hidden-control",
            VerificationFailureCode.CANDIDATE_CONTROL_FAILED,
        ),
        ("demo-saas-regression", VerificationFailureCode.REGRESSION_FAILED),
        ("candidate-integrity", VerificationFailureCode.CANDIDATE_MISMATCH),
    ],
)
async def test_control_and_integrity_failures_are_typed_rejections(
    failed_step: str, expected_code: VerificationFailureCode
) -> None:
    gateway = FakeGateway(
        [_snapshot(status="FAILURE", failure=failed_step)]
    )
    verifier = CloudBuildVerifier(_config(), gateway=gateway)

    outcome = await verifier.verify(_artifact())

    assert outcome.decision == VerificationDecision.REJECTED
    assert outcome.failure_code == expected_code
    assert outcome.publishable is False
    assert outcome.evidence is not None
    assert outcome.evidence.build_id == "build-1"


async def test_success_with_wrong_source_provenance_fails_closed() -> None:
    gateway = FakeGateway(
        [_snapshot(revision="b" * 40)]
    )
    verifier = CloudBuildVerifier(_config(), gateway=gateway)

    outcome = await verifier.verify(_artifact())

    assert outcome.decision == VerificationDecision.REJECTED
    assert outcome.failure_code == VerificationFailureCode.SOURCE_MISMATCH
    assert outcome.exact_source_verified is False
    assert outcome.publishable is False


async def test_success_without_https_log_receipt_is_unavailable() -> None:
    gateway = FakeGateway([_snapshot(log_url=None)])
    verifier = CloudBuildVerifier(_config(), gateway=gateway)

    outcome = await verifier.verify(_artifact())

    assert outcome.decision == VerificationDecision.UNAVAILABLE
    assert outcome.failure_code == VerificationFailureCode.EVIDENCE_INCOMPLETE
    assert outcome.exact_source_verified is True
    assert outcome.exact_candidate_verified is False
    assert outcome.publishable is False


async def test_bounded_polling_cancels_build_at_deadline() -> None:
    working = replace(_snapshot(), status="WORKING", log_url=None, steps=())
    gateway = FakeGateway([working])
    clock = ManualClock()
    verifier = CloudBuildVerifier(
        _config(), gateway=gateway, clock=clock, sleep=clock.sleep
    )

    outcome = await verifier.verify(_artifact())

    assert outcome.decision == VerificationDecision.UNAVAILABLE
    assert outcome.failure_code == VerificationFailureCode.DEADLINE_EXCEEDED
    assert outcome.publishable is False
    assert gateway.cancelled == [
        f"projects/{PROJECT_ID}/locations/australia-southeast1/builds/build-1"
    ]


def test_candidate_evidence_hashes_are_fresh_and_immutable() -> None:
    artifact = _artifact()
    for item in artifact.candidate_files:
        assert hashlib.sha256(item.content).hexdigest() == item.candidate_sha256


def test_trusted_control_is_red_before_green_after_and_regression_passes(
    tmp_path: Path,
) -> None:
    artifact = _artifact()
    repository_root = Path(__file__).resolve().parents[3]
    copy_root = tmp_path / "checkout"
    shutil.copytree(
        repository_root / "apps" / "demo_saas",
        copy_root / "apps" / "demo_saas",
        ignore=shutil.ignore_patterns(".venv", "__pycache__", ".pytest_cache"),
    )
    # Cloud Build verifies the captured vulnerable base SHA even when this test
    # itself runs from the generated repair branch.  Recreate that exact base
    # from independent hash-locked fixtures before exercising red -> green.
    for path, content in locked_remediation_preimages().items():
        (copy_root / path).write_bytes(content)
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(copy_root / "apps" / "demo_saas" / "src")
    environment["IPROMISE_VERIFIER_WORKSPACE"] = str(copy_root)

    baseline = subprocess.run(
        [sys.executable, "-c", _TRUSTED_CONTROL, "baseline"],
        cwd=copy_root,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert baseline.returncode == 0
    assert (
        "IPROMISE_CONTROL_RESULT result=FAIL reason=analytics_residual_after_25h"
        in baseline.stdout
    )

    materialize_args = [
        sys.executable,
        "-c",
        _MATERIALIZE_CANDIDATE,
        base64.b64encode(artifact.unified_diff.encode()).decode(),
        artifact.unified_diff_sha256,
    ]
    for item in artifact.candidate_files:
        materialize_args.extend(
            (
                item.path,
                item.preimage_sha256,
                item.candidate_sha256,
                base64.b64encode(item.content).decode(),
            )
        )
    materialized = subprocess.run(
        materialize_args,
        cwd=copy_root,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert materialized.returncode == 0, materialized.stderr
    assert "IPROMISE_CANDIDATE_RESULT result=MATERIALIZED" in materialized.stdout

    candidate = subprocess.run(
        [sys.executable, "-c", _TRUSTED_CONTROL, "candidate"],
        cwd=copy_root,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert candidate.returncode == 0
    assert (
        "IPROMISE_CONTROL_RESULT result=PASS reason=both_owned_stores_removed"
        in candidate.stdout
    )

    regression = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            str(copy_root / "apps" / "demo_saas" / "tests"),
            "-q",
        ],
        cwd=copy_root,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert regression.returncode == 0, regression.stdout + regression.stderr
    assert regression.stdout.count(".") >= 5
