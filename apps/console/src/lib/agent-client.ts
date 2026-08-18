import {
  githubIntegrationStatusSchema,
  parseAuditRun,
  type AuditRun,
  type GitHubIntegrationStatus,
} from "@/lib/contracts";

const GET_TIMEOUT_MS = 10_000;
// The synchronous hackathon path may spend up to 750 seconds in the isolated
// verifier. Keep the console proxy inside the same 900-second envelope as the
// agent and Cloud Run request timeouts so the UI does not abandon a live run.
const RUN_TIMEOUT_MS = 900_000;

export class AgentProxyError extends Error {
  constructor(
    message: string,
    readonly status = 502,
  ) {
    super(message);
    this.name = "AgentProxyError";
  }
}

export function isAgentConfigured(): boolean {
  return Boolean(process.env.IPROMISE_AGENT_URL?.trim());
}

function configuredAgentBase(required: boolean): URL | null {
  const rawBase = process.env.IPROMISE_AGENT_URL?.trim();
  if (!rawBase) {
    if (!required) return null;
    throw new AgentProxyError("The iPromise agent URL is not configured.", 503);
  }

  let base: URL;
  try {
    base = new URL(rawBase);
  } catch {
    throw new AgentProxyError("IPROMISE_AGENT_URL is not a valid URL.", 500);
  }

  if (base.protocol !== "http:" && base.protocol !== "https:") {
    throw new AgentProxyError(
      "IPROMISE_AGENT_URL must use HTTP or HTTPS.",
      500,
    );
  }

  if (
    base.username ||
    base.password ||
    base.search ||
    base.hash ||
    (base.pathname !== "/" && base.pathname !== "")
  ) {
    throw new AgentProxyError(
      "IPROMISE_AGENT_URL must be an origin without credentials, path, query, or fragment.",
      500,
    );
  }

  return base;
}

export function assertAgentProxyConfiguration(): boolean {
  const cloudRuntime = Boolean(process.env.K_SERVICE?.trim());
  const base = configuredAgentBase(cloudRuntime);
  if (!base) return false;

  if (cloudRuntime && base.protocol !== "https:") {
    throw new AgentProxyError(
      "Cloud Run requires an HTTPS IPROMISE_AGENT_URL origin.",
      500,
    );
  }
  const token = process.env.IPROMISE_AGENT_TOKEN?.trim() ?? "";
  if (cloudRuntime && (token.length < 24 || token.length > 512)) {
    throw new AgentProxyError(
      "Cloud Run requires a valid IPROMISE_AGENT_TOKEN.",
      500,
    );
  }
  return true;
}

function agentEndpoint(path: string): URL {
  const base = configuredAgentBase(true);
  if (!base) {
    throw new AgentProxyError("The iPromise agent URL is not configured.", 503);
  }

  return new URL(path, `${base.toString().replace(/\/$/, "")}/`);
}

function requestHeaders(
  includeBody: boolean,
  additional?: Record<string, string>,
): HeadersInit {
  const headers: Record<string, string> = {
    Accept: "application/json",
    ...additional,
  };
  const token = process.env.IPROMISE_AGENT_TOKEN?.trim();
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  if (includeBody) {
    headers["Content-Type"] = "application/json";
  }
  return headers;
}

async function fetchAgent(
  path: string,
  init: RequestInit,
  timeoutMs = GET_TIMEOUT_MS,
): Promise<Response> {
  const response = await fetch(agentEndpoint(path), {
    ...init,
    headers: requestHeaders(Boolean(init.body)),
    cache: "no-store",
    signal: AbortSignal.timeout(timeoutMs),
  });
  if (!response.ok) {
    let message = `Agent request failed with status ${response.status}.`;
    try {
      const payload = (await response.json()) as {
        error?: { message?: string };
      };
      message = payload.error?.message ?? message;
    } catch {
      // The upstream status remains the useful failure boundary.
    }
    throw new AgentProxyError(message, response.status >= 500 ? 502 : response.status);
  }
  return response;
}

async function callAgent(
  path: string,
  init: RequestInit,
  timeoutMs: number,
  allowNotFound = false,
  additionalHeaders?: Record<string, string>,
): Promise<AuditRun | null> {
  const response = await fetch(agentEndpoint(path), {
    ...init,
    headers: requestHeaders(Boolean(init.body), additionalHeaders),
    cache: "no-store",
    signal: AbortSignal.timeout(timeoutMs),
  });

  if (allowNotFound && (response.status === 204 || response.status === 404)) {
    return null;
  }

  if (!response.ok) {
    throw new AgentProxyError(
      `Agent request failed with status ${response.status}.`,
      502,
    );
  }

  try {
    return parseAuditRun(await response.json());
  } catch {
    throw new AgentProxyError(
      "The agent returned an invalid audit response.",
      502,
    );
  }
}

export function getLatestAgentRun(): Promise<AuditRun | null> {
  return callAgent("v1/runs/latest", { method: "GET" }, GET_TIMEOUT_MS, true);
}

export async function startAgentRun(idempotencyKey?: string): Promise<AuditRun> {
  const run = await callAgent(
    "v1/runs",
    {
      method: "POST",
      body: JSON.stringify({ trigger: "manual", source: "console" }),
    },
    RUN_TIMEOUT_MS,
    false,
    idempotencyKey ? { "Idempotency-Key": idempotencyKey } : undefined,
  );
  if (!run) {
    throw new AgentProxyError("The agent did not return an audit run.", 502);
  }
  return run;
}

export async function getGitHubStatus(): Promise<GitHubIntegrationStatus> {
  const response = await fetchAgent("v1/integrations/github", { method: "GET" });
  return githubIntegrationStatusSchema.parse(await response.json());
}

export async function getGitHubInstallUrl(): Promise<string> {
  const response = await fetchAgent("v1/integrations/github/install-url", {
    method: "GET",
  });
  const payload = (await response.json()) as { url?: unknown };
  if (typeof payload.url !== "string") {
    throw new AgentProxyError("The agent returned an invalid GitHub install URL.");
  }
  return payload.url;
}

export async function getGitHubOAuthUrl(input: {
  installationId: number;
  setupAction: string;
  state: string;
}): Promise<string> {
  const response = await fetchAgent("v1/integrations/github/oauth-url", {
    method: "POST",
    body: JSON.stringify(input),
  });
  const payload = (await response.json()) as { url?: unknown };
  if (typeof payload.url !== "string") {
    throw new AgentProxyError("The agent returned an invalid GitHub OAuth URL.");
  }
  return payload.url;
}

export async function completeGitHubOAuth(input: {
  code: string;
  state: string;
}): Promise<GitHubIntegrationStatus> {
  const response = await fetchAgent(
    "v1/integrations/github/oauth/callback",
    { method: "POST", body: JSON.stringify(input) },
    30_000,
  );
  return githubIntegrationStatusSchema.parse(await response.json());
}

export async function selectGitHubRepository(
  repositoryId: number,
): Promise<GitHubIntegrationStatus> {
  const response = await fetchAgent("v1/integrations/github/repository", {
    method: "PUT",
    body: JSON.stringify({ repositoryId }),
  });
  return githubIntegrationStatusSchema.parse(await response.json());
}

export async function disconnectGitHub(): Promise<GitHubIntegrationStatus> {
  const response = await fetchAgent("v1/integrations/github", {
    method: "DELETE",
  });
  return githubIntegrationStatusSchema.parse(await response.json());
}
