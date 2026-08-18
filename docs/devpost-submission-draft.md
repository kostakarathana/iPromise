# Devpost submission draft

Status: **working copy — do not submit until every final gate below has a real
receipt.** The Cloud Run + ADK + Gemini + Firestore + Scheduler baseline is live;
the verifier-to-PR path still has only local controlled-gateway proof. Last
reviewed 2026-08-18 AEST.

## Listing fields

- **Project:** iPromise
- **Category:** Taskmaster
- **Tagline:** Customer promises should behave like tests.
- **Repository:** https://github.com/kostakarathana/iPromise
- **Hosted application:** https://ipromise-console-ipj6vqlg2q-uc.a.run.app
- **Public video:** `[add public YouTube or Vimeo URL; maximum 4:00]`
- **Private testing instructions:** `[add console access code only in Devpost's
  private field; never place it in public copy or the video]`

## Elevator pitch

iPromise is CI for customer promises. It turns a supported privacy commitment
into a scheduled executable control, tests what the product actually does, and
routes an evidence-backed engineering action when reality drifts from the words
customers were given.

## Inspiration

Customer-facing promises live in policies and product copy while the behavior
that must uphold them is spread across application code, analytics tools, and
background jobs. A developer can add one new data sink and silently leave the
published promise behind. Teams usually discover that mismatch through a manual
audit or a customer incident. iPromise makes one narrow class of promise
continuously testable without pretending to make a legal conclusion.

## What it does

The hackathon workflow focuses on one exact account-deletion commitment. A manual
or six-hour scheduled trigger starts the same autonomous workflow. iPromise:

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
  itemized in the [provenance record](https://github.com/kostakarathana/iPromise/blob/REPLACE_WITH_FROZEN_SHA/docs/provenance.md).

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
[deployment guide](https://github.com/kostakarathana/iPromise/blob/REPLACE_WITH_FROZEN_SHA/docs/deployment.md).

## Final submission gate

Delete this section from the public listing only after all items are verified:

- [ ] Every `REPLACE_WITH_*` placeholder and commit-pinned link is resolved.
- [ ] The linked repository contains the tested source and a reproducible README.
- [ ] A live run records `modelInvoked: true`, Google ADK, the eligible Gemini
      model ID, and the Cloud Run revision.
- [ ] The hosted console works from a clean browser using the private judge code.
- [ ] The fixed authorized iPromise repository receives exactly one real,
      independently verified and reconciled draft PR; a forced verifier failure
      proves the issue fallback without creating a PR.
- [ ] The same run ID is visible in the console, Firestore, Cloud Build,
      Cloud Logging, and GitHub artifact.
- [ ] The architecture diagram matches the deployed system.
- [ ] The public video is in English, no longer than four minutes, shows the
      working application, and visibly proves the Google Cloud backend.
- [ ] Entrant eligibility, team acceptance, provenance, licenses, and any private
      repository judge access are confirmed.
- [ ] The submission-linked commit and artifacts are frozen for judging.
