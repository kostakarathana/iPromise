import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { AuditRun, Evidence } from "@/lib/contracts";
import { cn } from "@/lib/utils";

const RESULT_STYLES: Record<Evidence["result"], string> = {
  PASS: "text-status-success",
  FAIL: "text-status-danger",
  UNKNOWN: "text-muted-foreground",
};

const RESULT_LABELS: Record<Evidence["result"], string> = {
  PASS: "Passed",
  FAIL: "Failed",
  UNKNOWN: "Unknown",
};

const RESULT_ORDER: Record<Evidence["result"], number> = {
  FAIL: 0,
  UNKNOWN: 1,
  PASS: 2,
};

function Result({ result }: { result: Evidence["result"] }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-2 text-xs font-semibold",
        RESULT_STYLES[result],
      )}
    >
      <span className="size-1.5 rounded-full bg-current" aria-hidden="true" />
      {RESULT_LABELS[result]}
    </span>
  );
}

function conciseEvidence(item: Evidence) {
  // An UNKNOWN result means the control did not establish an observation. Keep
  // the backend's evidence verbatim so the presentation layer cannot make an
  // inconclusive check look like a successful one.
  if (item.result === "UNKNOWN") {
    return {
      label: item.label,
      expected: item.expected,
      observed: item.observed,
    };
  }
  if (item.id === "analytics-profile" || item.id === "analytics-store") {
    return {
      label: "Analytics profile",
      expected: "Removed within 24h",
      observed:
        item.result === "FAIL" ? "1 active record at 25h" : "No active record",
    };
  }
  if (item.id === "app-profile" || item.id === "profile-store") {
    return {
      label: "App profile",
      expected: "Removed within 24h",
      observed:
        item.result === "PASS" ? "No active record" : item.observed,
    };
  }
  if (item.id === "synthetic-virtual-timeline") {
    return {
      label: "Deletion timeline",
      expected: "Worker before deadline",
      observed: "Ran at +1h · checked at +25h",
    };
  }
  return {
    label: item.label,
    expected: item.expected,
    observed: item.observed,
  };
}

export function EvidencePanel({ run }: { run: AuditRun }) {
  const evidence = run.evidence.toSorted(
    (left, right) => RESULT_ORDER[left.result] - RESULT_ORDER[right.result],
  );

  return (
    <section aria-labelledby="evidence-heading" className="min-w-0">
      <div className="flex items-end justify-between gap-4">
        <h2 id="evidence-heading" className="text-sm font-semibold">
          Evidence
        </h2>
        <span className="shrink-0 text-xs text-muted-foreground">
          {run.evidence.length} checks
        </span>
      </div>

      <div className="mt-3 hidden border-y border-border bg-card sm:block">
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              <TableHead>Check</TableHead>
              <TableHead>Expected</TableHead>
              <TableHead>Observed</TableHead>
              <TableHead className="w-24 text-right">Result</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {evidence.map((item) => {
              const display = conciseEvidence(item);
              return (
                <TableRow key={item.id} className="hover:bg-secondary/30">
                  <TableCell
                    className={cn(
                      "w-[32%] font-medium",
                      item.result === "FAIL"
                        ? "border-l-2 border-l-status-danger pl-[14px]"
                        : "border-l-2 border-l-transparent pl-[14px]",
                    )}
                  >
                    {display.label}
                  </TableCell>
                  <TableCell className="w-[27%] text-muted-foreground">
                    {display.expected}
                  </TableCell>
                  <TableCell className="w-[29%] font-medium">
                    {display.observed}
                  </TableCell>
                  <TableCell className="text-right">
                    <Result result={item.result} />
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>

      <div className="mt-3 divide-y divide-border border-y border-border bg-card sm:hidden">
        {evidence.map((item) => {
          const display = conciseEvidence(item);
          return (
            <article
              className={cn(
                "border-l-2 px-3 py-4",
                item.result === "FAIL"
                  ? "border-l-status-danger"
                  : "border-l-transparent",
              )}
              key={item.id}
            >
              <div className="flex items-start justify-between gap-3">
                <h3 className="text-sm font-medium">{display.label}</h3>
                <Result result={item.result} />
              </div>
              <dl className="mt-3 grid gap-2 text-xs leading-5">
                <div className="grid grid-cols-[68px_minmax(0,1fr)] gap-3">
                  <dt className="text-muted-foreground">Expected</dt>
                  <dd>{display.expected}</dd>
                </div>
                <div className="grid grid-cols-[68px_minmax(0,1fr)] gap-3">
                  <dt className="text-muted-foreground">Observed</dt>
                  <dd className="font-medium">{display.observed}</dd>
                </div>
              </dl>
            </article>
          );
        })}
      </div>
    </section>
  );
}
