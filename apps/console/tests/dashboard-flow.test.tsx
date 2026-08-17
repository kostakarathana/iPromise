import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { PromiseDashboard } from "@/components/promise-dashboard";
import { createDemonstrationRun } from "@/lib/demo-data";

function auditResponse(
  run: ReturnType<typeof createDemonstrationRun>,
  source: "static-fixture" | "connected-agent",
  status = 200,
) {
  return new Response(JSON.stringify(run), {
    status,
    headers: {
      "Content-Type": "application/json",
      "X-iPromise-Presentation": source,
    },
  });
}

function githubStatusResponse(
  overrides: Partial<{
    configured: boolean;
    connected: boolean;
    actionsEnabled: boolean;
    accountLogin: string | null;
    repositories: Array<Record<string, unknown>>;
    selectedRepository: Record<string, unknown> | null;
  }> = {},
) {
  return Response.json({
    configured: false,
    connected: false,
    actionsEnabled: false,
    accountLogin: null,
    repositories: [],
    selectedRepository: null,
    ...overrides,
  });
}

describe("Promise Dashboard presentation provenance", () => {
  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
    window.sessionStorage.clear();
  });

  it("labels the unconnected route as a local snapshot", async () => {
    const fetchMock = vi.fn().mockImplementation((input: RequestInfo | URL) =>
      String(input).includes("/api/integrations/github")
        ? Promise.resolve(githubStatusResponse())
        : Promise.resolve(
            auditResponse(createDemonstrationRun(), "static-fixture"),
          ),
    );
    vi.stubGlobal("fetch", fetchMock);

    render(<PromiseDashboard />);

    expect(
      await screen.findByText(
        "Local snapshot · Sample data",
      ),
    ).toBeVisible();
    expect(screen.getByRole("button", { name: "Run audit" })).toBeVisible();
  });

  it("does not replay a connected synchronous agent result as live progress", async () => {
    const connectedRun = createDemonstrationRun();
    connectedRun.runtime = {
      agentFramework:
        "Deterministic local workflow · Google ADK not used",
      modelInvocationAttempted: false,
      modelInvoked: false,
      model: null,
      executionTarget: "local-process",
      cloudRunRevision: null,
    };

    const fetchMock = vi.fn().mockImplementation(
      (input: RequestInfo | URL, init?: RequestInit) => {
        if (String(input).includes("/api/integrations/github")) {
          return Promise.resolve(githubStatusResponse());
        }
        if (init?.method === "POST") {
          return Promise.resolve(
            auditResponse(connectedRun, "connected-agent", 202),
          );
        }
        return Promise.resolve(
          new Response(null, {
            status: 204,
            headers: { "X-iPromise-Presentation": "connected-agent" },
          }),
        );
      },
    );
    vi.stubGlobal("fetch", fetchMock);

    render(<PromiseDashboard />);
    const runButton = await screen.findByRole("button", { name: "Run audit" });
    await waitFor(() => expect(runButton).toBeEnabled());
    fireEvent.click(runButton);

    expect(
      await screen.findByText(
        "Local · Synthetic data",
      ),
    ).toBeVisible();
    expect(
      screen.queryByText(
        "Local snapshot · Sample data",
      ),
    ).not.toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Run audit" })).toBeEnabled();
    });
    const auditCalls = fetchMock.mock.calls.filter(
      ([input]) => !String(input).includes("/api/integrations/github"),
    );
    expect(auditCalls).toHaveLength(2);
  });

  it("shows Firestore-checkpointed progress while the start request is open", async () => {
    const initial = createDemonstrationRun();
    const pending = createDemonstrationRun();
    pending.status = "PROBING";
    pending.verdict = "PENDING";
    const complete = createDemonstrationRun();
    let auditGets = 0;
    let resolveStart!: (response: Response) => void;
    const startResponse = new Promise<Response>((resolve) => {
      resolveStart = resolve;
    });

    const fetchMock = vi.fn().mockImplementation(
      (input: RequestInfo | URL, init?: RequestInit) => {
        if (String(input).includes("/api/integrations/github")) {
          return Promise.resolve(githubStatusResponse());
        }
        if (init?.method === "POST") {
          const key = new Headers(init.headers).get("Idempotency-Key") ?? "";
          pending.idempotencyKey = key;
          complete.idempotencyKey = key;
          complete.id = pending.id;
          return startResponse;
        }
        auditGets += 1;
        return Promise.resolve(
          auditResponse(
            auditGets === 1 ? initial : pending,
            "connected-agent",
          ),
        );
      },
    );
    vi.stubGlobal("fetch", fetchMock);

    render(<PromiseDashboard />);
    const runButton = await screen.findByRole("button", { name: "Run audit" });
    await waitFor(() => expect(runButton).toBeEnabled());
    fireEvent.click(runButton);

    expect(await screen.findByText("Audit in progress")).toBeVisible();
    expect(screen.getByRole("button", { name: "Audit running" })).toBeDisabled();

    resolveStart(auditResponse(complete, "connected-agent", 202));
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Run audit" })).toBeEnabled();
    });
    expect(auditGets).toBeGreaterThanOrEqual(2);
  });

  it("never treats cloud configuration alone as deployment proof", async () => {
    const configuredOnly = createDemonstrationRun();
    configuredOnly.mode = "cloud";
    configuredOnly.runtime.executionTarget = "local-process";
    configuredOnly.runtime.cloudRunRevision = null;
    const fetchMock = vi.fn().mockImplementation((input: RequestInfo | URL) =>
      String(input).includes("/api/integrations/github")
        ? Promise.resolve(githubStatusResponse())
        : Promise.resolve(auditResponse(configuredOnly, "connected-agent")),
    );
    vi.stubGlobal("fetch", fetchMock);

    render(<PromiseDashboard />);

    expect(
      await screen.findByText("Cloud · Deployment unverified"),
    ).toBeVisible();
    expect(
      screen.queryByText("Cloud Run · Deployment verified"),
    ).not.toBeInTheDocument();
  });

  it("requires a selected repository when real issue creation is enabled", async () => {
    const repository = {
      id: 101,
      fullName: "octocat/alpha",
      defaultBranch: "main",
      private: true,
      archived: false,
      htmlUrl: "https://github.com/octocat/alpha",
    };
    const fetchMock = vi.fn().mockImplementation((input: RequestInfo | URL) =>
      String(input).includes("/api/integrations/github")
        ? Promise.resolve(
            githubStatusResponse({
              configured: true,
              connected: true,
              actionsEnabled: true,
              accountLogin: "octocat",
              repositories: [repository],
              selectedRepository: null,
            }),
          )
        : Promise.resolve(
            auditResponse(createDemonstrationRun(), "connected-agent"),
          ),
    );
    vi.stubGlobal("fetch", fetchMock);

    render(<PromiseDashboard />);

    expect(
      await screen.findByText(
        "Select a repository before running an action-ready audit.",
      ),
    ).toBeVisible();
    expect(screen.getByRole("button", { name: "Run audit" })).toBeDisabled();
  });

  it("keeps audits available while truthfully disclosing that actions are off", async () => {
    const fetchMock = vi.fn().mockImplementation((input: RequestInfo | URL) =>
      String(input).includes("/api/integrations/github")
        ? Promise.resolve(
            githubStatusResponse({
              configured: true,
              connected: false,
              actionsEnabled: false,
            }),
          )
        : Promise.resolve(
            auditResponse(createDemonstrationRun(), "connected-agent"),
          ),
    );
    vi.stubGlobal("fetch", fetchMock);

    render(<PromiseDashboard />);

    expect(
      await screen.findByText(
        "Issue creation is off. Audits will only record a proposed action.",
      ),
    ).toBeVisible();
    expect(screen.getByRole("button", { name: "Run audit" })).toBeEnabled();
  });

  it("does not announce completion when live polling reaches its limit", async () => {
    const completed = createDemonstrationRun();
    const pending = createDemonstrationRun();
    pending.status = "PROBING";
    pending.verdict = "PENDING";
    let auditGets = 0;
    const fetchMock = vi.fn().mockImplementation(
      (input: RequestInfo | URL, init?: RequestInit) => {
        if (String(input).includes("/api/integrations/github")) {
          return Promise.resolve(githubStatusResponse());
        }
        if (init?.method === "POST") {
          return Promise.resolve(auditResponse(pending, "connected-agent", 202));
        }
        auditGets += 1;
        return Promise.resolve(
          auditResponse(
            auditGets === 1 ? completed : pending,
            "connected-agent",
          ),
        );
      },
    );
    vi.stubGlobal("fetch", fetchMock);

    render(<PromiseDashboard />);
    const runButton = await screen.findByRole("button", { name: "Run audit" });
    await waitFor(() => expect(runButton).toBeEnabled());

    vi.useFakeTimers();
    fireEvent.click(runButton);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(121_000);
    });

    expect(screen.getByText("Audit status needs confirmation")).toBeVisible();
    expect(
      screen.getByText(/The audit is still running\./),
    ).toBeVisible();
    expect(
      screen.getByRole("button", { name: "Audit running" }),
    ).toBeDisabled();
    expect(
      screen.queryByText("Audit complete with verdict PENDING."),
    ).not.toBeInTheDocument();
  });

  it("reuses the same manual idempotency key for a retryable run", async () => {
    const retryable = createDemonstrationRun();
    retryable.status = "FAILED_RETRYABLE";
    retryable.verdict = "INCONCLUSIVE";
    const complete = createDemonstrationRun();
    const postedKeys: string[] = [];
    let postCount = 0;
    const fetchMock = vi.fn().mockImplementation(
      (input: RequestInfo | URL, init?: RequestInit) => {
        if (String(input).includes("/api/integrations/github")) {
          return Promise.resolve(githubStatusResponse());
        }
        if (init?.method === "POST") {
          const key = new Headers(init.headers).get("Idempotency-Key") ?? "";
          postedKeys.push(key);
          postCount += 1;
          const result = postCount === 1 ? retryable : complete;
          result.idempotencyKey = key;
          complete.id = retryable.id;
          return Promise.resolve(auditResponse(result, "connected-agent", 202));
        }
        return Promise.resolve(
          new Response(null, {
            status: 204,
            headers: { "X-iPromise-Presentation": "connected-agent" },
          }),
        );
      },
    );
    vi.stubGlobal("fetch", fetchMock);

    render(<PromiseDashboard />);
    const runButton = await screen.findByRole("button", { name: "Run audit" });
    await waitFor(() => expect(runButton).toBeEnabled());
    fireEvent.click(runButton);

    const retryButton = await screen.findByRole("button", { name: "Retry audit" });
    fireEvent.click(retryButton);
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Run audit" })).toBeEnabled();
    });

    expect(postedKeys).toHaveLength(2);
    expect(postedKeys[0]).toMatch(/^console:/);
    expect(postedKeys[1]).toBe(postedKeys[0]);
    expect(window.sessionStorage.getItem("ipromise.pendingRunIdempotencyKey")).toBeNull();
  });
});
