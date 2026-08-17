import { ChevronDown } from "lucide-react";

import type { AuditEvent, AuditRun } from "@/lib/contracts";
import { cn, formatTime } from "@/lib/utils";

const EVENT_STYLES: Record<AuditEvent["state"], string> = {
  PENDING: "bg-muted-foreground",
  RUNNING: "bg-status-info",
  SUCCEEDED: "bg-status-success",
  FAILED: "bg-status-danger",
  SKIPPED: "bg-muted-foreground",
};

const EVENT_LABELS: Record<AuditEvent["state"], string> = {
  PENDING: "Pending",
  RUNNING: "Running",
  SUCCEEDED: "Completed",
  FAILED: "Failed",
  SKIPPED: "Skipped",
};

function elapsedTime(run: AuditRun) {
  const milliseconds = Math.max(
    0,
    new Date(run.updatedAt).getTime() - new Date(run.startedAt).getTime(),
  );
  if (milliseconds < 1_000) return `${milliseconds}ms`;
  return `${Math.round(milliseconds / 1_000)}s`;
}

export function RunTimeline({ run }: { run: AuditRun }) {
  return (
    <section aria-label="Audit activity" className="border-y border-border">
      <details className="group">
        <summary className="flex cursor-pointer list-none items-center justify-between gap-4 py-3 text-sm font-medium outline-none hover:text-link focus-visible:rounded-sm focus-visible:ring-2 focus-visible:ring-ring">
          <span>Activity</span>
          <span className="inline-flex items-center gap-3 text-xs font-normal text-muted-foreground">
            {run.events.length} steps · {elapsedTime(run)}
            <ChevronDown
              className="size-3.5 transition-transform duration-150 group-open:rotate-180"
              aria-hidden="true"
            />
          </span>
        </summary>

        <div className="border-t border-border pb-5 pt-1">
          <ol className="divide-y divide-border">
            {run.events.map((event) => (
              <li
                className="grid gap-1 py-3 sm:grid-cols-[10px_minmax(0,1fr)_auto] sm:gap-x-3"
                key={event.id}
              >
                <span
                  className={cn(
                    "mt-[7px] hidden size-1.5 rounded-full sm:block",
                    EVENT_STYLES[event.state],
                    event.state === "RUNNING" && "animate-pulse",
                  )}
                  aria-hidden="true"
                />
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span
                      className={cn(
                        "size-1.5 rounded-full sm:hidden",
                        EVENT_STYLES[event.state],
                      )}
                      aria-hidden="true"
                    />
                    <p className="text-sm font-medium">{event.title}</p>
                  </div>
                  {event.detail ? (
                    <p className="mt-0.5 text-xs leading-5 text-muted-foreground">
                      {event.detail}
                    </p>
                  ) : null}
                </div>
                <span className="text-xs text-muted-foreground sm:pt-0.5">
                  {EVENT_LABELS[event.state]}
                  {event.state !== "PENDING" ? ` · ${formatTime(event.at)}` : ""}
                </span>
              </li>
            ))}
          </ol>

          <div className="mt-5 border-t border-border pt-5">
            <h2 className="text-sm font-semibold">Technical details</h2>
            <dl className="mt-3 grid gap-x-8 gap-y-3 text-xs sm:grid-cols-2">
              <div>
                <dt className="text-muted-foreground">Run ID</dt>
                <dd className="mt-0.5 break-all font-mono">{run.id}</dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Control</dt>
                <dd className="mt-0.5 break-all font-mono">
                  {run.claim.controlId ?? "No approved control"}
                </dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Workflow</dt>
                <dd className="mt-0.5">{run.runtime.agentFramework}</dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Runtime</dt>
                <dd className="mt-0.5">{run.runtime.executionTarget}</dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Model</dt>
                <dd className="mt-0.5">
                  {run.runtime.modelInvoked ? run.runtime.model : "Not used"}
                </dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Updated</dt>
                <dd className="mt-0.5">{formatTime(run.updatedAt)}</dd>
              </div>
            </dl>

            <p className="mt-4 border-t border-border pt-4 text-xs leading-5 text-muted-foreground">
              Results apply only to the systems and time shown. They are not
              legal conclusions.
            </p>
          </div>
        </div>
      </details>
    </section>
  );
}
