import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ActionsPanel } from "@/components/actions-panel";
import { EvidencePanel } from "@/components/evidence-panel";
import {
  FindingSummary,
  PromiseSummary,
} from "@/components/promise-summary";
import { VerificationPanel } from "@/components/verification-panel";
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

  it("shows the exact Cloud Build verification receipt and durable proof", () => {
    const run = createDemonstrationRun();
    run.verification = {
      verifier: "Google Cloud Build red-before/green-after gate",
      baselineControl: "FAIL",
      candidateControl: "PASS",
      regressionSuite: "PASS",
      exactTreeVerified: true,
      isolated: true,
      publishable: true,
      detail: "The exact candidate tree passed the hidden control and regression suite.",
      buildId: "build-123",
      logUrl: "https://console.cloud.google.com/cloud-build/builds/build-123",
    };

    render(<VerificationPanel run={run} />);

    expect(screen.getByText("Repair verification")).toBeVisible();
    expect(screen.getByText("Red before")).toBeVisible();
    expect(screen.getByText("Expected failure")).toBeVisible();
    expect(screen.getByText("Green after")).toBeVisible();
    expect(screen.getAllByText("Passed")).toHaveLength(2);
    expect(screen.getByText("Exact tree")).toBeVisible();
    expect(screen.getByText("Matched")).toBeVisible();
    expect(screen.getByText("Publishable")).toBeVisible();
    expect(screen.getByText("Build build-123")).toBeVisible();
    expect(screen.getByRole("link", { name: /Open logs/ })).toHaveAttribute(
      "href",
      "https://console.cloud.google.com/cloud-build/builds/build-123",
    );
  });
});
