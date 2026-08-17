import {
  consoleSessionCookie,
  createConsoleSession,
  rejectCrossOrigin,
  verifyAccessCode,
} from "@/lib/console-auth";

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  const denied = rejectCrossOrigin(request);
  if (denied) return denied;

  try {
    const payload = (await request.json()) as { accessCode?: unknown };
    if (
      typeof payload.accessCode !== "string" ||
      !verifyAccessCode(payload.accessCode)
    ) {
      return Response.json(
        {
          error: {
            code: "INVALID_ACCESS_CODE",
            message: "That access code is not valid.",
          },
        },
        { status: 401, headers: { "Cache-Control": "no-store" } },
      );
    }
    return Response.json(
      { authenticated: true },
      {
        headers: {
          "Cache-Control": "no-store",
          "Set-Cookie": consoleSessionCookie(createConsoleSession(), 12 * 60 * 60),
        },
      },
    );
  } catch {
    return Response.json(
      {
        error: {
          code: "INVALID_REQUEST",
          message: "Enter a valid access code.",
        },
      },
      { status: 422, headers: { "Cache-Control": "no-store" } },
    );
  }
}

export async function DELETE(request: Request) {
  const denied = rejectCrossOrigin(request);
  if (denied) return denied;

  return Response.json(
    { authenticated: false },
    {
      headers: {
        "Cache-Control": "no-store",
        "Set-Cookie": consoleSessionCookie("", 0),
      },
    },
  );
}
