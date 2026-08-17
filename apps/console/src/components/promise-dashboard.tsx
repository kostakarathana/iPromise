"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { LoaderCircle, TriangleAlert } from "lucide-react";

import { ActionsPanel } from "@/components/actions-panel";
import { BrandMark } from "@/components/brand-mark";
import {
  DashboardEmpty,
  DashboardError,
  DashboardSkeleton,
} from "@/components/dashboard-states";
import { EvidencePanel } from "@/components/evidence-panel";
import { FindingSummary, PromiseSummary } from "@/components/promise-summary";
import { RunTimeline } from "@/components/run-timeline";
import {
  RepositoryConnection,
  type RepositoryConnectionState,
} from "@/components/repository-connection";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { prepareDemonstrationRun } from "@/lib/demo-data";
import {
  auditRunSchema,
  isTerminalRun,
  type AuditRun,
  type AuditStatus,
} from "@/lib/contracts";

const DEMO_STEP_DELAY_MS = 430;
const LIVE_BOOTSTRAP_POLL_DELAY_MS = 300;
const LIVE_POLL_DELAY_MS = 1_000;
const MAX_LIVE_POLLS = 120;
const PENDING_RUN_KEY = "ipromise.pendingRunIdempotencyKey";

type PresentationSource = "static-fixture" | "connected-agent";
type AuditResponse = { run: AuditRun | null; source: PresentationSource };

const INITIAL_REPOSITORY_STATE: RepositoryConnectionState = {
  phase: "loading",
  status: null,
};

const EVENT_STAGE_STATUS: Record<string, AuditStatus> = {
  CAPTURING: "CAPTURING",
  COMPILING: "COMPILING",
  BINDING: "BINDING",
  PROBING: "PROBING",
  EVALUATING: "EVALUATING",
  REMEDIATING: "REMEDIATING",
  VERIFYING: "VERIFYING",
  ROUTING_ACTION: "ROUTING_ACTION",
};

function wait(milliseconds: number) {
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
}

function syncPendingRunKey(run: AuditRun | null) {
  if (!run) return;
  if (run.status === "FAILED_RETRYABLE" || !isTerminalRun(run)) {
    window.sessionStorage.setItem(PENDING_RUN_KEY, run.idempotencyKey);
    return;
  }
  if (window.sessionStorage.getItem(PENDING_RUN_KEY) === run.idempotencyKey) {
    window.sessionStorage.removeItem(PENDING_RUN_KEY);
  }
}

async function readErrorMessage(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as {
      error?: { message?: string };
    };
    return body.error?.message ?? `Request failed (${response.status}).`;
  } catch {
    return `Request failed (${response.status}).`;
  }
}

async function fetchAuditRun(
  method: "GET" | "POST",
  idempotencyKey?: string,
): Promise<AuditResponse> {
  const response = await fetch("/api/audit", {
    method,
    headers: {
      Accept: "application/json",
      ...(idempotencyKey ? { "Idempotency-Key": idempotencyKey } : {}),
    },
    cache: "no-store",
  });

  const source: PresentationSource =
    response.headers.get("X-iPromise-Presentation") === "static-fixture"
      ? "static-fixture"
      : "connected-agent";
  if (response.status === 204) return { run: null, source };
  if (!response.ok) throw new Error(await readErrorMessage(response));
  return { run: auditRunSchema.parse(await response.json()), source };
}

function demonstrationFrame(finalRun: AuditRun, activeIndex: number): AuditRun {
  const activeEvent = finalRun.events[activeIndex];
  return {
    ...prepareDemonstrationRun(finalRun),
    status: EVENT_STAGE_STATUS[activeEvent.stage] ?? "RECEIVED",
    updatedAt: activeEvent.at,
    events: finalRun.events.map((event, index) => ({
      ...event,
      state:
        index < activeIndex
          ? event.state
          : index === activeIndex
            ? event.state === "SKIPPED"
              ? "SKIPPED"
              : "RUNNING"
            : "PENDING",
    })),
  };
}

