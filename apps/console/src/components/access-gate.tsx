"use client";

import { FormEvent, useState } from "react";
import { LoaderCircle } from "lucide-react";

import { BrandMark } from "@/components/brand-mark";
import { Button } from "@/components/ui/button";

export function AccessGate() {
  const [accessCode, setAccessCode] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);
    try {
      const response = await fetch("/api/session", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ accessCode }),
      });
      if (!response.ok) {
        const payload = (await response.json()) as {
          error?: { message?: string };
        };
        throw new Error(payload.error?.message ?? "Access was not granted.");
      }
      window.location.reload();
    } catch (submitError) {
      setError(
        submitError instanceof Error
          ? submitError.message
          : "Access was not granted.",
      );
      setIsSubmitting(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-background px-4 py-12">
      <section className="w-full max-w-sm" aria-labelledby="access-heading">
        <div className="flex items-center gap-2.5">
          <BrandMark className="size-5" />
          <span className="text-sm font-semibold tracking-[-0.025em]">
            iPromise
          </span>
        </div>
        <div className="mt-10 border-t border-border pt-6">
          <h1
            id="access-heading"
            className="text-xl font-semibold tracking-[-0.025em]"
          >
            Access this build
          </h1>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            Enter the access code supplied with the evaluation link.
          </p>
          <form className="mt-6" onSubmit={submit}>
            <label className="text-xs font-medium" htmlFor="access-code">
              Access code
            </label>
            <input
              id="access-code"
              autoComplete="current-password"
              className="mt-2 h-10 w-full rounded-md border border-input bg-card px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
              disabled={isSubmitting}
              onChange={(event) => setAccessCode(event.target.value)}
              required
              type="password"
              value={accessCode}
            />
            {error ? (
              <p className="mt-2 text-xs text-status-danger" role="alert">
                {error}
              </p>
            ) : null}
            <Button
              className="mt-4 w-full"
              disabled={isSubmitting}
              type="submit"
            >
              {isSubmitting ? (
                <LoaderCircle
                  className="size-4 animate-spin motion-reduce:animate-none"
                  aria-hidden="true"
                />
              ) : null}
              {isSubmitting ? "Checking…" : "Continue"}
            </Button>
          </form>
        </div>
      </section>
    </main>
  );
}
