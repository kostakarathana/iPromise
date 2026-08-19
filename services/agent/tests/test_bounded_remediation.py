from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

import ipromise_agent.remediation as remediation
from ipromise_agent.remediation import (
    ALLOWED_REMEDIATION_PATHS,
    EXPECTED_CANDIDATE_SHA256 as LOCKED_CANDIDATE_SHA256,
    EXPECTED_PREIMAGE_SHA256,
    MAX_PREIMAGE_FILE_BYTES,
    BoundedRemediationError,
    _replace_exactly_once,
    build_bounded_remediation_artifact,
)
from remediation_fixtures import locked_remediation_preimages


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
BASE_SHA = "a" * 40
EXPECTED_CANDIDATE_SHA256 = {
    "apps/demo_saas/src/ipromise_demo/store.py": (
        "97a2fa9c336088fab7add92e960c0634f74466d43ba1ebacb9077187f1ab2deb"
    ),
    "apps/demo_saas/tests/test_app.py": (
        "a0abfa9b1eee37069e6265881d8231a7908146d1e2ff32c59046d045c2b57e24"
    ),
}
EXPECTED_DIFF_SHA256 = (
    "9891f6e42df7b14adfff9ccd7da2d788015ee2368747cc4ae36d3c4db029648a"
)


def test_builds_byte_exact_two_file_candidate_and_canonical_diff() -> None:
    preimages = locked_remediation_preimages()

    artifact = build_bounded_remediation_artifact(
        base_reference=BASE_SHA,
        preimages=preimages,
    )

    assert artifact.schema_version == "ipromise.bounded-remediation.v1"
    assert artifact.base_reference == BASE_SHA
    assert artifact.base_sha == BASE_SHA
    assert tuple(item.path for item in artifact.candidate_files) == (
        ALLOWED_REMEDIATION_PATHS
    )
    assert artifact.preimage_hashes == EXPECTED_PREIMAGE_SHA256
    assert artifact.candidate_hashes == EXPECTED_CANDIDATE_SHA256
    assert artifact.unified_diff_sha256 == EXPECTED_DIFF_SHA256
    assert hashlib.sha256(artifact.unified_diff.encode("utf-8")).hexdigest() == (
        artifact.unified_diff_sha256
    )

    store_path, test_path = ALLOWED_REMEDIATION_PATHS
    candidate_tree = artifact.candidate_tree
    assert set(candidate_tree) == set(ALLOWED_REMEDIATION_PATHS)
    assert b"INTENTIONAL DEMO DEFECT" not in candidate_tree[store_path]
    assert (
        candidate_tree[store_path].count(
            b"self._analytics_profiles.pop(account_id, None)"
        )
        == 1
    )
    assert b"intentionally_leaves_analytics_record" not in candidate_tree[test_path]
    assert b'assert after["analytics_profile_exists"] is False' in (
        candidate_tree[test_path]
    )

    assert artifact.unified_diff.startswith(
        "--- a/apps/demo_saas/src/ipromise_demo/store.py\n"
        "+++ b/apps/demo_saas/src/ipromise_demo/store.py\n"
    )
    assert (
        "--- a/apps/demo_saas/tests/test_app.py\n"
        "+++ b/apps/demo_saas/tests/test_app.py\n"
    ) in artifact.unified_diff
    assert "\t" not in artifact.unified_diff.splitlines()[0]


def test_fetcher_receives_only_approved_paths_and_produces_same_artifact() -> None:
    preimages = locked_remediation_preimages()
    fetched: list[tuple[str, str]] = []

    def fetch(base_reference: str, path: str) -> bytes:
        fetched.append((base_reference, path))
        return preimages[path]

    fetched_artifact = build_bounded_remediation_artifact(
        base_reference=BASE_SHA,
        fetch_preimage=fetch,
    )
    mapped_artifact = build_bounded_remediation_artifact(
        base_reference=BASE_SHA,
        preimages=preimages,
    )

    assert fetched == [
        (BASE_SHA, path) for path in ALLOWED_REMEDIATION_PATHS
    ]
    assert fetched_artifact == mapped_artifact


@pytest.mark.parametrize(
    "base_reference",
    ["main", "A" * 40, "a" * 39, "a" * 41, "../../heads/main"],
)
def test_rejects_non_exact_base_references(base_reference: str) -> None:
    with pytest.raises(BoundedRemediationError, match="full lowercase"):
        build_bounded_remediation_artifact(
            base_reference=base_reference,
            preimages=locked_remediation_preimages(),
        )


