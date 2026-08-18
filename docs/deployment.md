# Minimum Google Cloud deployment

Status: deployment procedure only. The existence of these files is **not** proof
that iPromise has been deployed, invoked Gemini, or completed an external action.
Those claims require the receipts listed below.

This procedure packages and deploys the smallest eligible Google Cloud slice:

- the synthetic reference SaaS on Cloud Run;
- the audit agent on Cloud Run with Google ADK 2.7.0 and
  `gemini-3.5-flash` configured through Vertex AI;
- Firestore-backed audit, execution/action lease, OAuth, repository-selection,
  finding-receipt, and idempotency state;
- a six-hour Cloud Scheduler job authenticated with a dedicated Google OIDC
  identity, with two bounded redeliveries after a retryable failure;
- an explicitly enabled red-before/green-after verifier on Cloud Build,
  executed as a dedicated identity with no runtime secrets or production-data
  permissions;
- a least-privilege GitHub App configuration whose secrets are mounted only into
  the agent; and
- the judge console on Cloud Run, protected by a server-side access code.

Cloud Run, Firestore, Cloud Scheduler, and Cloud Build are real infrastructure
dependencies once their deployed receipts are verified. Pub/Sub, Cloud Storage,
and Cloud Run Sandboxes remain explicit target-architecture gates; this script
does not pretend to provision integrations the current application does not use.
The verifier backend defaults to `disabled` until the integrated workflow and
permissions have passed the release gates below; configuration is not execution
proof.

## Security boundary for this minimum

The synthetic SaaS exposes its policy page publicly. Its stateful control routes
still require the shared synthetic-only token. The console has a public network
URL so judges can reach it, but its UI, audit mutations, and GitHub integration
routes require a signed session created from a separate high-entropy access code.
The access code is injected from Secret Manager and must be supplied only in the
private Devpost testing instructions, never in the repository, video, or a public
post.

The current agent is reachable at the Cloud Run network layer because the console
does not yet mint Google service-to-service identity tokens. Console requests use
a separate high-entropy bearer token injected from Secret Manager. Scheduler
requests use a Google-signed OIDC token whose audience and service-account email
are both verified by the agent. This is an interim deployment boundary, not the
final private-agent architecture.

The agent may submit, read, and cancel Cloud Build verifier runs through a
project-local custom role containing only `cloudbuild.builds.create`,
`cloudbuild.builds.get`, and `cloudbuild.builds.update`. It may act as only the
dedicated `ipromise-verifier` identity for this purpose. That build identity has
only `roles/logging.logWriter`: it receives no Secret Manager, Firestore, Vertex
AI, GitHub, Artifact Registry, or Cloud Run role. The trusted inline build fetches
one pinned commit from the public iPromise repository and writes its bounded
receipt to Cloud Logging. Candidate content cannot provide verifier commands or
the trusted out-of-band control; it can alter only the two exact source/test
files admitted by the locked remediation template.

Cloud Build has outbound network access for the pinned public source clone and
locked dependency installation. This boundary is not a no-egress sandbox and must
not be generalized to arbitrary generated code or arbitrary repositories. Its
current safety case depends on the fixed entrant-owned public repository, trusted
inline step program, exact-template hashes, no candidate-supplied commands, no
mounted runtime/GitHub secrets, and the minimal build identity above.

Do not use real customer data. Do not put secret values in command history,
environment files, build arguments, image layers, or source control.

## Prerequisites

- A dedicated Google Cloud project with billing enabled.
- An active `gcloud` login with permission to enable services, create service
  accounts, bind IAM roles, read secrets, build images, and deploy Cloud Run. The
  deployer must be able to create and bind the four runtime/trigger identities,
  the dedicated `ipromise-builder` source-build identity, and—when the verifier
  is enabled—the dedicated `ipromise-verifier` identity and project-local verifier
  controller role.
  Cloud Run source deployment also requires the deployer permissions represented
  by Cloud Run Source Developer and Service Usage Consumer.
- Vertex AI availability for the exact configured Gemini model in the selected
  region. Reverify model eligibility immediately before the final deployment.
- A GitHub App owned by the entrant. Record its numeric App ID, URL slug, and
  OAuth client ID. For the winning path grant repository **Contents: read and
  write**, **Pull requests: read and write**, **Issues: read and write** for the
  fallback, plus implicit Metadata read. Do not grant Actions, Workflows,
  Administration, Secrets, merge, or deployment authority. Install it only on the
  entrant-owned demonstration repository and keep actions disabled until the live
  permission review is complete.
- Five distinct Secret Manager secrets with enabled versions:
  `ipromise-demo-token`, `ipromise-agent-api-token`,
  `ipromise-console-access-code`, `ipromise-github-client-secret`, and
  `ipromise-github-private-key`.

