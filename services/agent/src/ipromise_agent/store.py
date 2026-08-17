"""Concurrency-safe MVP repository with idempotent run reservation."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from typing import Protocol

from .models import AuditRun


class RunStore(Protocol):
    async def reserve(
        self, idempotency_key: str, factory: Callable[[], AuditRun]
    ) -> tuple[AuditRun, bool]: ...

    async def save(self, run: AuditRun) -> None: ...

    async def get(self, run_id: str) -> AuditRun | None: ...

    async def latest(self) -> AuditRun | None: ...

    async def list(self, limit: int = 20) -> list[AuditRun]: ...

    async def acquire_run_lease(
        self,
        run_id: str,
        owner: str,
        *,
        lease_seconds: int,
    ) -> bool: ...

    async def release_run_lease(self, run_id: str, owner: str) -> None: ...

    async def acquire_action_lease(
        self,
        run_id: str,
        action_id: str,
        owner: str,
        *,
        lease_seconds: int,
    ) -> bool: ...

    async def release_action_lease(
        self, run_id: str, action_id: str, owner: str
    ) -> None: ...


class InMemoryRunStore:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._runs: dict[str, AuditRun] = {}
        self._idempotency: dict[str, str] = {}
        self._run_leases: dict[str, tuple[str, float]] = {}
        self._action_leases: dict[tuple[str, str], tuple[str, float]] = {}

    async def reserve(
        self, idempotency_key: str, factory: Callable[[], AuditRun]
    ) -> tuple[AuditRun, bool]:
        async with self._lock:
            existing_id = self._idempotency.get(idempotency_key)
            if existing_id is not None:
                return self._runs[existing_id].model_copy(deep=True), False
            run = factory()
            self._runs[run.id] = run.model_copy(deep=True)
            self._idempotency[idempotency_key] = run.id
            return run, True

    async def save(self, run: AuditRun) -> None:
        async with self._lock:
            if run.id not in self._runs:
                raise KeyError(run.id)
            self._runs[run.id] = run.model_copy(deep=True)

    async def get(self, run_id: str) -> AuditRun | None:
        async with self._lock:
            run = self._runs.get(run_id)
            return run.model_copy(deep=True) if run is not None else None

    async def latest(self) -> AuditRun | None:
        async with self._lock:
            if not self._runs:
                return None
            run = max(self._runs.values(), key=lambda item: item.started_at)
            return run.model_copy(deep=True)

    async def list(self, limit: int = 20) -> list[AuditRun]:
        async with self._lock:
            ordered = sorted(
                self._runs.values(), key=lambda item: item.started_at, reverse=True
            )[:limit]
            return [run.model_copy(deep=True) for run in ordered]

    async def acquire_run_lease(
        self,
        run_id: str,
        owner: str,
        *,
        lease_seconds: int,
    ) -> bool:
        async with self._lock:
            if run_id not in self._runs:
                raise KeyError(run_id)
            now = time.time()
            current = self._run_leases.get(run_id)
            if current is not None:
                current_owner, expires_at = current
                if current_owner != owner and expires_at > now:
                    return False
            self._run_leases[run_id] = (owner, now + lease_seconds)
            return True

    async def release_run_lease(self, run_id: str, owner: str) -> None:
        async with self._lock:
            current = self._run_leases.get(run_id)
            if current is not None and current[0] == owner:
                self._run_leases.pop(run_id, None)

    async def acquire_action_lease(
        self,
        run_id: str,
        action_id: str,
        owner: str,
        *,
        lease_seconds: int,
    ) -> bool:
        async with self._lock:
            run = self._runs.get(run_id)
            if run is None:
                raise KeyError(run_id)
            if not any(action.id == action_id for action in run.actions):
                raise KeyError(action_id)
            key = (run_id, action_id)
            now = time.time()
            current = self._action_leases.get(key)
            if current is not None:
                current_owner, expires_at = current
                if current_owner != owner and expires_at > now:
                    return False
            self._action_leases[key] = (owner, now + lease_seconds)
            return True

    async def release_action_lease(
        self, run_id: str, action_id: str, owner: str
    ) -> None:
        async with self._lock:
            key = (run_id, action_id)
            current = self._action_leases.get(key)
            if current is not None and current[0] == owner:
                self._action_leases.pop(key, None)
