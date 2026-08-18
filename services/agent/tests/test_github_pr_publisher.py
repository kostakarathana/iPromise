from __future__ import annotations

import asyncio
import base64
import hashlib
import json
from dataclasses import replace
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from ipromise_agent.github import (
    GitHubPublicationRejected,
    GitHubService,
)
from ipromise_agent.models import (
    ActionKind,
    ActionState,
    GitHubOAuthCallbackRequest,
    GitHubOAuthStartRequest,
    PlannedAction,
    VerificationArtifactBinding,
    VerificationReceipt,
    VerificationResult,
)
from ipromise_agent.service import AuditService


BASE_SHA = "1" * 40
BASE_TREE_SHA = "2" * 40
CANDIDATE_TREE_SHA = "c" * 40
COMMIT_SHA = "d" * 40
STORE_PATH = "apps/demo_saas/src/ipromise_demo/store.py"
TEST_PATH = "apps/demo_saas/tests/test_app.py"
BASE_FILES = {
    STORE_PATH: b"vulnerable store\n",
    TEST_PATH: b"assert analytics_exists\n",
}
CANDIDATE_FILES = {
    STORE_PATH: b"fixed store\n",
    TEST_PATH: b"assert not analytics_exists\n",
}


def _git_blob_sha(content: bytes) -> str:
    header = f"blob {len(content)}\0".encode("ascii")
    return hashlib.sha1(header + content, usedforsecurity=False).hexdigest()


def _private_key() -> str:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()


def _github_settings(settings):
    return replace(
        settings,
        github_actions_enabled=True,
        github_app_id="1234",
        github_app_slug="ipromise-test",
        github_app_client_id="Iv1.ipromise-test",
        github_app_client_secret="test-client-secret",
        github_app_private_key=_private_key(),
        console_base_url="http://console.test",
    )


def _repository_payload() -> dict[str, object]:
    return {
        "id": 101,
        "full_name": "octocat/alpha",
        "default_branch": "main",
        "private": True,
        "archived": False,
        "html_url": "https://github.com/octocat/alpha",
    }


def _tree_payload(tree_sha: str, files: dict[str, bytes]) -> dict[str, object]:
    return {
        "sha": tree_sha,
        "truncated": False,
        "tree": [
            {
                "path": path,
                "mode": "100644",
                "type": "blob",
                "sha": _git_blob_sha(content),
            }
            for path, content in sorted(files.items())
        ],
    }