Create the secret containers, then stream random values directly into Secret
Manager. These examples do not retain or print the generated values:

```bash
export IPROMISE_GCP_PROJECT=your-dedicated-project-id

# Secret containers must exist before the guarded deployment can pin versions.
gcloud services enable secretmanager.googleapis.com \
  --project "$IPROMISE_GCP_PROJECT"

gcloud secrets create ipromise-demo-token \
  --project "$IPROMISE_GCP_PROJECT" \
  --replication-policy automatic
openssl rand -hex 32 | tr -d '\n' | gcloud secrets versions add ipromise-demo-token \
  --project "$IPROMISE_GCP_PROJECT" \
  --data-file=-

gcloud secrets create ipromise-agent-api-token \
  --project "$IPROMISE_GCP_PROJECT" \
  --replication-policy automatic
openssl rand -hex 32 | tr -d '\n' | gcloud secrets versions add ipromise-agent-api-token \
  --project "$IPROMISE_GCP_PROJECT" \
  --data-file=-

gcloud secrets create ipromise-console-access-code \
  --project "$IPROMISE_GCP_PROJECT" \
  --replication-policy automatic
# First create and save a random value of 32 to 256 characters in a password
# manager. This hidden prompt streams the saved value without putting it in shell
# history or printing it.
python3 -c 'import getpass, sys; sys.stdout.write(getpass.getpass("Paste console access code: "))' \
  | gcloud secrets versions add ipromise-console-access-code \
      --project "$IPROMISE_GCP_PROJECT" \
      --data-file=-

gcloud secrets create ipromise-github-client-secret \
  --project "$IPROMISE_GCP_PROJECT" \
  --replication-policy automatic
python3 -c 'import getpass, sys; sys.stdout.write(getpass.getpass("GitHub client secret: "))' \
  | gcloud secrets versions add ipromise-github-client-secret \
      --project "$IPROMISE_GCP_PROJECT" \
      --data-file=-

gcloud secrets create ipromise-github-private-key \
  --project "$IPROMISE_GCP_PROJECT" \
  --replication-policy automatic
gcloud secrets versions add ipromise-github-private-key \
  --project "$IPROMISE_GCP_PROJECT" \
  --data-file=/secure/path/to-the-downloaded-github-app-private-key.pem
```

If a container already exists, skip its `secrets create` command and add a new
version. Keep the downloaded private-key file outside the repository with owner-
only permissions. Never reuse any value for another system. The console access
code is the only user-facing credential in this set; keep it in a password manager
and share it only with authorized evaluators.

The GitHub App uses two browser redirects. After the console is first deployed,
set these exact URLs:

```text
Setup URL:    https://CONSOLE_HOST/api/integrations/github/setup
Callback URL: https://CONSOLE_HOST/api/integrations/github/callback
```

The backend independently validates single-use state, completes user OAuth, and
verifies that the signed-in user can access the claimed installation before it
lists repositories. Do not use a generic wildcard callback. Leave **Request user
authorization (OAuth) during installation** disabled: this implementation first
uses the Setup URL and then starts its own OAuth flow to the Callback URL.

## Plan, then apply

The script defaults to no mode and will not mutate anything. `--plan` performs
authenticated read-only checks and identifies the exact project and resources:

```bash
export IPROMISE_GCP_PROJECT=your-dedicated-project-id
export IPROMISE_GCP_REGION=us-central1
# Vertex inference is independent from the Cloud Run region. Gemini 3.5 Flash
# Standard PayGo supports global, us, or eu; this release uses global.
export IPROMISE_GCP_LOCATION=global
export IPROMISE_VERIFIER_BACKEND=disabled
export IPROMISE_CLOUD_BUILD_LOCATION=australia-southeast1
export IPROMISE_GITHUB_APP_ID=123456
export IPROMISE_GITHUB_APP_SLUG=your-ipromise-app-slug
export IPROMISE_GITHUB_APP_CLIENT_ID=Iv1.your-public-client-id

# Keep real issue creation off during the first deployment and connection check.
export IPROMISE_GITHUB_ACTIONS_ENABLED=false

./scripts/deploy-cloud-run --plan
```

Review the account, project, regions, service identities, verifier backend, and
model. `IPROMISE_CLOUD_BUILD_PROJECT` and
`IPROMISE_CLOUD_BUILD_SERVICE_ACCOUNT` are deliberately not deployment inputs:
the script pins them to the selected project and its dedicated
`ipromise-verifier` identity. The default `disabled` backend is fail-closed and
cannot submit verifier builds. Change it to `cloud-build` only after reviewing the
integrated workflow, IAM diff, source commit, and cost boundary. Apply requires a
second variable that exactly matches the target project:

```bash
export IPROMISE_DEPLOY_CONFIRM="$IPROMISE_GCP_PROJECT"
./scripts/deploy-cloud-run --apply
```

