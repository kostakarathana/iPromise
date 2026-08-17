"use client";

import { useEffect, useState } from "react";
import { ExternalLink, LoaderCircle } from "lucide-react";

import { Button, ButtonLink } from "@/components/ui/button";
import {
  githubIntegrationStatusSchema,
  type GitHubIntegrationStatus,
} from "@/lib/contracts";

async function readStatus(
  path = "/api/integrations/github",
  init?: RequestInit,
): Promise<GitHubIntegrationStatus> {
  const response = await fetch(path, {
    ...init,
    headers: {
      Accept: "application/json",
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
    },
    cache: "no-store",
  });
  if (!response.ok) {
    let message = "GitHub is unavailable.";
    try {
      const payload = (await response.json()) as {
        error?: { message?: string };
      };
      message = payload.error?.message ?? message;
    } catch {
      // Keep the stable user-facing failure message.
    }
    throw new Error(message);
  }
  return githubIntegrationStatusSchema.parse(await response.json());
}

export type RepositoryConnectionState =
  | { phase: "loading"; status: null }
  | { phase: "updating"; status: GitHubIntegrationStatus | null }
  | { phase: "ready"; status: GitHubIntegrationStatus }
  | { phase: "error"; status: GitHubIntegrationStatus | null };

function actionStatus(status: GitHubIntegrationStatus | null): string {
  if (!status) return "Checking issue-creation access.";
  if (!status.configured) return "No GitHub issue will be opened.";
  if (!status.actionsEnabled) {
    return "Issue creation is off. Audits will only record a proposed action.";
  }
  if (!status.connected) {
    return "Connect GitHub before running an action-ready audit.";
  }
  if (!status.selectedRepository) {
    return "Select a repository before running an action-ready audit.";
  }
  return "Issue creation is enabled for this repository.";
}

function callbackErrorFromLocation(): string | null {
  if (typeof window === "undefined") return null;
  const result = new URLSearchParams(window.location.search).get("github");
  if (result === "cancelled") {
    return "GitHub connection was cancelled. Nothing changed.";
  }
  if (result === "error") return "GitHub could not be connected. Try again.";
  return null;
}