class _DraftPullTransport(httpx.AsyncBaseTransport):
    def __init__(self) -> None:
        self.base_ref_sha = BASE_SHA
        self.branch: str | None = None
        self.pr: dict[str, object] | None = None
        self.ambiguous_pull = False
        self.bad_candidate_tree = False
        self.requests: list[tuple[str, str]] = []
        self.token_payloads: list[dict[str, object]] = []
        self.uploaded_blobs: list[bytes] = []
        self.ref_posts = 0
        self.pull_posts = 0

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        self.requests.append((request.method, path))
        if path == "/login/oauth/access_token":
            return httpx.Response(200, json={"access_token": "ghu_transient"})
        if path == "/user/installations":
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
        if path == "/user/installations/77/repositories":
            return httpx.Response(
                200, json={"repositories": [_repository_payload()]}
            )
        if path == "/app/installations/77" and request.method == "GET":
            return httpx.Response(
                200,
                json={
                    "id": 77,
                    "app_id": 1234,
                    "suspended_at": None,
                    "account": {"login": "octocat"},
                },
            )
        if path == "/app/installations/77/access_tokens":
            payload = json.loads(request.content)
            self.token_payloads.append(payload)
            return httpx.Response(201, json={"token": "ghs_repo_scoped"})
        if path == "/installation/repositories":
            return httpx.Response(
                200, json={"repositories": [_repository_payload()]}
            )
        if path == "/repos/octocat/alpha/git/ref/heads/main":
            return httpx.Response(
                200,
                json={
                    "ref": "refs/heads/main",
                    "object": {"type": "commit", "sha": self.base_ref_sha},
                },
            )
        if path.startswith("/repos/octocat/alpha/git/ref/heads/ipromise/"):
            if self.branch is None:
                return httpx.Response(404, json={"message": "Not Found"})
            return httpx.Response(
                200,
                json={
                    "ref": f"refs/heads/{self.branch}",
                    "object": {"type": "commit", "sha": COMMIT_SHA},
                },
            )
        if path == f"/repos/octocat/alpha/git/commits/{BASE_SHA}":
            return httpx.Response(
                200,
                json={"sha": BASE_SHA, "tree": {"sha": BASE_TREE_SHA}, "parents": []},
            )
        if path == f"/repos/octocat/alpha/git/commits/{COMMIT_SHA}":
            return httpx.Response(
                200,
                json={
                    "sha": COMMIT_SHA,
                    "tree": {"sha": CANDIDATE_TREE_SHA},
                    "parents": [{"sha": BASE_SHA}],
                },
            )
        if path == f"/repos/octocat/alpha/git/trees/{BASE_TREE_SHA}":
            return httpx.Response(200, json=_tree_payload(BASE_TREE_SHA, BASE_FILES))
        if path == f"/repos/octocat/alpha/git/trees/{CANDIDATE_TREE_SHA}":
            files = dict(CANDIDATE_FILES)
            if self.bad_candidate_tree:
                files["README.md"] = b"unverified extra edit\n"
            return httpx.Response(
                200, json=_tree_payload(CANDIDATE_TREE_SHA, files)
            )
        for source_path, content in BASE_FILES.items():
            blob_sha = _git_blob_sha(content)
            if path == f"/repos/octocat/alpha/git/blobs/{blob_sha}":
                return httpx.Response(
                    200,
                    json={
                        "sha": blob_sha,
                        "encoding": "base64",
                        "content": base64.b64encode(content).decode("ascii"),
                    },
                )
        if path == "/repos/octocat/alpha/git/blobs" and request.method == "POST":
            payload = json.loads(request.content)
            assert payload["encoding"] == "base64"
            content = base64.b64decode(payload["content"], validate=True)
            self.uploaded_blobs.append(content)
            return httpx.Response(201, json={"sha": _git_blob_sha(content)})
        if path == "/repos/octocat/alpha/git/trees" and request.method == "POST":
            payload = json.loads(request.content)
            assert payload["base_tree"] == BASE_TREE_SHA
            assert {
                item["path"]: item["sha"] for item in payload["tree"]
            } == {
                name: _git_blob_sha(content)
                for name, content in CANDIDATE_FILES.items()
            }
            return httpx.Response(201, json={"sha": CANDIDATE_TREE_SHA})
        if path == "/repos/octocat/alpha/git/commits" and request.method == "POST":
            payload = json.loads(request.content)
            assert payload["tree"] == CANDIDATE_TREE_SHA
            assert payload["parents"] == [BASE_SHA]
            return httpx.Response(201, json={"sha": COMMIT_SHA})
        if path == "/repos/octocat/alpha/git/refs" and request.method == "POST":
            payload = json.loads(request.content)
            assert payload["sha"] == COMMIT_SHA
            self.branch = payload["ref"].removeprefix("refs/heads/")
            self.ref_posts += 1
            return httpx.Response(
                201,
                json={
                    "ref": payload["ref"],
                    "object": {"type": "commit", "sha": COMMIT_SHA},
                },
            )
        if path == "/repos/octocat/alpha/pulls" and request.method == "GET":
            return httpx.Response(200, json=[self.pr] if self.pr else [])
        if path == "/repos/octocat/alpha/pulls" and request.method == "POST":
            payload = json.loads(request.content)
            assert payload["draft"] is True
            assert payload["maintainer_can_modify"] is False
            assert payload["base"] == "main"
            assert payload["head"] == self.branch
            self.pull_posts += 1
            self.pr = {
                "id": 9100,
                "number": 23,
                "html_url": "https://github.com/octocat/alpha/pull/23",
                "state": "open",
                "draft": True,
                "merged_at": None,
                "body": payload["body"],
                "head": {
                    "ref": self.branch,
                    "sha": COMMIT_SHA,
                    "repo": {"id": 101},
                },
                "base": {"ref": "main", "sha": BASE_SHA, "repo": {"id": 101}},
            }
            if self.ambiguous_pull:
                return httpx.Response(500, json={"message": "response lost"})
            return httpx.Response(201, json=self.pr)
        raise AssertionError(f"Unexpected GitHub request: {request.method} {request.url}")