Before either mode performs project checks, the script asks `gcloud` for the
exact source-upload manifest of all three services and rejects environment
files, private keys, dependency trees, build output, tests, and caches. Apply
also refuses a dirty or untracked working tree. Commit the reviewed source first:
every Cloud Run revision is labeled `source-commit` with that exact full Git SHA.
This makes the recorded cloud run traceable to the repository artifact.

The apply path enables only the APIs needed for this slice, including Cloud Build.
It creates four scoped runtime/trigger service accounts plus the separate
`ipromise-builder` identity if absent. When and only when the verifier backend is
explicitly `cloud-build`, it also creates `ipromise-verifier` and the custom
controller role. The source builder receives only `roles/run.builder`; all three
source deployments explicitly use it, and it receives no runtime secret access.
The verifier receives only `roles/logging.logWriter`. The agent receives the
three-permission custom verifier controller role and
`roles/iam.serviceAccountUser` only on that verifier identity.
The script grants the agent Vertex AI and Firestore access, grants secret access
per runtime service, creates a Firestore Native database and regional source-image
repository if absent, deploys the three services with explicit minimum/maximum-
instance bounds, and creates the scheduled trigger.

The synchronous MVP allows 900 seconds through both the console/agent Cloud Run
requests and the Scheduler attempt, covering the compiler's bounded 120 seconds
plus the verifier's bounded 750-second overall deadline. The durable run lease is
1,200 seconds, deliberately longer than the HTTP envelope, while the narrower
action lease remains 900 seconds.
Scheduler makes one initial delivery plus at most two retries after a timeout or
non-2xx response. The agent returns HTTP 503 plus `Retry-After: 1200` while a
scheduled run remains retryable; terminal outcomes return 2xx. The first
configured retry waits at least 1,200 seconds so an abandoned run lease expires
before redelivery. Backoff is capped at 1,800 seconds and the whole retry window
is capped at 6,000 seconds, leaving room for both bounded retries.

If the project already has a `(default)` database, apply verifies that its type is
`FIRESTORE_NATIVE` and fails before deployment for Datastore mode. The database
mode cannot be treated as interchangeable with the Firestore client used here.

Apply resolves the newest enabled numeric version of each of the five secrets,
prints only the secret names and version numbers, and pins those numeric versions
into the Cloud Run revisions. It never reads or prints secret payloads and never
changes the active `gcloud` project. It also refuses to start if any payload is
present as `IPROMISE_DEMO_TOKEN`, `IPROMISE_AGENT_API_TOKEN`,
`IPROMISE_CONSOLE_ACCESS_TOKEN`, `IPROMISE_GITHUB_APP_CLIENT_SECRET`, or
`IPROMISE_GITHUB_APP_PRIVATE_KEY` in the deployment shell; unset local-development
values before running it.

Pinning is deliberate: adding a new Secret Manager version does not silently
change an existing revision. To rotate a value, add and enable the new version,
run `--plan`, deliberately run `--apply`, verify the new revision, and retain the
previous version until the rollback window closes.

The service URLs create a small first-deployment ordering dependency. On the first
apply, the agent receives only its non-GitHub base configuration, the console is
deployed with the new stable agent URL, and the agent is then activated with the
final console origin, GitHub settings, and Scheduler audience. GitHub actions are
off and no Scheduler job exists during that bootstrap. On later applies, the
script discovers both stable service URLs first and deploys the agent once with
its complete configuration, avoiding an intermediate revision that drops
GitHub/Scheduler settings. If a verified custom domain fronts the console, export
that HTTPS origin as `IPROMISE_CONSOLE_BASE_URL`; otherwise the script uses the
emitted `.run.app` origin.

Keep `IPROMISE_GITHUB_ACTIONS_ENABLED=false` during an initial connection-only
check. After the App permissions and intended repository have been reviewed, set
it to `true`, re-run `--plan`, and deliberately re-run `--apply`. That update
creates a new agent revision. The verified installation and selected repository
remain in Firestore. Enabling this flag authorizes the agent's bounded,
idempotent draft-PR or issue side effect; it does not authorize merge or deployment.

The verifier backend and GitHub action flag are independent. A first deployment
may use `IPROMISE_VERIFIER_BACKEND=cloud-build` while keeping
`IPROMISE_GITHUB_ACTIONS_ENABLED=false`: it can produce a real Cloud Build verifier
receipt without creating a branch or pull request. Enabling GitHub actions is a
separate, explicit deployment review.

## Judge access credential

Submit the emitted console URL and the saved console access code in Devpost's
private testing instructions. Do not put the code in the public description,
repository, screenshots, demo narration, or video. Test the credential in a clean
private browser session before submission, and keep the same pinned secret version
available through judging. If rotation is unavoidable, redeploy and update the
private testing instructions immediately.

