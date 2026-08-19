# iPromise submission release record

Last updated: **2026-08-19 AEST**

This is the judge-facing manifest for the final-source iPromise proof. It keeps
deployed product provenance separate from the later submission-release commit,
which changes documentation, static submission assets, link-check configuration,
and the development-only pytest lock but no deployed runtime source. A field
marked **Pending** is not yet submission evidence.

## Submission state

- Track: **Taskmaster**
- Entrant: solo individual, Australia
- Repository: https://github.com/kostakarathana/iPromise
- Hosted console: https://ipromise-console-ipj6vqlg2q-uc.a.run.app
- Devpost draft: **private draft saved at 2/5 steps; not submitted**
- Public video URL: **Pending upload**
- Immutable tag and GitHub Release: **Pending**
- Submission-release commit: **Pending merge**

## Deployed product

| Item | Final value |
| --- | --- |
| Product source commit | `a4e7a59f89a60d2ba0ad087d884836d22e5d39e4` |
| Console revision | `ipromise-console-00012-kk9` |
| Recorded actions-on agent revision | `ipromise-agent-00012-2gm` |
| Current judge-safe agent revision | `ipromise-agent-00013-kmv` |
| Synthetic SaaS revision | `ipromise-demo-saas-00010-xk5` |
| Agent URL | `https://ipromise-agent-ipj6vqlg2q-uc.a.run.app` |
| Synthetic SaaS URL | `https://ipromise-demo-saas-ipj6vqlg2q-uc.a.run.app` |
| Current external-action setting | Disabled |
| Cloud Scheduler | **PAUSED** |
| Final workflow state | Zero nonterminal runs; zero execution/action leases |
| Judge-access gate | Passed: unauthenticated audit 401; health 200; fresh authenticated session returned product content |

The current actions-off revision is the judge-access safety state. The recorded
actions-on revision existed only for the controlled external-action proof. Both
refer to the same deployed product source above.

## Final creator proof

