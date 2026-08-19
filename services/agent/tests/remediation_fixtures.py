"""Immutable vulnerable preimages used by remediation unit tests.

The repository's approved files legitimately move from the vulnerable preimage
to the verified candidate in the generated repair PR.  Tests must therefore not
use the mutable checkout as their source of vulnerable bytes.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from ipromise_agent.remediation import (
    ALLOWED_REMEDIATION_PATHS,
    EXPECTED_PREIMAGE_SHA256,
)


_FIXTURE_ROOT = Path(__file__).with_name("fixtures") / "bounded_remediation"
_FIXTURE_NAMES = {
    "apps/demo_saas/src/ipromise_demo/store.py": "store.py.preimage",
    "apps/demo_saas/tests/test_app.py": "test_app.py.preimage",
}


def locked_remediation_preimages() -> dict[str, bytes]:
    """Return fresh mappings around the independently stored, hash-locked bytes."""

    preimages = {
        path: (_FIXTURE_ROOT / _FIXTURE_NAMES[path]).read_bytes()
        for path in ALLOWED_REMEDIATION_PATHS
    }
    observed = {
        path: hashlib.sha256(content).hexdigest()
        for path, content in preimages.items()
    }
    if observed != EXPECTED_PREIMAGE_SHA256:
        raise AssertionError(
            "Bounded-remediation test fixtures do not match the approved preimage hashes"
        )
    return preimages
