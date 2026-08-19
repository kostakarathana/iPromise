# iPromise synthetic reference SaaS

This is a deliberately flawed, ephemeral product used only to demonstrate iPromise safely. It contains no real customers or production integrations.

Its public `/privacy` page promises that account deletion removes a profile from the app and analytics system within 24 hours. The control uses a disclosed synthetic virtual clock: request at T0, deletion processor at T0+1h, and observation at T0+25h. That processor removes the app profile on time but intentionally leaves the analytics record behind. iPromise should observe and report that narrow, overdue contradiction. No real wall-clock waiting is represented.

## Run locally

Python 3.12 and [`uv` 0.12.1](https://docs.astral.sh/uv/) are required. The
commands assume a POSIX shell; use WSL on Windows.

```bash
cp .env.example .env
uv sync --extra dev --locked
IPROMISE_DEMO_TOKEN=replace-with-a-long-random-value \
  uv run uvicorn ipromise_demo.app:app --host 127.0.0.1 --port 8081
```

Open <http://127.0.0.1:8081/privacy>. The OpenAPI document is available at `/docs`.

## Synthetic control API

Every state-changing or inspection route is under `/v1/synthetic/` and requires `X-iPromise-Demo-Token`.

- `POST /v1/synthetic/accounts` seeds a uniquely labelled fake account and a disclosed virtual timeline from T0 through T0+25h.
- `POST /v1/synthetic/accounts/{id}/process-deletion` replays the deliberately faulty worker at virtual T0+1h.
- `GET /v1/synthetic/accounts/{id}/state` exposes the two approved stores to the audit control.
- `DELETE /v1/synthetic/accounts` clears all ephemeral fixtures for a clean local run.

The local fallback token exists only to make first-run development straightforward. Set a strong secret in every shared or cloud environment. Startup fails in `cloud` or `production` when the fallback token is used.

## Intentional limitation

The orphaned analytics record is an intentional, repeatable baseline fixture, not
an accidental defect. iPromise has verified and published the bounded repair as a
real draft PR; the vulnerable baseline remains on the default branch so a judge can
reproduce the same red-before/green-after workflow without fabricated state.
