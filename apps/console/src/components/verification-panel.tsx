import { ExternalLink } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import type { AuditRun } from "@/lib/contracts";
import { cn } from "@/lib/utils";

type Verification = NonNullable<AuditRun["verification"]>;
type ReceiptResult = Verification["baselineControl"];

const RESULT_LABELS: Record<ReceiptResult, string> = {
  PASS: "Passed",
  FAIL: "Failed",
  NOT_RUN: "Not run",
};

const RESULT_STYLES: Record<ReceiptResult, string> = {
  PASS: "text-status-success",
  FAIL: "text-status-danger",
  NOT_RUN: "text-muted-foreground",
};

function ReceiptCheck({
  label,
  result,
  expectedFailure = false,
}: {
  label: string;
  result: ReceiptResult;
  expectedFailure?: boolean;
}) {
  const resultLabel =
    expectedFailure && result === "FAIL"
      ? "Expected failure"
      : RESULT_LABELS[result];

  return (
    <div className="min-w-0 border-t border-border px-3 py-3 sm:border-l sm:border-t-0 sm:first:border-l-0">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd
        className={cn(
          "mt-1.5 flex items-center gap-2 text-sm font-medium",
          RESULT_STYLES[result],
        )}
      >
        <span className="size-1.5 shrink-0 rounded-full bg-current" aria-hidden="true" />
        {resultLabel}
      </dd>
    </div>
  );
}

export function VerificationPanel({ run }: { run: AuditRun }) {
  const verification = run.verification;
  if (!verification) return null;

  return (
    <section aria-labelledby="verification-heading" className="min-w-0">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 id="verification-heading" className="text-sm font-semibold">
            Repair verification
          </h2>
          <p className="mt-1 text-xs text-muted-foreground">
            {verification.verifier}
          </p>
        </div>
        <Badge variant={verification.publishable ? "success" : "warning"}>
          {verification.publishable ? "Publishable" : "Blocked"}
        </Badge>
      </div>

      <dl className="mt-3 grid border-y border-border bg-card sm:grid-cols-4">
        <ReceiptCheck
          label="Red before"
          result={verification.baselineControl}
          expectedFailure
        />
        <ReceiptCheck label="Green after" result={verification.candidateControl} />
        <ReceiptCheck label="Regression" result={verification.regressionSuite} />
        <div className="min-w-0 border-t border-border px-3 py-3 sm:border-l sm:border-t-0">
          <dt className="text-xs text-muted-foreground">Exact tree</dt>
          <dd
            className={cn(
              "mt-1.5 flex items-center gap-2 text-sm font-medium",
              verification.exactTreeVerified
                ? "text-status-success"
                : "text-status-danger",
            )}
          >
            <span
              className="size-1.5 shrink-0 rounded-full bg-current"
              aria-hidden="true"
            />
            {verification.exactTreeVerified ? "Matched" : "Not matched"}
          </dd>
        </div>
      </dl>

      <div className="mt-3 flex flex-col gap-2 text-xs text-muted-foreground sm:flex-row sm:items-start sm:justify-between">
        <p className="max-w-3xl leading-5">{verification.detail}</p>
        {verification.buildId ? (
          <div className="flex shrink-0 items-center gap-2 font-mono">
            <span>Build {verification.buildId}</span>
            {verification.logUrl ? (
              <a
                className="inline-flex items-center gap-1 font-sans font-medium text-link underline-offset-4 hover:underline focus-visible:rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                href={verification.logUrl}
                target="_blank"
                rel="noreferrer"
              >
                Open logs
                <ExternalLink className="size-3" aria-hidden="true" />
              </a>
            ) : null}
          </div>
        ) : null}
      </div>
    </section>
  );
}
