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
- a least-privilege GitHub App configuration whose secrets are mounted only into
  the agent; and
- the judge console on Cloud Run, protected by a server-side access code.

Cloud Run, Firestore, and Cloud Scheduler are real infrastructure dependencies
once a deployment is verified. Pub/Sub, Cloud Storage, and the isolated verifier
remain explicit release gates in the target architecture; this script does not
pretend to provision integrations the current application does not use.

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

Do not use real customer data. Do not put secret values in command history,
environment files, build arguments, image layers, or source control.

## Prerequisites

- A dedicated Google Cloud project with billing enabled.
- An active `gcloud` login with permission to enable services, create service
  accounts, bind IAM roles, read secrets, build images, and deploy Cloud Run. The
  deployer must be able to act as the four runtime/trigger identities and the
  dedicated `ipromise-builder` build identity. Cloud Run source deployment also
  requires the deployer permissions represented by Cloud Run Source Developer
  and Service Usage Consumer.
- Vertex AI availability for the exact configured Gemini model in the selected
  region. Reverify model eligibility immediately before the final deployment.
- A GitHub App owned by the entrant. Record its numeric App ID, URL slug, and
  OAuth client ID. Grant only repository **Issues: read and write** plus the
  implicit Metadata read permission for the current issue-opening slice. Install
  it only on repositories the entrant is authorized to test.
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
export IPROMISE_GCP_LOCATION=us-central1
export IPROMISE_GITHUB_APP_ID=123456
export IPROMISE_GITHUB_APP_SLUG=your-ipromise-app-slug
export IPROMISE_GITHUB_APP_CLIENT_ID=Iv1.your-public-client-id

# Keep real issue creation off during the first deployment and connection check.
export IPROMISE_GITHUB_ACTIONS_ENABLED=false

./scripts/deploy-cloud-run --plan
```

Review the account, project, region, service names, and model. Apply requires a
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

The apply path enables only the APIs needed for this slice, creates four scoped
runtime/trigger service accounts plus a dedicated `ipromise-builder` service
account if absent, and grants only that build identity `roles/run.builder`. All
three source deployments explicitly use that identity; it receives no runtime
secret access. The script grants the agent Vertex AI and Firestore access, grants
secret access per runtime service, creates a Firestore Native database and regional
source-image repository if absent, deploys the three services with explicit
minimum/maximum-instance bounds, and creates the scheduled trigger. Scheduler
makes one initial delivery plus at most two retries after a timeout or non-2xx
response. The agent returns HTTP 503 plus `Retry-After: 300` while a scheduled run
remains retryable; terminal outcomes return 2xx. The first configured retry waits
at least 300 seconds so an abandoned five-minute execution or action lease can expire before
redelivery. Backoff is capped at 600 seconds and the whole retry window is capped
at 1,800 seconds.

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
idempotent issue side effect; it does not authorize merge or deployment.

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
     "$IPROMISE_DEPLOYED_DEMO_URL/healthz"
   curl --fail --silent --show-error \
     "$IPROMISE_DEPLOYED_AGENT_URL/healthz"
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
4. With actions explicitly enabled, cause the synthetic contradiction once and
   confirm exactly one evidence-backed GitHub issue appears in the selected
   repository. Run `./scripts/smoke-cloud "$IPROMISE_DEPLOYED_CONSOLE_URL"`.
   It proves that replaying one trigger returns the same run, then creates a
   distinct run for the unchanged finding and requires both runs to reconcile the
   same remote issue URL rather than duplicate it.
5. Confirm the same run ID in the console, GitHub issue marker, and a structured
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

6. Capture the console URL, Cloud Run service/revision screen, correlated log
   entry, and model/runtime receipt for the demo video and evidence matrix.
7. Run `pnpm verify` from a clean checkout and record the immutable commit SHA.

Until all relevant receipts exist, keep
[`implementation-status.md`](implementation-status.md) and
[`evidence-matrix.md`](evidence-matrix.md) marked pending.

## Rollback and cost controls

Cloud Run retains revisions. If a new revision fails verification, route traffic
back to the last verified revision with `gcloud run services update-traffic`; do
not describe the failed revision as production proof. The synthetic service and
console can scale to zero; Firestore preserves agent state across revisions.
Configure a project
budget and alerts before judge traffic, because budget alerts do not cap spend.

After judging, remove public access or delete only the three explicitly named
services after first preserving required submission evidence. Do not delete a
project or shared resources through a broad cleanup command.
