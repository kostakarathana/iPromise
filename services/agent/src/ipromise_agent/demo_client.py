"""Narrow client for the configured synthetic reference service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

import httpx

from .models import utc_now
from .source import CapturedSource, parse_capture


@dataclass(frozen=True, slots=True)
class SeededFixture:
    account_id: str
    virtual_deletion_requested_at: datetime
    virtual_observation_age_hours: int


@dataclass(frozen=True, slots=True)
class ProcessedDeletion:
    virtual_processing_elapsed_hours: float


@dataclass(frozen=True, slots=True)
class InspectedState:
    known_fixture: bool
    profile_exists: bool | None
    analytics_profile_exists: bool | None
    virtual_deletion_requested_at: datetime | None
    virtual_processed_at: datetime | None
    virtual_observation_at: datetime | None
    virtual_observation_elapsed_hours: float | None
    inspected_at: datetime


class ReferenceClient(Protocol):
    async def capture_privacy(self) -> CapturedSource: ...

    async def seed_account(self, run_id: str) -> SeededFixture: ...

    async def process_deletion(self, account_id: str) -> ProcessedDeletion: ...

    async def inspect_account(self, account_id: str) -> InspectedState: ...


class HttpReferenceClient:
    """Calls only fixed, configured paths; run requests cannot supply URLs."""

    def __init__(
        self,
        *,
        base_url: str,
        token: str,
        timeout_seconds: float = 10.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._timeout = timeout_seconds
        self._transport = transport

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self._base_url,
            timeout=self._timeout,
            transport=self._transport,
            headers={
                "Accept": "application/json",
                "X-iPromise-Demo-Token": self._token,
                "User-Agent": "iPromise-audit-control/0.1",
            },
            follow_redirects=False,
        )

    async def capture_privacy(self) -> CapturedSource:
        async with self._client() as client:
            response = await client.get("/privacy", headers={"Accept": "text/html"})
            response.raise_for_status()
        return parse_capture(
            html=response.text,
            url=f"{str(response.url).split('#', 1)[0]}#account-deletion",
            captured_at=utc_now(),
        )

    async def seed_account(self, run_id: str) -> SeededFixture:
        async with self._client() as client:
            response = await client.post(
                "/v1/synthetic/accounts",
                json={
                    "scenario": "deletion-control",
                    "run_id": run_id,
                    "deletion_requested_hours_ago": 25,
                },
            )
            response.raise_for_status()
        body = response.json()
        return SeededFixture(
            account_id=body["account_id"],
            virtual_deletion_requested_at=datetime.fromisoformat(
                body["virtual_deletion_requested_at"]
            ),
            virtual_observation_age_hours=body["virtual_observation_age_hours"],
        )

    async def process_deletion(self, account_id: str) -> ProcessedDeletion:
        async with self._client() as client:
            response = await client.post(
                f"/v1/synthetic/accounts/{account_id}/process-deletion"
            )
            response.raise_for_status()
        return ProcessedDeletion(
            virtual_processing_elapsed_hours=response.json()[
                "virtual_processing_elapsed_hours"
            ]
        )

    async def inspect_account(self, account_id: str) -> InspectedState:
        async with self._client() as client:
            response = await client.get(
                f"/v1/synthetic/accounts/{account_id}/state"
            )
            response.raise_for_status()
        body = response.json()
        return InspectedState(
            known_fixture=body["known_fixture"],
            profile_exists=body.get("profile_exists"),
            analytics_profile_exists=body.get("analytics_profile_exists"),
            virtual_deletion_requested_at=(
                datetime.fromisoformat(body["virtual_deletion_requested_at"])
                if body.get("virtual_deletion_requested_at")
                else None
            ),
            virtual_processed_at=(
                datetime.fromisoformat(body["virtual_processed_at"])
                if body.get("virtual_processed_at")
                else None
            ),
            virtual_observation_at=(
                datetime.fromisoformat(body["virtual_observation_at"])
                if body.get("virtual_observation_at")
                else None
            ),
            virtual_observation_elapsed_hours=body.get(
                "virtual_observation_elapsed_hours"
            ),
            inspected_at=datetime.fromisoformat(body["inspected_at"]),
        )
