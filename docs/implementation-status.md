# iPromise implementation status

Last reviewed: **2026-08-18 AEST**

This file distinguishes durable decisions from working software. A component is
“Verified” only after a reproducible test or deployment artifact exists. Planned
behavior is not a product claim.

## Current status

| Area | Status | Evidence / next proof |
| --- | --- | --- |
| Product name: iPromise | Decided | Product documentation in `docs/` |
| Hackathon end goal | Documented | Repository agent instructions and [evidence matrix](evidence-matrix.md) |
| Track: Taskmaster | Decided | [ADR 0001](adr/0001-product-and-track.md) |
| MVP: account-deletion promise | Decided | [ADR 0001](adr/0001-product-and-track.md) |
| PR-first / issue-email fallback policy | Decided | [ADR 0004](adr/0004-action-policy.md) |
| Google stack and trust boundaries | Baseline deployed | [Architecture ADR](adr/0002-architecture-and-google-stack.md); live Cloud Run, ADK, Gemini, Firestore, Secret Manager, Scheduler, and Logging receipt verified; Cloud Build and GitHub-action proof pending |
| Judge-facing architecture diagram | Documented | [Architecture](architecture.md) |
| Threat model | Partially implemented | [Threat model](threat-model.md); live scoped IAM, pinned secrets, actions-off receipt, and fail-closed model-location recovery verified; Cloud Build egress and live GitHub-action proof pending |
| Evaluation and release gates | Partially verified locally | 16 synthetic claim fixtures validate; full model metrics remain unmeasured |
| Under-four-minute demo plan | Documented | [Demo script](demo-script.md); no recording yet |
| Console information hierarchy | Decided | [Quiet evidence console ADR](adr/0005-quiet-evidence-console.md) |
| Application code and local workflow | Verified locally | `pnpm verify`: 16 claim fixtures, 6 synthetic SaaS tests, 96 agent tests, 34 console tests, lint, typecheck, production build, and standalone package smoke |
| Gemini 3.5 through Vertex AI | Verified live | Run `run_14a197bafd1d4a44a248e67320092d16` records `modelInvoked=true`, exact model `gemini-3.5-flash`, and Cloud Run revision `ipromise-agent-00005-hk6`; Vertex location is `global` |
| Google ADK graph | Verified live | The same correlated receipt records `Google Agent Development Kit 2 Graph Workflow`; the exact claim was compiled and grounded before deterministic control execution |
| Cloud Run / Firestore / Scheduler | Verified live baseline | Three healthy Cloud Run services, Firestore Native document, enabled OIDC six-hour Scheduler, and structured Cloud Logging receipt share the deployed workflow; live verifier/action proof remains pending |
| Secret Manager runtime credentials | Verified live | Five secrets are pinned to numeric version 1 and granted only to their runtime service identities; payloads remain outside Git and deployment output |
| Pub/Sub / Storage | Target only | Not required by the minimum deployed slice; do not show as implemented |
| Synthetic reference SaaS | Verified live | 6 tests plus healthy Cloud Run service; disclosed virtual clock, authenticated synthetic routes, and deliberate analytics residual produced the live contradiction |
| Claim capture and typed compiler | Verified live for HTTP source | Run `run_14a197bafd1d4a44a248e67320092d16` captured, compiled, grounded, and bound the exact account-deletion promise; rendered-browser capture remains pending |
| Deterministic deletion control | Verified locally | Known T0+1h pass, analytics residual fail, missing-evidence abstention, and known-late-worker contradiction tests |
| Cloud Build red-before/green-after verifier | Implemented and verified locally; cloud proof pending | Trusted inline Cloud Build request, exact public-repository/base provenance, expected-red baseline, byte-exact candidate materialization, green control, regression suite, bounded cancellation, and fail-closed receipt are covered by focused tests. A real Cloud Build receipt and repeated reliability runs remain required; Cloud Build has outbound source/dependency access and is not presented as a no-egress sandbox. |
| Bounded remediation/action policy | Verified locally | Exact two-file preimages, approved deterministic edits, canonical diff/hashes, strict drift/size/path guards, exactly one selected route, verifier handoff, and safe fallback are covered by focused and workflow integration tests. |
| Real GitHub draft PR | Integrated and verified locally; live proof pending | Exact verifier-shaped bytes are published through Git objects only after the complete gate; deterministic commits, base drift, ambiguous responses, concurrent/cross-run reconciliation, checkpoint recovery, draft-only behavior, scoped token identity, and no force/merge behavior are tested. The live GitHub App still needs Contents and Pull requests read/write permissions, deployed OAuth proof, and one real receipt. |
| GitHub repository connection | App provisioned; OAuth proof pending | Connection behavior is verified in integration tests. GitHub App `ipromise-promise-auditor` is registered and installed only on the entrant-owned repository; private-key and OAuth client-secret version 1 are stored in Secret Manager with no payload in Git. A deployed callback and live OAuth receipt remain pending. |
| GitHub issue fallback | Verified in integration tests | Repo-scoped tokens, stable finding fingerprints, remote-marker reconciliation, and a transactional cross-run intent lease produce one `OPENED` receipt even for concurrent runs; real GitHub receipt pending |
| Email notification | Optional / pending | Provider is not selected; do not claim delivery |
| Local judge console | Verified locally | Console tests, TypeScript, ESLint, production build, repository selector, connected run, exact source, and concise red/green/exact-tree/build-log receipt view |
| Hosted judge console | Deployed; private-access rehearsal pending | `https://ipromise-console-ipj6vqlg2q-uc.a.run.app`; health and agent proxy configuration pass, but the access-code and full browser rehearsal remain pending |
| Entrant/team/prize eligibility | Confirmed by entrant | Solo individual; above local age of majority; no employment conflict. Target Individual/Hobbyist as the relevant secondary prize, subject to a final full Official Rules eligibility check before submission. |
| Google Cloud billing | Linked and CLI-verified | Project `ipromise-agentic-2026` linked to billing on 2026-08-18 AEST; `billingEnabled=True`. The account identifier is deliberately omitted from the public repository. |
| Cloud credit status | Request submitted; inbox monitor active | Submitted 2026-08-17 AEST through the current official Resources form for Taskmaster; confirmation received; an hourly Gmail monitor watches for the approval/code without exposing or redeeming it. Wait up to 72 business hours and do not resubmit unless denied. Code receipt/redemption and expiry evidence remain pending. |
| Devpost entry, public video, frozen release | Pending | Complete and verify before internal August 28 target |

## Truthful environment labels

- **Production/judge mode:** real GCP services and explicitly authorized external
  integrations. A status is shown only after its receipt is persisted.
- **Local presentation mode:** synthetic/local substitutes are allowed for
  development, but the UI must visibly state **Local** and **Synthetic data**. It
  must not imply Cloud Run, Gemini, or an external action unless the run contains
  the corresponding receipt URL.
- **Synthetic reference SaaS:** a deliberately faulty product fixture owned by this
  project. Its behavior is real within the fixture, but it is not a claim about a
  third party or real customer system.

## Update discipline

When a component becomes operational, add the exact command/test, commit, cloud
resource, or receipt that verifies it. Do not replace “Pending” with “Verified”
because code exists or a mock screen renders. Reconcile this file with
[the evidence matrix](evidence-matrix.md) before every submission rehearsal.
