"""Thread-safe, ephemeral stores for the synthetic deletion control."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from threading import RLock

from .models import AccountStateResponse, ProcessDeletionResponse, SeedAccountResponse


@dataclass(frozen=True, slots=True)
class _Profile:
    account_id: str
    email: str
    seeded_at: datetime
    deletion_requested_at: datetime


@dataclass(frozen=True, slots=True)
class _AnalyticsProfile:
    account_id: str
    activity_history: tuple[str, ...]
    seeded_at: datetime


class SyntheticStore:
    """Two in-memory stores representing a product database and analytics system."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._profiles: dict[str, _Profile] = {}
        self._analytics_profiles: dict[str, _AnalyticsProfile] = {}
        self._deletion_requests: dict[str, datetime] = {}
        self._virtual_observations: dict[str, datetime] = {}
        self._virtual_processed: dict[str, datetime] = {}
        self._known_fixtures: set[str] = set()

    def seed(self, run_id: str, deletion_requested_hours_ago: int) -> SeedAccountResponse:
        now = datetime.now(UTC)
        deletion_requested_at = now - timedelta(hours=deletion_requested_hours_ago)
        # The run ID is already random. Hashing it gives this owned fixture a
        # stable pseudonymous identity, so a crash/retry cannot leave a second
        # synthetic account for the same logical audit.
        account_id = f"syn_{hashlib.sha256(run_id.encode()).hexdigest()[:32]}"
        email = f"ipromise+{account_id}@example.invalid"
        with self._lock:
            self._profiles[account_id] = _Profile(
                account_id, email, now, deletion_requested_at
            )
            self._analytics_profiles[account_id] = _AnalyticsProfile(
                account_id,
                (f"synthetic-session:{run_id}", "synthetic-page-view:/privacy"),
                now,
            )
            self._deletion_requests[account_id] = deletion_requested_at
            self._virtual_observations[account_id] = now
            self._known_fixtures.add(account_id)
        return SeedAccountResponse(
            account_id=account_id,
            email=email,
            seeded_at=now,
            virtual_deletion_requested_at=deletion_requested_at,
            virtual_observation_at=now,
            virtual_observation_age_hours=deletion_requested_hours_ago,
            stores=["profiles", "analytics_profiles"],
        )

    def process_deletion(self, account_id: str) -> ProcessDeletionResponse | None:
        with self._lock:
            profile = self._profiles.get(account_id)
            if account_id not in self._known_fixtures or profile is None:
                return None
            self._profiles.pop(account_id, None)
            virtual_processed_at = profile.deletion_requested_at + timedelta(hours=1)
            self._virtual_processed[account_id] = virtual_processed_at

            # Complete deletion across both owned synthetic stores.
            self._analytics_profiles.pop(account_id, None)

        return ProcessDeletionResponse(
            account_id=account_id,
            virtual_deletion_requested_at=profile.deletion_requested_at,
            virtual_processed_at=virtual_processed_at,
            virtual_processing_elapsed_hours=1,
        )

    def inspect(self, account_id: str) -> AccountStateResponse:
        with self._lock:
            known = account_id in self._known_fixtures
            profile_exists = account_id in self._profiles if known else None
            analytics_exists = account_id in self._analytics_profiles if known else None
            deletion_requested_at = self._deletion_requests.get(account_id)
            virtual_processed_at = self._virtual_processed.get(account_id)
            virtual_observation_at = self._virtual_observations.get(account_id)
        inspected_at = datetime.now(UTC)
        elapsed = (
            (virtual_observation_at - deletion_requested_at).total_seconds() / 3600
            if deletion_requested_at is not None and virtual_observation_at is not None
            else None
        )
        return AccountStateResponse(
            account_id=account_id,
            known_fixture=known,
            profile_exists=profile_exists,
            analytics_profile_exists=analytics_exists,
            virtual_deletion_requested_at=deletion_requested_at,
            virtual_processed_at=virtual_processed_at,
            virtual_observation_at=virtual_observation_at,
            virtual_observation_elapsed_hours=elapsed,
            inspected_at=inspected_at,
        )

    def reset(self) -> int:
        with self._lock:
            count = len(self._known_fixtures)
            self._profiles.clear()
            self._analytics_profiles.clear()
            self._deletion_requests.clear()
            self._virtual_observations.clear()
            self._virtual_processed.clear()
            self._known_fixtures.clear()
        return count