export function PromiseDashboard() {
  const [run, setRun] = useState<AuditRun | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [presentationSource, setPresentationSource] =
    useState<PresentationSource>("static-fixture");
  const [repositoryState, setRepositoryState] =
    useState<RepositoryConnectionState>(INITIAL_REPOSITORY_STATE);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    let ignore = false;

    async function loadInitialRun() {
      try {
        const latest = await fetchAuditRun("GET");
        if (!ignore) {
          setRun(latest.run);
          setPresentationSource(latest.source);
          syncPendingRunKey(latest.run);
        }
      } catch (loadError) {
        if (!ignore) {
          setError(
            loadError instanceof Error
              ? loadError.message
              : "The latest run could not be loaded.",
          );
        }
      } finally {
        if (!ignore) setIsLoading(false);
      }
    }

    void loadInitialRun();
    return () => {
      ignore = true;
      mountedRef.current = false;
    };
  }, []);

  const retryLoad = useCallback(async () => {
    setError(null);
    setIsLoading(true);
    try {
      const latest = await fetchAuditRun("GET");
      setRun(latest.run);
      setPresentationSource(latest.source);
      syncPendingRunKey(latest.run);
    } catch (loadError) {
      setError(
        loadError instanceof Error
          ? loadError.message
          : "The latest run could not be loaded.",
      );
    } finally {
      setIsLoading(false);
    }
  }, []);

  const runAudit = useCallback(async () => {
    setError(null);
    setIsRunning(true);
    const existingKey = window.sessionStorage.getItem(PENDING_RUN_KEY);
    const idempotencyKey =
      existingKey ?? `console:${window.crypto.randomUUID()}`;
    window.sessionStorage.setItem(PENDING_RUN_KEY, idempotencyKey);

    try {
      let startRequestSettled = false;
      const startRequest = fetchAuditRun("POST", idempotencyKey)
        .then((response) => ({ response, failure: null }))
        .catch((failure: unknown) => ({ response: null, failure }))
        .finally(() => {
          startRequestSettled = true;
        });

      // The agent checkpoints each stage while the POST remains open. Poll the
      // latest run in parallel so long Gemini/control work is visibly live in
      // the ledger instead of appearing only as a terminal result.
      while (!startRequestSettled) {
        await wait(LIVE_BOOTSTRAP_POLL_DELAY_MS);
        if (!mountedRef.current || startRequestSettled) break;
        try {
          const interim = await fetchAuditRun("GET");
          if (
            interim.source === "connected-agent" &&
            interim.run?.idempotencyKey === idempotencyKey
          ) {
            setPresentationSource(interim.source);
            setRun(interim.run);
          }
        } catch {
          // The authoritative POST response below reports connection failures.
        }
      }

      const startOutcome = await startRequest;
      if (startOutcome.failure) throw startOutcome.failure;
      const started = startOutcome.response;
      if (!started) throw new Error("The audit could not be started.");
      const startedRun = started.run;
      setPresentationSource(started.source);
      if (!startedRun) {
        setRun(null);
        return;
      }

      if (started.source === "static-fixture") {
        setRun(prepareDemonstrationRun(startedRun));
        for (let index = 0; index < startedRun.events.length; index += 1) {
          if (!mountedRef.current) return;
          setRun(demonstrationFrame(startedRun, index));
          await wait(DEMO_STEP_DELAY_MS);
        }
        if (mountedRef.current) {
          setRun(startedRun);
          window.sessionStorage.removeItem(PENDING_RUN_KEY);
        }
        return;
      }

      setRun(startedRun);
      let latestRun = startedRun;
      let pollCount = 0;
      while (!isTerminalRun(latestRun) && pollCount < MAX_LIVE_POLLS) {
        await wait(LIVE_POLL_DELAY_MS);
        if (!mountedRef.current) return;
        const polled = await fetchAuditRun("GET");
        if (!polled.run) {
          throw new Error(
            "The audit status could not be confirmed. Refresh before running again.",
          );
        }
        latestRun = polled.run;
        setPresentationSource(polled.source);
        setRun(latestRun);
        pollCount += 1;
      }
      if (!isTerminalRun(latestRun)) {
        throw new Error(
          "The audit is still running. Refresh to check its latest state before starting another run.",
        );
      }
      syncPendingRunKey(latestRun);
    } catch (runError) {
      if (mountedRef.current) {
        setError(
          runError instanceof Error
            ? runError.message
            : "The audit could not be started.",
        );
      }
    } finally {
      if (mountedRef.current) setIsRunning(false);
    }
  }, []);

  if (isLoading) {
    return (
      <AppShell environment="Connecting">
        <DashboardSkeleton />
      </AppShell>
    );
  }

  if (error && !run) {
    return (
      <AppShell environment="Unavailable">
        <DashboardError message={error} onRetry={retryLoad} />
      </AppShell>
    );
  }

  if (!run) {
    const repositoryIsChanging =
      repositoryState.phase === "loading" ||
      repositoryState.phase === "updating";
    const repositoryIsRequired = Boolean(
      repositoryState.status?.configured &&
        repositoryState.status.actionsEnabled &&
        !repositoryState.status.selectedRepository,
    );
    return (
      <AppShell
        environment={
          presentationSource === "static-fixture"
            ? "Local snapshot · Sample data"
            : "Local · Synthetic data"
        }
      >
        <DashboardEmpty
          isRunDisabled={repositoryIsChanging || repositoryIsRequired}
          onRepositoryStateChange={setRepositoryState}
          onRun={runAudit}
        />
      </AppShell>
    );
  }

  const latestEvent = run.events.findLast(
    (event) => event.state === "RUNNING" || event.state === "SUCCEEDED",
  );
  const isStaticFixture = presentationSource === "static-fixture";
  const hasCloudRunProof = Boolean(
    run.mode === "cloud" &&
      run.runtime.cloudRunRevision &&
      run.runtime.executionTarget.toLowerCase().includes("cloud-run"),
  );
  const environment = hasCloudRunProof
    ? "Cloud Run · Deployment verified"
    : run.mode === "cloud"
      ? "Cloud · Deployment unverified"
      : isStaticFixture
        ? "Local snapshot · Sample data"
        : "Local · Synthetic data";
  const repositoryIsChanging =
    repositoryState.phase === "loading" ||
    repositoryState.phase === "updating";
  const repositoryIsRequired = Boolean(
    repositoryState.status?.configured &&
      repositoryState.status.actionsEnabled &&
      !repositoryState.status.selectedRepository,
  );
  const runIsInProgress = isRunning || !isTerminalRun(run);
  const isRunDisabled =
    runIsInProgress || repositoryIsChanging || repositoryIsRequired;

  return (
    <AppShell environment={environment}>
      <main className="mx-auto w-full max-w-[1120px] px-4 py-8 sm:px-6 sm:py-9">
        {error ? (
          <Alert className="mb-6 border-status-danger/20 bg-[#fff5f6]">
            <TriangleAlert
              className="mt-0.5 size-4 shrink-0 text-status-danger"
              aria-hidden="true"
            />
            <div>
              <AlertTitle>
                {isTerminalRun(run)
                  ? "Audit stopped safely"
                  : "Audit status needs confirmation"}
              </AlertTitle>
              <AlertDescription>{error}</AlertDescription>
            </div>
          </Alert>
        ) : null}

        <PromiseSummary
          run={run}
          action={
            <Button
              aria-describedby="repository-action-status"
              className="min-w-[104px]"
              disabled={isRunDisabled}
              onClick={runAudit}
              size="sm"
            >
              {runIsInProgress ? (
                <LoaderCircle
                  className="size-3.5 animate-spin motion-reduce:animate-none"
                  aria-hidden="true"
                />
              ) : null}
              {runIsInProgress
                ? "Audit running"
                : run.status === "FAILED_RETRYABLE"
                  ? "Retry audit"
                  : "Run audit"}
            </Button>
          }
        />

        <RepositoryConnection onStateChange={setRepositoryState} />

        <div className="mt-7 grid min-w-0 gap-6 border-b border-border pb-5 lg:grid-cols-[minmax(0,2fr)_minmax(260px,1fr)] lg:gap-0">
          <FindingSummary run={run} />
          <div className="border-t border-border pt-5 lg:border-l lg:border-t-0 lg:pl-8 lg:pt-0">
            <ActionsPanel run={run} />
          </div>
        </div>

        <div className="mt-7">
          <EvidencePanel run={run} />
        </div>

        <div className="mt-6">
          <RunTimeline run={run} />
        </div>

        <p className="sr-only" aria-live="polite">
          {runIsInProgress
            ? `Audit running. ${latestEvent?.title ?? "Starting"}.`
            : run.status === "COMPLETE"
              ? `Audit complete with verdict ${run.verdict}.`
              : `Audit stopped with status ${run.status}.`}
        </p>
      </main>
    </AppShell>
  );
}

function AppShell({
  children,
  environment,
}: {
  children: React.ReactNode;
  environment: string;
}) {
  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border bg-card">
        <div className="mx-auto flex h-14 w-full max-w-[1120px] items-center justify-between gap-4 px-4 sm:px-6">
          <div className="flex min-w-0 items-center gap-2.5 text-foreground">
            <BrandMark className="size-5" />
            <p className="shrink-0 text-sm font-semibold tracking-[-0.025em]">
              iPromise
            </p>
          </div>
          <span className="truncate text-right text-xs text-muted-foreground">
            {environment}
          </span>
        </div>
      </header>
      {children}
    </div>
  );
}
