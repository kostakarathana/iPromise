import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ActionsPanel } from "@/components/actions-panel";
import { EvidencePanel } from "@/components/evidence-panel";
import {
  FindingSummary,
  PromiseSummary,
} from "@/components/promise-summary";
import { createDemonstrationRun } from "@/lib/demo-data";

describe("Promise Ledger", () => {
  it("shows the exact source claim and scoped verdict language", () => {
    const run = createDemonstrationRun();
    const { container } = render(
      <>
        <PromiseSummary run={run} />
        <FindingSummary run={run} />
      </>,
    );

    expect(screen.getByText(run.claim.exactQuote, { exact: false })).toBeVisible();
    expect(screen.getByText("Contradicted")).toBeVisible();
    expect(screen.getByText(/Expected:/)).toBeVisible();
    expect(container.textContent).not.toContain("COMPLIANT");
  });

  it("selects the issue fallback when a draft PR cannot be verified", () => {
    const run = createDemonstrationRun();
    render(<ActionsPanel run={run} />);

    expect(screen.getByText("Draft PR not selected")).toBeInTheDocument();
    expect(screen.getByText("Owner email not selected")).toBeInTheDocument();
    expect(
      screen.getByText("GitHub issue selected").closest("article"),
    ).toHaveAttribute("data-selected", "true");
  });

  it("preserves unknown analytics and timeline observations verbatim", () => {
    const run = createDemonstrationRun();
    run.evidence = [
      {
        id: "analytics-store",
        label: "Analytics deletion probe",
        expected: "A conclusive analytics query",
        observed: "Analytics API timed out; no observation was established",
        result: "UNKNOWN",
      },
      {
        id: "synthetic-virtual-timeline",
        label: "Timeline reconstruction",
        expected: "A complete event sequence",
        observed: "Worker timestamp was unavailable",
        result: "UNKNOWN",
      },
    ];

    render(<EvidencePanel run={run} />);

    expect(
      screen.getAllByText(
        "Analytics API timed out; no observation was established",
      ),
    ).toHaveLength(2);
    expect(screen.getAllByText("Worker timestamp was unavailable")).toHaveLength(
      2,
    );
    expect(screen.queryByText("No active record")).not.toBeInTheDocument();
    expect(
      screen.queryByText("Ran at +1h · checked at +25h"),
    ).not.toBeInTheDocument();
  });
});
