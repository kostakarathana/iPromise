from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

pytest.importorskip("google.adk")

from ipromise_agent.compiler import (
    MAX_ADK_COMPILE_TIMEOUT_SECONDS,
    AdkVertexClaimCompiler,
    ClaimCompilationError,
)
from ipromise_agent.models import utc_now
from ipromise_agent.source import CapturedSource


class _StalledRunner:
    def __init__(self, *, emit_model_event: bool) -> None:
        self.emit_model_event = emit_model_event
        self.session_service = self
        self.stream_cancelled = asyncio.Event()

    async def create_session(self, **_kwargs):
        return SimpleNamespace(id="stalled-session")

    async def run_async(self, **_kwargs):
        try:
            if self.emit_model_event:
                yield SimpleNamespace(
                    author="promise_compiler",
                    output={"partial": "model output"},
                    content=None,
                )
            await asyncio.Event().wait()
        finally:
            self.stream_cancelled.set()


def _capture() -> CapturedSource:
    return CapturedSource(
        url="https://synthetic.example.test/privacy",
        title="Synthetic privacy promise",
        captured_at=utc_now(),
        content_hash="sha256:test-capture",
        html="<p>Delete active account data within 24 hours.</p>",
        visible_text="Delete active account data within 24 hours.",
    )


def test_adk_graph_builds_without_invoking_gemini() -> None:
    app = AdkVertexClaimCompiler("gemini-3.5-flash").build_app()

    assert app.name == "ipromise"
    assert type(app.root_agent).__name__ == "Workflow"


@pytest.mark.parametrize(
    ("emit_model_event", "expected_model_invoked"),
    [(False, False), (True, True)],
)
@pytest.mark.asyncio
async def test_adk_compile_timeout_cancels_stream_and_preserves_provenance(
    monkeypatch,
    emit_model_event: bool,
    expected_model_invoked: bool,
) -> None:
    runner = _StalledRunner(emit_model_event=emit_model_event)
    compiler = AdkVertexClaimCompiler(
        "gemini-3.5-flash",
        timeout_seconds=0.02,
    )
    monkeypatch.setattr(compiler, "build_app", lambda: object())
    monkeypatch.setattr(
        "google.adk.runners.InMemoryRunner",
        lambda *, app: runner,
    )

    with pytest.raises(ClaimCompilationError, match="exceeded.*deadline") as raised:
        await compiler.compile(_capture())

    assert raised.value.retryable is True
    assert raised.value.model_invoked is expected_model_invoked
    assert raised.value.model == (
        "gemini-3.5-flash" if expected_model_invoked else None
    )
    assert raised.value.framework == "Google Agent Development Kit 2 Graph Workflow"
    assert isinstance(raised.value.__cause__, TimeoutError)
    assert runner.stream_cancelled.is_set()


@pytest.mark.parametrize("timeout_seconds", [0, -1, float("nan"), 120.01])
def test_adk_compile_timeout_cannot_exceed_bounded_maximum(
    timeout_seconds: float,
) -> None:
    with pytest.raises(ValueError, match="no more than"):
        AdkVertexClaimCompiler(
            "gemini-3.5-flash",
            timeout_seconds=timeout_seconds,
        )

    assert MAX_ADK_COMPILE_TIMEOUT_SECONDS == 120
