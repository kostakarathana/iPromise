# iPromise implementation status

Last reviewed: **2026-08-19 AEST**

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
| Google stack and trust boundaries | Verified live vertical slice | [Architecture ADR](adr/0002-architecture-and-google-stack.md); live Cloud Run, ADK, Gemini, Firestore, Secret Manager, Cloud Scheduler, Cloud Build, Cloud Logging, and one bounded GitHub draft-PR receipt are verified. Scheduler is intentionally paused after proof. |
| Judge-facing architecture diagram | Documented | [Static diagram](assets/architecture.svg) and [architecture narrative](architecture.md) |
| Threat model | Core live boundaries verified | [Threat model](threat-model.md); scoped IAM, pinned secrets, ten actions-off verifier receipts, exact-byte PR publication, and remote duplicate reconciliation are live. Cloud Build egress remains explicitly disclosed; Model Armor, generalized repair, artifact storage, and email are pending. |
| Evaluation and release gates | Core cloud path verified | [Evaluation](evaluation.md): ten consecutive actions-off red→green runs passed in 448.5 seconds; a controlled actions-on run opened one verified draft PR; same-key and distinct-run replay created no duplicate. Full held-out model-quality metrics remain unmeasured. |
| Under-four-minute demo plan | Documented | [Demo script](demo-script.md); no recording yet |
| Console information hierarchy | Decided | [Quiet evidence console ADR](adr/0005-quiet-evidence-console.md) |
| Application code and local workflow | Verified locally | `pnpm verify`: 16 claim fixtures, 6 synthetic SaaS tests, 97 agent tests, 36 console tests, lint, typecheck, production build, and standalone package smoke |
| Gemini 3.5 through Vertex AI | Verified live | Actions-on run `run_806d1fc144344baebb757747d1b56e83` records `modelInvoked=true`, exact model `gemini-3.5-flash`, and Cloud Run revision `ipromise-agent-00007-8p9`; Vertex location is `global`. |
| Google ADK graph | Verified live | The same correlated receipt records the Google Agent Development Kit graph workflow; the exact claim was compiled and grounded before deterministic control execution. |
| Cloud Run / Firestore / Scheduler | Verified live | Console, agent, and synthetic SaaS are healthy Cloud Run services; Firestore persisted run/action state. The OIDC six-hour Scheduler exists but is intentionally **PAUSED** after controlled proof. No nonterminal runs or execution/action leases remained after the final checks. |
| Secret Manager runtime credentials | Verified live | Five secrets are pinned to numeric version 1 and granted only to their runtime service identities; payloads remain outside Git and deployment output |
| Pub/Sub / Storage | Target only | Not required by the minimum deployed slice; do not show as implemented |
| Synthetic reference SaaS | Verified live | 6 tests plus healthy Cloud Run service; disclosed virtual clock, authenticated synthetic routes, and deliberate analytics residual produced the live contradiction |
| Claim capture and typed compiler | Verified live for HTTP source | Run `run_806d1fc144344baebb757747d1b56e83` captured, compiled, grounded, and bound the exact account-deletion promise; rendered-browser capture remains pending. |
| Deterministic deletion control | Verified live on synthetic data | Ten actions-off and three controlled actions-on/replay runs produced the intended scoped `CONTRADICTED` evidence: application record absent, analytics record retained. Missing-evidence and late-worker cases remain covered locally. |
| Cloud Build red-before/green-after verifier | Verified live repeatedly | Ten consecutive actions-off runs against base `b5c2badacc506b78c6eed314f155ecbc2188198b` each returned expected `FAIL / PASS / PASS`, exact-tree match, and a publishable receipt with unique run/build/fixture identities in 448.5 seconds total. The actions-on and distinct-occurrence runs also returned valid receipts. Cloud Build outbound source/dependency access is disclosed; it is not presented as a no-egress sandbox. |
| Bounded remediation/action policy | Verified live for the locked repair | Run `run_806d1fc144344baebb757747d1b56e83` passed the exact two-file/base/tree gate and published only the verified bytes as a draft PR. Broad or generalized repair is not claimed. |
| Real GitHub draft PR | Verified live | GitHub App run `run_806d1fc144344baebb757747d1b56e83`, Cloud Build `f4cbf983-db73-4bf5-9504-93c253a4b98b`, opened verified draft [PR #7](https://github.com/kostakarathana/iPromise/pull/7). Duplicate proof left exactly one deterministic branch and one open draft PR. The implemented publisher exposes no merge or deploy operation and creates draft PRs only. |
| GitHub repository connection | Verified live | GitHub App `ipromise-promise-auditor` completed hosted OAuth and is installed only on `kostakarathana/iPromise`, with Metadata read plus Contents, Pull requests, and Issues read/write. It has no Actions, Workflows, Administration, Secrets, or Deployments permission. |
| External-action idempotency | Verified live | Same-key run `run_60edca0afdd34918805f72464662b340` and distinct run `run_6babae8849fc46fca2d522caf3e2ce98` both reconciled to [PR #7](https://github.com/kostakarathana/iPromise/pull/7), using builds `75a9e18b-766f-48e4-ad10-06b52cac0025` and `5e77604a-5f19-4be3-9988-48809c48125c`. Final remote state: one branch, one open draft PR, zero issues. |
| GitHub issue fallback | Verified in integration tests; live route not exercised | Repo-scoped tokens, stable finding fingerprints, remote-marker reconciliation, and a transactional cross-run intent lease produce one `OPENED` receipt even for concurrent runs. The successful live PR proof intentionally created zero issues; no live issue receipt is claimed. |
| Email notification | Optional / pending | Provider is not selected; do not claim delivery |
| Local judge console | Verified locally | Console tests, TypeScript, ESLint, production build, repository selector, connected run, exact source, and concise red/green/exact-tree/build-log receipt view |
| Hosted judge console | Deployed and authenticated workflow rehearsed | Console `https://ipromise-console-ipj6vqlg2q-uc.a.run.app`; agent `https://ipromise-agent-ipj6vqlg2q-uc.a.run.app`; hosted OAuth, repository selection, controlled audit, verifier receipt, and outbound PR link completed. Final clean-browser judge rehearsal remains required before submission. |
| Entrant/team/prize eligibility | Confirmed by entrant | Solo individual; above local age of majority; no employment conflict. Target Individual/Hobbyist as the relevant secondary prize, subject to a final full Official Rules eligibility check before submission. |
| Google Cloud billing | Linked and CLI-verified | Project `ipromise-agentic-2026` linked to billing on 2026-08-18 AEST; `billingEnabled=True`. The account identifier is deliberately omitted from the public repository. |
| Cloud credit status | Request submitted; inbox monitor active | Submitted 2026-08-17 AEST through the current official Resources form for Taskmaster; confirmation received; an hourly Gmail monitor watches for the approval/code without exposing or redeeming it. Wait up to 72 business hours and do not resubmit unless denied. Code receipt/redemption and expiry evidence remain pending. |
| Devpost entry, public video, frozen release | Pending — not submitted | Complete the video, final rules/eligibility check, immutable release, and clean-browser judge-access rehearsal before the internal August 28 target. |

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
