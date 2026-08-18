from __future__ import annotations

import pytest

from ipromise_agent.config import LOCAL_FALLBACK_TOKEN, Settings


def test_cloud_mode_rejects_fallback_secret_and_loopback_target() -> None:
    with pytest.raises(ValueError, match="non-loopback"):
        Settings(
            mode="cloud",
            compiler="adk",
            demo_base_url="http://127.0.0.1:8081",
            demo_token="a-real-looking-token-that-is-long-enough",
        ).validate()

    with pytest.raises(ValueError, match="non-default"):
        Settings(
            mode="cloud",
            compiler="adk",
            demo_base_url="https://synthetic.example.test",
            demo_token=LOCAL_FALLBACK_TOKEN,
        ).validate()


def test_github_actions_require_complete_app_configuration() -> None:
    with pytest.raises(ValueError, match="fully configured"):
        Settings(github_actions_enabled=True).validate()

    with pytest.raises(ValueError, match="incomplete"):
        Settings(github_app_id="1234").validate()


def test_cloud_mode_requires_durable_state_and_api_authentication() -> None:
    with pytest.raises(ValueError, match="Firestore-backed"):
        Settings(
            mode="cloud",
            compiler="adk",
            demo_base_url="https://synthetic.example.test",
            demo_token="a-real-looking-token-that-is-long-enough",
            state_backend="memory",
            api_token="a-real-looking-api-token-value",
        ).validate()


def test_cloud_run_cannot_start_in_authless_local_mode() -> None:
    with pytest.raises(ValueError, match="Cloud Run requires IPROMISE_MODE=cloud"):
        Settings(cloud_run_revision="ipromise-agent-00001").validate()

    with pytest.raises(ValueError, match="agent API bearer token"):
        Settings(
            mode="cloud",
            compiler="adk",
            demo_base_url="https://synthetic.example.test",
            demo_token="a-real-looking-token-that-is-long-enough",
            state_backend="firestore",
        ).validate()


def test_console_base_url_must_be_a_clean_https_origin_in_cloud() -> None:
    with pytest.raises(ValueError, match="without credentials, path, query"):
        Settings(
            console_base_url="https://console.example.test/path?next=1"
        ).validate()


def test_cloud_build_verifier_requires_complete_project_owned_identity() -> None:
    with pytest.raises(ValueError, match="requires IPROMISE_CLOUD_BUILD_PROJECT"):
        Settings(verifier_backend="cloud-build").validate()

    project = "ipromise-test-2026"
    Settings(
        verifier_backend="cloud-build",
        cloud_build_project=project,
        cloud_build_location="australia-southeast1",
        cloud_build_service_account=(
            f"projects/{project}/serviceAccounts/"
            f"ipromise-verifier@{project}.iam.gserviceaccount.com"
        ),
    ).validate()

    with pytest.raises(ValueError, match="project-owned IAM service account"):
        Settings(
            verifier_backend="cloud-build",
            cloud_build_project=project,
            cloud_build_service_account=(
                f"projects/{project}/serviceAccounts/"
                "ipromise-verifier@different-project.iam.gserviceaccount.com"
            ),
        ).validate()

    with pytest.raises(ValueError, match="HTTPS console origin"):
        Settings(
            mode="cloud",
            compiler="adk",
            demo_base_url="https://synthetic.example.test",
            demo_token="a-real-looking-token-that-is-long-enough",
            api_token="a-real-looking-api-token-value",
            state_backend="firestore",
            console_base_url="http://console.example.test",
            github_app_id="1234",
            github_app_slug="ipromise-test",
            github_app_client_id="Iv1.test",
            github_app_client_secret="test-client-secret",
            github_app_private_key="test-private-key",
        ).validate()
