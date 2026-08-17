from __future__ import annotations

import asyncio
from dataclasses import replace
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from ipromise_agent.compiler import DeterministicDemonstrationCompiler
from ipromise_agent.github import (
    GitHubAuthorizationError,
    GitHubPublishUncertain,
    GitHubService,
    InMemoryGitHubStore,
    PublishedIssue,
    finding_fingerprint,
)
from ipromise_agent.models import (
    ActionKind,
    ActionState,
    CreateRunRequest,
    GitHubOAuthCallbackRequest,
    GitHubOAuthStartRequest,
    GitHubRepository,
    PlannedAction,
)
from ipromise_agent.service import AuditService

from conftest import FakeReferenceClient


def _private_key() -> str:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()


def _github_settings(settings, *, actions: bool = False):
    return replace(
        settings,
        github_actions_enabled=actions,
        github_app_id="1234",
        github_app_slug="ipromise-test",
        github_app_client_id="Iv1.ipromise-test",
        github_app_client_secret="test-client-secret",
        github_app_private_key=_private_key(),
        console_base_url="http://console.test",
    )


async def _connect(
    github: GitHubService, *, repository_count: int = 2
):
    install = await github.install_url()
    install_state = parse_qs(urlparse(install.url).query)["state"][0]
    oauth = await github.oauth_url(
        GitHubOAuthStartRequest(
            installation_id=77,
            setup_action="install",
            state=install_state,
        )
    )
    oauth_query = parse_qs(urlparse(oauth.url).query)
    assert oauth_query["code_challenge_method"] == ["S256"]
    status = await github.complete_oauth(
        GitHubOAuthCallbackRequest(
            code="authorization-code",
            state=oauth_query["state"][0],
        )
    )
    assert len(status.repositories) == repository_count
    return status, oauth_query["state"][0]


class _ObservedGitHubStore(InMemoryGitHubStore):
    def __init__(self) -> None:
        super().__init__()
        self.contention_observed = asyncio.Event()

    async def claim_issue_intent(
        self,
        fingerprint: str,
        owner: str,
        *,
        lease_seconds: int,
    ):
        claim = await super().claim_issue_intent(
            fingerprint,
            owner,
            lease_seconds=lease_seconds,
        )
        if not claim.acquired and claim.receipt is None:
            self.contention_observed.set()
        return claim


class _BarrierGitHubTransport(httpx.AsyncBaseTransport):
    def __init__(self) -> None:
        self.preflight_started = asyncio.Event()
        self.release_preflight = asyncio.Event()
        self.issue_body: str | None = None
        self.issue_gets = 0
        self.issue_posts = 0
        self.token_mints = 0

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        if request.url.path == "/login/oauth/access_token":
            return httpx.Response(200, json={"access_token": "ghu_transient"})
        if request.url.path == "/user/installations":
            return httpx.Response(
                200,
                json={
                    "installations": [
                        {
                            "id": 77,
                            "app_id": 1234,
                            "suspended_at": None,
                            "account": {"login": "octocat"},
                        }
                    ]
                },
            )
        if request.url.path == "/user/installations/77/repositories":
            return httpx.Response(
                200,
                json={
                    "repositories": [
                        {
                            "id": 101,
                            "full_name": "octocat/alpha",
                            "default_branch": "main",
                            "private": True,
                            "archived": False,
                            "html_url": "https://github.com/octocat/alpha",
                        }
                    ]
                },
            )
        if request.url.path == "/app/installations/77/access_tokens":
            self.token_mints += 1
            return httpx.Response(201, json={"token": "ghs_repo_scoped"})
        if request.url.path == "/repos/octocat/alpha/issues" and request.method == "GET":
            self.issue_gets += 1
            if self.issue_body is None:
                self.preflight_started.set()
                await self.release_preflight.wait()
                return httpx.Response(200, json=[])
            return httpx.Response(
                200,
                json=[
                    {
                        "id": 9001,
                        "number": 17,
                        "html_url": "https://github.com/octocat/alpha/issues/17",
                        "body": self.issue_body,
                    }
                ],
            )
        if request.url.path == "/repos/octocat/alpha/issues" and request.method == "POST":
            self.issue_posts += 1
            self.issue_body = __import__("json").loads(request.content)["body"]
            return httpx.Response(
                201,
                json={
                    "id": 9001,
                    "number": 17,
                    "html_url": "https://github.com/octocat/alpha/issues/17",
                },
            )
        raise AssertionError(f"Unexpected GitHub request: {request.method} {request.url}")


