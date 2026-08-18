"""Least-privilege GitHub App connection and idempotent publication."""

from __future__ import annotations

import asyncio
import base64
import binascii
import hashlib
import html
import json
import re
import secrets
import time
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol
from urllib.parse import quote, urlencode

import httpx

from .config import Settings
from .models import (
    ActionKind,
    ActionState,
    AuditRun,
    GitHubInstallUrl,
    GitHubIntegrationStatus,
    GitHubOAuthCallbackRequest,
    GitHubOAuthStartRequest,
    GitHubRepository,
    PlannedAction,
    VerificationResult,
)


GITHUB_API_VERSION = "2026-03-10"
CONNECTION_TTL_SECONDS = 10 * 60
ISSUE_RECONCILIATION_DELAYS_SECONDS = (0.0, 0.1, 0.25)
AMBIGUOUS_WRITE_STATUSES = {408, 425, 429, 500, 502, 503, 504}
ISSUE_INTENT_LEASE_SECONDS = 5 * 60
ISSUE_INTENT_WAIT_SECONDS = 30.0
ISSUE_INTENT_POLL_SECONDS = 0.05
PULL_REQUEST_RECONCILIATION_DELAYS_SECONDS = (0.0, 0.1, 0.25)
GIT_OBJECT_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
ALLOWED_BLOB_MODES = {"100644", "100755"}
MAX_CANDIDATE_BLOB_BYTES = 10 * 1024 * 1024
MAX_SOURCE_BLOB_BYTES = 64 * 1024
# Versioned with this hackathon's locked remediation template. It is deliberately
# run-independent so identical scheduled findings create one Git object.
DETERMINISTIC_COMMIT_TIMESTAMP = "2026-08-18T00:00:00Z"


