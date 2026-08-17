# iPromise threat model

Status: minimum issue-opening controls are partially implemented and locally
tested. Verifier, draft-PR, artifact-storage, Model Armor, and email controls are
explicit targets and are not treated as current evidence.

## Scope and assumptions

The working minimum reads an authorized public or staging product surface,
operates on a synthetic reference SaaS, binds an explicitly selected repository,
and may create one evidence-backed GitHub issue when enabled. It does not yet read
repository contents or execute candidate code. Isolated candidate verification,
exact-tree draft PRs, and opted-in email are target capabilities. Neither current
nor target workflow processes real customer data in the primary demonstration,
makes legal determinations, merges code, deploys code, or contacts customers.

## Assets

- Repository code, branch integrity, and GitHub App credentials
- GCP project, service identities, quotas, and billing
- Captured promise sources and evidence artifacts
- Synthetic fixture identifiers and operational state
- Finding/verifier integrity and action idempotency
- Notification recipient privacy and product reputation

## Security invariants

1. Untrusted page or repository text cannot grant itself a tool or permission.
2. Gemini cannot compute the final evidence verdict or authorize an external
   action.
3. **Target verifier gate:** generated code cannot access network, cloud metadata,
   or credentials.
4. **Target PR gate:** no candidate reaches GitHub without a matching baseline
   failure, candidate pass, immutable manifest, and current base SHA.
5. Duplicate delivery creates one logical run execution and at most one external
   action per finding intent.
6. Missing, stale, or unknown evidence cannot produce `SUPPORTED`.
7. Secrets and private chain-of-thought never appear in prompts, artifacts, logs,
   PRs, issues, or email.

## Threats and planned controls

| Threat | Boundary | Planned control | Failure mode |
| --- | --- | --- | --- |
| Prompt injection in policy/UI text | Source -> model | Treat source as quoted data, Model Armor screening, strict schemas, fixed system policy, no model credentials/tools | Reject or abstain |
| SSRF or metadata access | Capture | Scheme/host allowlist, DNS/IP validation before and after redirects, block private/link-local/metadata ranges | `FAILED_SAFE` |
| Malicious repository content | Repository -> agent | Parse as untrusted data; fixed tool catalog; never execute during analysis | No repair/action |
| Secret exfiltration through generated code | Verifier | No egress, no inherited environment, no mounted secrets, redacted logs | Kill sandbox; no PR |
| Destructive or broad patch | Model -> repository | Allowed-path policy, base/preimage hashes, file and diff limits, protected-file denial | Optional issue only |
| Candidate weakens its test | Patch -> verifier | Trusted control and harness are outside patchable paths; candidate tests are supplemental | No PR |
| False success from a missing configured probe | Probe -> verdict | Required completeness across the current two-store adapter and a deterministic verdict; versioned configurable inventory is a target | `INCONCLUSIVE` |
| Time-of-check/time-of-use branch drift | Verifier -> GitHub | Re-read base SHA; publish exact tested tree; regenerate on mismatch | Stale candidate |
| Duplicate run or PR/issue/email | Event/retry -> workflow/integrations | Stable trigger key, transactional execution/action leases, stable synthetic fixture identity, hidden markers, remote reconciliation | Reuse existing run/action |
| Partial GitHub timeout | Agent -> GitHub | Query by marker/branch before retry; never blindly recreate | Reconcile state |
| Email data leakage or spam | Agent -> provider | Off by default, recipient allowlist, fixed minimal templates, cooldown/digest, no raw evidence | Durable finding only |
| Unauthorized target testing | Project configuration | Explicit repository, URL, staging target, control, and action authorization | Block run |
| Evidence tampering | Storage/UI | Content hashes, immutable object naming, signed metadata, least-privilege write path | Mark unverifiable |
| PII retained in artifacts | Capture/storage | Synthetic data by default, minimization/redaction, TTL lifecycle, private bucket | Quarantine/delete artifact |
| Resource exhaustion or cost attack | Public trigger/cloud | Authentication, quotas, concurrency one, max instances, timeouts, budgets | Throttle/fail safely |
| Supply-chain compromise | Build/runtime | Lockfiles, dependency scanning, trusted base images, pinned build inputs | Block release |
| Sandbox Preview instability | Agent -> verifier | Repeated release gate and Cloud Build fallback behind the same interface | Switch backend |

## Action-specific controls

The GitHub App is installed only on selected repositories, with short-lived,
down-scoped tokens and no Administration, Actions, Secrets, merge, or deployment
authority. The permissions design follows GitHub's
[official guidance](https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/choosing-permissions-for-a-github-app).

The current integration can create issues and uses evidence-only language. Future
PRs will be drafts, and future email will be opt-in with only a finding summary
and safe link. The complete action policy is in
[ADR 0004](adr/0004-action-policy.md).

## Validation required before submission

- Adversarial source text cannot alter tools, destinations, or action policy.
- Metadata, localhost, private IP, and redirect-based SSRF cases are rejected.
- A patch touching protected files never reaches a verifier or remote branch.
- Failed, timed-out, missing, and stale evidence never produces a PR.
- Replaying the same event produces one run identity and one external action.
- Candidate processes cannot observe repository/GCP/GitHub secrets or use egress.
- Email opt-out, allowlist, rate limit, and redaction tests pass if email ships.

Test results belong in [evaluation.md](evaluation.md) only after they are measured.
