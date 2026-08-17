import { AgentProxyError } from "@/lib/agent-client";

export function integrationErrorResponse(error: unknown): Response {
  const proxyError =
    error instanceof AgentProxyError
      ? error
      : new AgentProxyError("The GitHub connection could not be completed.");
  return Response.json(
    {
      error: {
        code: "GITHUB_INTEGRATION_FAILED",
        message: proxyError.message,
      },
    },
    {
      status: proxyError.status,
      headers: { "Cache-Control": "no-store" },
    },
  );
}

export function githubRedirect(url: string, kind: "install" | "oauth"): Response {
  const parsed = new URL(url);
  const expectedPrefix = kind === "install" ? "/apps/" : "/login/oauth/authorize";
  if (
    parsed.protocol !== "https:" ||
    parsed.hostname !== "github.com" ||
    !parsed.pathname.startsWith(expectedPrefix)
  ) {
    throw new AgentProxyError("The agent returned an unsafe GitHub redirect.", 502);
  }
  return Response.redirect(parsed, 302);
}
