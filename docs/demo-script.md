# iPromise demo script

Target duration: **3:50**, normal speed. The central proof is one continuous,
uncut, actions-on audit that creates a new verified GitHub draft pull request.
The binding limit is four minutes under the
[official rules](https://allthingsagentichackathon.devpost.com/rules); assume
nothing after 4:00 will be judged.

Status: recording plan. Rehearse against the final frozen build, then record the
same path with Cloud Scheduler **PAUSED**. The manual trigger and Scheduler use
the same idempotent audit service; pausing the recurring trigger prevents an
unattended run from consuming the one clean draft-PR identity needed on camera.

## Before recording

Prepare these views without exposing credentials or unrelated browser tabs:

1. The authenticated hosted iPromise console at the top of the Promise Ledger.
2. The deployed synthetic reference SaaS privacy page, with its synthetic label
   and account-deletion promise visible.
3. Cloud Logging with this query ready; paste the live run ID after completion:

   ```text
   resource.type="cloud_run_revision"
   resource.labels.service_name="ipromise-agent"
   jsonPayload.event="ipromise.audit.receipt"
   jsonPayload.runId="PASTE_RUN_ID"
   ```

4. The `ipromise-agent` Cloud Run service page.
5. The public README architecture diagram.
6. The public GitHub repository, ready to open the new draft PR.

Pre-warm the pages, confirm external actions are enabled, confirm no run or
action lease is active, and confirm no draft PR already exists for the final
base/candidate fingerprint. Do not start or resume the Scheduler.

## 0:00–0:08 — Hook

**Visual:** Hosted iPromise Promise Ledger.

**Narration:**

> Your product makes promises in privacy pages, terms, help docs, and UI copy.
> iPromise turns those words into recurring controls—and when reality drifts, it
> finishes the engineering handoff.

## 0:08–0:21 — The exact promise

**Visual:** Deployed synthetic reference SaaS privacy page. Highlight the
account-deletion sentence and the visible synthetic disclosure.

**Narration:**

> This is an entrant-owned synthetic SaaS with synthetic users, not customer
> data. It promises that account deletion removes profile and activity data from
> active systems within 24 hours.

## 0:21–0:34 — Scope and trigger

**Visual:** Return to iPromise. Briefly show the authorized
`kostakarathana/iPromise` repository and Taskmaster workflow. Put
`LIVE RUN · UNCUT · NORMAL SPEED` on screen.

**Narration:**

> iPromise is a Taskmaster agent. Scheduled and manual triggers enter the same
> idempotent service. From this click onward, the workflow runs without
> step-by-step instructions.

## 0:34–1:43 — One uncut live run

**Visual:** Click **Run audit** once. Keep the console continuously visible while
Activity advances through capture, compilation, control binding, probe,
verification, and publication. Do not cut away, accelerate, or trigger another
run. Let the real loading time remain visible.

**Narration:**

> The agent captures and hashes the exact source. Gemini 3.5 Flash on Vertex AI,
> coordinated by Google ADK on Cloud Run, converts the language into a typed
> claim. Deterministic code verifies the quote, binds only a registered control,
> creates a randomized synthetic account, invokes the deployed deletion API, and
> probes each approved active store.
>
> The app profile disappears, but the analytics profile remains. Code—not the
> model—returns CONTRADICTED for this scoped control. That is operational
> evidence, not a legal or blanket compliance verdict.

If the terminal result has not appeared by 1:43, continue the uninterrupted
segment up to 2:04 and shorten the later architecture view. If it has not
completed within 90 seconds, stop and record a new truthful take after diagnosing
the run; never splice in an earlier result.

## 1:43–2:08 — The safety gate

**Visual:** Show the terminal `CONTRADICTED` result and compact verification
receipt: expected red baseline, green candidate, green regression suite, exact
tree match, build ID, and publishable status.

**Narration:**

> iPromise will not publish unverified code. A fixed Cloud Build program first
> proves the known failing baseline, then the repaired hidden control and full
> regression suite. It also proves the candidate tree exactly matches the bytes
> approved for publication.

## 2:08–2:28 — Independent Cloud Build proof

**Visual:** Open the run's Cloud Build link. Show the successful build and its
red-before/green-after verification steps. Keep the build ID visible.

**Narration:**

> This is the independent verifier running with a dedicated Google Cloud identity
> and no GitHub or runtime secrets. A failed or ambiguous receipt closes the
> publication gate.

## 2:28–2:47 — Same-run observability

**Visual:** Open Cloud Logging, paste the visible run ID into the prepared query,
and show the matching structured receipt. Briefly show the Cloud Run service and
`.run.app` deployment identity.

**Narration:**

> The same run ID connects the Cloud Run agent, Firestore checkpoints, Vertex and
> ADK model event, Cloud Build verification, and structured Cloud Logging receipt.

## 2:47–3:00 — Bounded authority

**Visual:** Return to the completed ledger and expand technical details or the
action receipt.

**Narration:**

> The GitHub App is installed only on this repository. The implemented publisher
> exposes no merge or deploy operation and creates draft pull requests only.
> Ambiguous repairs fall back to an issue; configured email escalation remains a
> separate bounded route.

## 3:00–3:29 — The real external action

**Visual:** Follow the new draft-PR link. Show the **Draft** badge, exact scoped
change, run/build provenance, and green release-gate check. Do not merge it.

**Narration:**

> This draft PR was created by the live run we just watched. It contains the exact
> verified repair, the customer promise, scoped evidence, limitations, and
> matching run and build provenance. Human review remains the final authority.

If the GitHub Actions check is still running, show the queued check truthfully and
use the already-green Cloud Build receipt as the live proof. Do not imply that CI
has completed until it has.

## 3:29–3:44 — Architecture

**Visual:** Public README architecture diagram.

**Narration:**

> The design separates probabilistic claim compilation from deterministic
> grounding, probing, verdicts, and action gates. Cloud Run executes the console,
> synthetic product, and ADK agent; Vertex AI runs Gemini; Firestore checkpoints
> state; Cloud Scheduler provides recurring triggers; and Cloud Build verifies
> the repair before GitHub sees it.

## 3:44–3:50 — Close

**Visual:** Return to the Promise Ledger: Promise → Proof → Draft PR.

**Narration:**

> iPromise is CI for company truth: if you promise it, prove it.

## Recording truth checklist

- The central run is live, uncut, normal speed, and creates a new draft PR during
  the recording.
- The synthetic SaaS and synthetic data are disclosed visually and verbally.
- The model, framework, and services are named exactly: Gemini 3.5 Flash on
  Vertex AI, Google ADK, Cloud Run, Firestore, Cloud Scheduler, Cloud Build,
  Secret Manager, and Cloud Logging.
- The run ID, timestamps, source hash, build ID, exact-tree receipt, deployed
  revision, and GitHub draft PR are mutually consistent.
- The verdict is scoped to the tested control and never presented as legal or
  blanket compliance.
- No secret, access code, API token, private prompt, personal tab, or unrelated
  product is visible.
- The exported video is below 4:00, in English, and tested through public playback
  while logged out.
- The public repository, architecture image, hosted URL, and video remain stable
  through judging.

## Failure policy

Keep one truthful fallback recording of the same frozen release. A fallback may
show an earlier genuine run only when its timestamp is visible and narration says
that it is a prior run. Never substitute a precomputed receipt for the live run,
hide a failed gate, splice separate runs into one apparent workflow, or claim a
queued check passed.
