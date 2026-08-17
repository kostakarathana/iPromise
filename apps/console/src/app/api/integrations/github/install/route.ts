import { getGitHubInstallUrl, isAgentConfigured } from "@/lib/agent-client";
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
    return githubRedirect(await getGitHubInstallUrl(), "install");
  } catch (error) {
    return integrationErrorResponse(error);
  }
}
