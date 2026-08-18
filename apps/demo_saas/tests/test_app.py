from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import pytest
from httpx import ASGITransport, AsyncClient

from ipromise_demo.app import create_app
from ipromise_demo.config import LOCAL_FALLBACK_TOKEN, Settings
from ipromise_demo.contract import DELETION_PROMISE
from ipromise_demo.store import SyntheticStore


TOKEN = "test-synthetic-token"


@asynccontextmanager
async def _client() -> AsyncIterator[AsyncClient]:
    app = create_app(settings=Settings(demo_token=TOKEN), store=SyntheticStore())
    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://synthetic.test",
        ) as client:
            yield client


async def test_privacy_page_contains_exact_promise_and_synthetic_disclosure() -> None:
    async with _client() as client:
        response = await client.get("/privacy")

    assert response.status_code == 200
    assert DELETION_PROMISE in response.text
    assert "SYNTHETIC HACKATHON FIXTURE" in response.text
    assert response.headers["X-iPromise-Synthetic"] == "true"


async def test_control_routes_require_demo_token() -> None:
    async with _client() as client:
        response = await client.post(
            "/v1/synthetic/accounts",
            json={"run_id": "run_12345678"},
        )

    assert response.status_code == 401


async def test_overdue_deletion_removes_application_and_analytics_records() -> None:
    headers = {"X-iPromise-Demo-Token": TOKEN}
    async with _client() as client:
        seeded_response = await client.post(
            "/v1/synthetic/accounts",
            headers=headers,
            json={"run_id": "run_12345678", "deletion_requested_hours_ago": 25},
        )
        seeded = seeded_response.json()
        account_id = seeded["account_id"]

        before_response = await client.get(
            f"/v1/synthetic/accounts/{account_id}/state", headers=headers
        )
        before = before_response.json()
        processed = await client.post(
            f"/v1/synthetic/accounts/{account_id}/process-deletion", headers=headers
        )
        after_response = await client.get(
            f"/v1/synthetic/accounts/{account_id}/state", headers=headers
        )
        after = after_response.json()

    assert before["profile_exists"] is True
    assert before["analytics_profile_exists"] is True
    assert processed.status_code == 200
    assert processed.json()["time_mode"] == "synthetic-virtual-clock"
    assert processed.json()["virtual_processing_elapsed_hours"] <= 24
    assert after["virtual_observation_elapsed_hours"] > 24
    assert after["profile_exists"] is False
    assert after["analytics_profile_exists"] is False
    assert after["synthetic"] is True


async def test_reseeding_the_same_run_reuses_one_synthetic_account() -> None:
    headers = {"X-iPromise-Demo-Token": TOKEN}
    payload = {"run_id": "run_retry_safe_001", "deletion_requested_hours_ago": 25}
    async with _client() as client:
        first = await client.post(
            "/v1/synthetic/accounts",
            headers=headers,
            json=payload,
        )
        second = await client.post(
            "/v1/synthetic/accounts",
            headers=headers,
            json=payload,
        )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["account_id"] == second.json()["account_id"]


def test_cloud_run_environment_rejects_local_fallback_token(monkeypatch) -> None:
    monkeypatch.setenv("K_REVISION", "ipromise-demo-00001")
    monkeypatch.delenv("IPROMISE_DEMO_ENV", raising=False)
    monkeypatch.delenv("IPROMISE_DEMO_TOKEN", raising=False)

    with pytest.raises(ValueError, match="Cloud deployments require"):
        Settings.from_env()

    assert Settings(environment="local").demo_token == LOCAL_FALLBACK_TOKEN
