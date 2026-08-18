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
| Address a real challenge beyond chat | Verified live for the scoped MVP | Run `run_806d1fc144344baebb757747d1b56e83` autonomously turned a captured promise and synthetic product contradiction into verified draft [PR #7](https://github.com/kostakarathana/iPromise/pull/7) | Show the continuous workflow in the final video |
| Gemini 3.5 or newer | Verified live | Correlated receipt `run_806d1fc144344baebb757747d1b56e83` records `gemini-3.5-flash`, `modelInvoked=true`, and revision `ipromise-agent-00007-8p9`; Vertex location is `global` | Capture the same proof visibly in the final video |
| Google agent framework | Verified live | The receipt records the Google Agent Development Kit graph workflow; the typed claim was grounded before deterministic control execution | Show the ADK/Vertex trajectory and same run ID in the final video |
| Google Cloud infrastructure | Verified live | Cloud Run hosts all three services; Firestore stores state; OIDC Cloud Scheduler exists and is paused after proof; Cloud Build produced repeated verifier receipts; Secret Manager and Cloud Logging support the deployed path | Capture Cloud Console, Build, Scheduler, Firestore, and correlated logging proof in the video |
| Deployed on Google Cloud | Verified live | Console `https://ipromise-console-ipj6vqlg2q-uc.a.run.app`; authenticated agent endpoint `https://ipromise-agent-ipj6vqlg2q-uc.a.run.app`; current agent revision `ipromise-agent-00007-8p9`; verified base `b5c2badacc506b78c6eed314f155ecbc2188198b` | Perform final clean-browser judge rehearsal and show URL plus Cloud Run dashboard/logs in video |
| Meaningful autonomous workflow | Verified live through real external action | The actions-on run captured and compiled the exact claim, exercised synthetic behavior, persisted scoped `CONTRADICTED` evidence, passed Cloud Build's exact-tree gate, and opened one verified draft PR | Record the same end-to-end story continuously for the final video |
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
| Hosted project URL, if supplied | Deployed / authenticated flow rehearsed | `https://ipromise-console-ipj6vqlg2q-uc.a.run.app`; hosted OAuth, repository selection, audit, verification, and PR-link flow completed | Rehearse from a clean judge browser and preserve stable access through judging |
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
| Innovation & Operational Utility | 40% | Convert a scattered customer promise into an executable control and a completed engineering action | Verified live for the exact synthetic deletion workflow and [draft PR #7](https://github.com/kostakarathana/iPromise/pull/7); show it in the video |
| Architectural Discipline & Tech Stack | 30% | Typed ADK graph; deterministic authority; checkpointed state; least privilege; idempotency; separate verifier identity and fallback | Live ten-run red/green gate and same-key/distinct-run remote reconciliation recorded in [evaluation](evaluation.md); capture IAM and trace visually |
| Demo & Production Readiness | 30% | Dead-simple Promise Ledger, reproducible setup, bounded failure modes, deployed Cloud Run path | Ten repeatable runs passed; clean setup rehearsal, architecture match, cloud console/log capture, and stable judge access remain |

Weights are reproduced from the current official rules and must be rechecked before
submission.

## Evidence IDs for the final demo

| ID | Evidence | Capture method | Status |
| --- | --- | --- | --- |
| E1 | Exact promise, source URL, timestamp, and content hash | Live run and Promise Ledger; screenshot capture remains planned | Verified live for HTTP source / partial |
| E2 | Gemini structured claim tied to an exact source span | Run `run_806d1fc144344baebb757747d1b56e83`, ADK receipt, Vertex `global`, and exact model provenance | Verified live |
| E3 | Synthetic user deleted from one store but retained in another | Live disclosed virtual-clock service: app record absent, analytics record retained at +25h | Verified live |
| E4 | `CONTRADICTED` verdict computed outside the model | Live scoped verdict plus residual/missing/late-worker unit tests | Verified live |
| E5 | Expected-red baseline, green hidden control, green regression, and exact candidate in the fixed seven-step Cloud Build program | [Ten consecutive deployed receipts](evaluation.md#measured-deployed-release-result) against frozen base, plus actions-on build `f4cbf983-db73-4bf5-9504-93c253a4b98b` | Verified live: every run `FAIL / PASS / PASS`, exact tree, publishable |
| E6 | Exact tested tree published as one draft PR | Run `run_806d1fc144344baebb757747d1b56e83` and [draft PR #7](https://github.com/kostakarathana/iPromise/pull/7) opened by the GitHub App | Verified live |
| E7 | Same run ID across UI, Firestore, logs, artifacts, and PR | `run_806d1fc144344baebb757747d1b56e83` is correlated to Cloud Build `f4cbf983-db73-4bf5-9504-93c253a4b98b` and PR #7 in the persisted receipt | Live action correlation verified; capture console and Cloud Logging correlation in the final video |
| E8 | Duplicate event reconciles to one run execution; distinct occurrences of one unchanged finding reconcile to one action | Same-key run `run_60edca0afdd34918805f72464662b340` and distinct run `run_6babae8849fc46fca2d522caf3e2ce98` both reconciled to PR #7; final state was one branch, one draft PR, zero issues, and no leases/nonterminal runs | Verified live |
| E9 | Unsafe, stale, tampered, failed, or unavailable repair evidence fails closed | Pre-execution template/hash rejection, verifier failure cases, PR gate tests, and missing-evidence abstention | Verified locally / live failure receipt pending |
| E10 | Optional issue/email action obeys policy and idempotency | GitHub App is installed only on `kostakarathana/iPromise` with Contents, Pull requests, and Issues read/write plus mandatory Metadata read; the live PR path created zero issues; email remains off | PR permissions verified live; issue/email delivery intentionally not claimed |

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
- Devpost has not been submitted; do not submit until the remaining checks below
  are complete.
- Submit a complete baseline before the internal August 28 target.
- Freeze the linked release at the deadline and preserve judge access through the
  announced judging period.