| Evidence | Final value |
| --- | --- |
| Audit run | `run_74ea1919b21a47b9846a4d3c5efb48b8` |
| Synthetic fixture | `syn_ca95780e5f9067a4641fd15384f90dd1` |
| Cloud Build | `e1a7a7a5-1878-41d6-9760-27c7085ae332` |
| Verification result | Expected `FAIL / PASS / PASS`; exact tree; publishable |
| Draft PR | [#14](https://github.com/kostakarathana/iPromise/pull/14) |
| Deterministic branch | `ipromise/promise-drift-085cacf0084a2728d277` |
| Published PR head | `a460858672ab176a4142c600fb9028f1b042a373` |
| Repository check | [Green release-gate job](https://github.com/kostakarathana/iPromise/actions/runs/32219511076/job/95967239117) |

PR #14 is the current open draft proof. Earlier generated proof PRs #7 and #12
are closed and are not counted in the final open state. No merge or deployment
operation is exposed by the publisher.

## Duplicate-suppression proof

A distinct trigger for the unchanged finding produced run
`run_a2dca42370fd42bda69f2eff361c3bfd` and Cloud Build
`e7966c07-97fd-4436-b7a8-8a0a1d4e86fd`. It reconciled to PR #14 rather than
creating another action. Replaying that duplicate trigger key returned the same
run ID, build ID, and PR URL. The final-fingerprint open draft-PR count remained
one.

This proves two separate properties:

1. repeated delivery of one idempotency key returns one logical run; and
2. a distinct occurrence of the unchanged finding reconciles to one remote
   action.

## Reliability evidence

The earlier ten-run actions-off gate remains historical, reproducible evidence.
Against base `b5c2badacc506b78c6eed314f155ecbc2188198b`, ten consecutive
audits produced unique run/build/fixture identities, completed in 448.5 seconds,
and returned the expected `FAIL / PASS / PASS`, exact-tree, publishable receipt.
Those identifiers are retained in [evaluation.md](evaluation.md). They do not
replace the final-source creator proof above.

## Video master

| Item | Value |
| --- | --- |
| Local file | `artifacts/video/browser-native/ipromise-hackathon-demo-final.mp4` |
| Duration | 3:30 |
| Frame size | 1920×1080 |
| Language | English narration |
| Captions | Burned English captions |
| Narration | Google Cloud Text-to-Speech `en-AU-Neural2-C`, speaking rate `1.10`; original entrant-authored script |
| SHA-256 | `b86db66c9ff511f8c27aa3537825c5c37e9097f4dd3620e610b07772fee971bd` |
| Caption-file SHA-256 | `59a11116f79b6134bc9cc528cb4b3a21103b111126e1a3bf3f04e13ba3db1616` |
| Narration-artifact SHA-256 | `6a196d4e175672be75a08fd0b008300f2fbf66cf97e1b30d57478d2965112f2e` |
| Visual-artifact SHA-256 | `0d258bbcd3e341a14041ca73c35bd7e91c8b0b9ba4ab757760c83d511556e6ed` |
| Local build-script SHA-256 | `8f259d026a62ab1da99adf482bc26cd761ff7bf5bce52e5d63986c7f2c8092e5` |
| Public URL | **Pending upload and processing** |
| Logged-out playback | **Pending** |

The continuous 49-second wall-clock segment from 0:30 to 1:19 is distinct run
`run_a2dca42370fd42bda69f2eff361c3bfd` and build
`e7966c07-97fd-4436-b7a8-8a0a1d4e86fd`. It performs the full workflow and
reconciles to existing PR #14; it does not create a new PR. All 202 frames in the
retained interval remain in original order, and the measured interval where the
browser sampler paused is held rather than removed. The cut omits only 98
trailing post-completion frames. From 1:43 onward, the video separately shows
the earlier creator Cloud Logging receipt, creator
build `e1a7a7a5-1878-41d6-9760-27c7085ae332`, PR #14, its diff, Cloud Run, and
the architecture. See the exact [recorded cut sheet](demo-script.md).

The local master is not yet a public submission artifact. Do not mark the video
gate complete until its public URL, processing state, and logged-out playback
have been checked. Local full decode, exact duration and stream inspection,
wall-clock timing reconstruction, narration-overlap validation, 55-cue caption
validation (maximum two lines and 42 characters per line), audio measurement
(`-16.02 LUFS` integrated, `-4.45 dBTP`, `5.00 LU LRA`), 6,300-frame full
decode, visual/privacy review, and checksum all passed. The three Google Cloud
stills mask the signed-in account avatar; no access token, key, personal email,
customer record, or unrelated product is visible.

## Static submission assets

| Asset | Dimensions | SHA-256 |
| --- | ---: | --- |
| `docs/assets/architecture.png` | 1440×900 | `99f3f9aaa765529c09f08bf65e95e364bf64f5ed379678e9d82ea370c1df9a19` |
| `docs/assets/ipromise-cover.png` | 1500×1000 | `a635ac7cacd5d1cf12d90d831d559b54a1ed31ae7eb1cc9fdfb11e813e1e3b38` |
| `docs/assets/ipromise-video-thumbnail.png` | 1920×1080 | `eced5f090eca84d797b405d1e79d9713cf9a508f20c5cfec1524aafb4346d24a` |

The architecture image matches the implemented Google Cloud vertical slice and
contains no dynamic run identifiers or credentials.

## Release verification

The final local release audit on **2026-08-19 AEST** passed:

- `./scripts/verify`: 16 synthetic claim fixtures, 6 synthetic-SaaS tests, 97
  agent tests, ESLint, TypeScript, 36 console tests, Next.js production build,
  standalone console-package smoke, lockfile policy, and `git diff --check`;
- `pnpm audit --prod`: no known vulnerabilities;
- `pip-audit` against both complete locked Python graphs, including development
  extras: no known vulnerabilities (the newly advised `pytest 8.4.2` was
  upgraded to `9.1.1` before release);
- high-confidence credential patterns across the working tree and every Git
  revision: no matches; the known local verification code and private-key
  filename are absent from both;
- all three Cloud Run source-upload manifests exclude environment files, private
  keys, test trees, local environments, and dependency caches; and
- a clean public clone of deployed source
  `a4e7a59f89a60d2ba0ad087d884836d22e5d39e4` passed the complete documented
  `./scripts/verify` release gate; and
- every README and documentation link passed the pinned `pnpm check:links` gate,
  apart
  from intentionally ignored localhost reproduction URLs and the planned,
  not-yet-created `v1.0.0-hackathon-submission` tag. Release-pinned links must be
  rechecked after that tag is created.

Secret values were never printed. Five runtime secrets remain enabled only at
numeric version 1 with service-level Secret Manager accessor bindings; the
judge access code passed a clean-session test and remains outside the repository.

## Remaining release gates

- Upload the video using the prepared [public upload metadata](video-upload-draft.md),
  allow processing to finish, and test playback while logged out.
- Recheck the binding Official Rules and entrant eligibility.
- Insert the already-tested console code only into Devpost's private field. The
  clean judge-equivalent HTTP access gate has passed without exposing it.
- Merge this documentation update through a green release gate.
- Create and preserve the immutable final tag and GitHub Release named
  `v1.0.0-hackathon-submission`, then verify every release-pinned link.
- Confirm the repository, release, architecture image, hosted URL, public video,
  and private judge instructions remain accessible.
- After the core release is frozen, optionally publish the prepared
  [build story](build-story-draft.md) and [social post](social-post-draft.md),
  then record their public URLs only if they still satisfy the live bonus rules.
- Complete and save the remaining Devpost draft fields only with the required
  user confirmation. Do not treat a saved draft as submission, and do not submit
  until every mandatory gate is complete.

The proof uses only the entrant-owned synthetic reference SaaS and establishes a
scoped technical `CONTRADICTED` verdict for one account-deletion control. It does
not establish legal compliance or a blanket product verdict.