@pytest.mark.asyncio
async def test_expired_issue_intent_owner_cannot_overwrite_new_owner() -> None:
    store = InMemoryGitHubStore()
    fingerprint = "stable-finding"
    first = await store.claim_issue_intent(
        fingerprint,
        "worker-one",
        lease_seconds=0,
    )
    second = await store.claim_issue_intent(
        fingerprint,
        "worker-two",
        lease_seconds=30,
    )
    assert first.acquired
    assert second.acquired

    receipt = PublishedIssue(
        url="https://github.com/octocat/alpha/issues/41",
        number=41,
        remote_id=4100,
    )
    with pytest.raises(GitHubPublishUncertain, match="ownership changed"):
        await store.complete_issue_intent(fingerprint, "worker-one", receipt)

    completed = await store.complete_issue_intent(
        fingerprint,
        "worker-two",
        receipt,
    )
    assert completed == receipt


@pytest.mark.asyncio
async def test_oauth_proves_installation_and_only_allows_returned_repositories(
    settings,
) -> None:
    exchanged_verifier: str | None = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal exchanged_verifier
        if request.url.path == "/login/oauth/access_token":
            assert request.headers["content-type"].startswith(
                "application/x-www-form-urlencoded"
            )
            payload = parse_qs(request.content.decode())
            exchanged_verifier = payload["code_verifier"][0]
            return httpx.Response(200, json={"access_token": "ghu_transient"})
        if request.url.path == "/user/installations":
            return httpx.Response(
                200,
                json={
                    "installations": [
                        {
                            "id": 77,
                            "app_id": 1234,
                            "suspended_at": None,
                            "account": {"login": "octocat"},
                        }
                    ]
                },
            )
        if request.url.path == "/user/installations/77/repositories":
            return httpx.Response(
                200,
                json={
                    "repositories": [
                        {
                            "id": 101,
                            "full_name": "octocat/alpha",
                            "default_branch": "main",
                            "private": True,
                            "archived": False,
                            "html_url": "https://github.com/octocat/alpha",
                        },
                        {
                            "id": 202,
                            "full_name": "octocat/beta",
                            "default_branch": "trunk",
                            "private": False,
                            "archived": False,
                            "html_url": "https://github.com/octocat/beta",
                        },
                    ]
                },
            )
        raise AssertionError(f"Unexpected GitHub request: {request.method} {request.url}")

    github = GitHubService(
        _github_settings(settings), transport=httpx.MockTransport(handler)
    )
    status, consumed_state = await _connect(github)

    assert exchanged_verifier
    assert status.connected is True
    assert status.account_login == "octocat"
    assert status.selected_repository is None
    selected = await github.select_repository(202)
    assert selected.selected_repository is not None
    assert selected.selected_repository.full_name == "octocat/beta"

    with pytest.raises(GitHubAuthorizationError, match="not available"):
        await github.select_repository(999)
    with pytest.raises(GitHubAuthorizationError, match="invalid or expired"):
        await github.complete_oauth(
            GitHubOAuthCallbackRequest(
                code="another-code",
                state=consumed_state,
            )
        )


