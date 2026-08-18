"""Deterministic, byte-exact remediation for the synthetic deletion control.

This module intentionally has no command runner and accepts no model-authored
commands.  It turns one locked pair of repository preimages into one bounded
candidate tree that a separate verifier can execute and a GitHub publisher can
upload byte-for-byte.
"""

from __future__ import annotations

import difflib
import hashlib
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from .models import (
    AuditRun,
    FileEdit,
    RemediationProposal,
    VerificationReceipt,
    VerificationResult,
)


ALLOWED_REMEDIATION_PATH = "apps/demo_saas/src/ipromise_demo/store.py"
ALLOWED_REMEDIATION_PATHS = tuple(
    sorted(
        (
            ALLOWED_REMEDIATION_PATH,
            "apps/demo_saas/tests/test_app.py",
        )
    )
)

# This approved template is deliberately tied to the exact vulnerable snapshot.
# Any source or test change, including a benign-looking one, requires review and a
# new template rather than silently carrying an old verification result forward.
EXPECTED_PREIMAGE_SHA256 = {
    ALLOWED_REMEDIATION_PATH: (
        "51c5fd65084d6cc8a69c1d21e12a6d7d560343b0e12575caa6f9fc3ebd712171"
    ),
    "apps/demo_saas/tests/test_app.py": (
        "9b1d2adf2621edc335dcf619ec67b90774673e8722edf08c341b454f2208d93d"
    ),
}
EXPECTED_CANDIDATE_SHA256 = {
    ALLOWED_REMEDIATION_PATH: (
        "97a2fa9c336088fab7add92e960c0634f74466d43ba1ebacb9077187f1ab2deb"
    ),
    "apps/demo_saas/tests/test_app.py": (
        "a0abfa9b1eee37069e6265881d8231a7908146d1e2ff32c59046d045c2b57e24"
    ),
}
EXPECTED_UNIFIED_DIFF_SHA256 = (
    "9891f6e42df7b14adfff9ccd7da2d788015ee2368747cc4ae36d3c4db029648a"
)

MAX_PREIMAGE_FILE_BYTES = 32 * 1024
MAX_TOTAL_PREIMAGE_BYTES = 64 * 1024
MAX_CANDIDATE_GROWTH_BYTES = 1024
MAX_UNIFIED_DIFF_BYTES = 8 * 1024
MAX_CHANGED_DIFF_LINES = 16

_FULL_GIT_SHA = re.compile(r"[0-9a-f]{40}\Z")
_STORE_DOCSTRING_BEFORE = (
    b'"""Thread-safe, ephemeral stores with one intentional deletion defect."""'
)
_STORE_DOCSTRING_AFTER = (
    b'"""Thread-safe, ephemeral stores for the synthetic deletion control."""'
)
_STORE_DEFECT_BEFORE = b"""            # INTENTIONAL DEMO DEFECT:
            # `self._analytics_profiles.pop(account_id, None)` is omitted so that
            # iPromise can detect a real contradiction and propose a bounded fix.
"""
_STORE_DEFECT_AFTER = b"""            # Complete deletion across both owned synthetic stores.
            self._analytics_profiles.pop(account_id, None)
"""
_TEST_NAME_BEFORE = (
    b"async def test_overdue_deletion_intentionally_leaves_analytics_record() -> None:"
)
_TEST_NAME_AFTER = (
    b"async def test_overdue_deletion_removes_application_and_analytics_records() -> None:"
)
_TEST_ASSERTION_BEFORE = b'    assert after["analytics_profile_exists"] is True\n'
_TEST_ASSERTION_AFTER = b'    assert after["analytics_profile_exists"] is False\n'


class BoundedRemediationError(ValueError):
    """The requested candidate could not be proven to match the approved template."""


@dataclass(frozen=True, slots=True)
class CandidateFile:
    """One exact candidate blob and its binding to the fetched preimage."""

    path: str
    preimage_sha256: str
    candidate_sha256: str
    content: bytes


@dataclass(frozen=True, slots=True)
class BoundedRemediationArtifact:
    """Canonical inputs and outputs for verification and exact-tree publication."""

    schema_version: str
    base_reference: str
    candidate_files: tuple[CandidateFile, ...]
    unified_diff: str
    unified_diff_sha256: str

    @property
    def base_sha(self) -> str:
        """Expose the validated base commit with unambiguous publisher naming."""

        return self.base_reference

    @property
    def preimage_hashes(self) -> dict[str, str]:
        """Return a fresh path-to-hash map safe for receipt serialization."""

        return {item.path: item.preimage_sha256 for item in self.candidate_files}

    @property
    def candidate_hashes(self) -> dict[str, str]:
        """Return the exact blob hashes expected from the verifier and publisher."""

        return {item.path: item.candidate_sha256 for item in self.candidate_files}

    @property
    def candidate_tree(self) -> dict[str, bytes]:
        """Return fresh mapping containers around the immutable candidate bytes."""

        return {item.path: item.content for item in self.candidate_files}


