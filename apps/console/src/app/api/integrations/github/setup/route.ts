import { getGitHubOAuthUrl, isAgentConfigured } from "@/lib/agent-client";
import { githubRedirect, integrationErrorResponse } from "@/lib/github-route";
import { requireConsoleAccess } from "@/lib/console-auth";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const denied = requireConsoleAccess(request);
  if (denied) return denied;

  if (!isAgentConfigured()) {
    return integrationErrorResponse(new Error("The audit service is unavailable."));
  }
  try {
    const query = new URL(request.url).searchParams;
    const installationId = Number(query.get("installation_id"));
    const setupAction = query.get("setup_action") ?? "install";
    const state = query.get("state") ?? "";
    if (!Number.isInteger(installationId) || installationId <= 0 || !state) {
      return Response.json(
        {
          error: {
            code: "INVALID_GITHUB_SETUP",
            message: "GitHub did not return a valid installation.",
          },
        },
        { status: 400 },
      );
    }
    const url = await getGitHubOAuthUrl({ installationId, setupAction, state });
    return githubRedirect(url, "oauth");
  } catch (error) {
    return integrationErrorResponse(error);
  }
}
