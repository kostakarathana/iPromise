import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  completeGitHubOAuth: vi.fn(),
  isAgentConfigured: vi.fn(),
  requireConsoleAccess: vi.fn(),
}));

vi.mock("@/lib/agent-client", () => ({
  completeGitHubOAuth: mocks.completeGitHubOAuth,
  isAgentConfigured: mocks.isAgentConfigured,
}));

vi.mock("@/lib/console-auth", () => ({
  requireConsoleAccess: mocks.requireConsoleAccess,
}));

import { GET } from "@/app/api/integrations/github/callback/route";

describe("GitHub OAuth callback", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.isAgentConfigured.mockReturnValue(true);
    mocks.requireConsoleAccess.mockReturnValue(null);
    mocks.completeGitHubOAuth.mockResolvedValue({});
  });

  it("returns successful authorization to the dashboard", async () => {
    const response = await GET(
      new Request(
        "https://ipromise.example/api/integrations/github/callback?code=code&state=state",
      ),
    );

    expect(response.status).toBe(303);
    expect(response.headers.get("location")).toBe(
      "https://ipromise.example/?github=connected",
    );
    expect(mocks.completeGitHubOAuth).toHaveBeenCalledWith({
      code: "code",
      state: "state",
    });
  });

  it("returns a cancelled authorization to the dashboard", async () => {
    const response = await GET(
      new Request(
        "https://ipromise.example/api/integrations/github/callback?error=access_denied&error_description=private-detail",
      ),
    );

    expect(response.status).toBe(303);
    expect(response.headers.get("location")).toBe(
      "https://ipromise.example/?github=cancelled",
    );
    expect(mocks.completeGitHubOAuth).not.toHaveBeenCalled();
  });

  it("uses a generic dashboard error without leaking upstream details", async () => {
    mocks.completeGitHubOAuth.mockRejectedValue(
      new Error("secret upstream failure"),
    );

    const response = await GET(
      new Request(
        "https://ipromise.example/api/integrations/github/callback?code=code&state=state",
      ),
    );
    const location = response.headers.get("location") ?? "";

    expect(response.status).toBe(303);
    expect(location).toBe("https://ipromise.example/?github=error");
    expect(location).not.toContain("secret");
  });
});
