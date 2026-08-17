import { ArrowUpRight, ChevronDown } from "lucide-react";

import { ButtonLink } from "@/components/ui/button";
import type { AuditAction, AuditRun } from "@/lib/contracts";

const DISPATCHABLE_STATES = new Set<AuditAction["state"]>([
  "PLANNED",
  "READY",
  "OPENED",
  "SENT",
]);

function actionOutcome(action: AuditAction): string {
  if (action.kind === "pull_request") {
    if (action.state === "OPENED") return "Draft PR opened";
    if (action.state === "READY") return "Draft PR ready";
    if (action.state === "PLANNED") return "Draft PR selected";
    if (action.state === "BLOCKED") return "Draft PR blocked";
    return "Draft PR not selected";
  }
  if (action.kind === "issue") {
    if (action.state === "OPENED") return "GitHub issue opened";
    if (action.state === "READY") return "GitHub issue ready";
    if (action.state === "PLANNED") return "GitHub issue selected";
    return "GitHub issue not selected";
  }
  if (action.state === "SENT") return "Owner email sent";
  if (action.state === "READY" || action.state === "PLANNED") {
    return "Owner email selected";
  }
  return "Owner email not selected";
}

export function ActionsPanel({ run }: { run: AuditRun }) {
  const selected = run.actions.find((action) =>
    DISPATCHABLE_STATES.has(action.state),
  );
  const otherRoutes = run.actions.filter((action) => action.id !== selected?.id);

  return (
    <section aria-labelledby="actions-heading" className="min-w-0">
      <p id="actions-heading" className="text-xs text-muted-foreground">
        Action
      </p>

      {selected ? (
        <article className="mt-1.5" data-selected="true">
          <div className="text-sm font-semibold">{actionOutcome(selected)}</div>
          <h3 className="mt-2 text-sm font-medium leading-5">
            {selected.title}
          </h3>
          {selected.reason ? (
            <p className="mt-1 text-xs leading-5 text-muted-foreground">
              {selected.reason}
            </p>
          ) : null}

          {selected.url ? (
            <ButtonLink
              className="mt-3 w-fit"
              href={selected.url}
              target="_blank"
              rel="noreferrer"
              size="sm"
            >
              Open {selected.kind === "pull_request" ? "draft PR" : "artifact"}
              <ArrowUpRight className="size-3.5" aria-hidden="true" />
            </ButtonLink>
          ) : run.mode !== "demonstration" ? (
            <p className="mt-3 text-xs text-muted-foreground">
              No external receipt recorded.
            </p>
          ) : null}
        </article>
      ) : (
        <p className="mt-1.5 text-sm text-muted-foreground">
          No action selected.
        </p>
      )}

      {otherRoutes.length > 0 ? (
        <details className="group mt-3 border-t border-border pt-2.5">
          <summary className="flex cursor-pointer list-none items-center justify-between gap-3 text-xs font-medium text-muted-foreground outline-none hover:text-foreground focus-visible:rounded-sm focus-visible:ring-2 focus-visible:ring-ring">
            Other actions
            <ChevronDown
              className="size-3.5 transition-transform duration-150 group-open:rotate-180"
              aria-hidden="true"
            />
          </summary>
          <ul className="mt-2 space-y-2.5 border-t border-border pt-2.5">
            {otherRoutes.map((action) => (
              <li key={action.id}>
                <div className="text-xs font-medium">
                  {actionOutcome(action)}
                </div>
                {action.reason ? (
                  <p className="mt-1 text-xs leading-5 text-muted-foreground">
                    {action.reason}
                  </p>
                ) : null}
              </li>
            ))}
          </ul>
        </details>
      ) : null}
    </section>
  );
}
