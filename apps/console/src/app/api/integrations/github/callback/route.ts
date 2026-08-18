import { completeGitHubOAuth, isAgentConfigured } from "@/lib/agent-client";
import { requireConsoleAccess } from "@/lib/console-auth";

export const dynamic = "force-dynamic";

function dashboardRedirect(
  result: "cancelled" | "connected" | "error",
): Response {
  return new Response(null, {
    status: 303,
    headers: {
      "Cache-Control": "no-store",
      // Keep the callback on the browser-visible console origin. Cloud Run can
      // expose its container address through request.url, so building an
      // absolute redirect from that value can send the browser to 0.0.0.0.
      // This fixed same-origin path contains no caller-controlled redirect.
      Location: `/?github=${result}`,
    },
  });
}

export async function GET(request: Request) {
  const denied = requireConsoleAccess(request);
  if (denied) return denied;

  if (!isAgentConfigured()) {
    return dashboardRedirect("error");
  }
  try {
    const query = new URL(request.url).searchParams;
    if (query.has("error")) {
      return dashboardRedirect("cancelled");
    }
    const code = query.get("code") ?? "";
    const state = query.get("state") ?? "";
    if (!code || !state) {
      return dashboardRedirect("error");
    }
    await completeGitHubOAuth({ code, state });
    return dashboardRedirect("connected");
  } catch {
    return dashboardRedirect("error");
  }
}