@pytest.mark.asyncio
async def test_distinct_scheduled_runs_reconcile_one_repo_scoped_finding(
    settings,
) -> None:
    issue_posts = 0
    issue_payload: dict | None = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal issue_posts, issue_payload
        if request.url.path == "/login/oauth/access_token":
            return httpx.Response(200, json={"access_token": "ghu_transient"})
        if request.url.path == "/user/installations":
            return httpx.Response(
                200,
                json={
                    "installations": [
                        {
                            "id": 77,
                            "app_id": 1234,
                            "suspended_at": None,
                            "account": {"login": "octocat"},
                        }
                    ]
                },
            )
        if request.url.path == "/user/installations/77/repositories":
            return httpx.Response(
                200,
                json={
                    "repositories": [
                        {
                            "id": 101,
                            "full_name": "octocat/alpha",
                            "default_branch": "main",
                            "private": True,
                            "archived": False,
                            "html_url": "https://github.com/octocat/alpha",
                        }
                    ]
                },
            )
        if request.url.path == "/app/installations/77/access_tokens":
            payload = __import__("json").loads(request.content)
            assert payload == {
                "repository_ids": [101],
                "permissions": {"issues": "write"},
            }
            return httpx.Response(201, json={"token": "ghs_repo_scoped"})
        if request.url.path == "/repos/octocat/alpha/issues" and request.method == "GET":
            if issue_payload is None:
                return httpx.Response(200, json=[])
            return httpx.Response(
                200,
                json=[
                    {
                        "id": 9001,
                        "number": 17,
                        "html_url": "https://github.com/octocat/alpha/issues/17",
                        "body": issue_payload["body"],
                    }
                ],
            )
        if request.url.path == "/repos/octocat/alpha/issues" and request.method == "POST":
            issue_posts += 1
            issue_payload = __import__("json").loads(request.content)
            return httpx.Response(
                201,
                json={
                    "id": 9001,
                    "number": 17,
                    "html_url": "https://github.com/octocat/alpha/issues/17",
                },
            )
        raise AssertionError(f"Unexpected GitHub request: {request.method} {request.url}")

    configured = _github_settings(settings, actions=True)
    github = GitHubService(configured, transport=httpx.MockTransport(handler))
    status, _ = await _connect(github, repository_count=1)
    assert status.selected_repository is not None

    service = AuditService(
        settings=configured,
        reference_client=FakeReferenceClient(),
        compiler=DeterministicDemonstrationCompiler(),
        github_service=github,
    )
    first = await service.create_run(
        CreateRunRequest(
            trigger="scheduled",
            source="scheduler",
            idempotency_key="scheduled-occurrence-2026-08-17t0000z",
        )
    )
    second = await service.create_run(
        CreateRunRequest(
            trigger="scheduled",
            source="scheduler",
            idempotency_key="scheduled-occurrence-2026-08-17t0100z",
        )
    )

    first_issue = next(
        action for action in first.actions if action.kind == ActionKind.ISSUE
    )
    second_issue = next(
        action for action in second.actions if action.kind == ActionKind.ISSUE
    )
    assert first.repository is not None
    assert second.repository is not None
    assert first.repository.full_name == "octocat/alpha"
    assert second.id != first.id
    assert first_issue.id != second_issue.id
    assert first_issue.id.startswith(first.id)
    assert second_issue.id.startswith(second.id)
    assert first_issue.state == ActionState.OPENED
    assert second_issue.state == ActionState.OPENED
    assert first_issue.url == second_issue.url
    assert second_issue.reason == "Existing marker-matched issue reconciled"
    assert issue_posts == 1
    assert issue_payload is not None
    fingerprint = finding_fingerprint(first, first.repository)
    assert fingerprint == finding_fingerprint(second, second.repository)
    assert f"<!-- ipromise-finding:v1:{fingerprint} -->" in issue_payload["body"]
    assert f"<!-- ipromise-run:v1:{first.id} -->" in issue_payload["body"]
    assert "not a legal-compliance conclusion" in issue_payload["body"]
    assert "synthetic data" in issue_payload["body"]

    changed_evidence = second.model_copy(deep=True)
    changed_evidence.evidence[-1].observed = "No active record at +25h"
    assert finding_fingerprint(changed_evidence, second.repository) != fingerprint

    changed_source = second.model_copy(deep=True)
    changed_source.claim.content_hash = "changed-source-snapshot"
    assert finding_fingerprint(changed_source, second.repository) != fingerprint

    changed_control = second.model_copy(deep=True)
    changed_control.claim.control_id = "privacy.account_deletion.v2"
    assert finding_fingerprint(changed_control, second.repository) != fingerprint

    changed_repository = second.repository.model_copy(update={"id": 202})
    assert finding_fingerprint(second, changed_repository) != fingerprint


