import { createHash, createHmac, timingSafeEqual } from "node:crypto";

export const CONSOLE_SESSION_COOKIE = "ipromise_session";
const SESSION_VERSION = "v1";
const SESSION_TTL_SECONDS = 12 * 60 * 60;

function configuredAccessToken(): string | null {
  const token = process.env.IPROMISE_CONSOLE_ACCESS_TOKEN?.trim() || null;
  if (!token && process.env.K_SERVICE?.trim()) {
    throw new Error(
      "IPROMISE_CONSOLE_ACCESS_TOKEN is required when the console runs on Cloud Run.",
    );
  }
  if (token && (token.length < 32 || token.length > 256)) {
    throw new Error(
      "IPROMISE_CONSOLE_ACCESS_TOKEN must contain 32 to 256 characters.",
    );
  }
  return token;
}

export function isConsoleAccessConfigured(): boolean {
  return configuredAccessToken() !== null;
}

export function verifyAccessCode(candidate: string): boolean {
  const expected = configuredAccessToken();
  if (!expected) return true;
  if (candidate.length > 256) return false;
  const candidateDigest = createHash("sha256").update(candidate).digest();
  const expectedDigest = createHash("sha256").update(expected).digest();
  return timingSafeEqual(candidateDigest, expectedDigest);
}

export function createConsoleSession(now = Date.now()): string {
  const accessToken = configuredAccessToken();
  if (!accessToken) return "";
  const expires = Math.floor(now / 1_000) + SESSION_TTL_SECONDS;
  const unsigned = `${SESSION_VERSION}.${expires}`;
  const signature = createHmac("sha256", accessToken)
    .update(unsigned)
    .digest("base64url");
  return `${unsigned}.${signature}`;
}

export function verifyConsoleSession(
  value: string | undefined,
  now = Date.now(),
): boolean {
  const accessToken = configuredAccessToken();
  if (!accessToken) return true;
  if (!value) return false;
  const [version, expiryText, suppliedSignature, ...rest] = value.split(".");
  if (
    version !== SESSION_VERSION ||
    rest.length > 0 ||
    !expiryText ||
    !suppliedSignature
  ) {
    return false;
  }
  const expiry = Number(expiryText);
  const nowSeconds = Math.floor(now / 1_000);
  if (
    !Number.isSafeInteger(expiry) ||
    expiry <= nowSeconds ||
    expiry > nowSeconds + SESSION_TTL_SECONDS + 60
  ) {
    return false;
  }
  const expectedSignature = createHmac("sha256", accessToken)
    .update(`${version}.${expiryText}`)
    .digest("base64url");
  const supplied = Buffer.from(suppliedSignature);
  const expected = Buffer.from(expectedSignature);
  return supplied.length === expected.length && timingSafeEqual(supplied, expected);
}

function cookieValue(cookieHeader: string | null, name: string): string | undefined {
  if (!cookieHeader) return undefined;
  for (const part of cookieHeader.split(";")) {
    const [key, ...valueParts] = part.trim().split("=");
    if (key === name) return decodeURIComponent(valueParts.join("="));
  }
  return undefined;
}

export function hasConsoleRequestAccess(request: Request): boolean {
  return verifyConsoleSession(
    cookieValue(request.headers.get("cookie"), CONSOLE_SESSION_COOKIE),
  );
}

export function consoleSessionCookie(value: string, maxAge: number): string {
  const secure = process.env.NODE_ENV === "production" ? "; Secure" : "";
  return `${CONSOLE_SESSION_COOKIE}=${encodeURIComponent(value)}; Path=/; HttpOnly; SameSite=Lax; Max-Age=${maxAge}${secure}`;
}

export function requireConsoleAccess(request: Request): Response | null {
  if (hasConsoleRequestAccess(request)) return null;
  return Response.json(
    {
      error: {
        code: "CONSOLE_AUTH_REQUIRED",
        message: "Enter the access code to use this build.",
      },
    },
    { status: 401, headers: { "Cache-Control": "no-store" } },
  );
}

export function rejectCrossOrigin(request: Request): Response | null {
  const origin = request.headers.get("origin");
  if (!origin) return null;

  const requestUrl = new URL(request.url);
  const allowedOrigins = new Set([requestUrl.origin]);
  const host = request.headers.get("host")?.split(",", 1)[0]?.trim();
  const forwardedProtocol = request.headers
    .get("x-forwarded-proto")
    ?.split(",", 1)[0]
    ?.trim()
    .toLowerCase();
  const protocol =
    forwardedProtocol === "http" || forwardedProtocol === "https"
      ? `${forwardedProtocol}:`
      : requestUrl.protocol;

  if (host) {
    try {
      allowedOrigins.add(new URL(`${protocol}//${host}`).origin);
    } catch {
      // Ignore malformed proxy headers and retain the request URL as the only
      // accepted origin.
    }
  }

  let normalizedOrigin: string;
  try {
    normalizedOrigin = new URL(origin).origin;
  } catch {
    normalizedOrigin = "";
  }
  if (allowedOrigins.has(normalizedOrigin)) return null;

  return Response.json(
    {
      error: {
        code: "CROSS_ORIGIN_REQUEST",
        message: "Cross-origin mutations are not allowed.",
      },
    },
    { status: 403, headers: { "Cache-Control": "no-store" } },
  );
}
