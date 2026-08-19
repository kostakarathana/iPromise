# iPromise

**Customer promises should behave like tests.**

![iPromise turns a customer promise into evidence and one bounded engineering action](docs/assets/ipromise-cover.png)

iPromise is an autonomous promise-assurance agent for the [All Things Agentic Hackathon](https://allthingsagentichackathon.devpost.com/). It captures exact customer-facing claims, binds supported claims to approved controls, tests real product behaviour, and routes a source-grounded finding to the safest useful action: a verified draft pull request, a GitHub issue, or a configured email escalation.

The hackathon MVP focuses on one complete Taskmaster workflow: verifying an account-deletion promise across synthetic application and analytics records. It does **not** claim legal compliance and does not pretend every promise is executable.

## Status

The complete vertical slice is deployed on Google Cloud. The judge console is
hosted at `https://ipromise-console-ipj6vqlg2q-uc.a.run.app`; its authenticated
agent endpoint is `https://ipromise-agent-ipj6vqlg2q-uc.a.run.app`. The deployed
product source is commit `a4e7a59f89a60d2ba0ad087d884836d22e5d39e4`.
The judge-safe agent revision `ipromise-agent-00013-kmv` runs Google ADK with
`gemini-3.5-flash` through Vertex AI's `global` location, persists state in
Firestore, and uses Cloud Build for the fixed verifier. GitHub publication is
disabled on that current revision, and Cloud Scheduler is intentionally
**PAUSED**, so judge access cannot create unattended external actions.

The earlier reliability gate remains reproducible historical evidence: on base
commit `b5c2badacc506b78c6eed314f155ecbc2188198b`, ten consecutive actions-off
audits completed the full expected-red → green-control → green-regression
gate in 448.5 seconds total. Every run reported `FAIL / PASS / PASS`, an exact
candidate tree, a publishable receipt, and unique run, build, and
synthetic-fixture identities without writing to GitHub.

The final PR-creator proof used actions-on agent revision
`ipromise-agent-00012-2gm`. Run
`run_74ea1919b21a47b9846a4d3c5efb48b8`, synthetic fixture
`syn_ca95780e5f9067a4641fd15384f90dd1`, and Cloud Build
`e1a7a7a5-1878-41d6-9760-27c7085ae332` opened verified draft
[PR #14](https://github.com/kostakarathana/iPromise/pull/14) through the scoped
GitHub App. Its exact published head
`a460858672ab176a4142c600fb9028f1b042a373` passed the repository release gate.
A distinct trigger produced run `run_a2dca42370fd42bda69f2eff361c3bfd`
and build `e7966c07-97fd-4436-b7a8-8a0a1d4e86fd`, then reconciled to that same
PR. The final 3:30 local video records this complete distinct run as a continuous
49-second browser-frame capture with original frame order and wall-clock timing;
it does not claim that the filmed run created the PR. The cut removes only
trailing post-completion frames, without accelerating or removing in-run time. It
shows the creator Logging
and Build receipts immediately afterward. Replaying the duplicate
trigger key returned the same run, build, and PR; the final fingerprint has one
branch and one open draft PR. Earlier generated proof PRs #7 and #12 are closed.
Final checks found zero unfinished Firestore runs or leases. See the
[submission release record](docs/submission-release.md),
[truthful implementation status](docs/implementation-status.md), and
[measured evaluation record](docs/evaluation.md).

## Winning workflow

1. A scheduled or manual event starts an audit.
2. iPromise captures the configured promise source, exact quote, URL, timestamp,
   and content hash. The current adapter uses the owned synthetic HTML fixture;
   rendered browser capture is a later hardening step.
3. In cloud mode, Gemini 3.5 Flash is orchestrated with Google ADK to compile the
   language into a typed claim. Local demonstration mode uses an explicit
   deterministic adapter and reports that no model invocation was attempted.
4. Deterministic code verifies the quote and binds it to an approved account-deletion control.
5. The control exercises a synthetic SaaS deployment and inspects both application and analytics records.
6. Evidence code returns a scoped verdict: `SUPPORTED`, `CONTRADICTED`, `INCONCLUSIVE`, or `NOT_TESTED`.
7. For the one locked deletion repair, deterministic code prepares exact source
   bytes and submits a fixed Cloud Build program. Publication requires the expected
   red baseline, green hidden control, green regression suite, exact source/base,
   and exact candidate hashes. Any missing or mismatched receipt fails closed.
8. iPromise performs exactly one configured action with the full audit trail. A
   verified draft PR is primary; an evidence-backed issue is the fallback when the
   exact repair cannot be generated or verified. Email remains off.

## Repository map

```text
apps/
  console/        Judge-facing Next.js promise ledger
  demo_saas/      Synthetic reference SaaS with a deliberate deletion defect
services/
  agent/          FastAPI + Google ADK audit workflow
docs/             Architecture, ADRs, threat model, evaluation, demo, evidence matrix
```

## Deployed stack

![iPromise deployed architecture](docs/assets/architecture.png)

- Gemini 3.5 Flash through Vertex AI
- Google Agent Development Kit (ADK)
- Cloud Run, Cloud Scheduler, Firestore, Secret Manager, Cloud Build, and Cloud Logging
- Next.js console and a synthetic FastAPI reference product
- Least-privilege GitHub App for draft pull requests and issues

Local demonstration adapters are allowed for development but are labeled and cannot be presented as hackathon cloud proof. The final submitted run must visibly use the required Google stack.

## Run the local MVP

Prerequisites (the same versions used by the release workflow):

- macOS or Linux with a POSIX shell; Windows users should run the commands in WSL
- Node.js 24 with Corepack and pnpm 11.19.0
- Python 3.12 and [uv 0.12.1](https://docs.astral.sh/uv/)

Enable the repository-pinned package manager before installing:

```bash
corepack enable
corepack prepare pnpm@11.19.0 --activate
```

Install locked dependencies once:

```bash
pnpm install --frozen-lockfile
uv sync --project apps/demo_saas --extra dev --locked
uv sync --project services/agent --extra dev --extra google --extra github --locked
```

Start all three services:

```bash
pnpm dev
```

Open <http://127.0.0.1:3000> and choose **Run audit**. The launcher uses ports
3000 (console), 8080 (agent), and 8081 (synthetic product). It supplies a local-only
token consistently to the two Python services and stops all child processes on exit.

The root `.env.example` is a reference inventory; it is not implicitly loaded by
the services. For individual-service operation, copy the relevant service-level
`.env.example` and follow its README.

## Reproducible demo and tests

Run the complete local release gate:

```bash
pnpm verify
```

This validates 16 synthetic claim fixtures, synchronizes both locked Python
environments, runs the SaaS and agent tests, then runs console lint, type checks,
tests, a production build, and a fresh isolated standalone-package boot matching
the Cloud Run source context. Service-specific instructions are in
[`apps/console`](apps/console/README.md),
[`apps/demo_saas`](apps/demo_saas/README.md), and
[`services/agent`](services/agent/README.md).

The deployment workflow can use the project wrapper [`scripts/gcloud`](scripts/gcloud).
A fresh clone can follow Google's
[versioned archive instructions](https://cloud.google.com/sdk/docs/downloads-versioned-archives)
or use a normal system installation. Cloud credentials and resources are not
required for the truthful local MVP.

Never commit credentials. The deployed services use Secret Manager and scoped
runtime identities rather than local environment files.

## Connect a GitHub repository

iPromise accepts repositories only through a GitHub App installation. It never
accepts a pasted personal access token or trusts an arbitrary `owner/repo` string.
“Any repository” means any GitHub.com repository the installation owner explicitly
authorizes for the App; the current executable audit remains limited to the
documented account-deletion control.

For the full verified-PR workflow, create a GitHub App with **Contents: read/write**,
**Pull requests: read/write**, **Issues: read/write**, and implicit Metadata read.
Install it only on repositories the entrant is authorized to test, then configure:

```text
Setup URL:    http://127.0.0.1:3000/api/integrations/github/setup
Callback URL: http://127.0.0.1:3000/api/integrations/github/callback
```

Then set the `IPROMISE_GITHUB_*` values from
[`services/agent/.env.example`](services/agent/.env.example). Keep
`IPROMISE_GITHUB_ACTIONS_ENABLED=false` while testing connection and repository
selection; enable it only after reviewing the repository and every granted
permission. OAuth user tokens and one-hour installation tokens are never persisted.

Repository connection is general, but the executable repair is deliberately not:
the current verifier is locked to the public `kostakarathana/iPromise` repository,
the exact vulnerable two-file snapshot, and a fixed test program. Other authorized
repositories can be selected, but this repair cannot produce a draft PR for them;
policy falls back safely rather than generalizing an unverified patch.

For the Cloud Run, Firestore, Scheduler, Vertex AI, Secret Manager, and GitHub App
deployment path, follow [`docs/deployment.md`](docs/deployment.md). The deployment
script defaults external actions off and refuses secret payloads in its shell
environment.

## Hackathon guardrails

- Selected track: **Taskmaster**
- Internal complete-baseline target: **August 28, 2026**
- Hard deadline: **September 1, 2026 at 10:00 AEST (Brisbane)**
- Synthetic/de-identified data only for the reference workflow
- No blanket compliance verdicts
- No generated shell commands, automatic merges, or deployments
- A finding never becomes success when evidence is unavailable
- One visible run ID across the console, state ledger, logs, verification receipt, and external action
- The final 3:30 English video master exists locally with burned captions. The
  private Devpost draft is saved at 2/5 steps and is not submitted; public video
  upload, remaining draft fields, immutable release creation, and submission
  remain open.

See [AGENTS.md](AGENTS.md) for the binding project operating rules,
[architecture](docs/architecture.md), and the
[hackathon evidence matrix](docs/evidence-matrix.md) for implementation and
submission evidence. The [Devpost submission draft](docs/devpost-submission-draft.md)
keeps required listing copy and remaining receipts explicit. Project dates, AI assistance, libraries, assets, and
synthetic-data ownership are recorded in [provenance](docs/provenance.md). The
[third-party notices](THIRD_PARTY_NOTICES.md) explain dependency licensing and
the current all-rights-reserved status of original project code.
