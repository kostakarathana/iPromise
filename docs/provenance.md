# Project provenance and third-party materials

Last reviewed: **2026-08-18 AEST**

This document supports the All Things Agentic Hackathon's new-project,
originality, licensing, data-authorization, and pre-existing-work disclosures. It
must be reconciled with the final release before submission.

## Project creation

- Repository: `https://github.com/kostakarathana/iPromise`
- Initial commit: `a5b1b50f9b49794ed11e97e35bba170647ea109b`
- Initial commit time: `2026-08-17T14:34:50+10:00`
- Initial committed content: a one-line `README.md` titled `YouPromise`
- The initial commit and all current implementation work are within the binding
  2026-08-03 through 2026-08-31 Submission Period.

The product was renamed to **iPromise** during development. No earlier product
code, dataset, model output, design system, or submission artifact was imported.
Reverify repository history and every final asset before submission.

## Permitted development tools and frameworks

The project uses ordinary open-source frameworks, libraries, starter tooling, and
AI coding assistance, which the rules permit. Current direct dependencies and
exact resolved transitive versions are recorded in `pnpm-lock.yaml` and the two
Python `uv.lock` files.

Principal third-party components:

- Next.js, React, TypeScript, Tailwind CSS, shadcn-style owned primitives,
  Lucide icons, Zod, Vitest, Testing Library, and ESLint.
- FastAPI, Uvicorn, Pydantic, HTTPX, pytest, and JSON Schema tooling.
- Google Agent Development Kit and Google Gen AI SDK.
- Google Cloud CLI for deployment work.
- OpenAI Codex was used as an AI coding and research assistant. All generated
  work remains subject to human review, repository tests, and this disclosure.

Do not describe third-party libraries as original iPromise technology. Preserve
their licenses and attribution requirements when the repository becomes public.

## Data and content

- The reference privacy page, promise wording, account identifiers, event data,
  and datastore records are original synthetic fixtures owned by this project.
- Synthetic email addresses use the reserved `.invalid` top-level domain.
- The virtual timeline is explicitly simulated; it does not represent 25 hours of
  real elapsed time.
- No real customer records, credentials, private policies, production telemetry,
  scraped datasets, or third-party product claims are included.
- The check-mark SVG favicon and interface visuals are original project assets.

## External systems

The deployed vertical slice has correlated Cloud Run, Google ADK,
`gemini-3.5-flash` through Vertex AI at `global`, Firestore, Cloud Scheduler,
Cloud Logging, Cloud Build, and GitHub receipts. Ten consecutive actions-off
verifier runs passed against frozen base
`b5c2badacc506b78c6eed314f155ecbc2188198b`; their unique run, build, and
synthetic-fixture identifiers are recorded in [evaluation](evaluation.md). After
that gate, run `run_806d1fc144344baebb757747d1b56e83` and build
`f4cbf983-db73-4bf5-9504-93c253a4b98b` opened verified draft
[PR #7](https://github.com/kostakarathana/iPromise/pull/7).

The GitHub App is installed only on `kostakarathana/iPromise`, with Metadata read
and Contents, Pull requests, and Issues read/write. Duplicate proof reconciled a
same-key replay and a distinct occurrence of the unchanged repair to PR #7,
leaving one branch, one open draft PR, and zero issues. The executable repair is
still locked to that public entrant-owned repository and one exact two-file
template; general repository repair is not claimed. Email is not implemented.
Cloud Scheduler is paused after proof.

Google Cloud runtime services and Gemini output were generated for this entry
against original synthetic data. These receipts prove only the documented scoped
control; they are not evidence of legal or blanket product compliance. Devpost has
not been submitted.
