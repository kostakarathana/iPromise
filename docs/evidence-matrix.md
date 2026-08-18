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
| Gemini 3.5 or newer | Pending | Target in [stack ADR](adr/0002-architecture-and-google-stack.md); target agent dependency/configuration | Vertex request/log proof with exact eligible model ID |
| Google agent framework | Verified locally / live pending | Google ADK graph and typed compiler tests in the agent service | ADK graph executing the live workflow with correlated receipt |
| Google Cloud infrastructure | Pending deployment proof | [Architecture](architecture.md), digest-pinned Cloud Run images, guarded clean-commit deployment script, Firestore stores, and Scheduler endpoint | Cloud Console, service URLs, Firestore document, scheduled delivery, logs, and state transition proof |
| Deployed on Google Cloud | Pending | Target deployment instructions/manifests | Clearly visible Cloud Run/Cloud Logging proof in video |
| Meaningful autonomous workflow | Verified locally / cloud pending | Authenticated scheduled endpoint executes the same idempotent audit and the controlled integration path routes a verified repair to one draft PR or issue fallback | Scheduled cloud trigger-to-evidence-to-real-action continuous run |
| English support and materials | Documented | Repository documentation is English | English UI, listing, narration, and subtitles if needed |
| New-project and third-party provenance disclosure | Documented | [Provenance and third-party materials](provenance.md); initial commit is dated inside the Submission Period | Reconcile final dependencies, assets, integrations, and licenses |
| No secrets in repository | Partially verified locally | [Threat model](threat-model.md), placeholder `.env.example`, Secret Manager-only deploy guards, transient GitHub tokens | Final secret scan plus Secret Manager/IAM evidence |

## Required submission artifacts

| Artifact | Status | Evidence/location | Final gate |
| --- | --- | --- | --- |
| Selected category | Documented | Taskmaster in [ADR 0001](adr/0001-product-and-track.md) | Devpost field matches exactly |
| Project description: features, technologies, sources, learnings | Documented / final proof pending | [Devpost submission draft](devpost-submission-draft.md) | Remove placeholders and cross-check every claim against this matrix |
| Repository URL | Documented / source publication pending | `https://github.com/kostakarathana/iPromise` | Commit and push the intentionally reviewed frozen source; if private, grant required judge accounts |
| Reproducible README | Verified locally | Root `README.md`, `scripts/dev-local`, `scripts/verify`, and the isolated standalone console-package smoke | Fresh-machine cloud setup remains pending |
| Architecture diagram | Documented | [Architecture](architecture.md) | Diagram matches the deployed system and is visible in submission |
| Hosted project URL, if supplied | Pending | Target judge console on Cloud Run | Stable, free, accessible credentials through judging |
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
| E1 | Exact promise, source URL, timestamp, and content hash | Local HTTP capture and Promise Ledger; screenshot capture remains planned | Verified locally / partial |
| E2 | Gemini structured claim tied to an exact source span | Run event/schema view and Vertex log | Pending |
| E3 | Synthetic user deleted from one store but retained in another | Disclosed virtual-clock reference service and deterministic probe output | Verified locally |
| E4 | `CONTRADICTED` verdict computed outside the model | Agent tests cover residual record, missing evidence, and late worker | Verified locally |
| E5 | Expected-red baseline, green hidden control, green regression, and exact candidate in the fixed seven-step Cloud Build program | Verifier request/receipt and durable Cloud Build log | Verified locally with controlled gateway / live receipt pending |
| E6 | Exact tested tree published as one draft PR | GitHub PR, deterministic commit/tree SHA, hidden action marker | Verified locally with controlled gateway / live receipt pending |
| E7 | Same run ID across UI, Firestore, logs, artifacts, and PR | Side-by-side browser/cloud proof | Pending |
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
