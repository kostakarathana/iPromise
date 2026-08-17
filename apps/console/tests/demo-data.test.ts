import { describe, expect, it } from "vitest";

import { auditRunSchema } from "@/lib/contracts";
import { createDemonstrationRun } from "@/lib/demo-data";

describe("demonstration audit run", () => {
  it("matches the shared AuditRun wire contract", () => {
    const run = createDemonstrationRun(
      new Date("2026-08-17T06:00:00.000Z"),
    );

    expect(() => auditRunSchema.parse(run)).not.toThrow();
    expect(run.mode).toBe("demonstration");
    expect(run.runtime.modelInvocationAttempted).toBe(false);
    expect(run.runtime.modelInvoked).toBe(false);
    expect(run.runtime.model).toBeNull();
  });

  it("uses the canonical promise and disclosed virtual-clock replay", () => {
    const run = createDemonstrationRun();

    expect(run.claim.exactQuote).toBe(
      "When you delete your account, we remove your profile from our app and analytics system within 24 hours.",
    );
    expect(run.claim.controlId).toBe("privacy.account_deletion.v1");
    expect(run.events.find((event) => event.id === "probe")?.detail).toContain(
      "+25h 04m",
    );
    expect(
      run.evidence.find((evidence) => evidence.result === "FAIL")?.observed,
    ).toContain("+25h");
    expect(run.events.find((event) => event.id === "probe")?.detail).toContain(
      "+1h",
    );
  });

  it("selects exactly one primary route without claiming an external action", () => {
    const run = createDemonstrationRun();
    const selectedRoutes = run.actions.filter(
      (action) => action.state !== "SKIPPED",
    );

    expect(selectedRoutes).toHaveLength(1);
    expect(selectedRoutes[0]).toMatchObject({
      kind: "issue",
      state: "PLANNED",
      verified: false,
    });
    expect(
      run.actions
        .filter((action) => action.kind !== "issue")
        .every((action) => action.state === "SKIPPED"),
    ).toBe(true);
    expect(run.events.find((event) => event.id === "verify")?.state).toBe(
      "SKIPPED",
    );
  });
});