class _ConcurrentDraftPullTransport(_DraftPullTransport):
    """Force two distinct runs through commit creation before either can publish."""

    def __init__(self) -> None:
        super().__init__()
        self.commit_payloads: list[dict[str, object]] = []
        self._commits_arrived = asyncio.Event()

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/repos/octocat/alpha/git/commits" and request.method == "POST":
            self.requests.append((request.method, path))
            payload = json.loads(request.content)
            self.commit_payloads.append(payload)
            if len(self.commit_payloads) == 2:
                self._commits_arrived.set()
            await asyncio.wait_for(self._commits_arrived.wait(), timeout=2)
            return httpx.Response(201, json={"sha": COMMIT_SHA})
        if path == "/repos/octocat/alpha/git/refs" and request.method == "POST":
            self.requests.append((request.method, path))
            payload = json.loads(request.content)
            branch = payload["ref"].removeprefix("refs/heads/")
            if self.branch is not None:
                return httpx.Response(422, json={"message": "Reference already exists"})
            assert payload["sha"] == COMMIT_SHA
            self.branch = branch
            self.ref_posts += 1
            return httpx.Response(
                201,
                json={
                    "ref": payload["ref"],
                    "object": {"type": "commit", "sha": COMMIT_SHA},
                },
            )
        if path == "/repos/octocat/alpha/pulls" and request.method == "POST":
            self.requests.append((request.method, path))
            payload = json.loads(request.content)
            if self.pr is not None:
                return httpx.Response(422, json={"message": "Pull request exists"})
            self.pull_posts += 1
            self.pr = {
                "id": 9100,
                "number": 23,
                "html_url": "https://github.com/octocat/alpha/pull/23",
                "state": "open",
                "draft": True,
                "merged_at": None,
                "body": payload["body"],
                "head": {
                    "ref": self.branch,
                    "sha": COMMIT_SHA,
                    "repo": {"id": 101},
                },
                "base": {
                    "ref": "main",
                    "sha": BASE_SHA,
                    "repo": {"id": 101},
                },
            }
            return httpx.Response(201, json=self.pr)
        return await super().handle_async_request(request)


async def _connect(github: GitHubService):
    install = await github.install_url()
    install_state = parse_qs(urlparse(install.url).query)["state"][0]
    oauth = await github.oauth_url(
        GitHubOAuthStartRequest(
            installation_id=77,
            setup_action="install",
            state=install_state,
        )
    )
    state = parse_qs(urlparse(oauth.url).query)["state"][0]
    status = await github.complete_oauth(
        GitHubOAuthCallbackRequest(code="authorization-code", state=state)
    )
    assert status.selected_repository is not None
    return status.selected_repository


def _candidate():
    return SimpleNamespace(
        base_sha=BASE_SHA,
        repository_url="https://github.com/octocat/alpha.git",
        unified_diff_sha256=hashlib.sha256(b"canonical diff").hexdigest(),
        candidate_tree=dict(CANDIDATE_FILES),
        candidate_hashes={
            path: hashlib.sha256(content).hexdigest()
            for path, content in CANDIDATE_FILES.items()
        },
        preimage_hashes={
            path: hashlib.sha256(content).hexdigest()
            for path, content in BASE_FILES.items()
        },
    )


def _verified_run_and_action(configured, github, repository):
    run = AuditService(settings=configured, github_service=github)._new_run(
        "verified-pr-run-01", repository
    )
    run.verification = VerificationReceipt(
        verifier="Cloud Build isolated verifier",
        baseline_control=VerificationResult.FAIL,
        candidate_control=VerificationResult.PASS,
        regression_suite=VerificationResult.PASS,
        exact_tree_verified=True,
        isolated=True,
        publishable=True,
        detail="Exact candidate bytes passed fail-before/pass-after verification",
    )
    candidate = _candidate()
    run.verification.checkpoint_artifact_binding(
        VerificationArtifactBinding.create(
            repository_url=candidate.repository_url,
            base_sha=candidate.base_sha,
            unified_diff_sha256=candidate.unified_diff_sha256,
            preimage_hashes=candidate.preimage_hashes,
            candidate_hashes=candidate.candidate_hashes,
            build_id="build-1",
            build_name="projects/test/locations/global/builds/build-1",
            log_url="https://console.cloud.google.com/cloud-build/builds/build-1",
        )
    )
    action = PlannedAction(
        id=f"{run.id}:pull_request",
        kind=ActionKind.PULL_REQUEST,
        state=ActionState.READY,
        title="Delete the orphaned analytics profile",
        verified=True,
    )
    return run, action


