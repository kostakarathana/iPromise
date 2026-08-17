import { completeGitHubOAuth, isAgentConfigured } from "@/lib/agent-client";
import { requireConsoleAccess } from "@/lib/console-auth";

export const dynamic = "force-dynamic";

function dashboardRedirect(
  request: Request,
  result: "cancelled" | "connected" | "error",
): Response {
  const location = new URL("/", request.url);
  location.searchParams.set("github", result);
  return new Response(null, {
    status: 303,
    headers: {
      "Cache-Control": "no-store",
      Location: location.toString(),
    },
  });
}

export async function GET(request: Request) {
  const denied = requireConsoleAccess(request);
  if (denied) return denied;

  if (!isAgentConfigured()) {
    return dashboardRedirect(request, "error");
  }
  try {
    const query = new URL(request.url).searchParams;
    if (query.has("error")) {
      return dashboardRedirect(request, "cancelled");
    }
    const code = query.get("code") ?? "";
    const state = query.get("state") ?? "";
    if (!code || !state) {
      return dashboardRedirect(request, "error");
    }
    await completeGitHubOAuth({ code, state });
    return dashboardRedirect(request, "connected");
  } catch {
    return dashboardRedirect(request, "error");
  }
}
