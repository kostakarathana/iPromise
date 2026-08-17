from __future__ import annotations

from datetime import timedelta

import pytest

from ipromise_agent.compiler import DeterministicDemonstrationCompiler
from ipromise_agent.config import Settings
from ipromise_agent.demo_client import InspectedState, ProcessedDeletion, SeededFixture
from ipromise_agent.models import utc_now
from ipromise_agent.service import AuditService
from ipromise_agent.source import CapturedSource, parse_capture
from ipromise_agent.store import InMemoryRunStore
from ipromise_demo.contract import DELETION_PROMISE


class FakeReferenceClient:
    def __init__(
        self,
        *,
        analytics_exists: bool | None = True,
        profile_exists: bool | None = False,
        processing_elapsed_hours: float = 1,
    ) -> None:
        self.analytics_exists = analytics_exists
        self.profile_exists = profile_exists
        self.processing_elapsed_hours = processing_elapsed_hours
        self.seed_calls = 0
        self.process_calls = 0
        self.account_id = "syn_test_fixture_0001"
        self.t0 = utc_now() - timedelta(hours=25)

    async def capture_privacy(self) -> CapturedSource:
        return parse_capture(
            html=(
                "<html><head><title>Privacy | Synthetic Reference</title></head>"
                '<body><p data-ipromise-claim="account-deletion">'
                + DELETION_PROMISE
                + "</p></body></html>"
            ),
            url="http://synthetic.test/privacy",
            captured_at=utc_now(),
        )

    async def seed_account(self, run_id: str) -> SeededFixture:
        self.seed_calls += 1
        return SeededFixture(
            account_id=self.account_id,
            virtual_deletion_requested_at=self.t0,
            virtual_observation_age_hours=25,
        )

    async def process_deletion(self, account_id: str) -> ProcessedDeletion:
        assert account_id == self.account_id
        self.process_calls += 1
        return ProcessedDeletion(
            virtual_processing_elapsed_hours=self.processing_elapsed_hours
        )

    async def inspect_account(self, account_id: str) -> InspectedState:
        assert account_id == self.account_id
        return InspectedState(
            known_fixture=True,
            profile_exists=self.profile_exists,
            analytics_profile_exists=self.analytics_exists,
            virtual_deletion_requested_at=self.t0,
            virtual_processed_at=self.t0
            + timedelta(hours=self.processing_elapsed_hours),
            virtual_observation_at=self.t0 + timedelta(hours=25),
            virtual_observation_elapsed_hours=25,
            inspected_at=utc_now(),
        )


@pytest.fixture
def settings() -> Settings:
    return Settings(
        mode="demonstration",
        compiler="deterministic",
        demo_base_url="http://synthetic.test",
        demo_token="test-token",
        execution_target="pytest",
    )


def make_service(
    settings: Settings,
    *,
    analytics_exists: bool | None = True,
    profile_exists: bool | None = False,
    processing_elapsed_hours: float = 1,
) -> tuple[AuditService, FakeReferenceClient]:
    client = FakeReferenceClient(
        analytics_exists=analytics_exists,
        profile_exists=profile_exists,
        processing_elapsed_hours=processing_elapsed_hours,
    )
    service = AuditService(
        settings=settings,
        store=InMemoryRunStore(),
        reference_client=client,
        compiler=DeterministicDemonstrationCompiler(),
    )
    return service, client
