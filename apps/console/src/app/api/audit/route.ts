import {
  AgentProxyError,
  getLatestAgentRun,
  isAgentConfigured,
  startAgentRun,
} from "@/lib/agent-client";
import { createDemonstrationRun } from "@/lib/demo-data";
import {
  rejectCrossOrigin,
  requireConsoleAccess,
} from "@/lib/console-auth";

export const dynamic = "force-dynamic";

function demonstrationResponse() {
  return Response.json(createDemonstrationRun(), {
    headers: {
      "Cache-Control": "no-store",
      "X-iPromise-Mode": "demonstration",
      "X-iPromise-Presentation": "static-fixture",
    },
  });
}

function proxyErrorResponse(error: unknown) {
  const proxyError =
    error instanceof AgentProxyError
      ? error
      : new AgentProxyError("The agent could not be reached.");

  return Response.json(
    {
      error: {
        code: "AGENT_UNAVAILABLE",
        message: proxyError.message,
      },
    },
    {
      status: proxyError.status,
      headers: { "Cache-Control": "no-store" },
    },
  );
}

export async function GET(request: Request) {
  const denied = requireConsoleAccess(request);
  if (denied) return denied;

  if (!isAgentConfigured()) {
    return demonstrationResponse();
  }

  try {
    const run = await getLatestAgentRun();
    if (!run) {
      return new Response(null, {
        status: 204,
        headers: {
          "Cache-Control": "no-store",
          "X-iPromise-Presentation": "connected-agent",
        },
      });
    }
    return Response.json(run, {
      headers: {
        "Cache-Control": "no-store",
        "X-iPromise-Presentation": "connected-agent",
      },
    });
  } catch (error) {
    return proxyErrorResponse(error);
  }
}

export async function POST(request: Request) {
  const denied = requireConsoleAccess(request) ?? rejectCrossOrigin(request);
  if (denied) return denied;

  const idempotencyKey = request.headers.get("Idempotency-Key")?.trim();
  if (
    idempotencyKey &&
    (idempotencyKey.length < 8 ||
      idempotencyKey.length > 128 ||
      !/^[A-Za-z0-9._:-]+$/.test(idempotencyKey))
  ) {
    return Response.json(
      {
        error: {
          code: "INVALID_IDEMPOTENCY_KEY",
          message: "Idempotency-Key must be 8–128 safe identifier characters.",
        },
      },
      { status: 422, headers: { "Cache-Control": "no-store" } },
    );
  }

  if (!isAgentConfigured()) {
    return demonstrationResponse();
  }

  try {
    return Response.json(await startAgentRun(idempotencyKey), {
      status: 202,
      headers: {
        "Cache-Control": "no-store",
        "X-iPromise-Presentation": "connected-agent",
      },
    });
  } catch (error) {
    return proxyErrorResponse(error);
  }
}
