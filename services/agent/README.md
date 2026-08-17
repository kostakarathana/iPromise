# iPromise agent service

The service converts one exact, customer-facing deletion promise into an executable control. It captures the source, grounds the quote, seeds a synthetic canary, calls the real reference deletion API, probes the approved stores, calculates a scoped verdict, and plans the safest response.

This MVP can perform one real GitHub side effect: an evidence-backed issue in a
repository verified through the GitHub App installation flow. It does so only when
actions are explicitly enabled. A draft pull request remains blocked until an
isolated verifier can truthfully prove fail-before/pass-after against an exact
repository tree. Email is off.

## Run the first MVP

Start `apps/demo_saas` on port 8081 first. Then, using Python 3.12:

```bash
cp .env.example .env
uv sync --extra dev --extra google --extra github
IPROMISE_MODE=demonstration \
IPROMISE_COMPILER=deterministic \
IPROMISE_DEMO_BASE_URL=http://127.0.0.1:8081 \
IPROMISE_DEMO_TOKEN=replace-with-the-same-long-random-value-as-demo-saas \
  uv run uvicorn ipromise_agent.app:app --host 127.0.0.1 --port 8080
```

Run an audit:

```bash
curl -sS -X POST http://127.0.0.1:8080/v1/runs \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: local-demo-0001' \
  -d '{"trigger":"manual","source":"console"}'
```

API routes:

- `GET /healthz`
- `POST /v1/runs` creates and completes an audit synchronously for the MVP.
- `GET /v1/runs` lists runs newest first.
- `GET /v1/runs/latest` returns the newest run.
- `GET /v1/runs/{id}` returns one run.
- `POST /v1/triggers/scheduled` accepts an authenticated Cloud Scheduler delivery.
- `GET /v1/integrations/github` returns connection and repository status.
- `GET /v1/integrations/github/install-url` begins GitHub App installation.
- `POST /v1/integrations/github/oauth-url` validates setup state and begins
  user OAuth with PKCE.
- `POST /v1/integrations/github/oauth/callback` verifies the installation owner.
- `PUT /v1/integrations/github/repository` selects only a repository returned by
  the verified installation.

Repeated requests with the same `Idempotency-Key` return the same run. A
run-execution lease serializes overlapping workers, and the synthetic account ID
is stable for that run, so retries cannot create a second logical fixture. Local
state is process memory. Cloud mode requires Firestore for run checkpoints,
execution/action leases, OAuth state, repository selection, and idempotency.

## Truthful model provenance

The default configuration is explicitly `demonstration` + `deterministic`. Responses say `runtime.modelInvocationAttempted: false`, `runtime.modelInvoked: false`, `runtime.model: null`, and disclose the limitation. That adapter only reads the reference page's explicit synthetic claim marker and is rejected outside demonstration mode.

For the real Vertex AI path:

```bash
uv sync --extra google
export IPROMISE_MODE=cloud
export IPROMISE_COMPILER=adk
export GOOGLE_GENAI_USE_VERTEXAI=TRUE
export GOOGLE_CLOUD_PROJECT=your-dedicated-ipromise-project
export GOOGLE_CLOUD_LOCATION=us-central1
export IPROMISE_GEMINI_MODEL=gemini-3.5-flash
export IPROMISE_DEMO_BASE_URL=https://your-synthetic-service.run.app
export IPROMISE_DEMO_TOKEN=replace-with-a-secret-manager-value
export IPROMISE_AGENT_API_TOKEN=replace-with-an-independent-long-secret
export IPROMISE_STATE_BACKEND=firestore
```

Cloud mode builds a typed Google ADK 2 graph (`START → promise_compiler`) and runs it through ADK's `InMemoryRunner`. Gemini receives captured visible text and must return a typed claim. Deterministic code still verifies the returned exact quote, binds the control, gathers evidence, calculates the verdict, and gates actions.

If ADK, ADC, Vertex configuration, or the model response is unavailable, the run fails safely or retryably. It never silently substitutes the deterministic adapter.

## Verdict semantics

- `SUPPORTED`: every required probe passed for this synthetic account and approved two-store scope.
- `CONTRADICTED`: at least one required probe returned explicit contradictory evidence.
- `INCONCLUSIVE`: required evidence was missing, stale, or unavailable.
- `NOT_TESTED`: no approved executable control was bound.

These are technical control results, never a legal-compliance conclusion. The action planner cannot mark a draft PR `READY` unless an isolated receipt proves the baseline failure, candidate success, regression success, and exact-tree verification.

## Tests

```bash
uv sync --extra dev --extra google --extra github
uv run --extra dev --extra google --extra github pytest
```

Tests cover the real synthetic contradiction, missing-evidence abstention, known
late workers, exact-quote grounding, idempotency, strict API compatibility, model
provenance, action safety, Cloud Scheduler deduplication, GitHub OAuth/PKCE and
repository authorization, one-repository token scoping, one issue side effect, cloud
configuration, and ADK graph construction without invoking Gemini.
