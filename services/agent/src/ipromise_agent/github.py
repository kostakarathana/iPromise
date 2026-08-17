"""Least-privilege GitHub App connection and idempotent issue publication."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import html
import json
import secrets
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import quote, urlencode

import httpx

from .config import Settings
from .models import (
    AuditRun,
    GitHubInstallUrl,
    GitHubIntegrationStatus,
    GitHubOAuthCallbackRequest,
    GitHubOAuthStartRequest,
    GitHubRepository,
    PlannedAction,
)


GITHUB_API_VERSION = "2026-03-10"
CONNECTION_TTL_SECONDS = 10 * 60
ISSUE_RECONCILIATION_DELAYS_SECONDS = (0.0, 0.1, 0.25)
AMBIGUOUS_WRITE_STATUSES = {408, 425, 429, 500, 502, 503, 504}
ISSUE_INTENT_LEASE_SECONDS = 5 * 60
ISSUE_INTENT_WAIT_SECONDS = 30.0
ISSUE_INTENT_POLL_SECONDS = 0.05


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


class GitHubIntegrationError(RuntimeError):
    """A safe, user-facing integration failure."""


class GitHubNotConfigured(GitHubIntegrationError):
    pass


class GitHubAuthorizationError(GitHubIntegrationError):
    pass


class GitHubPublishUncertain(GitHubIntegrationError):
    """The remote outcome could not be proven; callers must not blindly retry."""


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
            token = await self._installation_token(connection, repository)
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

    async def _installation_token(
        self, connection: _Connection, repository: GitHubRepository
    ) -> str:
        try:
            import jwt
        except ImportError as exc:  # pragma: no cover - packaging guard
            raise GitHubNotConfigured(
                "Install the agent's github dependency extra before enabling actions"
            ) from exc
        now = int(time.time())
        app_jwt = jwt.encode(
            {
                "iat": now - 60,
                "exp": now + 9 * 60,
                "iss": self.settings.github_app_client_id,
            },
            self.settings.github_app_private_key,
            algorithm="RS256",
        )
        async with self._client() as client:
            response = await client.post(
                (
                    f"{self.settings.github_api_url}/app/installations/"
                    f"{connection.installation_id}/access_tokens"
                ),
                headers=self._api_headers(app_jwt),
                json={
                    "repository_ids": [repository.id],
                    "permissions": {"issues": "write"},
                },
            )
        self._require_status(response, {201}, "GitHub token minting failed")
        token = response.json().get("token")
        if not isinstance(token, str) or not token:
            raise GitHubAuthorizationError("GitHub did not return an installation token")
        return token

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


def _safe(value: str, limit: int) -> str:
    return html.escape(value[:limit], quote=False).replace("\r", " ")