def test_rejects_missing_extra_and_dual_preimage_sources() -> None:
    preimages = locked_remediation_preimages()
    missing = dict(preimages)
    missing.pop(ALLOWED_REMEDIATION_PATHS[1])
    extra = {**preimages, ".github/workflows/verify.yml": b"unsafe"}

    with pytest.raises(BoundedRemediationError, match="approved path set"):
        build_bounded_remediation_artifact(
            base_reference=BASE_SHA,
            preimages=missing,
        )
    with pytest.raises(BoundedRemediationError, match="approved path set"):
        build_bounded_remediation_artifact(
            base_reference=BASE_SHA,
            preimages=extra,
        )
    with pytest.raises(BoundedRemediationError, match="exactly one preimage source"):
        build_bounded_remediation_artifact(base_reference=BASE_SHA)
    with pytest.raises(BoundedRemediationError, match="exactly one preimage source"):
        build_bounded_remediation_artifact(
            base_reference=BASE_SHA,
            preimages=preimages,
            fetch_preimage=lambda base_reference, path: preimages[path],
        )


def test_rejects_preimage_drift_before_generating_candidate_bytes() -> None:
    preimages = locked_remediation_preimages()
    path = ALLOWED_REMEDIATION_PATHS[0]
    preimages[path] = preimages[path].replace(
        b"Complete deletion",
        b"Unrelated text",
    )
    # The current source does not contain that phrase, so force a one-byte drift.
    preimages[path] += b" "

    with pytest.raises(BoundedRemediationError, match=f"Preimage drift for {path}"):
        build_bounded_remediation_artifact(
            base_reference=BASE_SHA,
            preimages=preimages,
        )


def test_rejects_non_bytes_and_oversized_preimages_before_hashing() -> None:
    preimages = locked_remediation_preimages()
    path = ALLOWED_REMEDIATION_PATHS[0]
    preimages[path] = "not bytes"  # type: ignore[assignment]

    with pytest.raises(BoundedRemediationError, match="must be raw bytes"):
        build_bounded_remediation_artifact(
            base_reference=BASE_SHA,
            preimages=preimages,
        )

    preimages[path] = b"x" * (MAX_PREIMAGE_FILE_BYTES + 1)
    with pytest.raises(BoundedRemediationError, match="exceeds"):
        build_bounded_remediation_artifact(
            base_reference=BASE_SHA,
            preimages=preimages,
        )


def test_rejects_oversized_candidate_and_diff(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    preimages = locked_remediation_preimages()

    monkeypatch.setattr(
        remediation,
        "_STORE_DEFECT_AFTER",
        b"x" * (MAX_PREIMAGE_FILE_BYTES + 1),
    )
    with pytest.raises(BoundedRemediationError, match="Candidate .* exceeds"):
        build_bounded_remediation_artifact(
            base_reference=BASE_SHA,
            preimages=preimages,
        )

    monkeypatch.setattr(
        remediation,
        "_STORE_DEFECT_AFTER",
        b"            # " + b"x" * 9_000 + b"\n",
    )
    monkeypatch.setattr(remediation, "MAX_CANDIDATE_GROWTH_BYTES", 16 * 1024)
    with pytest.raises(BoundedRemediationError, match="Candidate diff exceeds"):
        build_bounded_remediation_artifact(
            base_reference=BASE_SHA,
            preimages=preimages,
        )


@pytest.mark.parametrize("content", [b"no marker", b"anchor anchor"])
def test_approved_edit_helper_rejects_missing_or_ambiguous_anchor(
    content: bytes,
) -> None:
    with pytest.raises(BoundedRemediationError, match="expected exactly one anchor"):
        _replace_exactly_once(
            content,
            b"anchor",
            b"replacement",
            path=ALLOWED_REMEDIATION_PATHS[0],
            edit_name="test edit",
        )


def test_candidate_tree_mapping_cannot_mutate_the_artifact() -> None:
    artifact = build_bounded_remediation_artifact(
        base_reference=BASE_SHA,
        preimages=locked_remediation_preimages(),
    )
    candidate_tree = artifact.candidate_tree
    path = ALLOWED_REMEDIATION_PATHS[0]
    candidate_tree[path] = b"tampered"

    assert artifact.candidate_tree[path] != b"tampered"
    assert hashlib.sha256(artifact.candidate_tree[path]).hexdigest() == (
        artifact.candidate_hashes[path]
    )


def test_checkout_has_one_coherent_approved_remediation_state() -> None:
    """The release gate supports only the exact red baseline or green candidate."""

    observed = {
        path: hashlib.sha256((REPOSITORY_ROOT / path).read_bytes()).hexdigest()
        for path in ALLOWED_REMEDIATION_PATHS
    }

    assert observed in (EXPECTED_PREIMAGE_SHA256, LOCKED_CANDIDATE_SHA256), (
        "Approved remediation files must be the complete locked preimage pair or "
        "the complete locked candidate pair"
    )
