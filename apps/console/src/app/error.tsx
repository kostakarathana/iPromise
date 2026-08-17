"use client";

import { AlertTriangle, RotateCcw } from "lucide-react";

import { Button } from "@/components/ui/button";

export default function ErrorPage({ reset }: { reset: () => void }) {
  return (
    <main className="grid min-h-screen place-items-center px-6">
      <div className="max-w-sm text-center">
        <div className="mx-auto mb-4 grid size-10 place-items-center rounded-full border border-status-danger/25 bg-status-danger/10 text-status-danger">
          <AlertTriangle className="size-5" aria-hidden="true" />
        </div>
        <h1 className="text-lg font-semibold">The ledger could not open</h1>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">
          The console hit an unexpected error. No audit action was taken.
        </p>
        <Button className="mt-5" onClick={reset}>
          <RotateCcw className="size-4" aria-hidden="true" />
          Try again
        </Button>
      </div>
    </main>
  );
}
