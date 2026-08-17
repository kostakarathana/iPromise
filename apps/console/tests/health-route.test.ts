import { afterEach, describe, expect, it, vi } from "vitest";

import { GET } from "@/app/api/health/route";

describe("console health configuration", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("allows the intentionally unconfigured local snapshot", async () => {
    vi.stubEnv("K_SERVICE", "");
    vi.stubEnv("IPROMISE_AGENT_URL", "");
    vi.stubEnv("IPROMISE_CONSOLE_ACCESS_TOKEN", "");

    const response = GET();
    expect(response.status).toBe(200);
    expect(await response.json()).toMatchObject({
      status: "healthy",
      agentConfigured: false,
      mode: "local",
    });
  });

  it("fails readiness when Cloud Run secrets or the agent are absent", async () => {
    vi.stubEnv("K_SERVICE", "ipromise-console");
    vi.stubEnv("IPROMISE_AGENT_URL", "");
    vi.stubEnv("IPROMISE_AGENT_TOKEN", "");
    vi.stubEnv("IPROMISE_CONSOLE_ACCESS_TOKEN", "");

    const response = GET();
    expect(response.status).toBe(503);
    expect(await response.json()).toMatchObject({ status: "misconfigured" });
  });

  it("accepts the complete protected Cloud Run proxy configuration", async () => {
    vi.stubEnv("K_SERVICE", "ipromise-console");
    vi.stubEnv("IPROMISE_AGENT_URL", "https://agent.example.test");
    vi.stubEnv(
      "IPROMISE_AGENT_TOKEN",
      "agent-token-with-at-least-24-characters",
    );
    vi.stubEnv(
      "IPROMISE_CONSOLE_ACCESS_TOKEN",
      "judge-access-code-with-more-than-32-characters",
    );

    const response = GET();
    expect(response.status).toBe(200);
    expect(await response.json()).toMatchObject({
      status: "healthy",
      agentConfigured: true,
      mode: "proxy",
    });
  });
});
