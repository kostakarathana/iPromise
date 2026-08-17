#!/usr/bin/env python3
"""Validate the original synthetic claim-compiler evaluation fixtures."""

from __future__ import annotations

import json
from pathlib import Path


FIXTURE_PATH = Path(__file__).parents[1] / "fixtures" / "evals" / "claims.jsonl"
ALLOWED_TESTABILITY = {"EXECUTABLE", "PARTIAL", "NOT_TESTABLE"}
SUPPORTED_CONTROL = "privacy.account_deletion.v1"


def main() -> None:
    seen_ids: set[str] = set()
    count = 0

    for line_number, line in enumerate(FIXTURE_PATH.read_text().splitlines(), start=1):
        if not line.strip():
            continue

        record = json.loads(line)
        fixture_id = record["id"]
        assert fixture_id not in seen_ids, f"duplicate id at line {line_number}: {fixture_id}"
        seen_ids.add(fixture_id)

        exact_quote = record["exact_quote"]
        assert exact_quote in record["text"], f"ungrounded quote in {fixture_id}"
        assert record["testability"] in ALLOWED_TESTABILITY, fixture_id
        assert "compliant" not in record["notes"].lower(), fixture_id

        if record["control_id"] is not None:
            assert record["testability"] == "EXECUTABLE", fixture_id
            assert record["control_id"] == SUPPORTED_CONTROL, fixture_id

        count += 1

    assert count >= 12, "the initial safety set is unexpectedly small"
    print(f"validated {count} synthetic claim fixtures")


if __name__ == "__main__":
    main()
