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
| Evaluation and release gates | Core cloud path verified | [Evaluation](evaluation.md): ten consecutive actions-off red→green runs passed in 448.5 seconds; a controlled actions-on run opened one verified draft PR; same-key and distinct-run replay created no duplicate. The final code/test/build/package, dependency-vulnerability, link, upload-manifest, and repository/history secret gates passed; see the [release record](submission-release.md#release-verification). Full held-out model-quality metrics remain unmeasured. |
| Under-four-minute demo | Local master QA passed; public upload pending | The final local master is 3:30 at 1920×1080 with English narration and burned captions. Full decode, wall-clock timing, caption, audio (`-16.02 LUFS`), and privacy QA passed; the checksum is in the [submission release record](submission-release.md). Public upload, processing, and logged-out playback remain. |
| Console information hierarchy | Decided | [Quiet evidence console ADR](adr/0005-quiet-evidence-console.md) |
| Application code and local workflow | Verified locally | `pnpm verify`: 16 claim fixtures, 6 synthetic SaaS tests, 97 agent tests, 36 console tests, lint, typecheck, production build, and standalone package smoke |
| Gemini 3.5 through Vertex AI | Verified live on final source | Actions-on run `run_74ea1919b21a47b9846a4d3c5efb48b8` records `modelInvoked=true`, exact model `gemini-3.5-flash`, and Cloud Run revision `ipromise-agent-00012-2gm`; Vertex location is `global`. Current judge-safe revision `ipromise-agent-00013-kmv` has GitHub actions disabled. |
| Google ADK graph | Verified live | The same correlated receipt records the Google Agent Development Kit graph workflow; the exact claim was compiled and grounded before deterministic control execution. |
| Cloud Run / Firestore / Scheduler | Verified live | Source `a4e7a59f89a60d2ba0ad087d884836d22e5d39e4` is deployed as console `ipromise-console-00012-kk9`, judge-safe agent `ipromise-agent-00013-kmv`, and synthetic SaaS `ipromise-demo-saas-00010-xk5`. Firestore persisted run/action state. The OIDC six-hour Scheduler is intentionally **PAUSED**; no nonterminal runs or execution/action leases remained after final checks. |
| Secret Manager runtime credentials | Verified live | Five secrets are pinned to numeric version 1 and granted only to their runtime service identities; payloads remain outside Git and deployment output |
| Pub/Sub / Storage | Target only | Not required by the minimum deployed slice; do not show as implemented |
| Synthetic reference SaaS | Verified live | 6 tests plus healthy Cloud Run service; disclosed virtual clock, authenticated synthetic routes, and deliberate analytics residual produced the live contradiction |
| Claim capture and typed compiler | Verified live for HTTP source | Final run `run_74ea1919b21a47b9846a4d3c5efb48b8` captured, compiled, grounded, and bound the exact account-deletion promise; rendered-browser capture remains pending. |
| Deterministic deletion control | Verified live on synthetic data | The historical ten-run gate plus final creator and duplicate runs produced the intended scoped `CONTRADICTED` evidence: application record absent, analytics record retained. Missing-evidence and late-worker cases remain covered locally. |
| Cloud Build red-before/green-after verifier | Verified live repeatedly | Ten historical actions-off runs against base `b5c2badacc506b78c6eed314f155ecbc2188198b` each returned expected `FAIL / PASS / PASS`, exact-tree match, and a publishable receipt in 448.5 seconds total. Final-source builds `e1a7a7a5-1878-41d6-9760-27c7085ae332` and `e7966c07-97fd-4436-b7a8-8a0a1d4e86fd` returned the same complete gate. Cloud Build outbound source/dependency access is disclosed; it is not presented as a no-egress sandbox. |
| Bounded remediation/action policy | Verified live for the locked repair | Final run `run_74ea1919b21a47b9846a4d3c5efb48b8` passed the exact two-file/base/tree gate and published only the verified bytes as a draft PR. Broad or generalized repair is not claimed. |
| Real GitHub draft PR | Verified live on final source | GitHub App run `run_74ea1919b21a47b9846a4d3c5efb48b8` and Cloud Build `e1a7a7a5-1878-41d6-9760-27c7085ae332` opened verified draft [PR #14](https://github.com/kostakarathana/iPromise/pull/14). Head `a460858672ab176a4142c600fb9028f1b042a373` passed the [release gate](https://github.com/kostakarathana/iPromise/actions/runs/32219511076/job/95967239117). Earlier proof PRs #7 and #12 are closed. The publisher exposes no merge or deploy operation and creates draft PRs only. |
| GitHub repository connection | Verified live | GitHub App `ipromise-promise-auditor` completed hosted OAuth and is installed only on `kostakarathana/iPromise`, with Metadata read plus Contents, Pull requests, and Issues read/write. It has no Actions, Workflows, Administration, Secrets, or Deployments permission. |
| External-action idempotency | Verified live on final source | Distinct run `run_a2dca42370fd42bda69f2eff361c3bfd`, build `e7966c07-97fd-4436-b7a8-8a0a1d4e86fd`, reconciled to [PR #14](https://github.com/kostakarathana/iPromise/pull/14). Replaying its trigger key returned that same run, build, and PR; the PR count remained one for the final fingerprint. |
| GitHub issue fallback | Verified in integration tests; live route not exercised | Repo-scoped tokens, stable finding fingerprints, remote-marker reconciliation, and a transactional cross-run intent lease produce one `OPENED` receipt even for concurrent runs. The successful live PR proof intentionally created zero issues; no live issue receipt is claimed. |
| Email notification | Optional / pending | Provider is not selected; do not claim delivery |
| Local judge console | Verified locally | Console tests, TypeScript, ESLint, production build, repository selector, connected run, exact source, and concise red/green/exact-tree/build-log receipt view |
| Hosted judge console | Deployed; clean access gate passed | Console `https://ipromise-console-ipj6vqlg2q-uc.a.run.app`; unauthenticated `/api/audit` returned 401, `/api/health` returned 200, and a fresh session obtained with the Secret Manager console code returned authenticated product content without printing the credential. Hosted OAuth, repository selection, final-source audit, verifier receipt, and PR link also completed. Current judge-safe agent has GitHub actions disabled and Scheduler paused. Supplying the code in Devpost's private field remains pending. |
| Entrant/team/prize eligibility | Confirmed by entrant | Solo individual; above local age of majority; no employment conflict. Target Individual/Hobbyist as the relevant secondary prize, subject to a final full Official Rules eligibility check before submission. |
| Google Cloud billing | Linked and CLI-verified | Project `ipromise-agentic-2026` linked to billing on 2026-08-18 AEST; `billingEnabled=True`. The account identifier is deliberately omitted from the public repository. |
| Cloud credit status | Request submitted; inbox monitor active | Submitted 2026-08-17 AEST through the current official Resources form for Taskmaster; confirmation received; an hourly Gmail monitor watches for the approval/code without exposing or redeeming it. Wait up to 72 business hours and do not resubmit unless denied. Code receipt/redemption and expiry evidence remain pending. |
| Devpost entry, public video, frozen release | Pending — private draft saved at 2/5; not submitted | Title, elevator pitch, and architecture image are persisted. Complete public upload/playback, remaining fields, private credential insertion, and immutable tag/release before submission. |

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
