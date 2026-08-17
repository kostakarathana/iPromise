# iPromise implementation status

Last reviewed: **2026-08-17 AEST**

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
| Google stack and trust boundaries | Designed | [Architecture ADR](adr/0002-architecture-and-google-stack.md); deployment pending |
| Judge-facing architecture diagram | Documented | [Architecture](architecture.md) |
| Threat model | Partially implemented | [Threat model](threat-model.md); issue-path auth/idempotency controls tested, verifier/PR controls pending |
| Evaluation and release gates | Partially verified locally | 16 synthetic claim fixtures validate; full model metrics remain unmeasured |
| Under-four-minute demo plan | Documented | [Demo script](demo-script.md); no recording yet |
| Console information hierarchy | Decided | [Quiet evidence console ADR](adr/0005-quiet-evidence-console.md) |
| Application code and local workflow | Verified locally | `pnpm verify`; Chrome exercised console → agent → synthetic product end to end |
| Gemini 3.5 through Vertex AI | Pending | Require exact model config and correlated invocation evidence |
| Google ADK graph | Partially verified locally | Locked ADK 2.7 graph instantiates without a model call; live Gemini/Vertex trajectory pending |
| Cloud Run / Firestore / Scheduler | Implemented; deployment pending | Digest-pinned, non-root Dockerfiles; guarded clean-commit deploy; Firestore stores; OIDC Scheduler endpoint; require deployed resource and log proof |
| Pub/Sub / Storage | Target only | Not required by the minimum deployed slice; do not show as implemented |
| Synthetic reference SaaS | Verified locally | 5 tests; disclosed virtual clock, authenticated synthetic routes, deliberate analytics residual; cloud deployment pending |
| Claim capture and typed compiler | Partially verified locally | Exact HTTP-source capture, literal grounding, strict deterministic payload, and abstention tests work; Gemini/ADK and rendered-browser capture pending |
| Deterministic deletion control | Verified locally | Known T0+1h pass, analytics residual fail, missing-evidence abstention, and known-late-worker contradiction tests |
| Isolated red-before/green-after verifier | Pending | Require repeated Sandbox or Cloud Build receipts |
| Bounded remediation/action policy | Verified locally | Non-publishable `NOT_RUN` receipt; exactly one selected route; issue dispatch remains explicitly gated |
| Real GitHub draft PR | Pending | Require least-privilege App, isolated green receipt, and one reconciled action receipt |
| GitHub repository connection | Verified in integration tests | Single-use state, OAuth PKCE, installation-owner verification, authorized repository selection; live App receipt pending |
| GitHub issue fallback | Verified in integration tests | Repo-scoped tokens, stable finding fingerprints, remote-marker reconciliation, and a transactional cross-run intent lease produce one `OPENED` receipt even for concurrent runs; real GitHub receipt pending |
| Email notification | Optional / pending | Provider is not selected; do not claim delivery |
| Local judge console | Verified locally | Console test suite, TypeScript, ESLint, production build, repository selector, connected run, and exact source checked in Chrome |
| Hosted judge console | Pending | Require stable URL, access test, and cloud logs |
| Entrant/team/prize eligibility | Unresolved | Must be confirmed by the entrant; do not infer it |
| Cloud credit status | Unresolved | Verify through current official Resources/FAQ flow |
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
