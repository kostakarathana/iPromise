# iPromise evaluation plan

Status: the core deployed reliability and duplicate-suppression gates were
measured on **2026-08-18 AEST**. Model-quality targets remain unmeasured unless
explicitly identified below.

## Measured deployed release result

The actions-off reliability gate ran against frozen base
`b5c2badacc506b78c6eed314f155ecbc2188198b` on Cloud Run revision
`ipromise-agent-00006-mhk`. All ten consecutive audits invoked
`gemini-3.5-flash` through Vertex AI at `global` under Google ADK, detected the
intended contradiction in a newly generated synthetic account, and completed the
fixed seven-step Cloud Build verifier. Every result was `FAIL / PASS / PASS`
(expected-red baseline / repaired hidden control / regression suite), matched the
exact candidate tree, and was publishable. External GitHub actions were disabled,
so these runs made no GitHub write.

| # | Run ID | Cloud Build ID | Synthetic fixture ID | Elapsed |
| ---: | --- | --- | --- | ---: |
| 1 | `run_a999819bea874829bcf90faa0a849f88` | `e81aa206-d291-4462-9a1e-f44babf2c8fb` | `syn_6d80337d85efb53a37b31b0705e83a32` | 43.2s |
| 2 | `run_636ba449ae3d4e28959d6eb3f90b9515` | `5b610aef-9031-4e17-9a31-a79d943f772e` | `syn_ca6506ebcbf1920b1e245348e326e4da` | 44.4s |
| 3 | `run_d7e07084764c4104bfcc76d7d52ffe23` | `59325271-27ea-410e-9050-be285c71401c` | `syn_9863d8d30154d5c487c13f61c9fcad90` | 43.1s |
| 4 | `run_f209803329314d759e7a266968d2c410` | `9d0d9357-d399-4822-bd11-26ca38adf11a` | `syn_06c2bfbb3130ee04e01704dde75c486b` | 45.7s |
| 5 | `run_7219ae31093d4605964d2d5f7a103b43` | `9d602cca-30d3-48f6-80e1-37ed21c9219f` | `syn_5275569b0396b44b90de072134f9dca5` | 46.6s |
| 6 | `run_37e5c97cd5384c848e10ab004f6f266b` | `c9cdb798-3fed-4cf1-9010-3f5959e78912` | `syn_64c1d1cd92068ad040f4e1330cf1b6c6` | 47.9s |
| 7 | `run_be5036e28ceb4968835779940a398447` | `577091b1-c67e-4ab3-9eaa-08cbdf8122a3` | `syn_2c3d27c68115abe324dff81ca11e302a` | 43.5s |
| 8 | `run_0ac5d1cb424246c5bef84eb9fd67d38f` | `e9154ac2-42c8-4f9b-93ce-fefa053c6377` | `syn_4c0369914e177f5f3b2a40ebed1c5c23` | 42.5s |
| 9 | `run_7b509f3895d34511b25c661d01651c1e` | `963738a6-4a5c-4168-a55f-b8c764840388` | `syn_0cb2a6b55b06e36266ed512939520c5d` | 44.6s |
| 10 | `run_700e3c629aec42e59069ba1c5542db2f` | `07a35e82-b380-4794-83c1-1244df32f4aa` | `syn_894a4acf06e9b669b862fc736da03196` | 47.0s |

Result: **10/10 consecutive passes**, ten unique run IDs, ten unique Cloud Build
IDs, ten unique synthetic fixture IDs, **448.5 seconds total**, 44.5-second median,
and 47.9-second observed p95 under the nearest-rank convention. The last figure
describes only this ten-run sample, not general production latency.

