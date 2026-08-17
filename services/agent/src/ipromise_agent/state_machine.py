"""Explicit run-state transitions and ordered event trail."""

from __future__ import annotations

from .models import AuditRun, EventState, RunEvent, RunStatus, utc_now


class InvalidTransition(ValueError):
    pass


_TERMINAL = {RunStatus.COMPLETE, RunStatus.FAILED_RETRYABLE, RunStatus.FAILED_SAFE}

_ALLOWED: dict[RunStatus, set[RunStatus]] = {
    RunStatus.RECEIVED: {RunStatus.CAPTURING},
    RunStatus.CAPTURING: {RunStatus.COMPILING},
    RunStatus.COMPILING: {RunStatus.BINDING},
    RunStatus.BINDING: {RunStatus.PROBING, RunStatus.ROUTING_ACTION},
    RunStatus.PROBING: {RunStatus.EVALUATING},
    RunStatus.EVALUATING: {RunStatus.REMEDIATING, RunStatus.ROUTING_ACTION},
    RunStatus.REMEDIATING: {RunStatus.VERIFYING},
    RunStatus.VERIFYING: {RunStatus.ROUTING_ACTION},
    RunStatus.ROUTING_ACTION: {RunStatus.COMPLETE},
}


def start_stage(
    run: AuditRun,
    status: RunStatus,
    *,
    title: str,
    detail: str,
    system: str,
) -> None:
    current = RunStatus(run.status)
    if current in _TERMINAL or status not in _ALLOWED.get(current, set()):
        raise InvalidTransition(f"Invalid audit transition: {current} -> {status}")
    run.status = status
    now = utc_now()
    run.updated_at = now
    run.events.append(
        RunEvent(
            id=f"{run.id}:event:{len(run.events) + 1:02d}",
            stage=status.value,
            state=EventState.RUNNING,
            title=title,
            detail=detail,
            at=now,
            system=system,
        )
    )


def finish_stage(run: AuditRun, detail: str) -> None:
    if not run.events or run.events[-1].state != EventState.RUNNING:
        raise InvalidTransition("There is no running event to finish")
    run.events[-1].state = EventState.SUCCEEDED
    run.events[-1].detail = detail
    run.updated_at = utc_now()


def fail_run(
    run: AuditRun,
    status: RunStatus,
    *,
    detail: str,
    retryable: bool,
    side_effects_uncertain: bool = False,
) -> None:
    if status not in {RunStatus.FAILED_RETRYABLE, RunStatus.FAILED_SAFE}:
        raise InvalidTransition("Failure must use a terminal failure state")
    if RunStatus(run.status) in _TERMINAL:
        raise InvalidTransition("A terminal run cannot fail again")
    now = utc_now()
    if run.events and run.events[-1].state == EventState.RUNNING:
        run.events[-1].state = EventState.FAILED
        run.events[-1].detail = detail
    else:
        run.events.append(
            RunEvent(
                id=f"{run.id}:event:{len(run.events) + 1:02d}",
                stage=status.value,
                state=EventState.FAILED,
                title="Audit stopped safely",
                detail=detail,
                at=now,
                system="Safety boundary",
            )
        )
    run.status = status
    run.updated_at = now
    if side_effects_uncertain:
        run.limitations.append(
            "The external-action outcome is uncertain; reconcile the recorded intent "
            + ("before retrying." if retryable else "before operator resolution.")
        )
    else:
        run.limitations.append(
            "The workflow stopped without external side effects; "
            + (
                "the trigger may be retried."
                if retryable
                else "operator review is required."
            )
        )
