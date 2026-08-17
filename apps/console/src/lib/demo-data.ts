import type { AuditRun } from "@/lib/contracts";

const DEMO_RUN_ID = "run_01J5E8F4P7Q2N6C8";

function isoAt(now: Date, millisecondsAgo: number): string {
  return new Date(now.getTime() - millisecondsAgo).toISOString();
}

export function createDemonstrationRun(
  now = new Date("2026-08-17T06:00:00.000Z"),
): AuditRun {
  return {
    id: DEMO_RUN_ID,
    mode: "demonstration",
    status: "COMPLETE",
    verdict: "CONTRADICTED",
    startedAt: isoAt(now, 19_230),
    updatedAt: now.toISOString(),
    claim: {
      exactQuote:
        "When you delete your account, we remove your profile from our app and analytics system within 24 hours.",
      sourceUrl: "http://127.0.0.1:8081/privacy#account-deletion",
      sourceTitle: "Northstar · Privacy policy",
      capturedAt: isoAt(now, 19_006),
      contentHash: "fixture:precomputed-canonical-claim-v1",
      actor: "iPromise reference SaaS",
      action: "remove",
      object: "profile",
      deadlineHours: 24,
      qualifiers: [
        "Account deletion",
        "Active systems",
        "Within 24 hours",
        "Synthetic virtual clock",
      ],
      testability: "EXECUTABLE",
      controlId: "privacy.account_deletion.v1",
    },
    evidence: [
      {
        id: "profile-store",
        label: "Customer profiles",
        expected: "Removed within 24h",
        observed: "No active record at +25h",
        result: "PASS",
        scope: "profiles/usr_synthetic_4821",
        artifactRef: null,
      },
      {
        id: "analytics-store",
        label: "Analytics profiles",
        expected: "Removed within 24h",
        observed: "1 active record at +25h",
        result: "FAIL",
        scope: "analytics_profiles/usr_synthetic_4821",
        artifactRef: null,
      },
    ],
    events: [
      {
        id: "capture",
        stage: "CAPTURING",
        state: "SUCCEEDED",
        title: "Capture promise",
        detail: "Snapshot loaded; source was not fetched",
        at: isoAt(now, 19_006),
        system: "Static presentation fixture",
        artifactRef: null,
      },
      {
        id: "compile",
        stage: "COMPILING",
        state: "SUCCEEDED",
        title: "Structure promise",
        detail: "Saved mapping · privacy.account_deletion.v1",
        at: isoAt(now, 17_696),
        system: "Static presentation fixture",
        artifactRef: null,
      },
      {
        id: "probe",
        stage: "PROBING",
        state: "SUCCEEDED",
        title: "Test account deletion",
        detail: "Saved evidence · +1h to +25h 04m",
        at: isoAt(now, 14_856),
        system: "Static presentation fixture",
        artifactRef: null,
      },
      {
        id: "evaluate",
        stage: "EVALUATING",
        state: "SUCCEEDED",
        title: "Evaluate evidence",
        detail: "Contradicted · analytics profile remained",
        at: isoAt(now, 14_444),
        system: "Static presentation fixture",
        artifactRef: null,
      },
      {
        id: "verify",
        stage: "VERIFYING",
        state: "SKIPPED",
        title: "Verify repair",
        detail: "Not run · verification unavailable",
        at: isoAt(now, 640),
        system: "Isolated verifier",
        artifactRef: null,
      },
      {
        id: "publish",
        stage: "ROUTING_ACTION",
        state: "SKIPPED",
        title: "Select action",
        detail: "Issue selected · actions off",
        at: now.toISOString(),
        system: "Action router",
        artifactRef: null,
      },
    ],
    actions: [
      {
        id: "action_pr_demo_18",
        kind: "pull_request",
        state: "SKIPPED",
        title: "Repair not verified",
        reason: "No patch was tested in isolation.",
        url: null,
        verified: false,
      },
      {
        id: "action_issue_demo_17",
        kind: "issue",
        state: "PLANNED",
        title: "Account deletion does not clear analytics profiles",
        reason: "No verified repair is available.",
        url: null,
        verified: false,
      },
      {
        id: "action_email_demo_01",
        kind: "email",
        state: "SKIPPED",
        title: "Email not selected",
        reason: "Escalation requires two consecutive contradictions (1 of 2).",
        url: null,
        verified: false,
      },
    ],
    runtime: {
      agentFramework: "Static audit snapshot",
      modelInvocationAttempted: false,
      modelInvoked: false,
      model: null,
      executionTarget: "Browser-local snapshot",
      cloudRunRevision: null,
    },
    limitations: [
      "The local snapshot uses synthetic data; no audit control or Gemini call ran.",
      "External actions are disabled in this environment.",
      "A contradiction is a scoped control result, not a legal compliance conclusion.",
    ],
    remediation: null,
    verification: null,
    idempotencyKey: "static-snapshot-0001",
    syntheticFixtureId: "usr_synthetic_4821",
  };
}

export function prepareDemonstrationRun(finalRun: AuditRun): AuditRun {
  return {
    ...finalRun,
    status: "RECEIVED",
    verdict: "PENDING",
    updatedAt: finalRun.startedAt,
    events: finalRun.events.map((event) => ({
      ...event,
      state: "PENDING",
    })),
    actions: finalRun.actions.map((action) => ({
      ...action,
      verified: false,
    })),
  };
}
