import { z } from "zod";

export const auditModeSchema = z.enum(["cloud", "local", "demonstration"]);
export type AuditMode = z.infer<typeof auditModeSchema>;

export const verdictSchema = z.enum([
  "PENDING",
  "SUPPORTED",
  "CONTRADICTED",
  "INCONCLUSIVE",
  "NOT_TESTED",
]);
export type Verdict = z.infer<typeof verdictSchema>;

export const auditStatusSchema = z.enum([
  "RECEIVED",
  "CAPTURING",
  "COMPILING",
  "BINDING",
  "PROBING",
  "EVALUATING",
  "REMEDIATING",
  "VERIFYING",
  "ROUTING_ACTION",
  "COMPLETE",
  "FAILED_RETRYABLE",
  "FAILED_SAFE",
]);
export type AuditStatus = z.infer<typeof auditStatusSchema>;

export const eventStateSchema = z.enum([
  "PENDING",
  "RUNNING",
  "SUCCEEDED",
  "FAILED",
  "SKIPPED",
]);
export type EventState = z.infer<typeof eventStateSchema>;

export const claimSchema = z.object({
  exactQuote: z.string().min(1),
  sourceUrl: z.string().url(),
  sourceTitle: z.string(),
  capturedAt: z.string().datetime({ offset: true }),
  contentHash: z.string(),
  actor: z.string().nullable().optional(),
  action: z.string().nullable().optional(),
  object: z.string().nullable().optional(),
  deadlineHours: z.number().int().nonnegative().nullable().optional(),
  qualifiers: z.array(z.string()),
  testability: z.enum(["EXECUTABLE", "PARTIAL", "NOT_TESTABLE"]),
  controlId: z.string().nullable(),
}).strict();
export type Claim = z.infer<typeof claimSchema>;

export const evidenceSchema = z.object({
  id: z.string(),
  label: z.string(),
  expected: z.string(),
  observed: z.string(),
  result: z.enum(["PASS", "FAIL", "UNKNOWN"]),
  scope: z.string().nullable().optional(),
  artifactRef: z.string().nullable().optional(),
}).strict();
export type Evidence = z.infer<typeof evidenceSchema>;

export const auditEventSchema = z.object({
  id: z.string(),
  stage: z.string(),
  state: eventStateSchema,
  title: z.string(),
  detail: z.string().nullable().optional(),
  at: z.string().datetime({ offset: true }),
  system: z.string().nullable().optional(),
  artifactRef: z.string().nullable().optional(),
}).strict();
export type AuditEvent = z.infer<typeof auditEventSchema>;

export const auditActionSchema = z.object({
  id: z.string(),
  kind: z.enum(["pull_request", "issue", "email"]),
  state: z.enum(["PLANNED", "BLOCKED", "READY", "OPENED", "SENT", "SKIPPED"]),
  title: z.string(),
  reason: z.string().nullable().optional(),
  url: z.string().url().nullable().optional(),
  verified: z.boolean(),
}).strict();
export type AuditAction = z.infer<typeof auditActionSchema>;

export const runtimeSchema = z.object({
  agentFramework: z.string(),
  modelInvocationAttempted: z.boolean(),
  modelInvoked: z.boolean(),
  model: z.string().nullable().optional(),
  executionTarget: z.string(),
  cloudRunRevision: z.string().nullable().optional(),
}).strict();
export type AuditRuntime = z.infer<typeof runtimeSchema>;

export const fileEditSchema = z.object({
  path: z.string(),
  operation: z.string(),
  rationale: z.string(),
  contentPreview: z.string(),
}).strict();

export const remediationSchema = z.object({
  summary: z.string(),
  baseReference: z.string(),
  edits: z.array(fileEditSchema),
  generatedBy: z.string(),
}).strict();

export const verificationSchema = z.object({
  verifier: z.string(),
  baselineControl: z.enum(["PASS", "FAIL", "NOT_RUN"]),
  candidateControl: z.enum(["PASS", "FAIL", "NOT_RUN"]),
  regressionSuite: z.enum(["PASS", "FAIL", "NOT_RUN"]),
  exactTreeVerified: z.boolean(),
  isolated: z.boolean(),
  publishable: z.boolean(),
  detail: z.string(),
}).strict();

export const githubRepositorySchema = z.object({
  id: z.number().int().positive(),
  fullName: z.string().min(3),
  defaultBranch: z.string().min(1),
  private: z.boolean(),
  archived: z.boolean(),
  htmlUrl: z.string().url(),
}).strict();
export type GitHubRepository = z.infer<typeof githubRepositorySchema>;

export const githubIntegrationStatusSchema = z.object({
  configured: z.boolean(),
  connected: z.boolean(),
  actionsEnabled: z.boolean(),
  accountLogin: z.string().nullable().optional(),
  repositories: z.array(githubRepositorySchema),
  selectedRepository: githubRepositorySchema.nullable().optional(),
}).strict();
export type GitHubIntegrationStatus = z.infer<
  typeof githubIntegrationStatusSchema
>;

export const auditRunSchema = z.object({
  id: z.string().min(8),
  mode: auditModeSchema,
  status: auditStatusSchema,
  verdict: verdictSchema,
  startedAt: z.string().datetime({ offset: true }),
  updatedAt: z.string().datetime({ offset: true }),
  claim: claimSchema,
  evidence: z.array(evidenceSchema),
  events: z.array(auditEventSchema),
  actions: z.array(auditActionSchema),
  runtime: runtimeSchema,
  remediation: remediationSchema.nullable().optional(),
  verification: verificationSchema.nullable().optional(),
  repository: githubRepositorySchema.nullable().optional(),
  idempotencyKey: z.string().min(8),
  syntheticFixtureId: z.string().nullable().optional(),
  limitations: z.array(z.string()).optional(),
}).strict();
export type AuditRun = z.infer<typeof auditRunSchema>;

export const apiErrorSchema = z.object({
  error: z.object({
    code: z.string(),
    message: z.string(),
  }).strict(),
}).strict();
export type ApiError = z.infer<typeof apiErrorSchema>;

export function parseAuditRun(input: unknown): AuditRun {
  return auditRunSchema.parse(input);
}

export function isTerminalRun(run: AuditRun): boolean {
  return (
    run.status === "COMPLETE" ||
    run.status === "FAILED_RETRYABLE" ||
    run.status === "FAILED_SAFE"
  );
}
