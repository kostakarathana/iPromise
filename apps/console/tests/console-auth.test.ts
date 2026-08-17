import { afterEach, describe, expect, it, vi } from "vitest";

import {
  CONSOLE_SESSION_COOKIE,
  consoleSessionCookie,
  createConsoleSession,
  rejectCrossOrigin,
  requireConsoleAccess,
  verifyAccessCode,
  verifyConsoleSession,
} from "@/lib/console-auth";

describe("console access boundary", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("is transparent only when no access code is configured", () => {
    vi.stubEnv("IPROMISE_CONSOLE_ACCESS_TOKEN", "");
    expect(verifyAccessCode("anything")).toBe(true);
    expect(
      requireConsoleAccess(new Request("https://console.example/api/audit")),
    ).toBeNull();
  });

  it("accepts a valid signed session and rejects tampering and expiry", () => {
    vi.stubEnv(
      "IPROMISE_CONSOLE_ACCESS_TOKEN",
      "judge-access-code-with-more-than-32-characters",
    );
    const now = Date.UTC(2026, 7, 17, 12);
    const session = createConsoleSession(now);

    expect(verifyAccessCode("judge-access-code-with-more-than-32-characters")).toBe(
      true,
    );
    expect(verifyAccessCode("wrong-code")).toBe(false);
    expect(verifyConsoleSession(session, now + 1_000)).toBe(true);
    expect(verifyConsoleSession(`${session}x`, now + 1_000)).toBe(false);
    expect(verifyConsoleSession(session, now + 13 * 60 * 60 * 1_000)).toBe(false);

    const cookie = consoleSessionCookie(createConsoleSession(), 12 * 60 * 60);
    const request = new Request("https://console.example/api/audit", {
      headers: { cookie },
    });
    expect(requireConsoleAccess(request)).toBeNull();
  });

  it("rejects unauthenticated access and cross-origin mutations", async () => {
    vi.stubEnv(
      "IPROMISE_CONSOLE_ACCESS_TOKEN",
      "judge-access-code-with-more-than-32-characters",
    );
    const denied = requireConsoleAccess(
      new Request("https://console.example/api/audit"),
    );
    expect(denied?.status).toBe(401);
    expect(await denied?.json()).toMatchObject({
      error: { code: "CONSOLE_AUTH_REQUIRED" },
    });

    const crossOrigin = rejectCrossOrigin(
      new Request("https://console.example/api/audit", {
        method: "POST",
        headers: { origin: "https://attacker.example" },
      }),
    );
    expect(crossOrigin?.status).toBe(403);
    expect(await crossOrigin?.json()).toMatchObject({
      error: { code: "CROSS_ORIGIN_REQUEST" },
    });
  });

  it("accepts the browser origin represented by Host in local development", () => {
    const request = new Request("http://localhost:3000/api/audit", {
      method: "POST",
      headers: {
        host: "127.0.0.1:3000",
        origin: "http://127.0.0.1:3000",
      },
    });

    expect(rejectCrossOrigin(request)).toBeNull();
  });

  it("uses the forwarded protocol with Host behind Cloud Run", () => {
    const request = new Request("http://console:8080/api/audit", {
      method: "POST",
      headers: {
        host: "ipromise-console-abc.a.run.app",
        origin: "https://ipromise-console-abc.a.run.app",
        "x-forwarded-proto": "https",
      },
    });

    expect(rejectCrossOrigin(request)).toBeNull();
  });

  it("still rejects an external origin when proxy headers are present", async () => {
    const denied = rejectCrossOrigin(
      new Request("http://console:8080/api/audit", {
        method: "POST",
        headers: {
          host: "ipromise-console-abc.a.run.app",
          origin: "https://attacker.example",
          "x-forwarded-proto": "https",
        },
      }),
    );

    expect(denied?.status).toBe(403);
    expect(await denied?.json()).toMatchObject({
      error: { code: "CROSS_ORIGIN_REQUEST" },
    });
  });

  it("uses a host-only, HttpOnly, same-site session cookie", () => {
    vi.stubEnv("NODE_ENV", "production");
    const cookie = consoleSessionCookie("signed", 60);
    expect(cookie).toContain(`${CONSOLE_SESSION_COOKIE}=signed`);
    expect(cookie).toContain("HttpOnly");
    expect(cookie).toContain("SameSite=Lax");
    expect(cookie).toContain("Secure");
    expect(cookie).not.toContain("Domain=");
  });

  it("fails closed when the configured access code is weak", () => {
    vi.stubEnv("IPROMISE_CONSOLE_ACCESS_TOKEN", "too-short");
    expect(() => verifyAccessCode("too-short")).toThrow(/32 to 256/);
  });

  it("fails closed on Cloud Run when the access code is missing", () => {
    vi.stubEnv("K_SERVICE", "ipromise-console");
    vi.stubEnv("IPROMISE_CONSOLE_ACCESS_TOKEN", "");

    expect(() => verifyAccessCode("anything")).toThrow(
      /required when the console runs on Cloud Run/,
    );
  });
});
