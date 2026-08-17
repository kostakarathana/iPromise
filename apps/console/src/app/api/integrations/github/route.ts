import {
  disconnectGitHub,
  getGitHubStatus,
  isAgentConfigured,
  selectGitHubRepository,
} from "@/lib/agent-client";
import { integrationErrorResponse } from "@/lib/github-route";
import {
  rejectCrossOrigin,
  requireConsoleAccess,
} from "@/lib/console-auth";

export const dynamic = "force-dynamic";

const disconnectedStatus = {
  configured: false,
  connected: false,
  actionsEnabled: false,
  accountLogin: null,
  repositories: [],
  selectedRepository: null,
};

export async function GET(request: Request) {
  const denied = requireConsoleAccess(request);
  if (denied) return denied;

  if (!isAgentConfigured()) {
    return Response.json(disconnectedStatus, {
      headers: { "Cache-Control": "no-store" },
    });
  }
  try {
    return Response.json(await getGitHubStatus(), {
      headers: { "Cache-Control": "no-store" },
    });
  } catch (error) {
    return integrationErrorResponse(error);
  }
}

export async function PUT(request: Request) {
  const denied = requireConsoleAccess(request) ?? rejectCrossOrigin(request);
  if (denied) return denied;

  if (!isAgentConfigured()) {
    return integrationErrorResponse(new Error("The audit service is unavailable."));
  }
  try {
    const body = (await request.json()) as { repositoryId?: unknown };
    if (
      typeof body.repositoryId !== "number" ||
      !Number.isInteger(body.repositoryId) ||
      body.repositoryId <= 0
    ) {
      return Response.json(
        {
          error: {
            code: "INVALID_REPOSITORY",
            message: "Select a valid repository.",
          },
        },
        { status: 422 },
      );
    }
    return Response.json(await selectGitHubRepository(body.repositoryId), {
      headers: { "Cache-Control": "no-store" },
    });
  } catch (error) {
    return integrationErrorResponse(error);
  }
}

export async function DELETE(request: Request) {
  const denied = requireConsoleAccess(request) ?? rejectCrossOrigin(request);
  if (denied) return denied;

  if (!isAgentConfigured()) {
    return integrationErrorResponse(new Error("The audit service is unavailable."));
  }
  try {
    return Response.json(await disconnectGitHub(), {
      headers: { "Cache-Control": "no-store" },
    });
  } catch (error) {
    return integrationErrorResponse(error);
  }
}
