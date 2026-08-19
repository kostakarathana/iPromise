# Devpost submission draft

Status: **working copy — private Devpost draft saved at 2/5 steps; not
submitted.** The persisted draft contains the iPromise title, elevator pitch,
and architecture image. Project Details and the remaining Additional Info fields
are incomplete. The deployed Cloud Run, ADK,
Gemini, Firestore, Cloud Scheduler, Cloud Build, and GitHub draft-PR path has
final-source live proof, including the historical ten-run reliability gate, final
PR #14, and duplicate suppression. A 3:30 English video master with burned
captions exists locally. Do not submit until the remaining public-video,
private-field, rules, and release-freeze gates below are complete.
Last reviewed 2026-08-19 AEST.

The existing draft was created on 2026-08-17 during the submission period. Its
public preview retains Devpost's earlier `/software/handrail` slug from a brief
draft-name change before iPromise was locked. Keep this draft; do not create a
duplicate or modify any unrelated Devpost project.

## Listing fields

- **Project:** iPromise
- **Category:** Taskmaster
- **Tagline:** Customer promises should behave like tests.
- **Repository:** https://github.com/kostakarathana/iPromise
- **Hosted application:** https://ipromise-console-ipj6vqlg2q-uc.a.run.app
- **Public video:** `[pending public YouTube or Vimeo upload; local master is 3:30]`
- **Private testing instructions:** use the exact private-field copy below, and
  insert the console access code only in Devpost at save time
- **Google SDK used:** Google Agent Development Kit (ADK) 2.7.0 and Google Gen AI SDK 2.18.1
- **Reproducible README:** Yes — clean-checkout prerequisites, locked installs,
  local verification, cloud deployment, and rollback are documented
- **Project start date:** 08-17-26 (within the submission period; confirmed by
  the repository creation time and entrant-local initial-commit timestamp)
- **Architecture image:** [`docs/assets/architecture.png`](assets/architecture.png)
- **Video captions/language:** English narration with burned English captions;
  `[confirm public playback after final upload]`

## Elevator pitch

iPromise turns a supported customer promise into a recurring test and a verified
draft PR when product behavior drifts.

## Inspiration

Customer-facing promises live in policies and product copy while the behavior
that must uphold them is spread across application code, analytics tools, and
background jobs. A developer can add one new data sink and silently leave the
published promise behind. Teams usually discover that mismatch through a manual
audit or a customer incident. iPromise makes one narrow class of promise
continuously testable without pretending to make a legal conclusion.

## What it does

The hackathon workflow focuses on one exact account-deletion commitment. A manual
trigger, or the six-hour scheduled trigger when deliberately resumed, starts the
same autonomous workflow. iPromise:

1. captures the exact source text, URL, time, and content hash;
2. uses Gemini 3.5 Flash through Google ADK to compile that text into a strict,
   typed claim;
3. deterministically grounds the quote and binds only an approved control;
4. exercises an owned synthetic SaaS and probes its application and analytics
   records after the stated deadline;
5. computes a scoped verdict outside the model;
6. checkpoints the run and idempotency state in Firestore; and
7. selects exactly one bounded response. For the locked iPromise repair, a fixed
   Cloud Build program must prove the expected failing baseline, green hidden
   control, green regression suite, source provenance, and exact candidate tree
   before the agent uploads those same bytes to one reconciled draft PR. Any failed
   or unavailable gate routes to an evidence-backed issue instead.

The reference workflow deliberately leaves one analytics record active so the
agent has a real contradiction to detect. All identities and records are
synthetic. iPromise reports only the systems and time it actually observed; it
does not claim that a company is legally compliant or in violation.

## How it is built

- **Gemini 3.5 Flash on Vertex AI** performs constrained semantic claim
  compilation.
- **Google Agent Development Kit 2.7** supplies the workflow/agent boundary.
- **Cloud Run** hosts the console, audit service, and synthetic reference SaaS.
- **Cloud Scheduler** starts the background workflow with Google OIDC.
- **Firestore** stores runs, checkpoints, trigger idempotency, execution/action
  leases, OAuth state, selected repositories, and finding receipts.
- **Secret Manager** provides pinned, service-scoped runtime secrets.
- **Cloud Logging** records a structured receipt correlated by run ID.
- **Cloud Build** runs the fixed red-before/green-after verifier as a dedicated
  minimal identity and returns the durable build/log receipt. It has outbound
  source/dependency access; the exact candidate supplies no commands or URLs.
- A **least-privilege GitHub App** verifies installation ownership, lists only
  authorized repositories, mints a short-lived repository-scoped token, and
  reconciles an exact-repair branch/marker before opening a draft PR, or a stable
  finding marker before creating an issue fallback.
- A **Next.js** Promise Ledger presents the exact claim, evidence, selected
  action, and technical activity without a chat interface.

Model output never decides the evidence verdict or grants itself a tool.
Deterministic code owns grounding, probes, state transitions, action policy,
repository identity, and side effects. Duplicate deliveries and ambiguous
GitHub responses reconcile before another write is attempted.

## Data sources and permissions

- The privacy page, application records, analytics records, deletion endpoint,
  and virtual timeline are original synthetic fixtures in this repository.
