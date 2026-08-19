# iPromise agent instructions

These instructions apply to the entire repository. Direct user instructions take precedence.

## Ultimate project goal

iPromise exists to become an eligible, polished, highly competitive submission to Google's [All Things Agentic Hackathon](https://allthingsagentichackathon.devpost.com/). This hackathon is the project's ultimate end goal unless the user explicitly changes it.

Every product, architecture, implementation, testing, documentation, and delivery decision must advance that outcome. In priority order, optimize for:

1. Eligibility and complete compliance with the current official rules.
2. A high score against the published judging rubric.
3. A convincing end-to-end demonstration of useful autonomous action.
4. Robust, production-minded engineering on the required Google stack.
5. A clear, reproducible, judge-friendly submission delivered safely before the deadline.

Prefer a reliable, coherent, demo-ready vertical slice over feature breadth. Do not spend scarce hackathon time on generic polish, speculative scale, or post-hackathon work unless it materially improves the rubric, proof, reliability, or submission.

## Source of truth and volatility

Last deeply verified: **2026-08-19 AEST**.

- [Official Rules](https://allthingsagentichackathon.devpost.com/rules) are binding and take precedence.
- Also monitor the [Overview](https://allthingsagentichackathon.devpost.com/), [Resources](https://allthingsagentichackathon.devpost.com/resources), [FAQ](https://allthingsagentichackathon.devpost.com/details/faqs), [Schedule](https://allthingsagentichackathon.devpost.com/details/dates), [Updates](https://allthingsagentichackathon.devpost.com/updates), and [Discussions](https://allthingsagentichackathon.devpost.com/forum_topics).
- Recheck the official rules and updates before making a submission-critical decision and again before final submission. Record newly discovered rule changes here.
- Treat organizer discussion replies as useful clarification, but never let them override the binding rules.

The organizer's 2026-08-19 self-check update adds no new mandatory technology or
artifact. It emphasizes that judges may rely entirely on the video, description,
and repository; the video should name the Gemini model and agent framework
clearly, show a real action or state change, and visibly prove Google Cloud. It
also recommends rehearsing, removing setup/loading dead time, using a clear AI
voiceover when useful, testing the public repository logged out, opening the
submission form early, and uploading the video early enough for processing.

Known defects and inconsistencies in the official materials require conservative handling:

- The Rules and Devpost Schedule disagree on the submission start, judging end, and winner-announcement time. They agree on the hard submission deadline. Follow the Rules and the earliest/most restrictive safe interpretation.
- The Rules' architecture subcriteria retain obsolete track labels ("Continuous Action Engine," "Evolving Knowledge Engine," and "Multi-Agent Nexus"). Do not use those as current categories; apply the architectural intent to the selected current track.
- The FAQ says Gemini Enterprise Agent Platform deployment earns bonus points, but the binding Stage 3 bonus list does not. Do not count that as a bonus unless the Rules are updated.
- Official pages show the social hashtag both with and without a space. Use the valid, consistently advertised form: `#AllThingsAgenticHackathon`.
- Official pages have exposed different short links for the cloud-credit form. Always enter through the current Resources or FAQ page rather than preserving an old form URL.

## Hard timeline

- Binding Submission Period: **2026-08-03 09:00 PT through 2026-08-31 17:00 PT**.
- Hard deadline in the user's local time: **2026-09-01 10:00 AEST (Brisbane, UTC+10)**.
- Internal target: submit a complete baseline by **2026-08-28**, then use the remaining time only for verified improvements and final checks.
- The $150 hackathon Google Cloud credit request closes **2026-08-28 12:00 PT / 2026-08-29 05:00 AEST**, or earlier if supplies run out. Allow up to 72 business hours; only one code may be requested per entrant. Use the exact email registered on Devpost, name an official track, and give a concrete one- or two-sentence project description. The currently published form says to redeem the code before **2026-09-03** without stating a timezone; the credit then lasts 90 days. Reverify these details on the live form.
- The Rules state judging runs **2026-09-01 09:00 PT through 2026-10-01 23:45 PT**, with winners announced on or around **2026-10-08 10:00 PT**. Because the Schedule conflicts, keep submission-linked artifacts stable and judge-accessible until winners are announced.

Never plan to submit in the final hour.

## Eligibility and project provenance

- Confirm every entrant's eligibility against the Official Rules before submission. All team members must be eligible, added to the Devpost project, and accepted; a team or organization must designate one Representative. The FAQ states there is no maximum team size.
- The project must be newly created during the Submission Period. Standard frameworks, libraries, starter templates, and AI coding assistants are permitted. Disclose every other piece of pre-existing code or work incorporated into the project.
- Use only original or properly licensed code, media, datasets, SDKs, APIs, and other third-party material. Obtain authorization for third-party data and integrations.
- The application must support English. All submission materials must be in English or include an English translation/subtitles.
- Never commit secrets. Use environment variables, least-privilege credentials, a committed example environment file, and explicit setup instructions.

## Mandatory build constraints

The final submission must:

1. Enter exactly one current track: **Taskmaster**, **Collaborative Partner**, or **Fortified Enterprise Fleet**.
2. Use **Gemini 3.5 or newer**, accessed through the Gemini API or Vertex AI. The Overview specifically promotes Gemini 3.5 Flash; verify the current eligible model identifier before locking dependencies.
3. Use at least one Google agent framework: **Google ADK**, **Google Gen AI SDK**, **Antigravity SDK**, or **Genkit**.
4. Use at least one Google Cloud infrastructure service, such as **Cloud Run, Cloud SQL, Firestore, GKE, or Pub/Sub**. Do not assume that calling a model through Vertex AI alone is enough; use and visibly evidence a named infrastructure service.
5. Be deployed on Google Cloud at least long enough to capture undeniable proof in the demo and repository.
6. Operate beyond a standard chat loop: take real action, run a meaningful workflow, transform data, or coordinate specialized agents with appropriately bounded human input.

## Locked product and track strategy

iPromise targets the **Taskmaster** track. The primary user is a product, privacy, or platform engineer at a fast-moving SaaS company. The painful friction is customer-facing promises silently drifting away from real product behaviour. The measurable MVP outcome is one scheduled audit that captures an exact promise, executes an approved control against synthetic staging data, produces source-grounded evidence, verifies a bounded repair, and prepares exactly one external action without human guidance after the trigger.

The product vision is broad claim discovery across customer-facing product surfaces. The hackathon MVP deliberately executes one claim type deeply: account deletion across active application and analytics records. Never imply that every claim is executable or that iPromise establishes legal or regulatory compliance.

The interface must feel dead simple. It is a promise ledger and action timeline, not a chat product. The allowed user-facing outcomes are intentionally narrow:

1. Open a verified draft pull request when a bounded code repair is appropriate.
2. Raise a GitHub issue when remediation is ambiguous, crosses a safety boundary, or requires ownership.
3. Send a concise email only for configured escalation conditions.

Draft pull requests are the primary demo action. Issues and email are secondary truthful fallbacks, not ornamental integrations. Never auto-merge, auto-deploy, notify customers, contact regulators, or send email without an explicit configured destination and risk policy.

Track rationale: Taskmaster best matches the event-driven, end-to-end workflow that watches for a trigger, autonomously routes work, interacts with real systems, and closes a messy multi-step chore. Keep the main demo aligned to background completion with little or no intervention and a distinctive "Bring Your Own Friction" problem.

- **Taskmaster (selected):** best for an event-driven, end-to-end workflow that watches for a trigger, autonomously routes work, interacts with tools or systems, and finishes a messy multi-step chore. Judges emphasize background completion with little or no intervention and a distinctive "Bring Your Own Friction" problem.
- **Collaborative Partner:** best for guided, stateful collaboration that asks useful clarifying questions, captures feedback, retrieves context, persists memory, and adapts. Judges also emphasize actively synthesizing or mutating unusual, messy, complex, or unstructured data rather than merely reading it.
- **Fortified Enterprise Fleet:** best when the problem genuinely warrants multiple specialized agents, cross-department discovery, long-running state, secure routing, policy enforcement, auditability, observability, and failure-tolerant delegation. Judges also look for an "Unlikely Hero" outside standard corporate roles. Gemini Enterprise Agent Platform capabilities are recommended, not mandatory. An organizer has confirmed that first-party equivalents may demonstrate the capabilities and that synthetic or de-identified enterprise data is acceptable when the controls are real.

Do not choose Fortified Enterprise Fleet merely to appear sophisticated. Multi-agent complexity must be justified by the task.

## Judging-driven definition of done

Stage 1 is pass/fail: the submission must be complete, address a challenge, and satisfy all required technology and artifact requirements. Treat this as a hard release gate. The Rules permit expert panels, peer review, automated AI-driven analysis, or a combination, so make compliance explicit and machine-findable rather than merely implied.

| Criterion | Weight | What this repository must prove |
| --- | ---: | --- |
| Innovation & Operational Utility | 40% | A real, specific source of friction is removed through high-value autonomous decisions and actions, not a generic chatbot or scripted façade. |
| Architectural Discipline & Tech Stack | 30% | Components are decoupled; state and memory are intentional; tools and credentials are scoped; failures, retries, timeouts, idempotency, and recovery are handled; behavior is observable and testable. |
| Demo & Production Readiness | 30% | A concise live execution undeniably works; the architecture diagram is clear; setup is reproducible; the repository is clean; and Google Cloud deployment is visibly proven. |

For every major feature or dependency, be able to name the requirement, criterion, demo moment, or submission artifact it improves. If none applies, defer it.

The core release is done only when all of the following are true:

- One representative workflow runs end to end with minimal hand-holding and produces visible external state or a meaningful data transformation.
- The demo path is deterministic enough to reproduce under time pressure without faking autonomy.
- Expected failures and unsafe actions have bounded behavior, useful logs, and a recovery path.
- Architecture, permissions, state/memory, model/tool boundaries, and Google Cloud services are visible in both code and documentation.
- Automated tests cover the critical workflow and failure cases in proportion to risk.
- A fresh user can follow the README from prerequisites to a working local or cloud run.
- The system can generate convincing demo evidence: UI changes, terminal events, logs, database/state transitions, and Google Cloud deployment proof.
- The README contains an evidence matrix mapping each mandatory requirement and important rubric phrase to the relevant file, diagram element, demo timestamp, test, and cloud proof.

Mocks, synthetic data, and demo fixtures must be clearly disclosed. Never present a mocked integration, manual intervention, precomputed result, or edited sequence as live autonomous behavior. The organizer has not yet answered whether a mock third-party API fully satisfies external-action expectations, so do not make a mock-only integration central to the entry without obtaining a current clarification.

## Required submission artifacts

Maintain these as first-class deliverables throughout development, not as final-day cleanup:

- Exactly one selected category.
- A hosted project URL if feasible; it is highly encouraged but not mandatory.
- A text description covering features/functionality, technologies, other data sources, and findings/learnings.
- A GitHub, GitLab, or Bitbucket repository URL. A private repository must grant access to `testing@devpost.com` and `cloudhackathons@google.com`.
- A `README.md` with step-by-step local setup and/or cloud deployment instructions.
- A clear architecture diagram showing at least Gemini, the agent/framework layer, backend, Google Cloud services, data/state, frontend, and external tools.
- A public YouTube or Vimeo demonstration video no longer than **4:00**. Only the first four minutes may be judged.
- The video must explain the problem and value proposition, show the application in action, and visibly prove that its backend runs on Google Cloud (for example, Cloud Console, Cloud Run dashboard/logs, Vertex AI logs, or a `.run` URL).
- The video must be in English or include English subtitles.

Design the primary demo as a single, continuous live run that fits below four minutes at normal speed. An organizer has said a uniform speed-up of a genuine continuous run can be acceptable when there are no cuts or splices and an on-screen note discloses the speed-up, but normal-speed proof is safer.

The application does not have to stay publicly live solely to accrue cost, provided the submission contains clear deployment proof. If a hosted/test URL is submitted, keep it free, stable, and accessible with any necessary testing credentials through judging. Scale down or disable expensive services only after capturing proof.

At the deadline, freeze every artifact linked from the submission: Devpost entry, video, repository reference, architecture diagram, and judge-facing site/build. Create an immutable tag or release and continue later development only in a separate branch or fork. The FAQ warns that post-deadline edits can jeopardize eligibility.

Monitor the entrant email daily after judging. Potential-winner provisions include response and document-return windows as short as two days; treat the shortest published window as controlling.

## Bonus points and prize strategy

Do not pursue bonuses until Stage 1 compliance and the core 40/30/30 story are strong.

- Public build content that explicitly states it was created for entering this hackathon: up to **+0.2**.
- A qualifying public social post using `#AllThingsAgenticHackathon`: up to **+0.2**.
- Successfully integrating additional Google AI models such as Gemma, Veo, or Lyria: **+0.2 each**, up to **+0.6** total.

Additional models must improve the product and be genuinely integrated; do not add ornamental calls that weaken reliability or narrative coherence.

The listed cash pool is $180,000. It includes a $50,000 Grand Prize; $20,000 for each core track; a $20,000 Startup Excellence award for an incorporated organization using a corporate email; two $10,000 Individual/Hobbyist awards; two $5,000 Best Architectural Design awards; two $5,000 Best Multimodal UX awards; and five $2,000 Honorable Mentions. Each project may win at most one prize. Decide the relevant entrant and secondary-prize strategy early, without diluting the core track.

## Operating principles for all agents

- Start with the smallest credible vertical slice that proves the chosen track and required stack.
- Make autonomy visible. Preserve an auditable trail of triggers, plans, tool calls, approvals, state changes, outputs, failures, and recovery without exposing private chain-of-thought or secrets.
- Keep humans in control for consequential actions through clear, risk-based approval boundaries; do not add approvals to harmless steps merely to simulate collaboration.
- Favor modularity, scoped tools, idempotent operations, explicit state transitions, timeouts, retries, and compensating actions over brittle prompt-only orchestration.
- Use synthetic or de-identified data by default unless real data is authorized and necessary.
- Secure public endpoints and set Google Cloud budgets, alerts, scale-to-zero behavior, and maximum-instance caps.
- Capture architecture, setup, evaluation, and deployment evidence as the system evolves.
- Test the exact demo path repeatedly from a clean environment and maintain a fallback that remains truthful.
- Before calling work complete, verify both engineering behavior and the submission checklist.
- Keep the action surface narrow: verified draft PR first, issue when a safe repair cannot be proven, and email only for configured escalation. Every external side effect must be idempotent, attributable to a run ID, and visible in the audit trail.
- Use scoped verdicts only: `SUPPORTED`, `CONTRADICTED`, `INCONCLUSIVE`, and `NOT_TESTED`. Never display a blanket `COMPLIANT` verdict.

## Locked implementation decisions

- Product name: **iPromise**.
- Core track: **Taskmaster**.
- Core claim/control: a source-grounded account-deletion promise tested against synthetic application and analytics records.
- Primary model: exact stable `gemini-3.5-flash` through Vertex AI at the `global` location, reconsidered only after a fixed documented evaluation. The model is not available in `us-central1`; keep the Cloud Run region and Vertex model location separate.
- Agent framework: Google ADK with typed, mostly deterministic graph nodes.
- Core Google Cloud services for the minimum: Cloud Run, Cloud Scheduler,
  Firestore, Secret Manager, Cloud Logging, and Vertex AI. Pub/Sub and Cloud
  Storage are target components only when the verifier/artifact flow genuinely
  uses them; never claim them from configuration alone.
- Judge-facing console: Next.js App Router on Cloud Run.
- Primary external action: a verified GitHub draft PR through a least-privilege GitHub App. GitHub Issue and email are safe secondary routes.
- Verification: Cloud Run Sandboxes only after a reliability gate, with a fail-closed Cloud Build backend under the same verifier contract.

## Decisions still to make

Do not silently invent these. Resolve them from product evidence or explicit user direction and record the decisions in durable project documentation:

- Entrant status: **solo individual**, confirmed by the entrant on **2026-08-18
  AEST**. The entrant confirms being above the local age of majority and having
  no employment conflict. Optimize the secondary-prize strategy for the
  Individual/Hobbyist awards, subject to a final full Official Rules eligibility
  check immediately before submission.
- Whether multimodality or an additional Google AI model genuinely strengthens the experience.
- Demo script, evaluation plan, and judge-access strategy.
- Cloud-credit request: **submitted 2026-08-17 AEST** through the current official
  Resources-page form for the Taskmaster track, using the exact Devpost account
  email. Do not submit another request unless Google/Devpost explicitly denies it.
  Approval, code receipt, redemption, and expiry evidence remain pending. The
  Codex task has an hourly Gmail monitor for the approval/code email; it must not
  reveal or redeem a code without the entrant's explicit request. The
  Google Cloud project `ipromise-agentic-2026` was linked to its billing account
  on **2026-08-18 AEST** and independently verified with the Google Cloud CLI.
