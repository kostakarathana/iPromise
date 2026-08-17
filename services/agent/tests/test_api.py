from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from unittest.mock import AsyncMock

import httpx
import pytest
from httpx import ASGITransport, AsyncClient
from jsonschema import Draft202012Validator

from ipromise_agent.app import create_app
from ipromise_agent.compiler import DeterministicDemonstrationCompiler
from ipromise_agent.models import CreateRunRequest, RunStatus
from ipromise_agent.service import ACTION_LEASE_SECONDS, AuditService

from conftest import FakeReferenceClient, make_service


CONSOLE_TOKEN = "console-test-token-value"
SCHEDULER_TOKEN = "scheduler-test-oidc-token"
SCHEDULER_AUDIENCE = "https://agent.test"
SCHEDULER_SERVICE_ACCOUNT = "ipromise-scheduler@test.iam.gserviceaccount.com"


@pytest.fixture
def scheduler_oidc_verifier(monkeypatch: pytest.MonkeyPatch) -> None:
    from google.oauth2 import id_token

    def verify(token: str, _request: object, audience: str) -> dict[str, str | bool]:
        if token != SCHEDULER_TOKEN or audience != SCHEDULER_AUDIENCE:
            raise ValueError("invalid test OIDC token")
        return {
            "email": SCHEDULER_SERVICE_ACCOUNT,
            "email_verified": True,
        }

    monkeypatch.setattr(id_token, "verify_oauth2_token", verify)


def with_split_auth(settings):
    return replace(
        settings,
        api_token=CONSOLE_TOKEN,
        google_oidc_audience=SCHEDULER_AUDIENCE,
        scheduler_service_account=SCHEDULER_SERVICE_ACCOUNT,
    )


class _OnceUnavailableReference(FakeReferenceClient):
    def __init__(self) -> None:
        super().__init__()
        self.capture_calls = 0

    async def capture_privacy(self):
        self.capture_calls += 1
        if self.capture_calls == 1:
            raise httpx.ConnectTimeout("temporary failure")
        return await super().capture_privacy()


@pytest.mark.asyncio
async def test_api_matches_console_contract_and_supports_latest(settings) -> None:
    service, reference = make_service(settings)
    app = create_app(settings=settings, service=service)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://agent.test"
    ) as client:
        empty = await client.get("/v1/runs/latest")
        created = await client.post(
            "/v1/runs",
            headers={"Idempotency-Key": "api-contract-001"},
            json={"trigger": "manual", "source": "console"},
        )
        latest = await client.get("/v1/runs/latest")
        fetched = await client.get(f"/v1/runs/{created.json()['id']}")
        unsupported = await client.post(
            "/v1/runs",
            json={"controlId": "admin.delete_everything"},
        )

    assert empty.status_code == 204
    assert empty.content == b""
    assert created.status_code == 200
    body = created.json()
    schema = json.loads(
        (
            Path(__file__).resolve().parents[3]
            / "contracts/audit-run.schema.json"
        ).read_text()
    )
    Draft202012Validator(schema).validate(body)
    assert body["mode"] == "demonstration"
    assert body["verdict"] == "CONTRADICTED"
    assert body["claim"]["exactQuote"]
    assert body["claim"]["sourceUrl"] == "http://synthetic.test/privacy"
    assert body["claim"]["controlId"] == "privacy.account_deletion.v1"
    assert body["runtime"]["modelInvocationAttempted"] is False
    assert body["runtime"]["modelInvoked"] is False
    assert body["runtime"]["model"] is None
    assert body["events"]
    assert body["evidence"]
    assert body["actions"][0]["state"] == "BLOCKED"
    assert latest.json()["id"] == body["id"]
    assert fetched.json()["id"] == body["id"]
    assert unsupported.status_code == 422
    assert "accepts only privacy.account_deletion.v1" in unsupported.json()["error"][
        "message"
    ]
    assert reference.process_calls == 1


@pytest.mark.asyncio
async def test_authless_console_access_is_local_only_and_scheduler_fails_closed(
    settings,
) -> None:
    local_settings = replace(settings, mode="local", compiler="adk")
    cloud_settings = replace(settings, mode="cloud", compiler="adk")
    local_service, _ = make_service(local_settings)
    cloud_service, _ = make_service(cloud_settings)
    local_app = create_app(settings=local_settings, service=local_service)
    cloud_app = create_app(settings=cloud_settings, service=cloud_service)
    delivery_headers = {
        "X-CloudScheduler-JobName": "projects/test/locations/us/jobs/ipromise",
        "X-CloudScheduler-ScheduleTime": "2026-08-17T11:00:00Z",
    }

    async with AsyncClient(
        transport=ASGITransport(app=local_app), base_url="http://agent.test"
    ) as client:
        local_console = await client.get("/v1/runs/latest")
        local_scheduler = await client.post(
            "/v1/triggers/scheduled", headers=delivery_headers
        )
    async with AsyncClient(
        transport=ASGITransport(app=cloud_app), base_url="http://agent.test"
    ) as client:
        cloud_console = await client.get("/v1/runs/latest")

    assert local_console.status_code == 204
    assert local_scheduler.status_code == 401
    assert cloud_console.status_code == 401


