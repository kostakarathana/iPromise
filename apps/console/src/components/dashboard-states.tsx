import { RotateCcw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  RepositoryConnection,
  type RepositoryConnectionState,
} from "@/components/repository-connection";

export function DashboardSkeleton() {
  return (
    <main className="mx-auto w-full max-w-[1120px] px-4 py-9 sm:px-6">
      <Skeleton className="h-3 w-28" />
      <div className="mt-3 flex items-center justify-between gap-4">
        <Skeleton className="h-9 w-56" />
        <Skeleton className="h-8 w-24" />
      </div>
      <Skeleton className="mt-6 h-6 w-full max-w-3xl" />
      <Skeleton className="mt-2 h-4 w-2/3 max-w-xl" />
      <div className="mt-8 grid gap-6 border-y border-border py-5 lg:grid-cols-[2fr_1fr]">
        <Skeleton className="h-20 w-full" />
        <Skeleton className="h-20 w-full" />
      </div>
      <Skeleton className="mt-8 h-40 w-full" />
      <span className="sr-only">Loading promise audits</span>
    </main>
  );
}

export function DashboardEmpty({
  isRunDisabled,
  onRepositoryStateChange,
  onRun,
}: {
  isRunDisabled: boolean;
  onRepositoryStateChange: (state: RepositoryConnectionState) => void;
  onRun: () => void;
}) {
  return (
    <main className="mx-auto w-full max-w-[1120px] px-4 py-8 sm:px-6 sm:py-9">
      <RepositoryConnection onStateChange={onRepositoryStateChange} />
      <div className="mt-16 max-w-md border-t border-border pt-6 sm:mt-20">
        <h1 className="text-xl font-semibold tracking-[-0.025em]">
          No audits yet
        </h1>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">
          Compare account-deletion behavior with the published privacy promise.
        </p>
        <Button
          aria-describedby="repository-action-status"
          className="mt-6"
          disabled={isRunDisabled}
          onClick={onRun}
        >
          Run audit
        </Button>
      </div>
    </main>
  );
}

export function DashboardError({
  message,
  onRetry,
}: {
  message: string;
  onRetry: () => void;
}) {
  return (
    <main className="mx-auto w-full max-w-[1120px] px-4 py-24 sm:px-6">
      <div className="max-w-md border-t border-status-danger pt-6">
        <h1 className="text-xl font-semibold tracking-[-0.025em]">
          Audit service unavailable
        </h1>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">
          {message} No action was taken.
        </p>
        <Button className="mt-6" onClick={onRetry}>
          <RotateCcw className="size-4" aria-hidden="true" />
          Retry
        </Button>
      </div>
    </main>
  );
}