PreimageFetcher = Callable[[str, str], bytes]


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _replace_exactly_once(
    content: bytes,
    before: bytes,
    after: bytes,
    *,
    path: str,
    edit_name: str,
) -> bytes:
    occurrences = content.count(before)
    if occurrences != 1:
        raise BoundedRemediationError(
            f"Ambiguous {edit_name} in {path}: expected exactly one anchor, "
            f"found {occurrences}"
        )
    return content.replace(before, after, 1)


def _load_preimages(
    *,
    base_reference: str,
    preimages: Mapping[str, bytes] | None,
    fetch_preimage: PreimageFetcher | None,
) -> dict[str, bytes]:
    if (preimages is None) == (fetch_preimage is None):
        raise BoundedRemediationError(
            "Provide exactly one preimage source: preimages or fetch_preimage"
        )

    allowed = set(ALLOWED_REMEDIATION_PATHS)
    if preimages is not None:
        supplied = set(preimages)
        if supplied != allowed:
            unexpected = sorted(supplied - allowed)
            missing = sorted(allowed - supplied)
            raise BoundedRemediationError(
                f"Preimage paths must equal the approved path set; "
                f"unexpected={unexpected}, missing={missing}"
            )
        loaded = {path: preimages[path] for path in ALLOWED_REMEDIATION_PATHS}
    else:
        assert fetch_preimage is not None
        loaded = {}
        for path in ALLOWED_REMEDIATION_PATHS:
            try:
                loaded[path] = fetch_preimage(base_reference, path)
            except Exception as exc:  # isolate provider failures behind a safe error
                raise BoundedRemediationError(
                    f"Could not fetch approved preimage {path}"
                ) from exc

    total_size = 0
    for path, content in loaded.items():
        if not isinstance(content, bytes):
            raise BoundedRemediationError(f"Preimage {path} must be raw bytes")
        if len(content) > MAX_PREIMAGE_FILE_BYTES:
            raise BoundedRemediationError(
                f"Preimage {path} exceeds {MAX_PREIMAGE_FILE_BYTES} bytes"
            )
        total_size += len(content)
    if total_size > MAX_TOTAL_PREIMAGE_BYTES:
        raise BoundedRemediationError(
            f"Preimages exceed {MAX_TOTAL_PREIMAGE_BYTES} total bytes"
        )
    return loaded


def _apply_approved_edits(preimages: Mapping[str, bytes]) -> dict[str, bytes]:
    store_path, test_path = ALLOWED_REMEDIATION_PATHS
    store = _replace_exactly_once(
        preimages[store_path],
        _STORE_DOCSTRING_BEFORE,
        _STORE_DOCSTRING_AFTER,
        path=store_path,
        edit_name="store module description",
    )
    store = _replace_exactly_once(
        store,
        _STORE_DEFECT_BEFORE,
        _STORE_DEFECT_AFTER,
        path=store_path,
        edit_name="analytics deletion defect",
    )

    test = _replace_exactly_once(
        preimages[test_path],
        _TEST_NAME_BEFORE,
        _TEST_NAME_AFTER,
        path=test_path,
        edit_name="deletion regression test name",
    )
    test = _replace_exactly_once(
        test,
        _TEST_ASSERTION_BEFORE,
        _TEST_ASSERTION_AFTER,
        path=test_path,
        edit_name="analytics deletion regression assertion",
    )
    return {store_path: store, test_path: test}


def _canonical_unified_diff(
    preimages: Mapping[str, bytes], candidates: Mapping[str, bytes]
) -> str:
    chunks: list[str] = []
    for path in ALLOWED_REMEDIATION_PATHS:
        try:
            before = preimages[path].decode("utf-8")
            after = candidates[path].decode("utf-8")
        except UnicodeDecodeError as exc:
            raise BoundedRemediationError(
                f"Approved remediation file {path} must be UTF-8"
            ) from exc
        chunks.extend(
            difflib.unified_diff(
                before.splitlines(keepends=True),
                after.splitlines(keepends=True),
                fromfile=f"a/{path}",
                tofile=f"b/{path}",
                lineterm="\n",
            )
        )
    return "".join(chunks)


