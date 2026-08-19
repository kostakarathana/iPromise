# Project provenance and third-party materials

Last reviewed: **2026-08-19 AEST**

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

`iPromise` is used here as the hackathon project name. A basic web/App Store
search found unrelated software and services using similar wording. This project
is not affiliated with them and copies none of their code, visual identity,
screenshots, copy, or data. This disclosure is not a trademark-clearance opinion;
recheck the final public name and presentation before freezing the submission.

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
- The final video master is an original screen recording of the deployed project
  with an original English narration script and burned English captions. The
  narration was synthesized on 2026-08-19 with Google Cloud Text-to-Speech voice
  `en-AU-Neural2-C` at speaking rate `1.10`. Google's
  [Text-to-Speech documentation](https://docs.cloud.google.com/text-to-speech/docs/basics)
  expressly permits generated audio in media such as videos and recordings. The
  service was used only to produce the submission narration; it is not a product
  model integration or bonus-model claim. No customer data or third-party product
  footage is included. Post-render decode, timing, caption, audio, and privacy QA
  passed; its checksum is recorded in the [submission release
  manifest](submission-release.md). Public hosting remains pending.
- A superseded local candidate used a macOS System Voice. It was rejected before
  publication, replaced completely, and is not a submission artifact. The final
  master contains only the Google Cloud Text-to-Speech narration described above.
- The video's continuous live segment records distinct duplicate run
  `run_a2dca42370fd42bda69f2eff361c3bfd`, which executes the full workflow and
  reconciles to existing PR #14. It does not depict that run as the PR creator.
  Creator run `run_74ea1919b21a47b9846a4d3c5efb48b8` and its Cloud Build are
  shown immediately afterward as clearly separate provenance receipts.

## External systems

The deployed vertical slice has correlated Cloud Run, Google ADK,
`gemini-3.5-flash` through Vertex AI at `global`, Firestore, Cloud Scheduler,
Cloud Logging, Cloud Build, and GitHub receipts. Ten consecutive historical
actions-off verifier runs passed against base
`b5c2badacc506b78c6eed314f155ecbc2188198b`; their unique run, build, and
synthetic-fixture identifiers are recorded in [evaluation](evaluation.md).

The final deployed product source is
`a4e7a59f89a60d2ba0ad087d884836d22e5d39e4`. Actions-on run
`run_74ea1919b21a47b9846a4d3c5efb48b8`, synthetic fixture
`syn_ca95780e5f9067a4641fd15384f90dd1`, and build
`e1a7a7a5-1878-41d6-9760-27c7085ae332` opened verified draft
[PR #14](https://github.com/kostakarathana/iPromise/pull/14). Its exact head
`a460858672ab176a4142c600fb9028f1b042a373` passed the repository release gate.

The GitHub App is installed only on `kostakarathana/iPromise`, with Metadata read
and Contents, Pull requests, and Issues read/write. Distinct-trigger run
`run_a2dca42370fd42bda69f2eff361c3bfd` and build
`e7966c07-97fd-4436-b7a8-8a0a1d4e86fd` reconciled the unchanged repair to PR
#14. Replaying that trigger key returned the same run, build, and PR; the final
fingerprint retained one open draft PR. Earlier generated proof PRs #7 and #12
are closed. The executable repair remains locked to the public entrant-owned
repository and one exact two-file template; general repository repair is not
claimed. Email is not implemented. GitHub actions are disabled on the current
judge-safe revision, and Cloud Scheduler is paused after proof.

Google Cloud runtime services and Gemini output were generated for this entry
against original synthetic data. These receipts prove only the documented scoped
control; they are not evidence of legal or blanket product compliance.

The private Devpost draft was created on 2026-08-17 within the Submission Period
and is saved at 2/5 steps with the iPromise title, elevator pitch, and architecture
image. It has not been submitted. Devpost retains the earlier
`/software/handrail` preview slug from a brief draft-name change; local browser
history shows the same new draft changing from Handrail to iPromise that day, and
the repository contains no imported Handrail product code or assets. No unrelated
Devpost project is part of this entry.