- GitHub account and repository metadata comes only from repositories explicitly
  authorized to the entrant-owned GitHub App.
- No real customer data is required or used in the primary workflow.
- Dependencies, AI assistance, project dates, and third-party materials are
  itemized in the [provenance record](https://github.com/kostakarathana/iPromise/blob/v1.0.0-hackathon-submission/docs/provenance.md).

## Challenges and learnings

The hardest part was separating language understanding from authority. Gemini is
useful for translating changing prose into a strict candidate claim, but a model
statement is not evidence. The trustworthy design keeps exact source spans,
approved controls, observations, verdicts, and publication gates deterministic.

External idempotency was another important lesson. A local retry lock is not
enough once Cloud Run can restart or GitHub can accept a request whose response
is lost. iPromise uses Firestore leases plus stable issue and exact-repair
fingerprints, deterministic branches, and remote reconciliation so a retry can
discover the action that already exists.

Finally, a smaller truthful claim is stronger than a universal compliance pitch.
The MVP connects to repositories authorized through the App, but it executes one
well-defined deletion control and visibly abstains when evidence or support is
missing.

## Reproduce and test

From a clean checkout, follow the root README and run:

```bash
pnpm install --frozen-lockfile
uv sync --project apps/demo_saas --extra dev --locked
uv sync --project services/agent --extra dev --extra google --extra github --locked
pnpm verify
```

Cloud setup, exact health endpoints, GitHub App configuration, private judge
access, correlated logging proof, and rollback are documented in
[deployment guide](https://github.com/kostakarathana/iPromise/blob/v1.0.0-hackathon-submission/docs/deployment.md).

## Private testing instructions

Paste this section only into Devpost's private testing field. Replace the first
line at save time; never add the credential to this repository, the public
description, or the video.

```text
Console access code: <insert the Secret Manager value here>

1. Open https://ipromise-console-ipj6vqlg2q-uc.a.run.app and enter the access
   code when prompted.
2. The preloaded completed run is the final proof state. It links to verified
   draft PR #14 and shows the exact promise, scoped evidence, Cloud Build
   FAIL/PASS/PASS receipt, and action trail.
3. You may click Run audit to execute the full Gemini 3.5 Flash, Google ADK,
   synthetic-control, and Cloud Build workflow. It normally finishes in about a
   minute; if Cloud Build queues, leave the page open rather than clicking
   again. The current judge-safe deployment has external GitHub actions
   disabled, so a rerun will not create another PR or issue.
4. The GitHub App is already connected only to kostakarathana/iPromise. Please
   do not disconnect or change the repository selection.
5. The service uses only disclosed synthetic data. Results are scoped technical
   verdicts, not legal conclusions.
```

## Final submission gate

Delete this section from the public listing only after all items are verified:

- [ ] Every release placeholder is resolved. Release-pinned links target the
      planned immutable tag `v1.0.0-hackathon-submission`; this remains unchecked
      until that tag exists and its links pass logged-out verification.
- [x] The linked repository contains deployed source
      `a4e7a59f89a60d2ba0ad087d884836d22e5d39e4` and a reproducible README.
- [x] A live run records `modelInvoked: true`, Google ADK, the eligible Gemini
      model ID, and the Cloud Run revision.
- [x] The hosted console passed a clean judge-equivalent access check:
      unauthenticated `/api/audit` returned 401, `/api/health` returned 200, and
      a fresh authenticated session returned product content without printing or
      exposing the Secret Manager code. Inserting that code into Devpost's
      private field remains pending.
- [x] Final creator run `run_74ea1919b21a47b9846a4d3c5efb48b8` opened one
      real, independently verified draft [PR #14](https://github.com/kostakarathana/iPromise/pull/14).
      Distinct-run and same-key replay created no duplicate. Earlier proof PRs #7
      and #12 are closed. A forced live verifier-failure issue fallback remains
      optional evidence and has not been claimed.
- [x] The final live action is correlated across the persisted run, Cloud Build
      `e1a7a7a5-1878-41d6-9760-27c7085ae332`, exact GitHub head, green repository
      check, and creator receipts shown in the local recording. The continuous
      filmed segment is explicitly the distinct duplicate run
      `run_a2dca42370fd42bda69f2eff361c3bfd`, which reconciles to PR #14; it is not
      represented as the creator. Public playback remains a separate gate.
- [x] The architecture diagram matches the deployed system and has a static PNG
      in the format accepted by Devpost.
- [ ] The lawful 3:30 local video master is in English with burned captions and
      records the working application. Google Cloud Text-to-Speech licensing,
      decode, timing, caption, audio, privacy, and checksum QA passed. Complete
      public upload, processing, and logged-out playback before checking this
      item.
- [ ] Entrant eligibility is fully self-attested. Solo status, Australian
      residence, age of majority, and no employment conflict are confirmed; the
      entrant must still confirm the remaining sanctions/export, Contest Entity
      family/household, government-role, internet-access, and preferential-support
      conditions in the Official Rules. The repository is public; provenance and
      third-party notices are recorded.
- [ ] The submission-linked commit and artifacts are frozen for judging.