def build_bounded_remediation_artifact(
    *,
    base_reference: str,
    preimages: Mapping[str, bytes] | None = None,
    fetch_preimage: PreimageFetcher | None = None,
) -> BoundedRemediationArtifact:
    """Build the sole approved repair from exact repository preimages.

    ``fetch_preimage`` receives the immutable base SHA and only the two constant
    allowlisted paths.  The returned artifact contains no commands: a verifier
    writes ``candidate_tree`` into its isolated checkout, and a publisher uploads
    those same bytes against ``base_reference`` after rechecking all hashes.
    """

    if _FULL_GIT_SHA.fullmatch(base_reference) is None:
        raise BoundedRemediationError(
            "base_reference must be the full lowercase 40-character Git commit SHA"
        )

    loaded = _load_preimages(
        base_reference=base_reference,
        preimages=preimages,
        fetch_preimage=fetch_preimage,
    )
    for path in ALLOWED_REMEDIATION_PATHS:
        observed_hash = _sha256(loaded[path])
        expected_hash = EXPECTED_PREIMAGE_SHA256[path]
        if observed_hash != expected_hash:
            raise BoundedRemediationError(
                f"Preimage drift for {path}: expected {expected_hash}, "
                f"observed {observed_hash}"
            )

    candidates = _apply_approved_edits(loaded)
    for path in ALLOWED_REMEDIATION_PATHS:
        growth = len(candidates[path]) - len(loaded[path])
        if len(candidates[path]) > MAX_PREIMAGE_FILE_BYTES:
            raise BoundedRemediationError(
                f"Candidate {path} exceeds {MAX_PREIMAGE_FILE_BYTES} bytes"
            )
        if abs(growth) > MAX_CANDIDATE_GROWTH_BYTES:
            raise BoundedRemediationError(
                f"Candidate {path} changes file size by more than "
                f"{MAX_CANDIDATE_GROWTH_BYTES} bytes"
            )

    unified_diff = _canonical_unified_diff(loaded, candidates)
    diff_bytes = unified_diff.encode("utf-8")
    changed_lines = sum(
        line.startswith(("+", "-"))
        and not line.startswith(("+++", "---"))
        for line in unified_diff.splitlines()
    )
    if len(diff_bytes) > MAX_UNIFIED_DIFF_BYTES:
        raise BoundedRemediationError(
            f"Candidate diff exceeds {MAX_UNIFIED_DIFF_BYTES} bytes"
        )
    if changed_lines > MAX_CHANGED_DIFF_LINES:
        raise BoundedRemediationError(
            f"Candidate diff exceeds {MAX_CHANGED_DIFF_LINES} changed lines"
        )

    observed_candidate_hashes = {
        path: _sha256(candidates[path]) for path in ALLOWED_REMEDIATION_PATHS
    }
    if observed_candidate_hashes != EXPECTED_CANDIDATE_SHA256:
        raise BoundedRemediationError(
            "Approved remediation template did not produce the locked candidate bytes"
        )
    observed_diff_hash = _sha256(diff_bytes)
    if observed_diff_hash != EXPECTED_UNIFIED_DIFF_SHA256:
        raise BoundedRemediationError(
            "Approved remediation template did not produce the locked canonical diff"
        )

    files = tuple(
        CandidateFile(
            path=path,
            preimage_sha256=_sha256(loaded[path]),
            candidate_sha256=_sha256(candidates[path]),
            content=candidates[path],
        )
        for path in ALLOWED_REMEDIATION_PATHS
    )
    return BoundedRemediationArtifact(
        schema_version="ipromise.bounded-remediation.v1",
        base_reference=base_reference,
        candidate_files=files,
        unified_diff=unified_diff,
        unified_diff_sha256=observed_diff_hash,
    )


def propose_bounded_remediation(
    run: AuditRun,
    *,
    base_reference: str = "not-captured-in-first-mvp",
) -> RemediationProposal:
    """Return data, never commands; this approved template cannot widen its path."""

    return RemediationProposal(
        summary="Remove the matching analytics profile while processing account deletion.",
        base_reference=base_reference,
        edits=[
            FileEdit(
                path=ALLOWED_REMEDIATION_PATH,
                operation="insert_bounded_statement",
                rationale=(
                    "The virtual worker removed the app profile at T0+1h, but the "
                    "synthetic analytics profile remained active at T0+25h."
                ),
                content_preview="self._analytics_profiles.pop(account_id, None)",
            ),
            FileEdit(
                path="apps/demo_saas/tests/test_app.py",
                operation="replace_bounded_assertion",
                rationale=(
                    "Lock the repaired deletion behavior with an exact regression test."
                ),
                content_preview='assert after["analytics_profile_exists"] is False',
            ),
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
            "was executed by the Cloud Build verifier, so publication remains blocked."
        ),
    )


def unavailable_verification_receipt(detail: str) -> VerificationReceipt:
    """Represent verifier/source unavailability without authorizing publication."""

    return VerificationReceipt(
        verifier="Bounded Cloud Build verification gate",
        baseline_control=VerificationResult.FAIL,
        candidate_control=VerificationResult.NOT_RUN,
        regression_suite=VerificationResult.NOT_RUN,
        exact_tree_verified=False,
        isolated=False,
        publishable=False,
        detail=detail,
    )
