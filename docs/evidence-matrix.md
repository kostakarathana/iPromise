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
| Address a real challenge beyond chat | Documented | [Product contract](adr/0001-product-and-track.md) | Continuous deployed run ending in a real external action |
| Gemini 3.5 or newer | Verified live | Correlated receipt `run_14a197bafd1d4a44a248e67320092d16` records `gemini-3.5-flash`, `modelInvoked=true`, and revision `ipromise-agent-00005-hk6` | Capture the same proof visibly in the final video |
| Google agent framework | Verified live | The receipt records `Google Agent Development Kit 2 Graph Workflow`; local graph/timeout tests remain green | Show the ADK/Vertex trajectory and same run ID in the final video |
| Google Cloud infrastructure | Verified live baseline | Healthy Cloud Run services; Firestore Native document; enabled OIDC Scheduler; pinned Secret Manager versions; structured Cloud Logging receipt | Add Cloud Build verifier and GitHub-action receipts, then capture Cloud Console proof |
| Deployed on Google Cloud | Verified live baseline | Console `https://ipromise-console-ipj6vqlg2q-uc.a.run.app`; services carry source commit `2827325fb1a3437b5d9fe696269e1122e58aa55d` | Rehearse private access and show the URL plus Cloud Run dashboard/logs in video |
| Meaningful autonomous workflow | Cloud workflow verified through action routing | The live run captured and compiled a claim, exercised synthetic product behavior, persisted evidence, computed `CONTRADICTED`, and selected an issue while actions were deliberately off | Enable the verified Cloud Build → draft-PR path and capture one real external action |
| English support and materials | Documented | Repository documentation is English | English UI, listing, narration, and subtitles if needed |
| New-project and third-party provenance disclosure | Documented | [Provenance and third-party materials](provenance.md); initial commit is dated inside the Submission Period | Reconcile final dependencies, assets, integrations, and licenses |
| No secrets in repository | Partially verified locally | [Threat model](threat-model.md), placeholder `.env.example`, Secret Manager-only deploy guards, transient GitHub tokens | Final secret scan plus Secret Manager/IAM evidence |

## Required submission artifacts

| Artifact | Status | Evidence/location | Final gate |
| --- | --- | --- | --- |
| Selected category | Documented | Taskmaster in [ADR 0001](adr/0001-product-and-track.md) | Devpost field matches exactly |
| Project description: features, technologies, sources, learnings | Documented / final proof pending | [Devpost submission draft](devpost-submission-draft.md) | Remove placeholders and cross-check every claim against this matrix |
| Repository URL | Verified public | `https://github.com/kostakarathana/iPromise`; release changes merged through passing GitHub checks | Create the immutable final submission tag/release |
| Reproducible README | Verified locally | Root `README.md`, `scripts/dev-local`, `scripts/verify`, and the isolated standalone console-package smoke | Fresh-machine cloud setup remains pending |
| Architecture diagram | Documented | [Architecture](architecture.md) | Diagram matches the deployed system and is visible in submission |
| Hosted project URL, if supplied | Deployed / access rehearsal pending | `https://ipromise-console-ipj6vqlg2q-uc.a.run.app` | Rehearse the private access code and preserve stable access through judging |
| Public YouTube/Vimeo video, maximum 4:00 | Pending | [Planned script](demo-script.md) | Public playback; first four minutes contain all required proof |
| Video explains problem and value | Documented | 0:00–0:25 in [script](demo-script.md) | Confirm in final cut |
| Video shows application in action | Pending | 0:25–3:15 in [script](demo-script.md) | One truthful continuous live run |
| Video visibly proves Google Cloud backend | Pending | 3:15–3:38 in [script](demo-script.md) | Cloud Run URL/dashboard plus correlated run ID/logs |
| Synthetic/mock disclosure | Verified locally | Persistent console environment label (`Local · Synthetic data`), [architecture](architecture.md), [script](demo-script.md) | Preserve on-screen/spoken disclosure in final cloud demo |
| Immutable submission release | Pending | Target git tag/release and artifact manifest | Freeze linked commit, video, diagram, URL, and Devpost content before deadline |

