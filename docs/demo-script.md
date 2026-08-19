# iPromise recorded demo cut sheet

Duration: **3:30**, 1920×1080, English narration, burned English captions. The
binding judging limit is four minutes under the
[official rules](https://allthingsagentichackathon.devpost.com/rules).

Status: final local master recorded and QA-verified at
`artifacts/video/browser-native/ipromise-hackathon-demo-final.mp4`. Its SHA-256 is
`b86db66c9ff511f8c27aa3537825c5c37e9097f4dd3620e610b07772fee971bd`.
The entrant-authored narration uses Google Cloud Text-to-Speech
`en-AU-Neural2-C` at speaking rate `1.10`; it is submission-production tooling,
not a product-model bonus claim.
Public upload, processing, and logged-out playback remain pending.
Cloud Scheduler was **PAUSED** during recording and remains paused.

## What the recording proves

The continuous live segment records a **distinct duplicate occurrence**, not the
earlier PR-creation event. From 0:30 to 1:19, run
`run_a2dca42370fd42bda69f2eff361c3bfd` executes the complete live
Gemini/Google ADK/control/Cloud Build workflow in a 49-second browser-frame
capture. All 202 frames in the retained interval remain in original order. The
measured interval where the browser sampler paused is represented by holding the
last captured frame, so no retained wall-clock time is silently removed. The cut
omits 98 trailing frames only after the completed PR state is visible; it does
not accelerate or remove any in-run time. Its Cloud Build is
`e7966c07-97fd-4436-b7a8-8a0a1d4e86fd`. Because the unchanged finding already
had an open exact-repair action, the run correctly reconciles to existing draft
[PR #14](https://github.com/kostakarathana/iPromise/pull/14) instead of creating
a duplicate.

Immediately afterward, the recording shows the earlier creator proof that opened
that PR: Cloud Logging receipt `run_74ea1919b21a47b9846a4d3c5efb48b8` on
actions-on revision `ipromise-agent-00012-2gm`, Cloud Build
`e1a7a7a5-1878-41d6-9760-27c7085ae332`, and PR #14 with its exact scoped diff.
The creator and filmed duplicate runs are related by the same finding/action
fingerprint, but they are not presented as one run.

## Recorded timeline

### 0:00–0:09 — Cover and hook

**Visual:** iPromise cover and product promise.

**Proof:** Establishes the product: customer promises become recurring,
evidence-backed controls and bounded engineering actions.

### 0:09–0:20 — Exact synthetic policy

**Visual:** Deployed synthetic reference SaaS privacy page and account-deletion
sentence.

**Proof:** The source and data are entrant-owned synthetic fixtures, not customer
data. The exact promise says: “When you delete your account, we remove your
profile from our app and analytics system within 24 hours.”

### 0:20–0:30 — Console before the run

**Visual:** Hosted iPromise Promise Ledger before triggering the audit.

**Proof:** Shows the selected authorized repository and the compact
promise-to-proof-to-action interface. The workflow is a Taskmaster service, not a
chat interaction.

### 0:30–1:19 — Continuous live distinct-duplicate run

**Visual:** One click starts the audit. The hosted console remains visible for
the entire run. Browser frames retain original order and measured wall-clock
intervals; the sampler pause is held rather than removed.

**Run:** `run_a2dca42370fd42bda69f2eff361c3bfd`

**Build:** `e7966c07-97fd-4436-b7a8-8a0a1d4e86fd`

**Proof:** The run performs source capture, Gemini 3.5 Flash claim compilation on
Vertex AI, Google ADK orchestration, deterministic grounding/control binding,
synthetic deletion probing, scoped verdict computation, and the fixed Cloud
Build red-before/green-after/exact-tree verification. The application profile is
removed while the analytics profile remains, so deterministic code returns the
scoped `CONTRADICTED` verdict. The final action reconciles to existing PR #14;
this filmed run does **not** claim to create a new PR.

### 1:19–1:31.5 — Completed duplicate-run receipt

**Visual:** Completed console summary for the filmed run.

**Proof:** Shows `CONTRADICTED`, the complete verification receipt, and the
existing PR #14 action URL returned by remote reconciliation.

### 1:31.5–1:43 — Activity trail

**Visual:** Activity details for the filmed duplicate run.

**Proof:** Shows the autonomous state sequence and model/control/build events for
the same `run_a2dca42370fd42bda69f2eff361c3bfd` execution.

### 1:43–1:58.5 — Creator Cloud Logging receipt

**Visual:** Structured Cloud Logging receipt for the earlier creator run.

**Creator run:** `run_74ea1919b21a47b9846a4d3c5efb48b8`

**Revision:** `ipromise-agent-00012-2gm`

**Proof:** Establishes the model invocation, Google ADK workflow, deployed Cloud
Run revision, final action state, and correlation for the run that created PR
#14. This is explicitly a prior creator receipt, not the continuously filmed run.

### 1:58.5–2:15 — Creator Cloud Build receipt

**Visual:** Cloud Build details for
`e1a7a7a5-1878-41d6-9760-27c7085ae332`.

**Proof:** Shows the independent verifier used by the creator run: expected red
baseline, green repaired control, green regression suite, and exact-tree gate.
The verifier identity has no GitHub or runtime credentials.

### 2:15–2:34 — Existing verified draft PR

**Visual:** [Draft PR #14](https://github.com/kostakarathana/iPromise/pull/14).

**Proof:** Shows the real open draft action created by the earlier creator run,
including its bounded scope and provenance. The filmed duplicate run returned
this same PR rather than opening another one.

### 2:34–2:49 — Exact scoped diff

**Visual:** PR #14 file changes.

**Proof:** Shows the exact two-file repair admitted by the locked policy and
verified before publication. Human review remains the final authority; the agent
cannot merge or deploy.

### 2:49–3:01 — Cloud Run deployment

**Visual:** `ipromise-agent` Cloud Run service.

**Proof:** Visibly establishes the Google Cloud backend and deployed service
identity. The recorded actions-on revision is `ipromise-agent-00012-2gm`; after
proof, traffic moved to judge-safe actions-off revision
`ipromise-agent-00013-kmv` with Scheduler paused.

### 3:01–3:22 — Architecture

**Visual:** Public iPromise architecture diagram.

**Proof:** Shows Gemini 3.5 Flash on Vertex AI, Google ADK on Cloud Run,
Firestore state, Cloud Scheduler triggers, Cloud Build verification, Secret
Manager, Cloud Logging, the synthetic SaaS, and the scoped GitHub App. It also
shows the trust boundary: model output proposes structured meaning while code
owns evidence, credentials, verification, and side effects.

### 3:22–3:30 — Close

**Visual:** iPromise closing frame.

**Message:** Customer promises should behave like tests. If you promise it,
prove it.

## Recording truth checklist

- The 0:30–1:19 segment is one continuous live execution represented by all 202
  retained browser frames in original order and their measured wall-clock timing.
  The cut omits only 98 trailing post-completion frames.
- That live execution is the distinct duplicate run
  `run_a2dca42370fd42bda69f2eff361c3bfd`; it performs the full workflow and
  reconciles to PR #14.
- The recording does not claim that the filmed duplicate run created PR #14.
- The creator receipt shown at 1:43–2:15 is clearly the earlier run
  `run_74ea1919b21a47b9846a4d3c5efb48b8` and creator build
  `e1a7a7a5-1878-41d6-9760-27c7085ae332`.
- The synthetic SaaS and synthetic data are disclosed visually and verbally.
- The scoped verdict is never presented as legal or blanket compliance.
- No secret, access code, API token, private prompt, personal tab, or unrelated
  product is visible.
- The local master is 3:30 with English narration and burned English captions.
- Decode, timing, caption, audio, and privacy QA passed. Public upload,
  processing, and logged-out playback remain pending.

## Failure policy

Keep one truthful fallback recording of the same deployed source. Never relabel a
duplicate-reconciliation run as the PR creator, substitute a precomputed receipt
for a live segment, hide a failed gate, splice separate runs into one apparent
execution, or claim a queued check passed.