@pytest.mark.asyncio
async def test_concurrent_distinct_runs_share_one_durable_issue_intent(
    settings,
) -> None:
    store = _ObservedGitHubStore()
    transport = _BarrierGitHubTransport()
    configured = _github_settings(settings, actions=True)
    github = GitHubService(configured, store=store, transport=transport)
    status, _ = await _connect(github, repository_count=1)
    assert status.selected_repository is not None
    service = AuditService(
        settings=configured,
        reference_client=FakeReferenceClient(),
        compiler=DeterministicDemonstrationCompiler(),
        github_service=github,
    )

    first_task = asyncio.create_task(
        service.create_run(
            CreateRunRequest(
                trigger="scheduled",
                source="scheduler",
                idempotency_key="concurrent-schedule-2026-08-17t0000z",
            )
        )
    )
    await asyncio.wait_for(transport.preflight_started.wait(), timeout=5)

    second_task = asyncio.create_task(
        service.create_run(
            CreateRunRequest(
                trigger="scheduled",
                source="scheduler",
                idempotency_key="concurrent-schedule-2026-08-17t0100z",
            )
        )
    )
    await asyncio.wait_for(store.contention_observed.wait(), timeout=5)

    # The second run is demonstrably at the publication barrier, but only the
    # finding-level lease owner may reach GitHub.
    assert transport.issue_gets == 1
    assert transport.issue_posts == 0
    assert transport.token_mints == 1
    transport.release_preflight.set()

    first, second = await asyncio.gather(first_task, second_task)
    first_issue = next(
        action for action in first.actions if action.kind == ActionKind.ISSUE
    )
    second_issue = next(
        action for action in second.actions if action.kind == ActionKind.ISSUE
    )

    assert first.id != second.id
    assert first_issue.id != second_issue.id
    assert first_issue.state == ActionState.OPENED
    assert second_issue.state == ActionState.OPENED
    assert first_issue.url == second_issue.url
    assert transport.issue_gets == 1
    assert transport.issue_posts == 1
    assert transport.token_mints == 1
    assert second_issue.reason == "Existing marker-matched issue reconciled"


