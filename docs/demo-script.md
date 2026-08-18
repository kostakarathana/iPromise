# iPromise demo script

Target duration: **3:45**, normal speed, one continuous live workflow where
practical. The binding limit is four minutes under the
[official rules](https://allthingsagentichackathon.devpost.com/rules); only the
first four minutes should be assumed judgeable.

Status: planned script. Replace all placeholders and rehearse against the frozen
deployed build before recording.

## 0:00–0:25 — Hook and problem

**Visual:** The deployed iPromise Promise Ledger. Keep the interface clean; name
the Taskmaster category in narration rather than adding hackathon chrome to the
product UI.

**Narration:**

> Companies make hundreds of promises across privacy pages, terms, help docs, and
> product screens. Code changes every day, but those promises are usually tested
> once a year. iPromise turns supported promises into recurring executable
> controls—and when reality drifts, it finishes the engineering handoff.

## 0:25–0:45 — Truthful scope disclosure

**Visual:** Open the deployed reference SaaS privacy page. Highlight the account
deletion sentence and a persistent “Synthetic reference SaaS” badge.

**Narration:**

> This demonstration uses a deployed synthetic SaaS and synthetic users, not real
> customer data. Its policy promises that account deletion removes profile and
> activity data from active systems within the stated deadline.

## 0:45–1:05 — Trigger the real workflow

**Visual:** Return to iPromise, show the authorized repository, and choose **Run
audit**. Do not open a chat or guide individual stages.

**Narration:**

> Scheduled and manual runs enter the same idempotent audit service. From here,
> the agent operates without step-by-step instructions.

## 1:05–1:40 — Promise becomes a test

**Visual:** Expand **Activity** as soon as the run appears. The console polls the
Firestore-backed checkpoints while the start request remains active, so Capture,
Compile, Bind, and Probe advance from the real connected run. Show the exact
quote, source, timestamp, and control after they are captured.

**Narration:**

> iPromise captures the customer promise and hashes that exact
> source. Gemini 3.5 Flash, coordinated by Google ADK on Cloud Run, converts the
> language into a typed claim. Deterministic code confirms the quote exists and
> allows only a registered control.

## 1:40–2:10 — Contradiction, not a legal verdict

**Visual:** Evidence comparison: `profiles` absent, `analytics_profiles` present;
verdict changes to `CONTRADICTED`.

**Narration:**

> iPromise creates a randomized synthetic account, calls the actual deployed
> deletion endpoint, and probes every configured active store. The app profile is
> gone, but the analytics profile remains. Code—not the model—marks this tested
> promise contradicted. That is operational evidence, not a legal compliance
> opinion.

## 2:10–2:50 — Proof before publication

**Visual:** Let the connected run advance without intervention. Show the compact
Cloud Build receipt: expected red baseline, green candidate control, green
regression suite, exact tree matched, build ID, and durable log link. Then follow
the newly opened draft-PR link and show the exact tested commit/tree, promise,
scoped evidence, limitation, hidden marker, and matching run ID.

**Narration:**

> iPromise will not publish code it has not independently verified. A fixed Cloud
> Build program first proves the known failing baseline, then the repaired hidden
> control and full regression suite. It binds those results to the exact bytes
> uploaded into this draft PR. The agent never merges, deploys, or contacts
> customers.

## 2:50–3:15 — Recovery and duplicate suppression

**Visual:** Show the Firestore run receipt, or the already captured safe cloud-smoke
result. Demonstrate that a duplicate delivery resolves to the same run and that a
distinct occurrence of the unchanged exact repair resolves to the same draft PR.

**Narration:**

> Scheduler delivery is at-least-once, so iPromise uses transactional execution
> and action leases. A retry resumes the same run; a later audit of the unchanged
> exact repair reconciles the existing branch and draft PR instead of creating a
> duplicate.

## 3:15–3:38 — Undeniable Google Cloud proof

**Visual:** Show the `.run.app` application URL, then Cloud Run service and Cloud
Logging filtered to the same run ID. Briefly show the Cloud Scheduler execution,
Firestore run document, Vertex/ADK event, and Cloud Build log without exposing
secrets.

**Narration:**

> This run is hosted on Google Cloud: Cloud Run executes the console, reference
> product, and ADK agent; Cloud Scheduler starts the recurring workflow; Vertex AI
> runs Gemini; Firestore checkpoints state; and Cloud Logging ties it together
> with the same run ID.

## 3:38–3:45 — Close

**Visual:** Return to the Promise Ledger: Promise → Proof → Draft PR.

**Narration:**

> iPromise is CI for company truth: if you promise it, prove it.

## Recording truth checklist

- The run is live and the draft PR is newly created during the recording.
- Any waiting is shown honestly. If uniformly sped up, disclose the exact speed on
  screen; do not splice a fake autonomous sequence.
- The synthetic SaaS and synthetic data are disclosed visually and verbally.
- Local demo mode is not used as cloud proof.
- The model/framework/service names match the locked submission dependencies.
- The run ID, timestamps, source hash, Cloud Build receipt, Firestore checkpoint,
  and GitHub draft PR are mutually consistent.
- No API key, secret, customer data, private prompt, or private repository content
  is visible.
- Total exported duration is below 4:00 and public playback is tested logged out.

## Release condition before final recording

The verifier-to-PR path is implemented and tested locally, but this script may be
recorded as written only after repeated deployed Cloud Build runs and a real
GitHub draft-PR receipt prove it. Until then, it is a plan, not evidence. If the
verifier fails during a genuine run, show the truthful issue fallback and explain
the failed gate; never substitute a precomputed receipt or imply that it was live.

Keep a truthful fallback recording of the same frozen release. A fallback may
show an earlier genuine run, clearly labeled with its timestamp; it may not imply
that precomputed or mocked output was generated live.
