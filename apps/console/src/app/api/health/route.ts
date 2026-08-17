import { assertConsoleRuntimeConfiguration } from "@/lib/runtime-config";

export const dynamic = "force-dynamic";

export function GET() {
  try {
    const { agentConfigured } = assertConsoleRuntimeConfiguration();

    return Response.json(
      {
        status: "healthy",
        service: "ipromise-console",
        agentConfigured,
        mode: agentConfigured ? "proxy" : "local",
      },
      { headers: { "Cache-Control": "no-store" } },
    );
  } catch {
    return Response.json(
      {
        status: "misconfigured",
        service: "ipromise-console",
      },
      { status: 503, headers: { "Cache-Control": "no-store" } },
    );
  }
}
