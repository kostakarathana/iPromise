from __future__ import annotations

import pytest

pytest.importorskip("google.adk")

from ipromise_agent.compiler import AdkVertexClaimCompiler


def test_adk_graph_builds_without_invoking_gemini() -> None:
    app = AdkVertexClaimCompiler("gemini-3.5-flash").build_app()

    assert app.name == "ipromise"
    assert type(app.root_agent).__name__ == "Workflow"
