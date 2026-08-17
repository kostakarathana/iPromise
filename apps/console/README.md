# iPromise console

The judge-facing Promise Ledger for iPromise. It shows the exact customer
promise, its narrowly scoped verdict, evidence from enumerated systems, the
observable agent timeline, and the single action selected by policy.

There is no chat interface. The primary workflow is **Run audit → evidence →
verified draft PR**. GitHub issues and owner email are explicit fallback routes,
not actions that fire alongside a successful repair.

## Run locally

Requirements: Node.js 24 and pnpm 11.

```bash
pnpm install
pnpm dev
```

Open <http://localhost:3000>. The agent conventionally runs on port 8080 and
the synthetic reference SaaS on port 8081. With no environment variables, the app runs a
clearly labeled **local snapshot with sample data**. No source capture, control,
agent, or model runs in that snapshot. It reports
`runtime.modelInvocationAttempted: false` and `runtime.modelInvoked: false`, and
no pull request, issue, or email is performed.

## Connect the agent

Copy `.env.example` to `.env.local` and set:

```bash
IPROMISE_AGENT_URL=http://localhost:8080
IPROMISE_AGENT_TOKEN=
```

The server-only console proxy calls:

- `GET {IPROMISE_AGENT_URL}/v1/runs/latest`
- `POST {IPROMISE_AGENT_URL}/v1/runs`

Both endpoints return the repository's canonical
`contracts/audit-run.schema.json` `AuditRun` object directly. The optional
token is sent as a bearer token from the server and is never exposed to the
browser.

Console routes:

- `GET /api/audit` — latest connected run or the disclosed static preview
- `POST /api/audit` — start a connected run or replay only the static preview
- `GET /api/health` — process health and proxy configuration mode

## Verify

```bash
pnpm lint
pnpm typecheck
pnpm test
pnpm build
```

The tests enforce the canonical claim wording, the disclosed synthetic
virtual-clock replay (+1h worker and +25h observation), scoped verdict language,
static-versus-connected provenance, cloud-proof gating, and the exactly-one-route
action policy.

## Container and Cloud Run

The Next.js build uses standalone output and listens on Cloud Run's `PORT`
(8080 in the image).

```bash
docker build -t ipromise-console .
docker run --rm -p 8080:8080 ipromise-console
```

Do not deploy this directory with an ad-hoc public `gcloud run deploy` command.
Cloud Run sets `K_SERVICE`, and the console deliberately fails closed there
unless a strong `IPROMISE_CONSOLE_ACCESS_TOKEN` is mounted. The repository's
guarded deployment provisions the dedicated service account, pins numeric
Secret Manager versions, injects the agent URL/token, sets instance bounds, and
creates the rest of the eligible Google Cloud slice:

```bash
cd ../..
./scripts/deploy-cloud-run --plan
# After reviewing the plan and setting the documented confirmation variable:
./scripts/deploy-cloud-run --apply
```

Follow [`docs/deployment.md`](../../docs/deployment.md) for prerequisites,
GitHub App settings, private judge credentials, verification, and rollback.