The access code creates an HttpOnly, SameSite session cookie. It protects both the
ledger and the server routes that can run audits or change the selected GitHub
repository. A successful Cloud Run health response alone does not bypass this
gate.

## Verification gates

Do not mark deployment, ADK, or Gemini as verified merely because `gcloud run
deploy` returned successfully.

1. Check the exact health endpoints, then open the console URL in a clean private
   browser and authenticate with the saved access code:

   ```bash
   export IPROMISE_DEPLOYED_CONSOLE_URL=https://CONSOLE_HOST
   export IPROMISE_DEPLOYED_AGENT_URL=https://AGENT_HOST
   export IPROMISE_DEPLOYED_DEMO_URL=https://DEMO_HOST

   curl --fail --silent --show-error \
     "$IPROMISE_DEPLOYED_DEMO_URL/health"
   curl --fail --silent --show-error \
     "$IPROMISE_DEPLOYED_AGENT_URL/health"
   curl --fail --silent --show-error \
     "$IPROMISE_DEPLOYED_CONSOLE_URL/api/health"
   ```
   The console validates its Cloud Run access secret, agent origin, and agent
   bearer at server startup; the health route returns 503 for incomplete runtime
   configuration rather than reporting a broken revision as healthy.
2. Run one audit through the console. Confirm the returned runtime receipt names
   the exact Cloud Run revision, Google ADK, the exact Gemini model, and a real
   successful model invocation. Configuration alone is not model proof.
3. Connect the GitHub App from the console. Confirm the browser returns only to
   the exact configured HTTPS callback, the accessible repository list matches
   the App installation, and an archived repository cannot be selected.
4. Cause the synthetic contradiction and require a Cloud Build receipt with the
   exact public repository URL, full base SHA, candidate diff hash, seven trusted
   step results, and durable HTTPS log URL. Confirm the build ran as
   `ipromise-verifier@PROJECT_ID.iam.gserviceaccount.com` and that the receipt
   reports expected red-before, green-after, regression pass, and byte-exact
   candidate verification. Confirm the console receipt shows the same build ID and
   durable log link. A configured backend or a submitted build alone is not
   verification proof.
5. With actions explicitly enabled, cause the synthetic contradiction once and
   confirm exactly one evidence-backed draft GitHub pull request appears in the
   selected repository. Run `./scripts/smoke-cloud "$IPROMISE_DEPLOYED_CONSOLE_URL"`.
   Replay the same trigger/idempotency key and require it to return the same run
   and remote pull-request receipt without creating a duplicate. The smoke command
   also starts a distinct run for the unchanged exact repair and requires the same
   PR URL, complete verifier receipt, and no second remote action. Local tests cover
   this reconciliation; the command is the required deployed proof.
6. Confirm the same run ID in the console, GitHub pull-request marker, Cloud Build
   receipt, and a structured
   application receipt in Cloud Logging. Set the exact ID returned by the audit;
   a Cloud Run request-access log without the application receipt is not proof:

   ```bash
   export IPROMISE_VERIFIED_RUN_ID=run_replace_with_exact_id
   ./scripts/gcloud run services logs read ipromise-agent \
     --project "$IPROMISE_GCP_PROJECT" \
     --region "$IPROMISE_GCP_REGION" \
     --log-filter="textPayload:\"$IPROMISE_VERIFIED_RUN_ID\" OR jsonPayload.runId=\"$IPROMISE_VERIFIED_RUN_ID\"" \
     --limit 100
   ```

   Require an `ipromise.audit.receipt` record containing that run ID, the exact
   Cloud Run revision, `modelInvoked: true`, the eligible Gemini model, and the
   final action state. If the application receipt is absent or only infrastructure
   access logs appear, logging proof is still pending.

7. Capture the console URL, Cloud Run service/revision screen, correlated agent
   and Cloud Build log entries, and model/runtime receipt for the demo video and
   evidence matrix.
8. Run `pnpm verify` from a clean checkout and record the immutable commit SHA.

Until all relevant receipts exist, keep
[`implementation-status.md`](implementation-status.md) and
[`evidence-matrix.md`](evidence-matrix.md) marked pending.

## Rollback and cost controls

Cloud Run retains revisions. If a new revision fails verification, route traffic
back to the last verified revision with `gcloud run services update-traffic`; do
not describe the failed revision as production proof. The synthetic service and
console can scale to zero; Firestore preserves agent state across revisions.
Cloud Build verifier runs do not scale to zero in the same sense: every submitted
verification consumes build resources until it terminates or reaches the bounded
deadline. Keep Scheduler paused outside deliberate testing until cost and
idempotency receipts are proven. Configure a project budget and alerts before
judge traffic, because budget alerts do not cap spend.

After judging, remove public access or delete only the three explicitly named
services after first preserving required submission evidence. Do not delete a
project or shared resources through a broad cleanup command.