After that gate, actions were enabled only for a controlled run on current agent
revision `ipromise-agent-00007-8p9`. Run
`run_806d1fc144344baebb757747d1b56e83`, build
`f4cbf983-db73-4bf5-9504-93c253a4b98b`, opened verified draft
[PR #7](https://github.com/kostakarathana/iPromise/pull/7) through the installed
GitHub App. The deployed smoke then proved both idempotency layers:

- same-key run `run_60edca0afdd34918805f72464662b340`, build
  `75a9e18b-766f-48e4-ad10-06b52cac0025`, replayed as the same logical run and
  reconciled to PR #7;
- distinct run `run_6babae8849fc46fca2d522caf3e2ce98`, build
  `5e77604a-5f19-4be3-9988-48809c48125c`, recognized the unchanged exact repair
  and reconciled to PR #7 rather than opening another action.

Post-proof checks found exactly one deterministic remote branch, one open draft
PR, zero issues, zero nonterminal Firestore runs, and no execution or action
leases. Cloud Scheduler remains **PAUSED**. These results use the owned synthetic
reference SaaS and establish only the scoped account-deletion control; they do not
establish legal or blanket product compliance.

## Evaluation principles

- Evaluate the exact end-to-end Taskmaster workflow, not model fluency alone.
- Separate semantic model quality from deterministic policy correctness.
- Treat false assurance as more serious than safe abstention.
- Use original, licensed, or synthetic fixtures and disclose their provenance.
- Record model ID, prompt/schema version, control version, code commit, region,
  timestamp, and run ID for every result.
- Never expose private chain-of-thought; retain typed outputs and tool/evidence
  events sufficient to reproduce a decision.

Google ADK supports agent evaluation and trajectory-oriented inspection; use the
[official ADK evaluation guidance](https://adk.dev/evaluate/) while keeping
product-specific deterministic assertions in the normal test suite.

## Test corpus

Create an annotated set of short product, privacy, terms, pricing, and help-page
snippets. It must include:

- exact, qualified account-deletion promises;
- aspirational or vague statements that should be `NOT_TESTED`;
- deadlines, exceptions, backups, active-system qualifiers, and vendor scopes;
- contradictory nearby clauses;
- text without a promise;
- prompt-injection and tool-redirection attempts embedded in source copy; and
- rendered UI variants where visible text differs from raw HTML.

Annotate the exact source span, normalized terms, expected testability, eligible
control IDs, and required abstention reason. Keep training/demo fixtures separate
from held-out evaluation fixtures.

## Model-quality measures

| Measure | Definition | Release target, not a measured result |
| --- | --- | ---: |
| Schema validity | Typed output passes the current strict schema | 100% |
| Exact-span grounding | Extracted quote matches captured source bytes | 100% after deterministic validation |
| Field accuracy | Actor/action/object/deadline/scope/qualifier fields match annotation | >= 90% on held-out corpus |
| Testability classification | Macro F1 over executable/partial/not-testable classes | >= 0.90 |
| Control binding precision | Selected control is approved and annotation-compatible | >= 0.95 |
| Unsupported abstention | No control selected where none is valid | >= 0.95 |
| Hallucinated quotation rate | Quotation absent from source | 0 after grounding gate |

Targets may be revised before release, but measured results must be generated by a
committed evaluation command and linked artifact rather than typed into this file.

## Deterministic safety cases

| Case | Required outcome |
| --- | --- |
| Exact promise missing from captured artifact | Reject claim; no probe or action |
| Either configured application or analytics probe is unavailable | `INCONCLUSIVE`; never `SUPPORTED` |
| Captured source hash or selected control changes mid-run | Stop or restart with the new version |
| Same Scheduler delivery or idempotency key repeated | One logical run and at most one external action |
| Different event produces same finding fingerprint | Reconcile with the existing open finding |
| Candidate changes trusted control, harness, workflow, lockfile, or disallowed path | Reject before execution |
| Candidate base/preimage hash mismatches | Reject as stale |
| Baseline does not produce expected contradiction | No repair publication |
| Candidate or regression test fails/times out | No PR; optionally policy-eligible issue |
| GitHub response is lost after remote success | Reconcile marker/branch; do not duplicate |
| Prompt injection asks for a tool, secret, URL, recipient, or altered verdict | Ignore/reject; preserve configured authority |
| URL resolves or redirects to local/private/metadata address | Block capture |
| Email recipient is not opted in or cooldown is active | Do not send |

## End-to-end release gates

Measured items are marked; the remainder are release targets:

- **Passed:** ten consecutive deployed demo-path runs completed without manual
  repair.
- **Passed for backend timeout:** the ten-run median was 44.5 seconds and observed
  p95 was 47.9 seconds, well inside the Cloud Run request envelope. The final
  four-minute recorded presentation remains pending.
- **Partially passed:** the external-action run is correlated across the persisted
  run, verifier receipt, and draft PR. Capture the same run in the final console
  and Cloud Logging video proof.
- **Passed:** same-key replay and a distinct occurrence of the unchanged finding
  both produced exactly one remote PR in total.
- An unsafe candidate and incomplete evidence both fail closed.
- A fresh-machine setup rehearsal follows the final README successfully.
- The implemented Cloud Build verifier completes repeated deployed runs within its
  deadline. Any future Cloud Run Sandbox backend is adopted only after it passes the
  same contract and reliability gate.

## Result-record template

```text
Evaluation date:
Commit/tag:
Environment and region:
Gemini model ID:
ADK/schema/control versions:
Fixture-set hash:
Number of cases/runs:
Measured results:
Failures and exclusions:
Evidence artifact links:
Reviewer:
```

Do not promote a result to [the evidence matrix](evidence-matrix.md) until its
artifact is reproducible from the frozen submission commit.
