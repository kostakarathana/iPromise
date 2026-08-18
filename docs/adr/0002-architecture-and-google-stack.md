# ADR 0002: Architecture and Google stack

- Status: Accepted; minimum implemented, deployment evidence pending
- Date: 2026-08-17

## Context

The final entry must use Gemini 3.5 or newer, a permitted Google agent framework,
Google Cloud infrastructure, and a meaningful workflow beyond chat. It must also
show Google Cloud deployment in the demo. The binding requirements remain the
[official rules](https://allthingsagentichackathon.devpost.com/rules).

## Decision

Use the following target stack:

| Concern | Choice |
| --- | --- |
| Agent workflow | Python 3.12 and Google ADK graph workflow |
| Model | `gemini-3.5-flash` through Vertex AI and the Google Gen AI SDK |
| Triggers | Cloud Scheduler calls the shared run service with Google OIDC; console uses the same service through its server proxy |
| Agent runtime | Cloud Run service with application-layer bearer/OIDC auth; private service-to-service networking is later hardening |
| Judge console | TypeScript/React web application on Cloud Run |
| Reference target | Small FastAPI synthetic SaaS on Cloud Run |
| Operational state | Firestore |
| Evidence artifacts | Typed Firestore run record; private Cloud Storage is a later verifier artifact gate |
| Capture | Exact server-rendered HTML text and content hash; browser capture is later hardening |
| Untrusted-text screening | Strict model schema and deterministic grounding; Model Armor remains planned defense in depth |
| Repair verification | Integrated Cloud Build backend with fixed inline program and exact-template candidate; Cloud Run Sandbox remains a later reliability option |
| Repository action | Least-privilege GitHub App; exact-byte draft PR primary, reconciled issue fallback |
| Secrets | Secret Manager and per-service identities |
| Telemetry | Structured Cloud Logging receipts; OpenTelemetry/Cloud Trace remains later hardening |

The model identifier must be rechecked against the live eligible model list
before dependency lock and submission. Relevant primary documentation includes
[Gemini 3.5 Flash](https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash),
[ADK graphs](https://adk.dev/graphs/),
[Pub/Sub push delivery](https://cloud.google.com/pubsub/docs/push), and
[Cloud Run code execution](https://cloud.google.com/run/docs/code-execution).
[Model Armor](https://cloud.google.com/security/products/model-armor) is a
supplementary screen for untrusted content, not a permissions or verdict boundary.

## Workflow topology

Cloud Scheduler calls the agent with a Google-signed OIDC token. Its job name and
scheduled timestamp derive the run's idempotency key. The console calls the same
run route through a server-side bearer-authenticated proxy. The ADK compiler node
handles the semantic claim; deterministic code owns capture, grounding, control
selection, probes, verdicts, and actions. Every material transition is
checkpointed in Firestore. Pub/Sub and Cloud Storage are deferred until they
support a concrete verifier/artifact need.

The scheduled and manual paths intentionally share the same event contract so the
demo does not bypass the autonomous implementation.

## Verifier decision

The implemented `VerifierBackend` uses Cloud Build because it has a stable service
contract and durable build/log receipt. Cloud Run Sandboxes remain a later option
only after a repeated reliability gate and would plug into the same interface
without changing action policy. They are not part of the current implementation or
submission evidence.

Cloud Build is a clean, separately identified execution environment, but not a
no-egress sandbox: its trusted steps clone one pinned public repository commit and
install dependencies from the locked Python environment. The candidate contributes
no commands, images, URLs, or destinations. A deterministic template admits only
two exact files and binds their preimage, candidate, diff, base, and source hashes;
the hidden control and step program remain outside candidate authority.

## IAM and network policy

- The public console cannot invoke privileged tools directly.
- Cloud Scheduler uses an OIDC token with an exact audience and dedicated
  allowlisted service-account email.
- The console proxy uses a separate high-entropy bearer from Secret Manager.
- Each Cloud Run service has its own service account.
- The minimum agent receives only Firestore and Vertex project roles plus
  secret-level access to its exact Secret Manager entries. Storage permissions
  are deferred until the verifier artifact path exists.
- The verifier receives no GitHub token, model credential, runtime secret, Firestore
  role, or production-data permission. Its dedicated service account has only
  `roles/logging.logWriter`; the agent receives only create/get/update access to
  Cloud Build and `actAs` on that identity.
- Cloud Build has outbound dependency/source access as described above. A future
  no-egress sandbox would be a separate, explicitly evidenced hardening step.
- The GitHub App is installed only on selected repositories. The verified-PR path
  requires **Contents: read/write**, **Pull requests: read/write**, **Issues:
  read/write** for fallback, and implicit Metadata read. The App never needs Actions,
  Workflows, Administration, Secrets, merge, or deployment authority.
  Installation tokens are short-lived and down-scoped. See GitHub's primary documentation on
  [choosing permissions](https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/choosing-permissions-for-a-github-app)
  and [installation tokens](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-an-installation-access-token-for-a-github-app).

## Alternatives not selected

- A chat-first UI does not prove autonomous Taskmaster value.
- A multi-agent fleet adds coordination cost without improving the initial
  deletion-control workflow.
- Kubernetes, Cloud SQL, and a vector database add operational surface without
  improving the judging proof.
- Local-only execution cannot satisfy the cloud-deployment requirement.
- Terraform is deferred until the core cloud path is stable; checked-in,
  idempotent deployment scripts and manifests provide the initial reproducibility.

## Consequences

This architecture adds one event service and explicit state transitions, but it
makes retries, idempotency, cloud proof, and background completion visible. The
console is a Promise Ledger and evidence viewer, not a conversational interface.
