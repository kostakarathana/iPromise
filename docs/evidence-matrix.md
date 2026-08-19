# Hackathon evidence matrix

This is iPromise's release gate for Google's All Things Agentic Hackathon. The
[official rules](https://allthingsagentichackathon.devpost.com/rules) are binding;
the [overview](https://allthingsagentichackathon.devpost.com/),
[resources](https://allthingsagentichackathon.devpost.com/resources), and
[schedule](https://allthingsagentichackathon.devpost.com/details/dates) are
supporting references. Recheck all four before submission-critical decisions.

Statuses mean:

- **Documented**: a durable decision or artifact exists, but runtime proof may not.
- **Pending**: required implementation or evidence has not been verified.
- **Verified**: use only with a reproducible artifact and recorded proof.

Local-only evidence may be marked **Verified locally**. That status never satisfies
the separate Gemini, Google ADK, Google Cloud deployment, or real-external-action
gates.

## Stage 1 and mandatory technology

| Requirement | Status | Repository evidence | Demo/submission proof still required |
| --- | --- | --- | --- |
| Enter exactly one track | Documented | [Taskmaster decision](adr/0001-product-and-track.md) | Select Taskmaster on Devpost and show consistent wording everywhere |
| Address a real challenge beyond chat | Verified live for the scoped MVP | Creator run `run_74ea1919b21a47b9846a4d3c5efb48b8` opened verified draft [PR #14](https://github.com/kostakarathana/iPromise/pull/14); the filmed distinct run `run_a2dca42370fd42bda69f2eff361c3bfd` executes the full workflow and reconciles to it | Local final video recorded; complete public upload and playback QA |
| Gemini 3.5 or newer | Verified live | Creator receipt records `gemini-3.5-flash`, `modelInvoked=true`, actions-on revision `ipromise-agent-00012-2gm`, and Vertex `global`; the filmed duplicate run also executes the live Gemini/ADK workflow | Confirm both run identities remain clear in public playback |
| Google agent framework | Verified live | The receipt records the Google Agent Development Kit graph workflow; the typed claim was grounded before deterministic control execution | Confirm the recorded ADK/Vertex trajectory and run ID remain legible in public playback |
| Google Cloud infrastructure | Verified live | Cloud Run hosts all three services; Firestore stores state; OIDC Cloud Scheduler exists and is paused after proof; Cloud Build produced repeated verifier receipts; Secret Manager and Cloud Logging support the deployed path | Confirm Cloud proof remains legible in public video playback |
| Deployed on Google Cloud | Verified live | Source `a4e7a59f89a60d2ba0ad087d884836d22e5d39e4`; console `ipromise-console-00012-kk9`; judge-safe agent `ipromise-agent-00013-kmv`; synthetic SaaS `ipromise-demo-saas-00010-xk5`; stable URLs; clean access-code session passed | Public video playback and private Devpost credential insertion |
| Meaningful autonomous workflow | Verified live through real external action | Creator run captured and compiled the claim, produced scoped `CONTRADICTED` evidence, passed Cloud Build, and opened PR #14. The continuous filmed distinct run repeats the full workflow and safely reconciles to that existing action | Public upload remains; do not imply the filmed run created the PR |
| English support and materials | Recorded locally / public playback pending | Repository, UI, listing draft, English narration, and burned English captions | Confirm public playback and listing text |
| New-project and third-party provenance disclosure | Documented | [Provenance and third-party materials](provenance.md); initial commit is dated inside the Submission Period; final video and assets are disclosed | Recheck the frozen release against the inventory |
| No secrets in repository | Verified locally and against deployed configuration | [Release verification](submission-release.md#release-verification): working-tree and full-history high-confidence scans passed; known local sensitive literals are absent; Cloud Run upload manifests exclude secret-shaped files; five enabled numeric secret versions have service-level accessor bindings | Re-run after the final documentation commit and do not expose the private Devpost credential |

## Required submission artifacts

| Artifact | Status | Evidence/location | Final gate |
| --- | --- | --- | --- |
| Selected category | Documented | Taskmaster in [ADR 0001](adr/0001-product-and-track.md) | Devpost field matches exactly |
| Project description: features, technologies, sources, learnings | Documented / final proof pending | [Devpost submission draft](devpost-submission-draft.md) | Remove placeholders and cross-check every claim against this matrix |
| Repository URL | Verified public | `https://github.com/kostakarathana/iPromise`; deployed source and generated PR head passed GitHub checks | Create the immutable final submission tag/release after the evidence-doc update |
| Reproducible README | Verified from a clean public clone | Root `README.md`, `scripts/dev-local`, `scripts/verify`, and the isolated standalone console-package smoke. A clean public clone of deployed source `a4e7a59f89a60d2ba0ad087d884836d22e5d39e4` passed the complete release gate on 2026-08-19 AEST | Re-run from the immutable tag after it is created |
| Architecture diagram | Documented | [Architecture](architecture.md) | Diagram matches the deployed system and is visible in submission |
| Hosted project URL, if supplied | Verified live with clean access gate | `https://ipromise-console-ipj6vqlg2q-uc.a.run.app`; unauthenticated audit returned 401, health returned 200, and a fresh authenticated session returned product content without exposing the code. Hosted OAuth, final-source audit, and PR-link flow also completed; actions are now off and Scheduler paused | Put the code only in Devpost's private field and preserve access through judging |
| Public YouTube/Vimeo video, maximum 4:00 | Local master QA passed / public upload pending | 3:30, 1920×1080, English narration, burned captions, full decode, measured timing, `-16.02 LUFS`, and SHA-256 recorded in the [release manifest](submission-release.md) | Public upload, processing, and logged-out playback |
| Video explains problem and value | Recorded locally | 0:00–0:30 in the [recorded cut sheet](demo-script.md) | Confirm legibility and audio in public playback |
| Video shows application in action | Recorded locally | 0:30–1:19 is a continuous, 49-second wall-clock browser-frame capture of run `run_a2dca42370fd42bda69f2eff361c3bfd`; all 202 retained frames remain in original order, only trailing post-completion frames are omitted, and the run reconciles to existing PR #14 | Public upload and logged-out playback; never label it the creator run |
| Video visibly proves Google Cloud backend | Recorded locally | 1:43–1:58.5 creator Cloud Logging receipt; 1:58.5–2:15 creator Cloud Build; 2:49–3:01 Cloud Run; 3:01–3:22 architecture | Confirm identifiers and creator-versus-duplicate distinction remain legible in public playback |
| Synthetic/mock disclosure | Recorded locally / final playback pending | Synthetic policy at 0:09–0:20 plus visual and spoken disclosure in the [cut sheet](demo-script.md) | Confirm disclosure remains legible in public playback |
| Immutable submission release | Pending | [Submission release record](submission-release.md); tag and GitHub Release pending | Freeze linked commit, video, diagram, URL, and Devpost content before deadline |

The repository is public. Verify it while logged out immediately before submission
and preserve the frozen release through judging. If visibility changes, follow the
private-repository organizer-access requirements in the live rules.

## Judging rubric

| Criterion | Weight | Design response | Evidence required before claiming it |
| --- | ---: | --- | --- |
| Innovation & Operational Utility | 40% | Convert a scattered customer promise into an executable control and a completed engineering action | Verified live for the exact synthetic deletion workflow and final [draft PR #14](https://github.com/kostakarathana/iPromise/pull/14); public video upload remains |
| Architectural Discipline & Tech Stack | 30% | Typed ADK graph; deterministic authority; checkpointed state; least privilege; idempotency; separate verifier identity and fallback | Live ten-run red/green gate and final-source same-key/distinct-run remote reconciliation are recorded in [evaluation](evaluation.md); confirm trace legibility in public playback |
| Demo & Production Readiness | 30% | Dead-simple Promise Ledger, reproducible setup, bounded failure modes, deployed Cloud Run path | Historical ten-run gate, final-source PR/duplicate proof, clean console access, and local 3:30 video passed; public playback, private Devpost field, and immutable release remain |

Weights are reproduced from the current official rules and must be rechecked before
submission.

## Optional bonus preparation

The core 40/30/30 submission remains the priority. A truthful public
[build-story draft](build-story-draft.md) and
[social-post draft](social-post-draft.md) are prepared but not published. The
build story explicitly states that it was created for entry into this hackathon,
and the social draft uses `#AllThingsAgenticHackathon`. Do not claim either bonus
until the final public URLs exist and the live Rules still recognize them.

## Evidence IDs for the final demo

| ID | Evidence | Capture method | Status |
| --- | --- | --- | --- |
| E1 | Exact promise, source URL, timestamp, and content hash | Filmed run `run_a2dca42370fd42bda69f2eff361c3bfd` and Promise Ledger | Verified live for HTTP source and recorded locally |
| E2 | Gemini structured claim tied to an exact source span | Filmed duplicate run executes the live Gemini/ADK path; the immediately following creator receipt records Vertex `global`, the exact model, and revision | Verified live; retain clear run labels in public playback |
| E3 | Synthetic user deleted from one store but retained in another | Live disclosed virtual-clock service: app record absent, analytics record retained at +25h | Verified live |
| E4 | `CONTRADICTED` verdict computed outside the model | Live scoped verdict plus residual/missing/late-worker unit tests | Verified live |
| E5 | Expected-red baseline, green hidden control, green regression, and exact candidate in the fixed seven-step Cloud Build program | [Ten historical deployed receipts](evaluation.md#historical-ten-run-reliability-gate), final creator build `e1a7a7a5-1878-41d6-9760-27c7085ae332`, and duplicate build `e7966c07-97fd-4436-b7a8-8a0a1d4e86fd` | Verified live: every cited result `FAIL / PASS / PASS`, exact tree, publishable |
| E6 | Exact tested tree published as one draft PR | Final run `run_74ea1919b21a47b9846a4d3c5efb48b8` and [draft PR #14](https://github.com/kostakarathana/iPromise/pull/14) opened by the GitHub App | Verified live; PR head passed release gate |
| E7 | Same run ID across UI, Firestore, logs, artifacts, and PR | The video first shows duplicate run/build correlation, then explicitly shows creator run `run_74ea1919b21a47b9846a4d3c5efb48b8`, build `e1a7a7a5-1878-41d6-9760-27c7085ae332`, and PR #14 as a separate provenance sequence | Live artifact correlation verified; public playback pending |
| E8 | Duplicate event reconciles to one run execution; distinct occurrences of one unchanged finding reconcile to one action | Distinct run `run_a2dca42370fd42bda69f2eff361c3bfd` and build `e7966c07-97fd-4436-b7a8-8a0a1d4e86fd` reconciled to PR #14; same-key replay returned that same run/build/PR; final PR count stayed one | Verified live |
| E9 | Unsafe, stale, tampered, failed, or unavailable repair evidence fails closed | Pre-execution template/hash rejection, verifier failure cases, PR gate tests, and missing-evidence abstention | Verified locally / live failure receipt pending |
| E10 | Optional issue/email action obeys policy and idempotency | GitHub App is installed only on `kostakarathana/iPromise` with Contents, Pull requests, and Issues read/write plus mandatory Metadata read; final live PR proof created no issue; email remains off | PR permissions verified live; issue/email delivery intentionally not claimed |

## Final compliance checks

- Reconfirm the entrant's eligibility and accepted Devpost membership. The entrant
  has stated they are solo, above the local age of majority, and have no employment
  conflict; the final Official Rules check remains mandatory.
- Verify the project was created during the permitted period and disclose all
  pre-existing work.
- Verify the final eligible Gemini model ID and locked dependencies.
- Re-run security, action-idempotency, and exact demo-path evaluations.
- Test all judge links and credentials in a clean browser.
- Confirm the recorded live run preserves original frame order and measured
  wall-clock timing; disclose any timing transformation if the master changes.
- The private Devpost draft is saved at 2/5 steps and has not been submitted; do
  not submit until the remaining checks below are complete.
- Submit a complete baseline before the internal August 28 target.
- Freeze the linked release at the deadline and preserve judge access through the
  announced judging period.