@pytest.mark.asyncio
async def test_publishes_exact_bytes_with_minimum_pr_permissions_and_reconciles(
    settings,
) -> None:
    transport = _DraftPullTransport()
    configured = _github_settings(settings)
    github = GitHubService(configured, transport=transport)
    repository = await _connect(github)
    run, action = _verified_run_and_action(configured, github, repository)

    receipt = await github.publish_draft_pull_request(run, action, _candidate())

    assert transport.token_payloads[-1] == {
        "repository_ids": [101],
        "permissions": {"contents": "write", "pull_requests": "write"},
    }
    assert transport.uploaded_blobs == [
        CANDIDATE_FILES[STORE_PATH],
        CANDIDATE_FILES[TEST_PATH],
    ]
    assert receipt.url == "https://github.com/octocat/alpha/pull/23"
    assert receipt.base_sha == BASE_SHA
    assert receipt.tree_sha == CANDIDATE_TREE_SHA
    assert receipt.head_sha == COMMIT_SHA
    assert receipt.branch.startswith("ipromise/promise-drift-")
    assert receipt.reconciled is False
    assert transport.ref_posts == 1
    assert transport.pull_posts == 1
    assert transport.pr is not None
    assert "<!-- ipromise-draft-pr:v1:" in str(transport.pr["body"])
    assert "This is a draft only" in str(transport.pr["body"])
    assert not any(
        method in {"PATCH", "PUT", "DELETE"} or path.endswith("/merge")
        for method, path in transport.requests
    )

    reconciled = await github.publish_draft_pull_request(run, action, _candidate())

    assert reconciled.url == receipt.url
    assert reconciled.reconciled is True
    assert transport.ref_posts == 1
    assert transport.pull_posts == 1
    assert len(transport.uploaded_blobs) == 2


@pytest.mark.asyncio
async def test_reconciles_ambiguous_pr_response_without_duplicate(settings) -> None:
    transport = _DraftPullTransport()
    transport.ambiguous_pull = True
    configured = _github_settings(settings)
    github = GitHubService(configured, transport=transport)
    repository = await _connect(github)
    run, action = _verified_run_and_action(configured, github, repository)

    receipt = await github.publish_draft_pull_request(run, action, _candidate())

    assert receipt.reconciled is True
    assert receipt.number == 23
    assert transport.pull_posts == 1


@pytest.mark.asyncio
async def test_rejects_base_drift_before_any_git_or_pr_write(settings) -> None:
    transport = _DraftPullTransport()
    configured = _github_settings(settings)
    github = GitHubService(configured, transport=transport)
    repository = await _connect(github)
    run, action = _verified_run_and_action(configured, github, repository)
    transport.base_ref_sha = "9" * 40

    with pytest.raises(GitHubPublicationRejected, match="moved away"):
        await github.publish_draft_pull_request(run, action, _candidate())

    assert transport.uploaded_blobs == []
    assert transport.ref_posts == 0
    assert transport.pull_posts == 0


@pytest.mark.asyncio
async def test_rejects_candidate_hash_mismatch_before_remote_publication(settings) -> None:
    transport = _DraftPullTransport()
    configured = _github_settings(settings)
    github = GitHubService(configured, transport=transport)
    repository = await _connect(github)
    run, action = _verified_run_and_action(configured, github, repository)
    candidate = _candidate()
    candidate.candidate_hashes[STORE_PATH] = "0" * 64
    request_count = len(transport.requests)

    with pytest.raises(GitHubPublicationRejected, match="verifier SHA-256"):
        await github.publish_draft_pull_request(run, action, candidate)

    assert len(transport.requests) == request_count
    assert transport.ref_posts == 0
    assert transport.pull_posts == 0