def finding_fingerprint(run: AuditRun, repository: GitHubRepository) -> str:
    """Return the stable identity of one repository-scoped audit finding.

    GitHub reconciliation must survive distinct scheduled runs, so the digest is
    derived only from the immutable source snapshot, bound control, scoped
    semantic evidence, verdict, and GitHub repository ID. Volatile execution
    data (run/idempotency IDs, timestamps, synthetic subject IDs in ``scope``,
    and artifact locations) is deliberately excluded.

    This fingerprint is only the remote finding identity. ``PlannedAction.id``
    remains run-scoped, preserving the per-run lease and checkpoint semantics in
    ``AuditService``.
    """

    evidence = sorted(
        (
            {
                "id": item.id,
                "label": item.label,
                "expected": item.expected,
                "observed": item.observed,
                "result": item.result.value,
            }
            for item in run.evidence
        ),
        key=lambda item: json.dumps(
            item, ensure_ascii=False, separators=(",", ":"), sort_keys=True
        ),
    )
    finding = {
        "schema": "ipromise.github-issue-finding.v1",
        "repository": {"id": repository.id},
        "source": {
            "url": run.claim.source_url,
            "contentHash": run.claim.content_hash,
            "exactQuote": run.claim.exact_quote,
        },
        "control": {
            "id": run.claim.control_id,
            "verdict": run.verdict.value,
        },
        "evidence": evidence,
    }
    canonical = json.dumps(
        finding, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class VerifiedCandidateInput(Protocol):
    """Structural boundary shared with the separate verifier.

    The publisher intentionally does not import the verifier implementation.
    It snapshots these fields before its first await, verifies every SHA-256,
    and uploads exactly the supplied byte strings.
    """

    @property
    def base_sha(self) -> str: ...

    @property
    def repository_url(self) -> str: ...

    @property
    def unified_diff_sha256(self) -> str: ...

    @property
    def candidate_tree(self) -> Mapping[str, bytes]: ...

    @property
    def candidate_hashes(self) -> Mapping[str, str]: ...

    @property
    def preimage_hashes(self) -> Mapping[str, str]: ...


@dataclass(frozen=True, slots=True)
class _CandidateSnapshot:
    base_sha: str
    repository_url: str
    unified_diff_sha256: str
    files: tuple[tuple[str, bytes, str, str], ...]


@dataclass(frozen=True, slots=True)
class PublishedPullRequest:
    """A receipt whose Git object identities can be independently checked."""

    url: str
    number: int
    remote_id: int
    branch: str
    head_sha: str
    base_sha: str
    tree_sha: str
    reconciled: bool = False


@dataclass(frozen=True, slots=True)
class RepositorySourceSnapshot:
    """Immutable base commit and exact allowlisted repository preimages."""

    base_sha: str
    files: tuple[tuple[str, bytes], ...]

    @property
    def preimages(self) -> dict[str, bytes]:
        return dict(self.files)


def pull_request_fingerprint(
    repository: GitHubRepository,
    candidate: VerifiedCandidateInput,
) -> str:
    """Return one cross-run identity for the exact repository repair intent."""

    snapshot = _snapshot_candidate(candidate)
    return _pull_request_fingerprint(repository, snapshot)


class GitHubIntegrationError(RuntimeError):
    """A safe, user-facing integration failure."""


class GitHubNotConfigured(GitHubIntegrationError):
    pass


class GitHubAuthorizationError(GitHubIntegrationError):
    pass


class GitHubPublishUncertain(GitHubIntegrationError):
    """The remote outcome could not be proven; callers must not blindly retry."""


class GitHubPublicationRejected(GitHubIntegrationError):
    """A fail-closed publication refusal with a proven safety reason."""


@dataclass(frozen=True, slots=True)
class _PendingOAuth:
    installation_id: int
    verifier: str
    expires_at: float


@dataclass(frozen=True, slots=True)
class _Connection:
    installation_id: int
    account_login: str
    repositories: tuple[GitHubRepository, ...]
    selected_repository_id: int | None


@dataclass(frozen=True, slots=True)
class PublishedIssue:
    url: str
    number: int
    remote_id: int
    reconciled: bool = False


@dataclass(frozen=True, slots=True)
class _IssueIntentClaim:
    acquired: bool
    receipt: PublishedIssue | None = None


@dataclass(frozen=True, slots=True)
class _IssueIntentRecord:
    owner: str | None
    expires_at: float
    receipt: PublishedIssue | None = None


def _as_reconciled(receipt: PublishedIssue) -> PublishedIssue:
    return PublishedIssue(
        url=receipt.url,
        number=receipt.number,
        remote_id=receipt.remote_id,
        reconciled=True,
    )


class InMemoryGitHubStore:
    """Small local store behind an interface that can be replaced by Firestore."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._install_states: dict[str, float] = {}
        self._oauth_states: dict[str, _PendingOAuth] = {}
        self._connection: _Connection | None = None
        self._issue_intents: dict[str, _IssueIntentRecord] = {}

    async def add_install_state(self, state: str, expires_at: float) -> None:
        async with self._lock:
            self._install_states[state] = expires_at

    async def consume_install_state(self, state: str, now: float) -> bool:
        async with self._lock:
            expires_at = self._install_states.pop(state, None)
            self._drop_expired(now)
            return expires_at is not None and expires_at >= now

    async def add_oauth_state(self, state: str, pending: _PendingOAuth) -> None:
        async with self._lock:
            self._oauth_states[state] = pending

    async def consume_oauth_state(
        self, state: str, now: float
    ) -> _PendingOAuth | None:
        async with self._lock:
            pending = self._oauth_states.pop(state, None)
            self._drop_expired(now)
            if pending is None or pending.expires_at < now:
                return None
            return pending

    async def save_connection(self, connection: _Connection) -> None:
        async with self._lock:
            self._connection = connection

    async def connection(self) -> _Connection | None:
        async with self._lock:
            return self._connection

    async def select(self, repository_id: int) -> _Connection:
        async with self._lock:
            if self._connection is None:
                raise GitHubAuthorizationError("Connect GitHub before selecting a repository")
            repository = next(
                (
                    item
                    for item in self._connection.repositories
                    if item.id == repository_id
                ),
                None,
            )
            if repository is None:
                raise GitHubAuthorizationError(
                    "The repository is not available to this verified installation"
                )
            if repository.archived:
                raise GitHubAuthorizationError("Archived repositories cannot be selected")
            self._connection = _Connection(
                installation_id=self._connection.installation_id,
                account_login=self._connection.account_login,
                repositories=self._connection.repositories,
                selected_repository_id=repository_id,
            )
            return self._connection

    async def disconnect(self) -> None:
        async with self._lock:
            self._connection = None

    async def claim_issue_intent(
        self,
        fingerprint: str,
        owner: str,
        *,
        lease_seconds: int,
    ) -> _IssueIntentClaim:
        """Atomically claim one cross-run GitHub finding publication."""

        async with self._lock:
            now = time.time()
            current = self._issue_intents.get(fingerprint)
            if current is not None and current.receipt is not None:
                return _IssueIntentClaim(
                    acquired=False,
                    receipt=_as_reconciled(current.receipt),
                )
            if (
                current is not None
                and current.owner != owner
                and current.expires_at > now
            ):
                return _IssueIntentClaim(acquired=False)
            self._issue_intents[fingerprint] = _IssueIntentRecord(
                owner=owner,
                expires_at=now + lease_seconds,
            )
            return _IssueIntentClaim(acquired=True)

    async def complete_issue_intent(
        self,
        fingerprint: str,
        owner: str,
        receipt: PublishedIssue,
    ) -> PublishedIssue:
        """Persist a verified receipt; the first completed receipt wins."""

        async with self._lock:
            current = self._issue_intents.get(fingerprint)
            if current is not None and current.receipt is not None:
                return _as_reconciled(current.receipt)
            if current is None or current.owner != owner:
                raise GitHubPublishUncertain(
                    "GitHub issue intent ownership changed before completion"
                )
            self._issue_intents[fingerprint] = _IssueIntentRecord(
                owner=None,
                expires_at=0,
                receipt=receipt,
            )
            return receipt

    async def release_issue_intent(
        self, fingerprint: str, owner: str
    ) -> None:
        """Release only this worker's unfinished claim after a safe stop."""

        async with self._lock:
            current = self._issue_intents.get(fingerprint)
            if (
                current is not None
                and current.receipt is None
                and current.owner == owner
            ):
                self._issue_intents.pop(fingerprint, None)

    def _drop_expired(self, now: float) -> None:
        self._install_states = {
            state: expiry
            for state, expiry in self._install_states.items()
            if expiry >= now
        }
        self._oauth_states = {
            state: pending
            for state, pending in self._oauth_states.items()
            if pending.expires_at >= now
        }


class FirestoreGitHubStore:
    """Durable OAuth handoff and repository selection for Cloud Run."""

    def __init__(self, *, database: str = "(default)", client: Any = None) -> None:
        try:
            from google.cloud import firestore_v1
        except ImportError as exc:  # pragma: no cover - packaging guard
            raise RuntimeError(
                "Install the agent's google dependency extra to use Firestore"
            ) from exc
        self._firestore = firestore_v1
        self._client = client or firestore_v1.AsyncClient(database=database)
        self._states = self._client.collection("github_oauth_states")
        self._connections = self._client.collection("github_connections")
        self._active = self._connections.document("active")
        self._issue_intents = self._client.collection("github_issue_intents")

    @staticmethod
    def _state_id(state: str) -> str:
        return hashlib.sha256(state.encode()).hexdigest()

    async def add_install_state(self, state: str, expires_at: float) -> None:
        await self._states.document(self._state_id(state)).set(
            {"kind": "install", "expiresAt": expires_at}
        )

    async def consume_install_state(self, state: str, now: float) -> bool:
        reference = self._states.document(self._state_id(state))
        transaction = self._client.transaction()

        @self._firestore.async_transactional
        async def consume(transaction):
            snapshot = await reference.get(transaction=transaction)
            if not snapshot.exists:
                return False
            payload = snapshot.to_dict() or {}
            transaction.delete(reference)
            return (
                payload.get("kind") == "install"
                and float(payload.get("expiresAt", 0)) >= now
            )

        return await consume(transaction)

    async def add_oauth_state(self, state: str, pending: _PendingOAuth) -> None:
        await self._states.document(self._state_id(state)).set(
            {
                "kind": "oauth",
                "installationId": pending.installation_id,
                "verifier": pending.verifier,
                "expiresAt": pending.expires_at,
            }
        )

    async def consume_oauth_state(
        self, state: str, now: float
    ) -> _PendingOAuth | None:
        reference = self._states.document(self._state_id(state))
        transaction = self._client.transaction()

        @self._firestore.async_transactional
        async def consume(transaction):
            snapshot = await reference.get(transaction=transaction)
            if not snapshot.exists:
                return None
            payload = snapshot.to_dict() or {}
            transaction.delete(reference)
            if (
                payload.get("kind") != "oauth"
                or float(payload.get("expiresAt", 0)) < now
            ):
                return None
            return _PendingOAuth(
                installation_id=int(payload["installationId"]),
                verifier=str(payload["verifier"]),
                expires_at=float(payload["expiresAt"]),
            )

        return await consume(transaction)

    async def save_connection(self, connection: _Connection) -> None:
        await self._active.set(self._encode_connection(connection))

    async def connection(self) -> _Connection | None:
        snapshot = await self._active.get()
        return self._decode_connection(snapshot.to_dict()) if snapshot.exists else None

    async def select(self, repository_id: int) -> _Connection:
        transaction = self._client.transaction()

        @self._firestore.async_transactional
        async def select_in_transaction(transaction):
            snapshot = await self._active.get(transaction=transaction)
            if not snapshot.exists:
                raise GitHubAuthorizationError(
                    "Connect GitHub before selecting a repository"
                )
            connection = self._decode_connection(snapshot.to_dict())
            repository = next(
                (
                    item
                    for item in connection.repositories
                    if item.id == repository_id
                ),
                None,
            )
            if repository is None:
                raise GitHubAuthorizationError(
                    "The repository is not available to this verified installation"
                )
            if repository.archived:
                raise GitHubAuthorizationError("Archived repositories cannot be selected")
            selected = _Connection(
                installation_id=connection.installation_id,
                account_login=connection.account_login,
                repositories=connection.repositories,
                selected_repository_id=repository_id,
            )
            transaction.set(self._active, self._encode_connection(selected))
            return selected

        return await select_in_transaction(transaction)

    async def disconnect(self) -> None:
        await self._active.delete()

    async def claim_issue_intent(
        self,
        fingerprint: str,
        owner: str,
        *,
        lease_seconds: int,
    ) -> _IssueIntentClaim:
        """Atomically claim a finding across every Cloud Run instance."""

        reference = self._issue_intents.document(fingerprint)
        transaction = self._client.transaction()
        now = datetime.now(UTC)
        expires_at = now + timedelta(seconds=lease_seconds)

        @self._firestore.async_transactional
        async def claim_in_transaction(transaction):
            snapshot = await reference.get(transaction=transaction)
            document = snapshot.to_dict() or {} if snapshot.exists else {}
            receipt = self._decode_issue_receipt(document.get("receipt"))
            if document.get("status") == "COMPLETE" and receipt is not None:
                return _IssueIntentClaim(
                    acquired=False,
                    receipt=_as_reconciled(receipt),
                )
            current_owner = document.get("owner")
            current_expiry = document.get("leaseExpiresAt")
            if (
                current_owner != owner
                and isinstance(current_expiry, datetime)
                and current_expiry > now
            ):
                return _IssueIntentClaim(acquired=False)
            transaction.set(
                reference,
                {
                    "fingerprint": fingerprint,
                    "status": "IN_PROGRESS",
                    "owner": owner,
                    "leaseExpiresAt": expires_at,
                    "updatedAt": now,
                },
            )
            return _IssueIntentClaim(acquired=True)

        return await claim_in_transaction(transaction)

    async def complete_issue_intent(
        self,
        fingerprint: str,
        owner: str,
        receipt: PublishedIssue,
    ) -> PublishedIssue:
        """Persist the first proven remote receipt as the durable winner."""

        reference = self._issue_intents.document(fingerprint)
        transaction = self._client.transaction()
        now = datetime.now(UTC)

        @self._firestore.async_transactional
        async def complete_in_transaction(transaction):
            snapshot = await reference.get(transaction=transaction)
            document = snapshot.to_dict() or {} if snapshot.exists else {}
            existing = self._decode_issue_receipt(document.get("receipt"))
            if document.get("status") == "COMPLETE" and existing is not None:
                return _as_reconciled(existing)
            if document.get("owner") != owner:
                raise GitHubPublishUncertain(
                    "GitHub issue intent ownership changed before completion"
                )
            transaction.set(
                reference,
                {
                    "fingerprint": fingerprint,
                    "status": "COMPLETE",
                    "owner": None,
                    "leaseExpiresAt": now,
                    "receipt": self._encode_issue_receipt(receipt),
                    "completedBy": owner,
                    "updatedAt": now,
                },
            )
            return receipt

        return await complete_in_transaction(transaction)

    async def release_issue_intent(
        self, fingerprint: str, owner: str
    ) -> None:
        """Release an unfinished claim without erasing a completed receipt."""

        reference = self._issue_intents.document(fingerprint)
        transaction = self._client.transaction()

        @self._firestore.async_transactional
        async def release_in_transaction(transaction):
            snapshot = await reference.get(transaction=transaction)
            if not snapshot.exists:
                return
            document = snapshot.to_dict() or {}
            if document.get("status") != "COMPLETE" and document.get("owner") == owner:
                transaction.delete(reference)

        await release_in_transaction(transaction)

    @staticmethod
    def _encode_issue_receipt(receipt: PublishedIssue) -> dict[str, Any]:
        return {
            "url": receipt.url,
            "number": receipt.number,
            "remoteId": receipt.remote_id,
        }

    @staticmethod
    def _decode_issue_receipt(payload: Any) -> PublishedIssue | None:
        if not isinstance(payload, dict):
            return None
        try:
            return PublishedIssue(
                url=str(payload["url"]),
                number=int(payload["number"]),
                remote_id=int(payload["remoteId"]),
            )
        except (KeyError, TypeError, ValueError):
            return None

    @staticmethod
    def _encode_connection(connection: _Connection) -> dict[str, Any]:
        return {
            "installationId": connection.installation_id,
            "accountLogin": connection.account_login,
            "repositories": [
                item.model_dump(mode="json", by_alias=True)
                for item in connection.repositories
            ],
            "selectedRepositoryId": connection.selected_repository_id,
            "updatedAt": datetime.now(UTC),
        }

    @staticmethod
    def _decode_connection(document: dict[str, Any] | None) -> _Connection:
        if not document:
            raise GitHubAuthorizationError("The GitHub connection record is invalid")
        try:
            return _Connection(
                installation_id=int(document["installationId"]),
                account_login=str(document["accountLogin"]),
                repositories=tuple(
                    GitHubRepository.model_validate(item)
                    for item in document.get("repositories", [])
                ),
                selected_repository_id=(
                    int(document["selectedRepositoryId"])
                    if document.get("selectedRepositoryId") is not None
                    else None
                ),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise GitHubAuthorizationError(
                "The GitHub connection record is invalid"
            ) from exc


class GitHubService:
    def __init__(
        self,
        settings: Settings,
        *,
        store: InMemoryGitHubStore | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.settings = settings
        if store is not None:
            self.store = store
        elif settings.state_backend == "firestore":
            self.store = FirestoreGitHubStore(database=settings.firestore_database)
        else:
            self.store = InMemoryGitHubStore()
        self.transport = transport

    async def status(self) -> GitHubIntegrationStatus:
        connection = await self.store.connection()
        repositories = list(connection.repositories) if connection else []
        selected = self._selected_from(connection)
        return GitHubIntegrationStatus(
            configured=self.settings.github_configured,
            connected=connection is not None,
            actions_enabled=self.settings.github_actions_enabled,
            account_login=connection.account_login if connection else None,
            repositories=repositories,
            selected_repository=selected,
        )

    async def selected_repository(self) -> GitHubRepository | None:
        return self._selected_from(await self.store.connection())

    async def capture_repository_files(
        self,
        target: GitHubRepository,
        paths: tuple[str, ...],
    ) -> RepositorySourceSnapshot:
        """Read exact blobs at one immutable default-branch commit.

        This is a read-only preparation boundary. The caller supplies the
        remediation allowlist; arbitrary paths, tree entries, and oversized
        blobs are rejected before candidate construction.
        """

        self._require_configured()
        if (
            not paths
            or len(paths) > 16
            or len(paths) != len(set(paths))
            or any(not _safe_candidate_path(path) for path in paths)
        ):
            raise GitHubPublicationRejected(
                "Repository source capture requires unique safe allowlisted paths"
            )
        connection = await self.store.connection()
        repository = self._bound_repository(connection, target)
        await self._validate_installation_identity(connection, repository)
        token = await self._installation_token(
            connection,
            repository,
            permissions={"contents": "read"},
        )
        await self._validate_token_repository(repository, token)
        base_sha = await self._get_ref_sha(
            repository,
            token,
            f"heads/{repository.default_branch}",
        )
        if base_sha is None:
            raise GitHubPublicationRejected(
                "The selected repository default branch has no commit"
            )
        tree_sha = await self._commit_tree_sha(
            repository,
            token,
            base_sha,
            expected_parent=None,
        )
        leaves = await self._tree_leaves(repository, token, tree_sha)
        files: list[tuple[str, bytes]] = []
        for path in paths:
            entry = leaves.get(path)
            if entry is None:
                raise GitHubPublicationRejected(
                    f"Approved remediation source is absent: {path}"
                )
            mode, object_type, blob_sha = entry
            if (
                mode not in ALLOWED_BLOB_MODES
                or object_type != "blob"
                or GIT_OBJECT_SHA_PATTERN.fullmatch(blob_sha) is None
            ):
                raise GitHubPublicationRejected(
                    f"Approved remediation source is not a regular blob: {path}"
                )
            files.append(
                (path, await self._read_exact_source_blob(repository, token, blob_sha))
            )
        return RepositorySourceSnapshot(base_sha=base_sha, files=tuple(files))

    async def install_url(self) -> GitHubInstallUrl:
        self._require_configured()
        state = secrets.token_urlsafe(32)
        await self.store.add_install_state(
            state, time.time() + CONNECTION_TTL_SECONDS
        )
        query = urlencode({"state": state})
        return GitHubInstallUrl(
            url=(
                f"{self.settings.github_web_url}/apps/"
                f"{quote(self.settings.github_app_slug or '', safe='')}/installations/new?{query}"
            )
        )

    async def oauth_url(self, request: GitHubOAuthStartRequest) -> GitHubInstallUrl:
        self._require_configured()
        if request.setup_action not in {"install", "update"}:
            raise GitHubAuthorizationError("Unsupported GitHub setup action")
        if not await self.store.consume_install_state(request.state, time.time()):
            raise GitHubAuthorizationError("GitHub connection state is invalid or expired")

        state = secrets.token_urlsafe(32)
        verifier = secrets.token_urlsafe(64)
        challenge = _base64url(hashlib.sha256(verifier.encode()).digest())
        await self.store.add_oauth_state(
            state,
            _PendingOAuth(
                installation_id=request.installation_id,
                verifier=verifier,
                expires_at=time.time() + CONNECTION_TTL_SECONDS,
            ),
        )
        query = urlencode(
            {
                "client_id": self.settings.github_app_client_id or "",
                "redirect_uri": self._callback_url,
                "state": state,
                "code_challenge": challenge,
                "code_challenge_method": "S256",
            }
        )
        return GitHubInstallUrl(
            url=f"{self.settings.github_web_url}/login/oauth/authorize?{query}"
        )

    async def complete_oauth(
        self, request: GitHubOAuthCallbackRequest
    ) -> GitHubIntegrationStatus:
        self._require_configured()
        pending = await self.store.consume_oauth_state(request.state, time.time())
        if pending is None:
            raise GitHubAuthorizationError("GitHub OAuth state is invalid or expired")

        async with self._client() as client:
            token_response = await client.post(
                f"{self.settings.github_web_url}/login/oauth/access_token",
                headers={"Accept": "application/json"},
                data={
                    "client_id": self.settings.github_app_client_id,
                    "client_secret": self.settings.github_app_client_secret,
                    "code": request.code,
                    "redirect_uri": self._callback_url,
                    "code_verifier": pending.verifier,
                },
            )
            self._require_status(token_response, {200}, "GitHub OAuth exchange failed")
            token_body = token_response.json()
            user_token = token_body.get("access_token")
            if not isinstance(user_token, str) or not user_token:
                raise GitHubAuthorizationError("GitHub did not return a user token")

            headers = self._api_headers(user_token)
            installations = await self._paginate(
                client,
                f"{self.settings.github_api_url}/user/installations",
                headers=headers,
                collection_key="installations",
            )
            installation = next(
                (
                    item
                    for item in installations
                    if item.get("id") == pending.installation_id
                    and str(item.get("app_id")) == str(self.settings.github_app_id)
                ),
                None,
            )
            if installation is None or installation.get("suspended_at") is not None:
                raise GitHubAuthorizationError(
                    "The signed-in GitHub user cannot authorize this installation"
                )

            repositories_payload = await self._paginate(
                client,
                (
                    f"{self.settings.github_api_url}/user/installations/"
                    f"{pending.installation_id}/repositories"
                ),
                headers=headers,
                collection_key="repositories",
            )

        repositories = tuple(
            GitHubRepository(
                id=int(item["id"]),
                full_name=str(item["full_name"]),
                default_branch=str(item.get("default_branch") or "main"),
                private=bool(item.get("private", False)),
                archived=bool(item.get("archived", False)),
                html_url=str(item["html_url"]),
            )
            for item in repositories_payload
            if item.get("id") and item.get("full_name") and item.get("html_url")
        )
        if not repositories:
            raise GitHubAuthorizationError(
                "The GitHub App installation has no accessible repositories"
            )
        account = installation.get("account") or {}
        selectable = [item for item in repositories if not item.archived]
        connection = _Connection(
            installation_id=pending.installation_id,
            account_login=str(account.get("login") or "GitHub account"),
            repositories=repositories,
            selected_repository_id=selectable[0].id if len(selectable) == 1 else None,
        )
        await self.store.save_connection(connection)
        return await self.status()

    async def select_repository(self, repository_id: int) -> GitHubIntegrationStatus:
        await self.store.select(repository_id)
        return await self.status()

    async def disconnect(self) -> GitHubIntegrationStatus:
        await self.store.disconnect()
        return await self.status()

    async def publish_issue(
        self, run: AuditRun, action: PlannedAction
    ) -> PublishedIssue:
        if not self.settings.github_actions_enabled:
            raise GitHubNotConfigured("GitHub actions are disabled")
        target = run.repository
        if target is None:
            raise GitHubAuthorizationError("The run has no bound repository target")
        connection = await self.store.connection()
        if connection is None:
            raise GitHubAuthorizationError("The run's repository is no longer connected")
        repository = next(
            (item for item in connection.repositories if item.id == target.id),
            None,
        )
        if repository is None:
            raise GitHubAuthorizationError(
                "The run's repository is not available to the verified installation"
            )
        if repository.archived:
            raise GitHubAuthorizationError("The run's repository is archived")

        fingerprint = finding_fingerprint(run, repository)
        marker = f"<!-- ipromise-finding:v1:{fingerprint} -->"
        owner = f"github_issue_{secrets.token_hex(16)}"
        claim = await self._wait_for_issue_intent(fingerprint, owner)
        if claim.receipt is not None:
            return claim.receipt
        if not claim.acquired:  # defensive invariant; wait returns or raises
            raise GitHubPublishUncertain(
                "GitHub issue publication is still owned by another worker"
            )

        completed = False
        release_claim = True
        try:
            token = await self._installation_token(
                connection,
                repository,
                permissions={"issues": "write"},
            )
            receipt = await self._publish_or_reconcile_issue(
                run=run,
                action=action,
                repository=repository,
                token=token,
                marker=marker,
            )
            try:
                durable = await self.store.complete_issue_intent(
                    fingerprint,
                    owner,
                    receipt,
                )
            except Exception as exc:
                raise GitHubPublishUncertain(
                    "GitHub issue exists but its durable receipt could not be recorded"
                ) from exc
            completed = True
            return durable
        except (GitHubPublishUncertain, asyncio.CancelledError):
            # Preserve the durable exclusion window after an ambiguous write or
            # interrupted worker. A later owner must wait for expiry, then run
            # marker reconciliation before it is allowed to POST.
            release_claim = False
            raise
        finally:
            if not completed and release_claim:
                try:
                    await asyncio.shield(
                        self.store.release_issue_intent(fingerprint, owner)
                    )
                except Exception:
                    # A stale durable lease is safer than an uncoordinated retry;
                    # it expires and the next owner reconciles the remote marker.
                    pass

    async def publish_draft_pull_request(
        self,
        run: AuditRun,
        action: PlannedAction,
        candidate: VerifiedCandidateInput,
    ) -> PublishedPullRequest:
        """Publish one verifier-proven candidate without re-encoding its bytes.

        The run-bound repository, exact base commit, complete resulting Git
        tree, deterministic branch, and draft PR are all checked before a
        receipt is returned. Visible writes are reconciled by immutable
        identities; this method never updates an existing ref, merges a PR, or
        retries a write whose outcome cannot be proven.
        """

        snapshot = _snapshot_candidate(candidate)
        self._require_pull_request_gate(run, action, snapshot)
        target = run.repository
        if target is None:  # guarded above; keeps type narrowing local
            raise GitHubPublicationRejected(
                "The run has no immutable repository target"
            )
        connection = await self.store.connection()
        repository = self._bound_repository(connection, target)
        expected_source = f"{repository.html_url.rstrip('/')}.git"
        if snapshot.repository_url != expected_source:
            raise GitHubPublicationRejected(
                "The verified candidate source repository did not match the run"
            )

        fingerprint = _pull_request_fingerprint(repository, snapshot)
        branch = _pull_request_branch(fingerprint)
        marker = f"<!-- ipromise-draft-pr:v1:{fingerprint} -->"

        await self._validate_installation_identity(connection, repository)
        token = await self._installation_token(
            connection,
            repository,
            permissions={"contents": "write", "pull_requests": "write"},
        )
        await self._validate_token_repository(repository, token)

        # A prior successful call is safe to reconcile even if the default
        # branch subsequently advanced. Its commit still has the exact base as
        # its sole parent and its full tree is verified below.
        existing = await self._find_pull_request(
            repository=repository,
            token=token,
            branch=branch,
            marker=marker,
            snapshot=snapshot,
        )
        if existing is not None:
            return existing

        current_base = await self._get_ref_sha(
            repository,
            token,
            f"heads/{repository.default_branch}",
        )
        if current_base != snapshot.base_sha:
            raise GitHubPublicationRejected(
                "The repository default branch moved away from the verified base SHA"
            )

        candidate_tree_sha = await self._create_candidate_tree(
            repository,
            token,
            snapshot,
        )
        commit_sha = await self._create_candidate_commit(
            repository=repository,
            token=token,
            snapshot=snapshot,
            tree_sha=candidate_tree_sha,
        )

        # Close the time-of-check/time-of-use window before making a ref visible.
        if (
            await self._get_ref_sha(
                repository,
                token,
                f"heads/{repository.default_branch}",
            )
            != snapshot.base_sha
        ):
            raise GitHubPublicationRejected(
                "The repository default branch moved during candidate publication"
            )

        branch_reconciled = await self._create_or_reconcile_branch(
            repository=repository,
            token=token,
            branch=branch,
            commit_sha=commit_sha,
        )

        # A branch is harmless and recoverable; opening a stale PR is not. Fail
        # closed if the base moved after ref creation and leave the exact branch
        # for a later operator to inspect.
        if (
            await self._get_ref_sha(
                repository,
                token,
                f"heads/{repository.default_branch}",
            )
            != snapshot.base_sha
        ):
            raise GitHubPublicationRejected(
                "The repository default branch moved before draft PR creation"
            )

        reconciled_after_ref = await self._find_pull_request(
            repository=repository,
            token=token,
            branch=branch,
            marker=marker,
            snapshot=snapshot,
        )
        if reconciled_after_ref is not None:
            return reconciled_after_ref

        return await self._create_or_reconcile_pull_request(
            run=run,
            action=action,
            repository=repository,
            token=token,
            branch=branch,
            marker=marker,
            snapshot=snapshot,
            tree_sha=candidate_tree_sha,
            commit_sha=commit_sha,
            prior_reconciliation=branch_reconciled,
        )

    def _require_pull_request_gate(
        self,
        run: AuditRun,
        action: PlannedAction,
        snapshot: _CandidateSnapshot,
    ) -> None:
        if not self.settings.github_actions_enabled:
            raise GitHubNotConfigured("GitHub actions are disabled")
        if run.repository is None:
            raise GitHubPublicationRejected(
                "The run has no immutable repository target"
            )
        if action.kind != ActionKind.PULL_REQUEST:
            raise GitHubPublicationRejected(
                "Only a pull-request action can invoke draft PR publication"
            )
        if action.state != ActionState.READY or not action.verified:
            raise GitHubPublicationRejected(
                "The draft PR action is not verified and ready"
            )
        receipt = run.verification
        if not (
            receipt is not None
            and receipt.publishable
            and receipt.isolated
            and receipt.exact_tree_verified
            and receipt.baseline_control == VerificationResult.FAIL
            and receipt.candidate_control == VerificationResult.PASS
            and receipt.regression_suite == VerificationResult.PASS
        ):
            raise GitHubPublicationRejected(
                "The run does not contain a complete isolated verification receipt"
            )
        binding = receipt.artifact_binding
        if binding is None:
            raise GitHubPublicationRejected(
                "The verification receipt is not bound to an exact build and candidate"
            )
        candidate_hashes = {
            path: candidate_sha
            for path, _content, candidate_sha, _preimage_sha in snapshot.files
        }
        preimage_hashes = {
            path: preimage_sha
            for path, _content, _candidate_sha, preimage_sha in snapshot.files
        }
        if (
            binding.repository_url != snapshot.repository_url
            or binding.base_sha != snapshot.base_sha
            or binding.unified_diff_sha256 != snapshot.unified_diff_sha256
            or binding.candidate_hashes != candidate_hashes
            or binding.preimage_hashes != preimage_hashes
        ):
            raise GitHubPublicationRejected(
                "The candidate did not match the verification receipt's artifact binding"
            )

    def _bound_repository(
        self,
        connection: _Connection | None,
        target: GitHubRepository,
    ) -> GitHubRepository:
        if connection is None:
            raise GitHubAuthorizationError(
                "The run's repository is no longer connected"
            )
        repository = next(
            (item for item in connection.repositories if item.id == target.id),
            None,
        )
        if repository is None:
            raise GitHubAuthorizationError(
                "The run's repository is not available to the verified installation"
            )
        immutable_identity = (
            repository.full_name,
            repository.default_branch,
            repository.private,
            repository.html_url,
        )
        target_identity = (
            target.full_name,
            target.default_branch,
            target.private,
            target.html_url,
        )
        if immutable_identity != target_identity:
            raise GitHubAuthorizationError(
                "The run's bound repository identity no longer matches the connection"
            )
        if repository.archived or target.archived:
            raise GitHubAuthorizationError("The run's repository is archived")
        return repository

    async def _validate_installation_identity(
        self,
        connection: _Connection,
        repository: GitHubRepository,
    ) -> None:
        url = (
            f"{self.settings.github_api_url}/app/installations/"
            f"{connection.installation_id}"
        )
        try:
            async with self._client() as client:
                response = await client.get(
                    url,
                    headers=self._api_headers(self._app_jwt()),
                )
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise GitHubPublishUncertain(
                "GitHub installation identity could not be proven"
            ) from exc
        self._require_status(
            response, {200}, "GitHub installation identity check failed"
        )
        body = self._json_object(
            response, "GitHub returned an invalid installation identity"
        )
        account = body.get("account")
        account_login = account.get("login") if isinstance(account, dict) else None
        repository_owner = repository.full_name.partition("/")[0]
        if (
            str(body.get("id")) != str(connection.installation_id)
            or str(body.get("app_id")) != str(self.settings.github_app_id)
            or body.get("suspended_at") is not None
            or not isinstance(account_login, str)
            or account_login.casefold() != connection.account_login.casefold()
            or account_login.casefold() != repository_owner.casefold()
        ):
            raise GitHubAuthorizationError(
                "The selected GitHub App installation identity did not match the run"
            )

    async def _validate_token_repository(
        self,
        repository: GitHubRepository,
        token: str,
    ) -> None:
        try:
            async with self._client() as client:
                repositories = await self._paginate(
                    client,
                    f"{self.settings.github_api_url}/installation/repositories",
                    headers=self._api_headers(token),
                    collection_key="repositories",
                )
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise GitHubPublishUncertain(
                "The repository-scoped installation token could not be verified"
            ) from exc
        if len(repositories) != 1:
            raise GitHubAuthorizationError(
                "The publication token was not scoped to exactly one repository"
            )
        item = repositories[0]
        identity = (
            str(item.get("id")),
            str(item.get("full_name") or ""),
            str(item.get("default_branch") or ""),
            bool(item.get("private", False)),
            str(item.get("html_url") or ""),
            bool(item.get("archived", False)),
        )
        expected = (
            str(repository.id),
            repository.full_name,
            repository.default_branch,
            repository.private,
            repository.html_url,
            False,
        )
        if identity != expected:
            raise GitHubAuthorizationError(
                "The repository-scoped token identity did not match the run"
            )

    async def _wait_for_issue_intent(
        self, fingerprint: str, owner: str
    ) -> _IssueIntentClaim:
        deadline = asyncio.get_running_loop().time() + ISSUE_INTENT_WAIT_SECONDS
        while True:
            try:
                claim = await self.store.claim_issue_intent(
                    fingerprint,
                    owner,
                    lease_seconds=ISSUE_INTENT_LEASE_SECONDS,
                )
            except Exception as exc:
                raise GitHubPublishUncertain(
                    "The durable GitHub issue intent could not be claimed"
                ) from exc
            if claim.acquired or claim.receipt is not None:
                return claim
            if asyncio.get_running_loop().time() >= deadline:
                raise GitHubPublishUncertain(
                    "GitHub issue publication is still owned by another worker"
                )
            await asyncio.sleep(ISSUE_INTENT_POLL_SECONDS)

    async def _publish_or_reconcile_issue(
        self,
        *,
        run: AuditRun,
        action: PlannedAction,
        repository: GitHubRepository,
        token: str,
        marker: str,
    ) -> PublishedIssue:
        try:
            existing = await self._find_issue(repository, token, marker)
        except (
            GitHubIntegrationError,
            httpx.TimeoutException,
            httpx.NetworkError,
        ) as exc:
            raise GitHubPublishUncertain(
                "GitHub issue reconciliation could not prove the remote state"
            ) from exc
        if existing is not None:
            return existing

        payload = {
            "title": f"[iPromise] {action.title}"[:256],
            "body": self._issue_body(run, marker),
        }
        url = (
            f"{self.settings.github_api_url}/repos/"
            f"{quote(repository.full_name, safe='/')}/issues"
        )
        try:
            async with self._client() as client:
                response = await client.post(
                    url,
                    headers=self._api_headers(token),
                    json=payload,
                )
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            return await self._reconcile_ambiguous_write(
                repository, token, marker, cause=exc
            )

        if response.status_code == 201:
            try:
                payload_body = response.json()
                if not isinstance(payload_body, dict):
                    raise ValueError("GitHub issue receipt is not an object")
                return self._published_issue(payload_body, reconciled=False)
            except (ValueError, GitHubIntegrationError) as exc:
                return await self._reconcile_ambiguous_write(
                    repository, token, marker, cause=exc
                )
        if response.status_code in AMBIGUOUS_WRITE_STATUSES:
            return await self._reconcile_ambiguous_write(
                repository,
                token,
                marker,
                cause=GitHubIntegrationError(
                    f"GitHub returned an ambiguous issue status ({response.status_code})"
                ),
            )
        self._require_status(response, {201}, "GitHub issue creation failed")
        raise AssertionError("unreachable GitHub issue status")

    async def _get_ref_sha(
        self,
        repository: GitHubRepository,
        token: str,
        ref: str,
    ) -> str | None:
        url = (
            f"{self.settings.github_api_url}/repos/"
            f"{quote(repository.full_name, safe='/')}/git/ref/{quote(ref, safe='/')}"
        )
        try:
            async with self._client() as client:
                response = await client.get(url, headers=self._api_headers(token))
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise GitHubPublishUncertain(
                "GitHub ref state could not be proven"
            ) from exc
        if response.status_code == 404:
            return None
        self._require_status(response, {200}, "GitHub ref lookup failed")
        body = self._json_object(response, "GitHub returned an invalid ref")
        object_body = body.get("object")
        sha = object_body.get("sha") if isinstance(object_body, dict) else None
        if (
            body.get("ref") != f"refs/{ref}"
            or not isinstance(sha, str)
            or not GIT_OBJECT_SHA_PATTERN.fullmatch(sha)
        ):
            raise GitHubIntegrationError("GitHub returned an invalid ref")
        return sha

    async def _read_exact_source_blob(
        self,
        repository: GitHubRepository,
        token: str,
        blob_sha: str,
    ) -> bytes:
        url = (
            f"{self.settings.github_api_url}/repos/"
            f"{quote(repository.full_name, safe='/')}/git/blobs/{blob_sha}"
        )
        try:
            async with self._client() as client:
                response = await client.get(url, headers=self._api_headers(token))
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise GitHubIntegrationError(
                "GitHub source blob could not be read"
            ) from exc
        self._require_status(response, {200}, "GitHub source blob lookup failed")
        body = self._json_object(response, "GitHub returned an invalid source blob")
        encoded = body.get("content")
        if (
            body.get("sha") != blob_sha
            or body.get("encoding") != "base64"
            or not isinstance(encoded, str)
        ):
            raise GitHubIntegrationError("GitHub returned an invalid source blob")
        try:
            content = base64.b64decode("".join(encoded.split()), validate=True)
        except (ValueError, binascii.Error) as exc:
            raise GitHubIntegrationError(
                "GitHub returned invalid source blob encoding"
            ) from exc
        if len(content) > MAX_SOURCE_BLOB_BYTES:
            raise GitHubPublicationRejected(
                "Approved remediation source exceeds the read bound"
            )
        if _git_blob_sha(content) != blob_sha:
            raise GitHubPublicationRejected(
                "GitHub source blob bytes did not match their object identity"
            )
        return content

    async def _create_candidate_tree(
        self,
        repository: GitHubRepository,
        token: str,
        snapshot: _CandidateSnapshot,
    ) -> str:
        base_tree_sha = await self._commit_tree_sha(
            repository,
            token,
            snapshot.base_sha,
            expected_parent=None,
        )
        base_entries = await self._tree_leaves(
            repository,
            token,
            base_tree_sha,
        )
        tree_entries: list[dict[str, str]] = []
        for path, content, _sha256, _preimage_sha256 in snapshot.files:
            existing = base_entries.get(path)
            if existing is None:
                raise GitHubPublicationRejected(
                    f"Candidate path is absent from the verified base tree: {path}"
                )
            mode, object_type, _base_blob_sha = existing
            if object_type != "blob" or mode not in ALLOWED_BLOB_MODES:
                raise GitHubPublicationRejected(
                    f"Candidate path is not a bounded regular file: {path}"
                )
            blob_sha = await self._create_exact_blob(repository, token, content)
            tree_entries.append(
                {
                    "path": path,
                    "mode": mode,
                    "type": "blob",
                    "sha": blob_sha,
                }
            )

        url = (
            f"{self.settings.github_api_url}/repos/"
            f"{quote(repository.full_name, safe='/')}/git/trees"
        )
        try:
            async with self._client() as client:
                response = await client.post(
                    url,
                    headers=self._api_headers(token),
                    json={"base_tree": base_tree_sha, "tree": tree_entries},
                )
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise GitHubPublishUncertain(
                "GitHub candidate tree creation had an ambiguous outcome"
            ) from exc
        if response.status_code in AMBIGUOUS_WRITE_STATUSES:
            raise GitHubPublishUncertain(
                "GitHub candidate tree creation had an ambiguous outcome"
            )
        self._require_status(response, {201}, "GitHub candidate tree creation failed")
        body = self._json_object(
            response, "GitHub returned an invalid candidate tree"
        )
        tree_sha = body.get("sha")
        if not isinstance(tree_sha, str) or not GIT_OBJECT_SHA_PATTERN.fullmatch(
            tree_sha
        ):
            raise GitHubIntegrationError("GitHub returned an invalid candidate tree")
        await self._verify_candidate_tree(
            repository,
            token,
            base_tree_sha=base_tree_sha,
            candidate_tree_sha=tree_sha,
            snapshot=snapshot,
        )
        return tree_sha

    async def _create_exact_blob(
        self,
        repository: GitHubRepository,
        token: str,
        content: bytes,
    ) -> str:
        expected_sha = _git_blob_sha(content)
        url = (
            f"{self.settings.github_api_url}/repos/"
            f"{quote(repository.full_name, safe='/')}/git/blobs"
        )
        try:
            async with self._client() as client:
                response = await client.post(
                    url,
                    headers=self._api_headers(token),
                    json={
                        "content": base64.b64encode(content).decode("ascii"),
                        "encoding": "base64",
                    },
                )
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            return await self._reconcile_exact_blob(
                repository, token, content, expected_sha, cause=exc
            )
        if response.status_code == 201:
            body = self._json_object(response, "GitHub returned an invalid blob")
            if body.get("sha") != expected_sha:
                raise GitHubPublicationRejected(
                    "GitHub blob identity did not match the exact candidate bytes"
                )
            return expected_sha
        if response.status_code in AMBIGUOUS_WRITE_STATUSES:
            return await self._reconcile_exact_blob(
                repository,
                token,
                content,
                expected_sha,
                cause=GitHubIntegrationError(
                    f"GitHub returned an ambiguous blob status ({response.status_code})"
                ),
            )
        self._require_status(response, {201}, "GitHub blob creation failed")
        raise AssertionError("unreachable GitHub blob status")

    async def _reconcile_exact_blob(
        self,
        repository: GitHubRepository,
        token: str,
        content: bytes,
        expected_sha: str,
        *,
        cause: Exception,
    ) -> str:
        last_error: Exception = cause
        url = (
            f"{self.settings.github_api_url}/repos/"
            f"{quote(repository.full_name, safe='/')}/git/blobs/{expected_sha}"
        )
        for delay in PULL_REQUEST_RECONCILIATION_DELAYS_SECONDS:
            if delay:
                await asyncio.sleep(delay)
            try:
                async with self._client() as client:
                    response = await client.get(
                        url, headers=self._api_headers(token)
                    )
                if response.status_code == 404:
                    continue
                self._require_status(response, {200}, "GitHub blob lookup failed")
                body = self._json_object(
                    response, "GitHub returned an invalid blob"
                )
                encoded = body.get("content")
                if body.get("sha") != expected_sha or not isinstance(encoded, str):
                    raise GitHubPublicationRejected(
                        "GitHub blob identity did not match the candidate"
                    )
                remote = base64.b64decode("".join(encoded.split()), validate=True)
                if remote != content:
                    raise GitHubPublicationRejected(
                        "GitHub blob bytes did not match the verified candidate"
                    )
                return expected_sha
            except GitHubPublicationRejected:
                raise
            except (
                GitHubIntegrationError,
                ValueError,
                httpx.TimeoutException,
                httpx.NetworkError,
            ) as exc:
                last_error = exc
        raise GitHubPublishUncertain(
            "GitHub did not confirm the exact blob outcome; no blind retry was attempted"
        ) from last_error

    async def _create_candidate_commit(
        self,
        *,
        repository: GitHubRepository,
        token: str,
        snapshot: _CandidateSnapshot,
        tree_sha: str,
    ) -> str:
        message = (
            "Repair promise drift detected by iPromise\n\n"
            f"Base: {snapshot.base_sha}\n"
            f"Verified diff: {snapshot.unified_diff_sha256}"
        )
        identity = {
            "name": "iPromise",
            "email": "bot@ipromise.dev",
            # Git commit identity must be stable across duplicate scheduled
            # runs so concurrent publishers create the same content-addressed
            # object and can safely reconcile one deterministic branch.
            "date": DETERMINISTIC_COMMIT_TIMESTAMP,
        }
        url = (
            f"{self.settings.github_api_url}/repos/"
            f"{quote(repository.full_name, safe='/')}/git/commits"
        )
        try:
            async with self._client() as client:
                response = await client.post(
                    url,
                    headers=self._api_headers(token),
                    json={
                        "message": message,
                        "tree": tree_sha,
                        "parents": [snapshot.base_sha],
                        "author": identity,
                        "committer": identity,
                    },
                )
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise GitHubPublishUncertain(
                "GitHub candidate commit creation had an ambiguous outcome"
            ) from exc
        if response.status_code in AMBIGUOUS_WRITE_STATUSES:
            raise GitHubPublishUncertain(
                "GitHub candidate commit creation had an ambiguous outcome"
            )
        self._require_status(response, {201}, "GitHub candidate commit creation failed")
        body = self._json_object(
            response, "GitHub returned an invalid candidate commit"
        )
        commit_sha = body.get("sha")
        if not isinstance(commit_sha, str) or not GIT_OBJECT_SHA_PATTERN.fullmatch(
            commit_sha
        ):
            raise GitHubIntegrationError("GitHub returned an invalid candidate commit")
        verified_tree = await self._commit_tree_sha(
            repository,
            token,
            commit_sha,
            expected_parent=snapshot.base_sha,
        )
        if verified_tree != tree_sha:
            raise GitHubPublicationRejected(
                "GitHub candidate commit did not contain the exact candidate tree"
            )
        return commit_sha

    async def _commit_tree_sha(
        self,
        repository: GitHubRepository,
        token: str,
        commit_sha: str,
        *,
        expected_parent: str | None,
    ) -> str:
        url = (
            f"{self.settings.github_api_url}/repos/"
            f"{quote(repository.full_name, safe='/')}/git/commits/{commit_sha}"
        )
        try:
            async with self._client() as client:
                response = await client.get(url, headers=self._api_headers(token))
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise GitHubPublishUncertain(
                "GitHub commit identity could not be proven"
            ) from exc
        self._require_status(response, {200}, "GitHub commit lookup failed")
        body = self._json_object(response, "GitHub returned an invalid commit")
        tree = body.get("tree")
        tree_sha = tree.get("sha") if isinstance(tree, dict) else None
        parents = body.get("parents")
        if (
            body.get("sha") != commit_sha
            or not isinstance(tree_sha, str)
            or not GIT_OBJECT_SHA_PATTERN.fullmatch(tree_sha)
            or not isinstance(parents, list)
        ):
            raise GitHubIntegrationError("GitHub returned an invalid commit")
        if expected_parent is not None:
            parent_shas = [
                item.get("sha") for item in parents if isinstance(item, dict)
            ]
            if parent_shas != [expected_parent]:
                raise GitHubPublicationRejected(
                    "GitHub candidate commit was not based only on the verified base"
                )
        return tree_sha

    async def _tree_leaves(
        self,
        repository: GitHubRepository,
        token: str,
        tree_sha: str,
    ) -> dict[str, tuple[str, str, str]]:
        url = (
            f"{self.settings.github_api_url}/repos/"
            f"{quote(repository.full_name, safe='/')}/git/trees/{tree_sha}"
        )
        try:
            async with self._client() as client:
                response = await client.get(
                    url,
                    headers=self._api_headers(token),
                    params={"recursive": "1"},
                )
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise GitHubPublishUncertain(
                "GitHub tree identity could not be proven"
            ) from exc
        self._require_status(response, {200}, "GitHub tree lookup failed")
        body = self._json_object(response, "GitHub returned an invalid tree")
        items = body.get("tree")
        if (
            body.get("sha") != tree_sha
            or body.get("truncated") is True
            or not isinstance(items, list)
        ):
            raise GitHubPublicationRejected(
                "GitHub could not return the complete exact tree"
            )
        result: dict[str, tuple[str, str, str]] = {}
        for item in items:
            if not isinstance(item, dict) or item.get("type") == "tree":
                continue
            path = item.get("path")
            mode = item.get("mode")
            object_type = item.get("type")
            sha = item.get("sha")
            if not all(isinstance(value, str) for value in (path, mode, object_type, sha)):
                raise GitHubIntegrationError("GitHub returned an invalid tree entry")
            if path in result:
                raise GitHubIntegrationError("GitHub returned a duplicate tree path")
            result[path] = (mode, object_type, sha)
        return result

    async def _verify_candidate_tree(
        self,
        repository: GitHubRepository,
        token: str,
        *,
        base_tree_sha: str,
        candidate_tree_sha: str,
        snapshot: _CandidateSnapshot,
    ) -> None:
        base = await self._tree_leaves(repository, token, base_tree_sha)
        expected = dict(base)
        for path, content, _sha256, _preimage_sha256 in snapshot.files:
            current = base.get(path)
            if current is None or current[1] != "blob":
                raise GitHubPublicationRejected(
                    f"Candidate path is not a base-tree blob: {path}"
                )
            expected[path] = (current[0], "blob", _git_blob_sha(content))
        observed = await self._tree_leaves(repository, token, candidate_tree_sha)
        if observed != expected:
            raise GitHubPublicationRejected(
                "The resulting Git tree did not match the exact verified candidate"
            )

    async def _create_or_reconcile_branch(
        self,
        *,
        repository: GitHubRepository,
        token: str,
        branch: str,
        commit_sha: str,
    ) -> bool:
        ref_name = f"heads/{branch}"
        existing = await self._get_ref_sha(repository, token, ref_name)
        if existing is not None:
            if existing != commit_sha:
                raise GitHubPublicationRejected(
                    "The deterministic iPromise branch already points elsewhere"
                )
            return True
        url = (
            f"{self.settings.github_api_url}/repos/"
            f"{quote(repository.full_name, safe='/')}/git/refs"
        )
        cause: Exception | None = None
        try:
            async with self._client() as client:
                response = await client.post(
                    url,
                    headers=self._api_headers(token),
                    json={"ref": f"refs/heads/{branch}", "sha": commit_sha},
                )
            if response.status_code == 201:
                body = self._json_object(
                    response, "GitHub returned an invalid branch receipt"
                )
                object_body = body.get("object")
                if (
                    body.get("ref") != f"refs/heads/{branch}"
                    or not isinstance(object_body, dict)
                    or object_body.get("sha") != commit_sha
                ):
                    raise GitHubPublicationRejected(
                        "GitHub branch did not point to the exact candidate commit"
                    )
                return False
            if response.status_code not in AMBIGUOUS_WRITE_STATUSES | {422}:
                self._require_status(response, {201}, "GitHub branch creation failed")
            cause = GitHubIntegrationError(
                f"GitHub returned an ambiguous branch status ({response.status_code})"
            )
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            cause = exc

        for delay in PULL_REQUEST_RECONCILIATION_DELAYS_SECONDS:
            if delay:
                await asyncio.sleep(delay)
            found = await self._get_ref_sha(repository, token, ref_name)
            if found is None:
                continue
            if found != commit_sha:
                raise GitHubPublicationRejected(
                    "The deterministic iPromise branch points to a different commit"
                )
            return True
        raise GitHubPublishUncertain(
            "GitHub did not confirm the branch outcome; the ref was not force-updated"
        ) from cause

    async def _find_pull_request(
        self,
        *,
        repository: GitHubRepository,
        token: str,
        branch: str,
        marker: str,
        snapshot: _CandidateSnapshot,
    ) -> PublishedPullRequest | None:
        url = (
            f"{self.settings.github_api_url}/repos/"
            f"{quote(repository.full_name, safe='/')}/pulls"
        )
        owner = repository.full_name.partition("/")[0]
        matches: list[dict[str, Any]] = []
        for page in range(1, 11):
            try:
                async with self._client() as client:
                    response = await client.get(
                        url,
                        headers=self._api_headers(token),
                        params={
                            "state": "all",
                            "head": f"{owner}:{branch}",
                            "base": repository.default_branch,
                            "per_page": "100",
                            "page": str(page),
                        },
                    )
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                raise GitHubPublishUncertain(
                    "GitHub draft PR reconciliation could not prove remote state"
                ) from exc
            self._require_status(
                response, {200}, "GitHub draft PR reconciliation failed"
            )
            try:
                items = response.json()
            except ValueError as exc:
                raise GitHubIntegrationError(
                    "GitHub returned an invalid draft PR list"
                ) from exc
            if not isinstance(items, list):
                raise GitHubIntegrationError(
                    "GitHub returned an invalid draft PR list"
                )
            matches.extend(item for item in items if isinstance(item, dict))
            if len(items) < 100:
                break
        else:
            raise GitHubPublishUncertain(
                "GitHub draft PR reconciliation exceeded its pagination limit"
            )

        if not matches:
            return None
        marked = [item for item in matches if marker in str(item.get("body") or "")]
        if len(marked) != 1 or len(matches) != 1:
            raise GitHubPublicationRejected(
                "The deterministic branch has an ambiguous or unmarked PR history"
            )
        return await self._published_pull_request(
            marked[0],
            repository=repository,
            token=token,
            branch=branch,
            marker=marker,
            snapshot=snapshot,
            reconciled=True,
        )

    async def _create_or_reconcile_pull_request(
        self,
        *,
        run: AuditRun,
        action: PlannedAction,
        repository: GitHubRepository,
        token: str,
        branch: str,
        marker: str,
        snapshot: _CandidateSnapshot,
        tree_sha: str,
        commit_sha: str,
        prior_reconciliation: bool,
    ) -> PublishedPullRequest:
        url = (
            f"{self.settings.github_api_url}/repos/"
            f"{quote(repository.full_name, safe='/')}/pulls"
        )
        payload = {
            "title": f"[iPromise] {action.title}"[:256],
            "head": branch,
            "base": repository.default_branch,
            "body": self._pull_request_body(
                run,
                marker=marker,
                snapshot=snapshot,
                tree_sha=tree_sha,
                commit_sha=commit_sha,
            ),
            "draft": True,
            "maintainer_can_modify": False,
        }
        cause: Exception | None = None
        try:
            async with self._client() as client:
                response = await client.post(
                    url,
                    headers=self._api_headers(token),
                    json=payload,
                )
            if response.status_code == 201:
                try:
                    body = self._json_object(
                        response, "GitHub returned an invalid draft PR receipt"
                    )
                    receipt = await self._published_pull_request(
                        body,
                        repository=repository,
                        token=token,
                        branch=branch,
                        marker=marker,
                        snapshot=snapshot,
                        reconciled=prior_reconciliation,
                    )
                    if receipt.head_sha != commit_sha or receipt.tree_sha != tree_sha:
                        raise GitHubPublicationRejected(
                            "GitHub draft PR did not contain the exact candidate commit"
                        )
                    return receipt
                except GitHubPublicationRejected:
                    raise
                except GitHubIntegrationError as exc:
                    cause = exc
            elif response.status_code in AMBIGUOUS_WRITE_STATUSES | {422}:
                cause = GitHubIntegrationError(
                    f"GitHub returned an ambiguous draft PR status ({response.status_code})"
                )
            else:
                self._require_status(
                    response, {201}, "GitHub draft PR creation failed"
                )
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            cause = exc

        last_error = cause or GitHubIntegrationError(
            "GitHub returned an invalid draft PR receipt"
        )
        for delay in PULL_REQUEST_RECONCILIATION_DELAYS_SECONDS:
            if delay:
                await asyncio.sleep(delay)
            try:
                receipt = await self._find_pull_request(
                    repository=repository,
                    token=token,
                    branch=branch,
                    marker=marker,
                    snapshot=snapshot,
                )
            except GitHubPublicationRejected:
                raise
            except GitHubIntegrationError as exc:
                last_error = exc
                continue
            if receipt is not None:
                if receipt.head_sha != commit_sha or receipt.tree_sha != tree_sha:
                    raise GitHubPublicationRejected(
                        "The reconciled draft PR did not contain the candidate commit"
                    )
                return receipt
        raise GitHubPublishUncertain(
            "GitHub did not confirm the draft PR outcome; no duplicate was opened"
        ) from last_error

    async def _published_pull_request(
        self,
        payload: dict[str, Any],
        *,
        repository: GitHubRepository,
        token: str,
        branch: str,
        marker: str,
        snapshot: _CandidateSnapshot,
        reconciled: bool,
    ) -> PublishedPullRequest:
        head = payload.get("head")
        base = payload.get("base")
        head_repo = head.get("repo") if isinstance(head, dict) else None
        base_repo = base.get("repo") if isinstance(base, dict) else None
        head_sha = head.get("sha") if isinstance(head, dict) else None
        valid = (
            payload.get("state") == "open"
            and payload.get("draft") is True
            and payload.get("merged_at") is None
            and marker in str(payload.get("body") or "")
            and isinstance(head, dict)
            and head.get("ref") == branch
            and isinstance(head_repo, dict)
            and str(head_repo.get("id")) == str(repository.id)
            and isinstance(base, dict)
            and base.get("ref") == repository.default_branch
            and isinstance(base_repo, dict)
            and str(base_repo.get("id")) == str(repository.id)
            and isinstance(head_sha, str)
            and GIT_OBJECT_SHA_PATTERN.fullmatch(head_sha) is not None
        )
        if not valid:
            raise GitHubPublicationRejected(
                "GitHub returned a PR that was not the expected open draft"
            )
        branch_sha = await self._get_ref_sha(repository, token, f"heads/{branch}")
        if branch_sha != head_sha:
            raise GitHubPublicationRejected(
                "The draft PR head did not match the deterministic branch"
            )
        tree_sha = await self._commit_tree_sha(
            repository,
            token,
            head_sha,
            expected_parent=snapshot.base_sha,
        )
        base_tree_sha = await self._commit_tree_sha(
            repository,
            token,
            snapshot.base_sha,
            expected_parent=None,
        )
        await self._verify_candidate_tree(
            repository,
            token,
            base_tree_sha=base_tree_sha,
            candidate_tree_sha=tree_sha,
            snapshot=snapshot,
        )
        try:
            return PublishedPullRequest(
                url=str(payload["html_url"]),
                number=int(payload["number"]),
                remote_id=int(payload["id"]),
                branch=branch,
                head_sha=head_sha,
                base_sha=snapshot.base_sha,
                tree_sha=tree_sha,
                reconciled=reconciled,
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise GitHubIntegrationError(
                "GitHub returned an invalid draft PR receipt"
            ) from exc

    def _pull_request_body(
        self,
        run: AuditRun,
        *,
        marker: str,
        snapshot: _CandidateSnapshot,
        tree_sha: str,
        commit_sha: str,
    ) -> str:
        files = "\n".join(
            f"- `{_safe(path, 500)}` — SHA-256 `{sha256}`"
            for path, _content, sha256, _preimage_sha256 in snapshot.files
        )
        return f"""{marker}
<!-- ipromise-base:v1:{snapshot.base_sha} -->
<!-- ipromise-tree:v1:{tree_sha} -->

## Verified repair

iPromise detected a scoped contradiction in the account-deletion promise and prepared this bounded repair from an isolated fail-before/pass-after run.

- Run: `{_safe(run.id, 128)}`
- Exact base commit: `{snapshot.base_sha}`
- Exact candidate tree: `{tree_sha}`
- Exact candidate commit: `{commit_sha}`
- Verified unified diff SHA-256: `{snapshot.unified_diff_sha256}`

## Exact candidate files

{files}

## Safety boundary

This is a draft only. iPromise did not merge or deploy it. The evidence used synthetic data, is scoped to the systems and time shown, and is not a legal-compliance conclusion.
"""[:65_000]

    @staticmethod
    def _json_object(response: httpx.Response, message: str) -> dict[str, Any]:
        try:
            body = response.json()
        except ValueError as exc:
            raise GitHubIntegrationError(message) from exc
        if not isinstance(body, dict):
            raise GitHubIntegrationError(message)
        return body

    async def _installation_token(
        self,
        connection: _Connection,
        repository: GitHubRepository,
        *,
        permissions: dict[str, str],
    ) -> str:
        app_jwt = self._app_jwt()
        async with self._client() as client:
            response = await client.post(
                (
                    f"{self.settings.github_api_url}/app/installations/"
                    f"{connection.installation_id}/access_tokens"
                ),
                headers=self._api_headers(app_jwt),
                json={
                    "repository_ids": [repository.id],
                    "permissions": permissions,
                },
            )
        self._require_status(response, {201}, "GitHub token minting failed")
        try:
            body = response.json()
        except ValueError as exc:
            raise GitHubAuthorizationError(
                "GitHub returned an invalid installation token response"
            ) from exc
        if not isinstance(body, dict):
            raise GitHubAuthorizationError(
                "GitHub returned an invalid installation token response"
            )
        token = body.get("token")
        if not isinstance(token, str) or not token:
            raise GitHubAuthorizationError("GitHub did not return an installation token")
        return token

    def _app_jwt(self) -> str:
        try:
            import jwt
        except ImportError as exc:  # pragma: no cover - packaging guard
            raise GitHubNotConfigured(
                "Install the agent's github dependency extra before enabling actions"
            ) from exc
        now = int(time.time())
        return jwt.encode(
            {
                "iat": now - 60,
                "exp": now + 9 * 60,
                "iss": self.settings.github_app_client_id,
            },
            self.settings.github_app_private_key,
            algorithm="RS256",
        )

    async def _find_issue(
        self, repository: GitHubRepository, token: str, marker: str
    ) -> PublishedIssue | None:
        url = (
            f"{self.settings.github_api_url}/repos/"
            f"{quote(repository.full_name, safe='/')}/issues"
        )
        async with self._client() as client:
            for page in range(1, 101):
                response = await client.get(
                    url,
                    headers=self._api_headers(token),
                    params={
                        "state": "all",
                        "per_page": "100",
                        "sort": "created",
                        "direction": "desc",
                        "page": str(page),
                    },
                )
                self._require_status(
                    response, {200}, "GitHub issue reconciliation failed"
                )
                try:
                    items = response.json()
                except ValueError as exc:
                    raise GitHubIntegrationError(
                        "GitHub returned an invalid issue reconciliation response"
                    ) from exc
                if not isinstance(items, list):
                    raise GitHubIntegrationError(
                        "GitHub returned an invalid issue reconciliation response"
                    )
                for item in items:
                    if not isinstance(item, dict) or item.get("pull_request"):
                        continue
                    if marker in str(item.get("body") or ""):
                        return self._published_issue(item, reconciled=True)
                if len(items) < 100:
                    return None
        raise GitHubPublishUncertain(
            "GitHub issue reconciliation exceeded the pagination safety limit"
        )

    async def _reconcile_ambiguous_write(
        self,
        repository: GitHubRepository,
        token: str,
        marker: str,
        *,
        cause: Exception,
    ) -> PublishedIssue:
        last_error: Exception = cause
        for delay in ISSUE_RECONCILIATION_DELAYS_SECONDS:
            if delay:
                await asyncio.sleep(delay)
            try:
                reconciled = await self._find_issue(repository, token, marker)
            except (
                GitHubIntegrationError,
                httpx.TimeoutException,
                httpx.NetworkError,
            ) as exc:
                last_error = exc
                continue
            if reconciled is not None:
                return PublishedIssue(
                    url=reconciled.url,
                    number=reconciled.number,
                    remote_id=reconciled.remote_id,
                    reconciled=True,
                )
        raise GitHubPublishUncertain(
            "GitHub did not confirm the issue outcome; no blind retry was attempted"
        ) from last_error

    async def _paginate(
        self,
        client: httpx.AsyncClient,
        url: str,
        *,
        headers: dict[str, str],
        collection_key: str,
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for page in range(1, 101):
            response = await client.get(
                url,
                headers=headers,
                params={"per_page": "100", "page": str(page)},
            )
            self._require_status(response, {200}, "GitHub authorization check failed")
            body = response.json()
            items = body.get(collection_key)
            if not isinstance(items, list):
                raise GitHubAuthorizationError("GitHub returned an invalid repository list")
            results.extend(item for item in items if isinstance(item, dict))
            if len(items) < 100:
                return results
        raise GitHubAuthorizationError("GitHub repository pagination exceeded safety limit")

    def _issue_body(self, run: AuditRun, marker: str) -> str:
        quote_text = _safe(run.claim.exact_quote, 2_000)
        source_url = _safe(run.claim.source_url, 2_000)
        evidence_lines = "\n".join(
            (
                f"- **{_safe(item.label, 200)}** — expected "
                f"{_safe(item.expected, 500)}; observed {_safe(item.observed, 500)} "
                f"(`{item.result.value}`)"
            )
            for item in run.evidence
        )
        # Keep reconciliation markers ahead of bounded human-readable content so
        # an unexpectedly large evidence set cannot truncate remote identity.
        body = f"""{marker}
<!-- ipromise-run:v1:{_safe(run.id, 128)} -->

## Promise

> {quote_text}

- Source: {source_url}
- Captured: {run.claim.captured_at.astimezone(UTC).isoformat()}
- Content hash: `{_safe(run.claim.content_hash, 256)}`
- Control: `{_safe(run.claim.control_id or 'unbound', 128)}`

## Scoped evidence

{evidence_lines}

## Why this issue was opened

iPromise found a scoped contradiction but did not have an isolated fail-before/pass-after receipt for the proposed repair. It opened an issue instead of publishing unverified code.

Run: `{_safe(run.id, 128)}`

## Limits

This run used synthetic data. The result applies only to the systems and time shown and is not a legal-compliance conclusion.
"""
        return body[:65_000]

    def _published_issue(
        self, payload: dict[str, Any], *, reconciled: bool
    ) -> PublishedIssue:
        try:
            return PublishedIssue(
                url=str(payload["html_url"]),
                number=int(payload["number"]),
                remote_id=int(payload["id"]),
                reconciled=reconciled,
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise GitHubIntegrationError(
                "GitHub returned an invalid issue receipt"
            ) from exc

    def _selected_from(
        self, connection: _Connection | None
    ) -> GitHubRepository | None:
        if connection is None or connection.selected_repository_id is None:
            return None
        return next(
            (
                item
                for item in connection.repositories
                if item.id == connection.selected_repository_id
            ),
            None,
        )

    @property
    def _callback_url(self) -> str:
        return f"{self.settings.console_base_url}/api/integrations/github/callback"

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            transport=self.transport,
            timeout=httpx.Timeout(15.0, connect=5.0),
            follow_redirects=False,
        )

    def _api_headers(self, token: str) -> dict[str, str]:
        return {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": GITHUB_API_VERSION,
            "User-Agent": "iPromise-hackathon-agent",
        }

    def _require_configured(self) -> None:
        if not self.settings.github_configured:
            raise GitHubNotConfigured("The GitHub App is not configured")

    @staticmethod
    def _require_status(
        response: httpx.Response, allowed: set[int], message: str
    ) -> None:
        if response.status_code not in allowed:
            raise GitHubIntegrationError(f"{message} ({response.status_code})")


def _base64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()


def _snapshot_candidate(candidate: VerifiedCandidateInput) -> _CandidateSnapshot:
    """Copy and authenticate the verifier boundary before any network await."""

    try:
        base_sha = candidate.base_sha
        repository_url = candidate.repository_url
        diff_sha = candidate.unified_diff_sha256
        tree = candidate.candidate_tree
        hashes = candidate.candidate_hashes
        preimage_hashes = candidate.preimage_hashes
    except (AttributeError, TypeError) as exc:
        raise GitHubPublicationRejected(
            "The verified candidate input is incomplete"
        ) from exc
    if (
        not isinstance(base_sha, str)
        or not GIT_OBJECT_SHA_PATTERN.fullmatch(base_sha)
    ):
        raise GitHubPublicationRejected(
            "The verified candidate base must be a full lowercase Git SHA"
        )
    if (
        not isinstance(repository_url, str)
        or not repository_url.startswith("https://")
        or not repository_url.endswith(".git")
    ):
        raise GitHubPublicationRejected(
            "The verified candidate source repository is invalid"
        )
    if (
        not isinstance(diff_sha, str)
        or re.fullmatch(r"[0-9a-f]{64}", diff_sha) is None
    ):
        raise GitHubPublicationRejected(
            "The verified candidate diff must have a lowercase SHA-256"
        )
    if (
        not isinstance(tree, Mapping)
        or not isinstance(hashes, Mapping)
        or not isinstance(preimage_hashes, Mapping)
    ):
        raise GitHubPublicationRejected(
            "The verified candidate tree and hashes must be mappings"
        )
    try:
        tree_keys = set(tree.keys())
        hash_keys = set(hashes.keys())
        preimage_keys = set(preimage_hashes.keys())
    except TypeError as exc:
        raise GitHubPublicationRejected(
            "The verified candidate contains invalid paths"
        ) from exc
    if not tree_keys or tree_keys != hash_keys or tree_keys != preimage_keys:
        raise GitHubPublicationRejected(
            "The verified candidate tree and hash paths do not match exactly"
        )

    files: list[tuple[str, bytes, str, str]] = []
    total_bytes = 0
    for path in sorted(tree_keys):
        if not isinstance(path, str) or not _safe_candidate_path(path):
            raise GitHubPublicationRejected(
                "The verified candidate contains an unsafe repository path"
            )
        content = tree[path]
        expected_hash = hashes[path]
        preimage_hash = preimage_hashes[path]
        if not isinstance(content, bytes):
            raise GitHubPublicationRejected(
                f"Candidate content must be immutable bytes: {path}"
            )
        if len(content) > MAX_CANDIDATE_BLOB_BYTES:
            raise GitHubPublicationRejected(
                f"Candidate file exceeds the bounded publication size: {path}"
            )
        total_bytes += len(content)
        if total_bytes > MAX_CANDIDATE_BLOB_BYTES:
            raise GitHubPublicationRejected(
                "The verified candidate exceeds the bounded total publication size"
            )
        if (
            not isinstance(expected_hash, str)
            or re.fullmatch(r"[0-9a-f]{64}", expected_hash) is None
            or hashlib.sha256(content).hexdigest() != expected_hash
        ):
            raise GitHubPublicationRejected(
                f"Candidate bytes did not match the verifier SHA-256: {path}"
            )
        if (
            not isinstance(preimage_hash, str)
            or re.fullmatch(r"[0-9a-f]{64}", preimage_hash) is None
        ):
            raise GitHubPublicationRejected(
                f"Candidate preimage did not contain a verifier SHA-256: {path}"
            )
        files.append((path, content, expected_hash, preimage_hash))
    return _CandidateSnapshot(
        base_sha=base_sha,
        repository_url=repository_url,
        unified_diff_sha256=diff_sha,
        files=tuple(files),
    )


def _safe_candidate_path(path: str) -> bool:
    if (
        not path
        or len(path) > 1_000
        or path.startswith("/")
        or path.endswith("/")
        or "\\" in path
        or "\x00" in path
    ):
        return False
    parts = path.split("/")
    return all(
        part not in {"", ".", ".."} and part.casefold() != ".git"
        for part in parts
    )


def _pull_request_fingerprint(
    repository: GitHubRepository,
    snapshot: _CandidateSnapshot,
) -> str:
    intent = {
        "schema": "ipromise.github-draft-pr.v1",
        "repository": {
            "id": repository.id,
            "fullName": repository.full_name,
        },
        "baseSha": snapshot.base_sha,
        "repositoryUrl": snapshot.repository_url,
        "unifiedDiffSha256": snapshot.unified_diff_sha256,
        "files": [
            {
                "path": path,
                "preimageSha256": preimage_sha256,
                "candidateSha256": candidate_sha256,
            }
            for path, _content, candidate_sha256, preimage_sha256 in snapshot.files
        ],
    }
    canonical = json.dumps(
        intent, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _pull_request_branch(fingerprint: str) -> str:
    return f"ipromise/promise-drift-{fingerprint[:20]}"


def _git_blob_sha(content: bytes) -> str:
    header = f"blob {len(content)}\0".encode("ascii")
    return hashlib.sha1(header + content, usedforsecurity=False).hexdigest()


def _safe(value: str, limit: int) -> str:
    return html.escape(value[:limit], quote=False).replace("\r", " ")