@pytest.mark.asyncio
async def test_cloud_run_revision_cannot_use_authless_demonstration_routes(
    settings,
) -> None:
    cloud_run_settings = replace(
        settings,
        cloud_run_revision="ipromise-agent-00001",
        execution_target="cloud-run",
    )
    service, _ = make_service(cloud_run_settings)
    app = create_app(settings=cloud_run_settings, service=service)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://agent.test"
    ) as client:
        response = await client.get("/v1/runs/latest")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_cloud_scheduler_trigger_requires_identity_and_dedupes_delivery(
    settings,
    scheduler_oidc_verifier,
) -> None:
    protected = with_split_auth(settings)
    service, reference = make_service(protected)
    app = create_app(settings=protected, service=service)
    headers = {
        "Authorization": f"Bearer {SCHEDULER_TOKEN}",
        "X-CloudScheduler-JobName": "projects/test/locations/us/jobs/ipromise",
        "X-CloudScheduler-ScheduleTime": "2026-08-17T12:00:00Z",
    }

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://agent.test"
    ) as client:
        unauthenticated = await client.post(
            "/v1/triggers/scheduled",
            headers={
                "X-CloudScheduler-JobName": headers["X-CloudScheduler-JobName"],
                "X-CloudScheduler-ScheduleTime": headers[
                    "X-CloudScheduler-ScheduleTime"
                ],
            },
        )
        first = await client.post("/v1/triggers/scheduled", headers=headers)
        second = await client.post("/v1/triggers/scheduled", headers=headers)

    assert unauthenticated.status_code == 401
    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["id"] == second.json()["id"]
    assert first.json()["idempotencyKey"].startswith("scheduler:")
    assert reference.process_calls == 1


@pytest.mark.asyncio
async def test_scheduler_returns_failure_until_same_delivery_recovers(
    settings,
    scheduler_oidc_verifier,
) -> None:
    protected = with_split_auth(settings)
    reference = _OnceUnavailableReference()
    service = AuditService(
        settings=protected,
        reference_client=reference,
        compiler=DeterministicDemonstrationCompiler(),
    )
    app = create_app(settings=protected, service=service)
    headers = {
        "Authorization": f"Bearer {SCHEDULER_TOKEN}",
        "X-CloudScheduler-JobName": "projects/test/locations/us/jobs/ipromise",
        "X-CloudScheduler-ScheduleTime": "2026-08-17T18:00:00Z",
    }

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://agent.test"
    ) as client:
        first = await client.post("/v1/triggers/scheduled", headers=headers)
        recovered = await client.post("/v1/triggers/scheduled", headers=headers)

    assert first.status_code == 503
    assert first.headers["retry-after"] == str(ACTION_LEASE_SECONDS)
    assert first.json()["status"] == "FAILED_RETRYABLE"
    assert recovered.status_code == 202
    assert recovered.json()["status"] == "COMPLETE"
    assert recovered.json()["id"] == first.json()["id"]
    assert reference.capture_calls == 2


@pytest.mark.asyncio
async def test_scheduler_does_not_acknowledge_nonterminal_lease_contention(
    settings,
    scheduler_oidc_verifier,
) -> None:
    protected = with_split_auth(settings)
    service, _ = make_service(protected)
    checkpoint = await service.create_run(
        CreateRunRequest(idempotency_key="scheduler-routing-checkpoint")
    )
    checkpoint.status = RunStatus.ROUTING_ACTION
    service.create_run = AsyncMock(return_value=checkpoint)
    app = create_app(settings=protected, service=service)
    headers = {
        "Authorization": f"Bearer {SCHEDULER_TOKEN}",
        "X-CloudScheduler-JobName": "projects/test/locations/us/jobs/ipromise",
        "X-CloudScheduler-ScheduleTime": "2026-08-17T19:00:00Z",
    }

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://agent.test"
    ) as client:
        response = await client.post("/v1/triggers/scheduled", headers=headers)

    assert response.status_code == 503
    assert response.headers["retry-after"] == str(ACTION_LEASE_SECONDS)
    assert response.json()["status"] == "ROUTING_ACTION"


@pytest.mark.asyncio
async def test_console_and_scheduler_credentials_are_not_interchangeable(
    settings,
    scheduler_oidc_verifier,
) -> None:
    protected = with_split_auth(settings)
    service, reference = make_service(protected)
    app = create_app(settings=protected, service=service)
    console_headers = {"Authorization": f"Bearer {CONSOLE_TOKEN}"}
    scheduler_headers = {"Authorization": f"Bearer {SCHEDULER_TOKEN}"}
    delivery_headers = {
        "X-CloudScheduler-JobName": "projects/test/locations/us/jobs/ipromise",
        "X-CloudScheduler-ScheduleTime": "2026-08-17T20:00:00Z",
    }

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://agent.test"
    ) as client:
        scheduler_manual_run = await client.post(
            "/v1/runs", headers=scheduler_headers
        )
        scheduler_github_read = await client.get(
            "/v1/integrations/github", headers=scheduler_headers
        )
        scheduler_github_change = await client.delete(
            "/v1/integrations/github", headers=scheduler_headers
        )
        console_scheduled_run = await client.post(
            "/v1/triggers/scheduled",
            headers=console_headers | delivery_headers,
        )
        console_manual_run = await client.post("/v1/runs", headers=console_headers)
        scheduler_scheduled_run = await client.post(
            "/v1/triggers/scheduled",
            headers=scheduler_headers | delivery_headers,
        )

    assert scheduler_manual_run.status_code == 401
    assert scheduler_github_read.status_code == 401
    assert scheduler_github_change.status_code == 401
    assert console_scheduled_run.status_code == 401
    assert console_manual_run.status_code == 200
    assert scheduler_scheduled_run.status_code == 202
    assert reference.process_calls == 2
