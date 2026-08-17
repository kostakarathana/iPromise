"""Firestore-backed run checkpoints and atomic idempotency reservations."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from .models import AuditRun


class FirestoreRunStore:
    def __init__(self, *, database: str = "(default)", client: Any = None) -> None:
        try:
            from google.cloud import firestore_v1
        except ImportError as exc:  # pragma: no cover - packaging guard
            raise RuntimeError(
                "Install the agent's google dependency extra to use Firestore"
            ) from exc
        self._firestore = firestore_v1
        self._client = client or firestore_v1.AsyncClient(database=database)
        self._runs = self._client.collection("audit_runs")
        self._keys = self._client.collection("audit_idempotency")

    async def reserve(
        self, idempotency_key: str, factory: Callable[[], AuditRun]
    ) -> tuple[AuditRun, bool]:
        key_id = hashlib.sha256(idempotency_key.encode()).hexdigest()
        key_ref = self._keys.document(key_id)
        transaction = self._client.transaction()

        @self._firestore.async_transactional
        async def reserve_in_transaction(transaction):
            key_snapshot = await key_ref.get(transaction=transaction)
            if key_snapshot.exists:
                run_id = key_snapshot.get("runId")
                run_snapshot = await self._runs.document(run_id).get(
                    transaction=transaction
                )
                if not run_snapshot.exists:
                    raise RuntimeError("Firestore idempotency record has no audit run")
                return self._decode(run_snapshot.to_dict()), False

            run = factory()
            transaction.set(self._runs.document(run.id), self._encode(run))
            transaction.set(
                key_ref,
                {
                    "runId": run.id,
                    "keyHash": key_id,
                    "createdAt": run.started_at,
                },
            )
            return run.model_copy(deep=True), True

        return await reserve_in_transaction(transaction)

    async def save(self, run: AuditRun) -> None:
        reference = self._runs.document(run.id)
        snapshot = await reference.get()
        if not snapshot.exists:
            raise KeyError(run.id)
        # Preserve transactional action-lease metadata while replacing the typed
        # run checkpoint. The lease is deliberately outside the public payload.
        await reference.set(self._encode(run), merge=True)

    async def get(self, run_id: str) -> AuditRun | None:
        snapshot = await self._runs.document(run_id).get()
        return self._decode(snapshot.to_dict()) if snapshot.exists else None

    async def latest(self) -> AuditRun | None:
        runs = await self.list(1)
        return runs[0] if runs else None

    async def list(self, limit: int = 20) -> list[AuditRun]:
        query = self._runs.order_by(
            "startedAt", direction=self._firestore.Query.DESCENDING
        ).limit(limit)
        return [
            self._decode(snapshot.to_dict())
            async for snapshot in query.stream()
        ]

    async def acquire_run_lease(
        self,
        run_id: str,
        owner: str,
        *,
        lease_seconds: int,
    ) -> bool:
        reference = self._runs.document(run_id)
        transaction = self._client.transaction()
        now = datetime.now(UTC)
        expires_at = now + timedelta(seconds=lease_seconds)

        @self._firestore.async_transactional
        async def acquire_in_transaction(transaction):
            snapshot = await reference.get(transaction=transaction)
            if not snapshot.exists:
                raise KeyError(run_id)
            document = snapshot.to_dict() or {}
            current = document.get("executionLease")
            if isinstance(current, dict):
                current_owner = current.get("owner")
                current_expiry = current.get("expiresAt")
                if (
                    current_owner != owner
                    and isinstance(current_expiry, datetime)
                    and current_expiry > now
                ):
                    return False
            transaction.update(
                reference,
                {
                    "executionLease": {
                        "owner": owner,
                        "expiresAt": expires_at,
                    }
                },
            )
            return True

        return await acquire_in_transaction(transaction)

    async def release_run_lease(self, run_id: str, owner: str) -> None:
        reference = self._runs.document(run_id)
        transaction = self._client.transaction()

        @self._firestore.async_transactional
        async def release_in_transaction(transaction):
            snapshot = await reference.get(transaction=transaction)
            if not snapshot.exists:
                return
            document = snapshot.to_dict() or {}
            current = document.get("executionLease")
            if isinstance(current, dict) and current.get("owner") == owner:
                transaction.update(
                    reference,
                    {"executionLease": self._firestore.DELETE_FIELD},
                )

        await release_in_transaction(transaction)

    async def acquire_action_lease(
        self,
        run_id: str,
        action_id: str,
        owner: str,
        *,
        lease_seconds: int,
    ) -> bool:
        reference = self._runs.document(run_id)
        transaction = self._client.transaction()
        now = datetime.now(UTC)
        expires_at = now + timedelta(seconds=lease_seconds)

        @self._firestore.async_transactional
        async def acquire_in_transaction(transaction):
            snapshot = await reference.get(transaction=transaction)
            if not snapshot.exists:
                raise KeyError(run_id)
            document = snapshot.to_dict() or {}
            run = self._decode(document)
            if not any(action.id == action_id for action in run.actions):
                raise KeyError(action_id)
            leases = dict(document.get("actionLeases") or {})
            current = leases.get(action_id)
            if isinstance(current, dict):
                current_owner = current.get("owner")
                current_expiry = current.get("expiresAt")
                if (
                    current_owner != owner
                    and isinstance(current_expiry, datetime)
                    and current_expiry > now
                ):
                    return False
            leases[action_id] = {"owner": owner, "expiresAt": expires_at}
            transaction.update(reference, {"actionLeases": leases})
            return True

        return await acquire_in_transaction(transaction)

    async def release_action_lease(
        self, run_id: str, action_id: str, owner: str
    ) -> None:
        reference = self._runs.document(run_id)
        transaction = self._client.transaction()

        @self._firestore.async_transactional
        async def release_in_transaction(transaction):
            snapshot = await reference.get(transaction=transaction)
            if not snapshot.exists:
                return
            document = snapshot.to_dict() or {}
            leases = dict(document.get("actionLeases") or {})
            current = leases.get(action_id)
            if isinstance(current, dict) and current.get("owner") == owner:
                leases.pop(action_id, None)
                transaction.update(reference, {"actionLeases": leases})

        await release_in_transaction(transaction)

    @staticmethod
    def _encode(run: AuditRun) -> dict[str, Any]:
        return {
            "runId": run.id,
            "startedAt": run.started_at,
            "updatedAt": run.updated_at,
            "payload": run.model_dump(mode="json", by_alias=True),
        }

    @staticmethod
    def _decode(document: dict[str, Any] | None) -> AuditRun:
        if not document or not isinstance(document.get("payload"), dict):
            raise RuntimeError("Firestore returned an invalid audit document")
        return AuditRun.model_validate(document["payload"])