@pytest.mark.asyncio
async def test_issue_destination_is_bound_to_the_run_not_current_selection(settings) -> None:
    post_paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/login/oauth/access_token":
            return httpx.Response(200, json={"access_token": "ghu_transient"})
        if request.url.path == "/user/installations":
            return httpx.Response(
                200,
                json={
                    "installations": [
                        {
                            "id": 77,
                            "app_id": 1234,
                            "suspended_at": None,
                            "account": {"login": "octocat"},
                        }
                    ]
                },
            )
        if request.url.path == "/user/installations/77/repositories":
            return httpx.Response(
                200,
                json={
                    "repositories": [
                        {
                            "id": 101,
                            "full_name": "octocat/alpha",
                            "default_branch": "main",
                            "private": True,
                            "archived": False,
                            "html_url": "https://github.com/octocat/alpha",
                        },
                        {
                            "id": 202,
                            "full_name": "octocat/beta",
                            "default_branch": "main",
                            "private": True,
                            "archived": False,
                            "html_url": "https://github.com/octocat/beta",
                        },
                    ]
                },
            )
        if request.url.path == "/app/installations/77/access_tokens":
            assert __import__("json").loads(request.content)["repository_ids"] == [101]
            return httpx.Response(201, json={"token": "ghs_repo_scoped"})
        if request.method == "GET" and request.url.path == "/repos/octocat/alpha/issues":
            return httpx.Response(200, json=[])
        if request.method == "POST" and request.url.path == "/repos/octocat/alpha/issues":
            post_paths.append(request.url.path)
            return httpx.Response(
                201,
                json={
                    "id": 9001,
                    "number": 17,
                    "html_url": "https://github.com/octocat/alpha/issues/17",
                },
            )
        raise AssertionError(f"Unexpected GitHub request: {request.method} {request.url}")

    configured = _github_settings(settings, actions=True)
    github = GitHubService(configured, transport=httpx.MockTransport(handler))
    await _connect(github)
    selected = await github.select_repository(101)
    bound_repository = selected.selected_repository
    assert bound_repository is not None
    service = AuditService(settings=configured, github_service=github)
    run = service._new_run("immutable-destination-01", bound_repository)
    action = PlannedAction(
        id=f"{run.id}:issue",
        kind=ActionKind.ISSUE,
        state=ActionState.PLANNED,
        title="Account deletion mismatch",
        verified=False,
    )

    await github.select_repository(202)
    receipt = await github.publish_issue(run, action)

    assert post_paths == ["/repos/octocat/alpha/issues"]
    assert receipt.url == "https://github.com/octocat/alpha/issues/17"


@pytest.mark.asyncio
async def test_ambiguous_server_response_reconciles_before_returning(settings) -> None:
    issue_body: str | None = None
    issue_posts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal issue_body, issue_posts
        if request.url.path == "/login/oauth/access_token":
            return httpx.Response(200, json={"access_token": "ghu_transient"})
        if request.url.path == "/user/installations":
            return httpx.Response(
                200,
                json={
                    "installations": [
                        {
                            "id": 77,
                            "app_id": 1234,
                            "suspended_at": None,
                            "account": {"login": "octocat"},
                        }
                    ]
                },
            )
        if request.url.path == "/user/installations/77/repositories":
            return httpx.Response(
                200,
                json={
                    "repositories": [
                        {
                            "id": 101,
                            "full_name": "octocat/alpha",
                            "default_branch": "main",
                            "private": True,
                            "archived": False,
                            "html_url": "https://github.com/octocat/alpha",
                        }
                    ]
                },
            )
        if request.url.path == "/app/installations/77/access_tokens":
            return httpx.Response(201, json={"token": "ghs_repo_scoped"})
        if request.method == "GET" and request.url.path.endswith("/issues"):
            if issue_body is None:
                return httpx.Response(200, json=[])
            return httpx.Response(
                200,
                json=[
                    {
                        "id": 9001,
                        "number": 17,
                        "html_url": "https://github.com/octocat/alpha/issues/17",
                        "body": issue_body,
                    }
                ],
            )
        if request.method == "POST" and request.url.path.endswith("/issues"):
            issue_posts += 1
            issue_body = __import__("json").loads(request.content)["body"]
            return httpx.Response(500, json={"message": "response lost after commit"})
        raise AssertionError(f"Unexpected GitHub request: {request.method} {request.url}")

    configured = _github_settings(settings, actions=True)
    github = GitHubService(configured, transport=httpx.MockTransport(handler))
    status, _ = await _connect(github, repository_count=1)
    repository = status.selected_repository
    assert isinstance(repository, GitHubRepository)
    run = AuditService(settings=configured, github_service=github)._new_run(
        "ambiguous-write-reconcile-01", repository
    )
    action = PlannedAction(
        id=f"{run.id}:issue",
        kind=ActionKind.ISSUE,
        state=ActionState.PLANNED,
        title="Account deletion mismatch",
        verified=False,
    )

    receipt = await github.publish_issue(run, action)

    assert issue_posts == 1
    assert receipt.reconciled is True
    assert receipt.url == "https://github.com/octocat/alpha/issues/17"