@pytest.mark.asyncio
async def test_rejects_candidate_that_does_not_match_receipt_binding(settings) -> None:
    transport = _DraftPullTransport()
    configured = _github_settings(settings)
    github = GitHubService(configured, transport=transport)
    repository = await _connect(github)
    run, action = _verified_run_and_action(configured, github, repository)
    candidate = _candidate()
    candidate.unified_diff_sha256 = hashlib.sha256(b"different diff").hexdigest()
    request_count = len(transport.requests)

    with pytest.raises(GitHubPublicationRejected, match="artifact binding"):
        await github.publish_draft_pull_request(run, action, candidate)

    assert len(transport.requests) == request_count
    assert transport.ref_posts == 0
    assert transport.pull_posts == 0


@pytest.mark.asyncio
async def test_reconciles_same_exact_candidate_across_distinct_runs(settings) -> None:
    transport = _DraftPullTransport()
    configured = _github_settings(settings)
    github = GitHubService(configured, transport=transport)
    repository = await _connect(github)
    first_run, first_action = _verified_run_and_action(configured, github, repository)

    first = await github.publish_draft_pull_request(
        first_run, first_action, _candidate()
    )
    second_run, second_action = _verified_run_and_action(
        configured, github, repository
    )
    second_run.id = "run_distinct_scheduled_execution"
    second_action.id = f"{second_run.id}:pull_request"
    second = await github.publish_draft_pull_request(
        second_run, second_action, _candidate()
    )

    assert second.url == first.url
    assert second.branch == first.branch
    assert second.reconciled is True
    assert transport.ref_posts == 1
    assert transport.pull_posts == 1


@pytest.mark.asyncio
async def test_concurrent_distinct_runs_create_one_deterministic_pr(settings) -> None:
    transport = _ConcurrentDraftPullTransport()
    configured = _github_settings(settings)
    github = GitHubService(configured, transport=transport)
    repository = await _connect(github)
    first_run, first_action = _verified_run_and_action(configured, github, repository)
    second_run, second_action = _verified_run_and_action(
        configured, github, repository
    )
    second_run.id = "run_concurrent_distinct_execution"
    second_action.id = f"{second_run.id}:pull_request"

    first, second = await asyncio.gather(
        github.publish_draft_pull_request(first_run, first_action, _candidate()),
        github.publish_draft_pull_request(second_run, second_action, _candidate()),
    )

    assert first.url == second.url
    assert first.branch == second.branch
    assert transport.commit_payloads[0] == transport.commit_payloads[1]
    assert "Run:" not in str(transport.commit_payloads[0]["message"])
    assert transport.commit_payloads[0]["author"] == {
        "name": "iPromise",
        "email": "bot@ipromise.dev",
        "date": "2026-08-18T00:00:00Z",
    }
    assert transport.ref_posts == 1
    assert transport.pull_posts == 1


@pytest.mark.asyncio
async def test_captures_exact_allowlisted_source_at_immutable_base(settings) -> None:
    transport = _DraftPullTransport()
    configured = _github_settings(settings)
    github = GitHubService(configured, transport=transport)
    repository = await _connect(github)

    snapshot = await github.capture_repository_files(
        repository,
        tuple(sorted(BASE_FILES)),
    )

    assert snapshot.base_sha == BASE_SHA
    assert snapshot.preimages == {
        path: BASE_FILES[path] for path in sorted(BASE_FILES)
    }
    assert transport.token_payloads[-1] == {
        "repository_ids": [101],
        "permissions": {"contents": "read"},
    }


@pytest.mark.asyncio
async def test_rejects_resulting_tree_with_any_unverified_extra_change(settings) -> None:
    transport = _DraftPullTransport()
    transport.bad_candidate_tree = True
    configured = _github_settings(settings)
    github = GitHubService(configured, transport=transport)
    repository = await _connect(github)
    run, action = _verified_run_and_action(configured, github, repository)

    with pytest.raises(GitHubPublicationRejected, match="resulting Git tree"):
        await github.publish_draft_pull_request(run, action, _candidate())

    assert transport.ref_posts == 0
    assert transport.pull_posts == 0
