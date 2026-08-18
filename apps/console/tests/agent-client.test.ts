import { afterEach, describe, expect, it, vi } from "vitest";

import { startAgentRun } from "@/lib/agent-client";
import { createDemonstrationRun } from "@/lib/demo-data";

const originalAgentUrl = process.env.IPROMISE_AGENT_URL;
const originalAgentToken = process.env.IPROMISE_AGENT_TOKEN;

afterEach(() => {
  vi.restoreAllMocks();
  if (originalAgentUrl === undefined) {
    delete process.env.IPROMISE_AGENT_URL;
  } else {
    process.env.IPROMISE_AGENT_URL = originalAgentUrl;
  }
  if (originalAgentToken === undefined) {
    delete process.env.IPROMISE_AGENT_TOKEN;
  } else {
    process.env.IPROMISE_AGENT_TOKEN = originalAgentToken;
  }
});

describe("agent run proxy", () => {
  it("keeps manual runs inside the 900-second verifier envelope", async () => {
    process.env.IPROMISE_AGENT_URL = "https://agent.example.run.app";
    process.env.IPROMISE_AGENT_TOKEN = "test-agent-token-with-safe-length";
    const signal = new AbortController().signal;
    const timeout = vi
      .spyOn(AbortSignal, "timeout")
      .mockReturnValue(signal);
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify(createDemonstrationRun()), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );

    await expect(startAgentRun("manual-verifier-envelope-01")).resolves.toMatchObject({
      status: "COMPLETE",
    });

    expect(timeout).toHaveBeenCalledWith(900_000);
  });
});