If the repository remains private, the rules require access for the organizer test
accounts named in the rules. Verify the live addresses immediately before the
submission rather than relying only on this document.

## Judging rubric

| Criterion | Weight | Design response | Evidence required before claiming it |
| --- | ---: | --- | --- |
| Innovation & Operational Utility | 40% | Convert a scattered customer promise into an executable control and a completed engineering action | Exact captured claim, real synthetic staging behavior, meaningful contradiction, verified draft PR |
| Architectural Discipline & Tech Stack | 30% | Typed ADK graph; deterministic authority; checkpointed state; least privilege; idempotency; separate verifier identity and fallback | Source links, tests, IAM policy, duplicate-event proof, red/green receipt, trace with one run ID |
| Demo & Production Readiness | 30% | Dead-simple Promise Ledger, reproducible setup, bounded failure modes, deployed Cloud Run path | Ten repeatable runs as a target gate, clean setup rehearsal, architecture diagram, cloud console/log proof, stable judge URL |

Weights are reproduced from the current official rules and must be rechecked before
submission.

## Evidence IDs for the final demo

| ID | Evidence | Capture method | Status |
| --- | --- | --- | --- |
| E1 | Exact promise, source URL, timestamp, and content hash | Live run and Promise Ledger; screenshot capture remains planned | Verified live for HTTP source / partial |
| E2 | Gemini structured claim tied to an exact source span | Run `run_14a197bafd1d4a44a248e67320092d16`, ADK receipt, and Vertex model provenance | Verified live |
| E3 | Synthetic user deleted from one store but retained in another | Live disclosed virtual-clock service: app record absent, analytics record retained at +25h | Verified live |
| E4 | `CONTRADICTED` verdict computed outside the model | Live scoped verdict plus residual/missing/late-worker unit tests | Verified live |
| E5 | Expected-red baseline, green hidden control, green regression, and exact candidate in the fixed seven-step Cloud Build program | Verifier request/receipt and durable Cloud Build log | Verified locally with controlled gateway / live receipt pending |
| E6 | Exact tested tree published as one draft PR | GitHub PR, deterministic commit/tree SHA, hidden action marker | Verified locally with controlled gateway / live receipt pending |
| E7 | Same run ID across UI, Firestore, logs, artifacts, and PR | `run_14a197bafd1d4a44a248e67320092d16` is verified in API output, Firestore, and structured Cloud Logging | Partial: UI, verifier artifact, and PR correlation pending |
| E8 | Duplicate event reconciles to one run execution; distinct occurrences of one unchanged finding reconcile to one action | Cross-instance execution-lease test, stable synthetic fixture identity test, trigger replay tests, and two-distinct-run/one-GitHub-POST tests pass; `scripts/smoke-cloud` requires remote proof | Verified locally / remote receipt pending |
| E9 | Unsafe, stale, tampered, failed, or unavailable repair evidence fails closed | Pre-execution template/hash rejection, verifier failure cases, PR gate tests, and missing-evidence abstention | Verified locally / live failure receipt pending |
| E10 | Optional issue/email action obeys policy and idempotency | GitHub App OAuth, repository authorization, repo-scoped issue token, and one-POST integration tests; email remains off | Verified locally / live receipt pending |

## Final compliance checks

- Reconfirm the entrant's eligibility and accepted Devpost membership. The entrant
  has stated they are solo, above the local age of majority, and have no employment
  conflict; the final Official Rules check remains mandatory.
- Verify the project was created during the permitted period and disclose all
  pre-existing work.
- Verify the final eligible Gemini model ID and locked dependencies.
- Re-run security, action-idempotency, and exact demo-path evaluations.
- Test all judge links and credentials in a clean browser.
- Record a truthful, normal-speed run where possible; disclose any uniform speed-up.
- Submit a complete baseline before the internal August 28 target.
- Freeze the linked release at the deadline and preserve judge access through the
  announced judging period.