export function RepositoryConnection({
  onStateChange,
}: {
  onStateChange?: (state: RepositoryConnectionState) => void;
}) {
  const [status, setStatus] = useState<GitHubIntegrationStatus | null>(null);
  const [isUpdating, setIsUpdating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const callbackError = callbackErrorFromLocation();
    const callbackResult = new URLSearchParams(window.location.search).get(
      "github",
    );
    if (callbackResult) {
      void Promise.resolve().then(() => {
        if (cancelled) return;
        if (callbackError) setError(callbackError);
        const url = new URL(window.location.href);
        url.searchParams.delete("github");
        window.history.replaceState(window.history.state, "", url);
      });
    }

    onStateChange?.({ phase: "loading", status: null });
    void readStatus()
      .then((nextStatus) => {
        if (!cancelled) {
          setStatus(nextStatus);
          onStateChange?.({ phase: "ready", status: nextStatus });
        }
      })
      .catch((loadError: unknown) => {
        if (!cancelled) {
          setError(
            loadError instanceof Error
              ? loadError.message
              : "GitHub is unavailable.",
          );
          onStateChange?.({ phase: "error", status: null });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [onStateChange]);

  async function selectRepository(repositoryId: number) {
    setIsUpdating(true);
    setError(null);
    onStateChange?.({ phase: "updating", status });
    try {
      const nextStatus = await readStatus(undefined, {
        method: "PUT",
        body: JSON.stringify({ repositoryId }),
      });
      setStatus(nextStatus);
      onStateChange?.({ phase: "ready", status: nextStatus });
    } catch (selectionError) {
      setError(
        selectionError instanceof Error
          ? selectionError.message
          : "The repository could not be selected.",
      );
      onStateChange?.({ phase: "error", status });
    } finally {
      setIsUpdating(false);
    }
  }

  async function disconnect() {
    setIsUpdating(true);
    setError(null);
    onStateChange?.({ phase: "updating", status });
    try {
      const nextStatus = await readStatus(undefined, { method: "DELETE" });
      setStatus(nextStatus);
      onStateChange?.({ phase: "ready", status: nextStatus });
    } catch (disconnectError) {
      setError(
        disconnectError instanceof Error
          ? disconnectError.message
          : "GitHub could not be disconnected.",
      );
      onStateChange?.({ phase: "error", status });
    } finally {
      setIsUpdating(false);
    }
  }

  const selected = status?.selectedRepository;

  return (
    <section
      aria-label="Repository connection"
      aria-busy={status === null || isUpdating}
      className="mt-5 flex min-h-12 flex-wrap items-center justify-between gap-3 border-y border-border py-2.5"
    >
      <div className="min-w-0 flex-1 basis-full sm:basis-auto">
        <p className="text-xs text-muted-foreground">Repository</p>
        {selected ? (
          <a
            className="mt-0.5 inline-flex max-w-full items-center gap-1.5 truncate text-sm font-medium text-link underline-offset-4 hover:underline focus-visible:rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            href={selected.htmlUrl}
            target="_blank"
            rel="noreferrer"
          >
            <span className="truncate">{selected.fullName}</span>
            <ExternalLink className="size-3 shrink-0" aria-hidden="true" />
          </a>
        ) : (
          <p className="mt-0.5 text-sm font-medium">
            {status === null && !error
              ? "Checking connection"
              : status?.connected
              ? "Choose an installed repository"
              : status?.configured
                ? "No repository connected"
                : "GitHub App not configured"}
          </p>
        )}
        {error ? (
          <p className="mt-1 text-xs text-status-danger" role="alert">
            {error}
          </p>
        ) : null}
        <p
          id="repository-action-status"
          className="mt-1 text-xs text-muted-foreground"
          aria-live="polite"
        >
          {actionStatus(status)}
        </p>
      </div>

      <div className="flex w-full min-w-0 flex-wrap items-center gap-2 sm:w-auto sm:justify-end">
        {isUpdating ? (
          <LoaderCircle
            className="size-4 animate-spin text-muted-foreground motion-reduce:animate-none"
            aria-label="Updating repository"
          />
        ) : null}

        {status?.connected && status.repositories.length > 0 ? (
          <label className="sr-only" htmlFor="repository-select">
            Selected repository
          </label>
        ) : null}
        {status?.connected && status.repositories.length > 0 ? (
          <select
            id="repository-select"
            aria-label="Selected repository"
            className="h-8 min-w-0 flex-1 rounded-md border border-input bg-card px-2.5 text-xs outline-none focus-visible:ring-2 focus-visible:ring-ring sm:max-w-[230px] sm:flex-none"
            disabled={isUpdating}
            value={selected?.id ?? ""}
            onChange={(event) => {
              const repositoryId = Number(event.target.value);
              if (repositoryId) void selectRepository(repositoryId);
            }}
          >
            <option value="" disabled>
              Select repository
            </option>
            {status.repositories.map((repository) => (
              <option
                key={repository.id}
                value={repository.id}
                disabled={repository.archived}
              >
                {repository.fullName}
                {repository.archived ? " (archived)" : ""}
              </option>
            ))}
          </select>
        ) : status?.configured ? (
          <ButtonLink
            href="/api/integrations/github/install"
            size="sm"
            variant="secondary"
          >
            Connect GitHub
          </ButtonLink>
        ) : null}

        {status?.connected ? (
          <Button
            disabled={isUpdating}
            onClick={() => void disconnect()}
            size="sm"
            type="button"
            variant="ghost"
          >
            Disconnect
          </Button>
        ) : null}
      </div>
    </section>
  );
}
