import { ExternalLink } from "lucide-react";

import type { AuditRun, Verdict } from "@/lib/contracts";
import { cn, formatTime } from "@/lib/utils";

const VERDICT_LABELS: Record<Verdict, string> = {
  PENDING: "Pending",
  SUPPORTED: "Supported",
  CONTRADICTED: "Contradicted",
  INCONCLUSIVE: "Inconclusive",
  NOT_TESTED: "Not tested",
};

const VERDICT_STYLES: Record<Verdict, string> = {
  PENDING: "text-status-info",
  SUPPORTED: "text-status-success",
  CONTRADICTED: "text-status-danger",
  INCONCLUSIVE: "text-status-warning",
  NOT_TESTED: "text-muted-foreground",
};

function findingCopy(run: AuditRun): { detail: string; title: string } {
  const failedEvidence = run.evidence.find((item) => item.result === "FAIL");

  if (run.verdict === "CONTRADICTED" && failedEvidence) {
    return {
      title: "Deletion failed in analytics",
      detail: `${failedEvidence.observed}. Expected: ${failedEvidence.expected.toLowerCase()}.`,
    };
  }
  if (run.verdict === "SUPPORTED") {
    return {
      title: "All configured checks passed",
      detail: "Limited to these systems and this run.",
    };
  }
  if (run.verdict === "INCONCLUSIVE") {
    return {
      title: "Evidence was incomplete",
      detail: "No action was selected.",
    };
  }
  if (run.verdict === "NOT_TESTED") {
    return {
      title: "No approved control",
      detail: "The promise was recorded; product behavior was not tested.",
    };
  }
  return {
    title: "Audit in progress",
    detail: "Waiting for required evidence.",
  };
}

export function PromiseSummary({
  action,
  run,
}: {
  action?: React.ReactNode;
  run: AuditRun;
}) {
  return (
    <section aria-labelledby="promise-heading" className="min-w-0">
      <p className="text-xs text-muted-foreground">Promises / Privacy</p>

      <div className="mt-2 flex items-start justify-between gap-4">
        <div className="flex min-w-0 flex-wrap items-baseline gap-x-4 gap-y-2">
          <h1
            id="promise-heading"
            className="text-[28px] font-semibold leading-9 tracking-[-0.035em]"
          >
            Account deletion
          </h1>
          <span
            className={cn(
              "inline-flex items-center gap-2 text-xs font-semibold",
              VERDICT_STYLES[run.verdict],
            )}
          >
            <span
              className="size-1.5 rounded-full bg-current"
              aria-hidden="true"
            />
            {VERDICT_LABELS[run.verdict]}
          </span>
        </div>
        {action ? <div className="shrink-0">{action}</div> : null}
      </div>

      <blockquote className="mt-5 max-w-4xl border-l-2 border-border pl-4 text-[15px] leading-6 text-foreground">
        “{run.claim.exactQuote}”
      </blockquote>

      <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
        <a
          className="inline-flex items-center gap-1 font-medium text-link underline-offset-4 hover:underline focus-visible:rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          href={run.claim.sourceUrl}
          target="_blank"
          rel="noreferrer"
        >
          {run.claim.sourceTitle}
          <ExternalLink className="size-3" aria-hidden="true" />
        </a>
        <span aria-hidden="true">·</span>
        <span>Checked {formatTime(run.updatedAt)}</span>
        <span aria-hidden="true">·</span>
        <span>24-hour deadline</span>
      </div>
    </section>
  );
}

export function FindingSummary({ run }: { run: AuditRun }) {
  const finding = findingCopy(run);

  return (
    <section aria-labelledby="finding-heading" className="flex min-w-0 gap-4">
      <span
        className={cn(
          "h-10 w-0.5 shrink-0 rounded-full",
          run.verdict === "CONTRADICTED"
            ? "bg-status-danger"
            : run.verdict === "SUPPORTED"
              ? "bg-status-success"
              : "bg-border",
        )}
        aria-hidden="true"
      />
      <div className="min-w-0">
        <p className="text-xs text-muted-foreground">Finding</p>
        <h2 id="finding-heading" className="mt-1.5 text-base font-semibold">
          {finding.title}
        </h2>
        <p className="mt-1.5 max-w-2xl text-sm leading-5 text-muted-foreground">
          {finding.detail}
        </p>
      </div>
    </section>
  );
}
