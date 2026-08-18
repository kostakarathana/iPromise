# iPromise threat model

Status: issue fallback and the locked verifier-to-draft-PR path are implemented and
tested locally with controlled external gateways. Live Cloud Build/GitHub receipts,
Model Armor, generalized repository repair, artifact storage, and email remain
pending and are not treated as current evidence.

## Scope and assumptions

The working minimum reads an authorized public or staging product surface,
operates on a synthetic reference SaaS, and binds an explicitly selected
repository. The current executable repair is narrower than repository connection:
it reads two allowlisted files from the fixed public entrant-owned iPromise
repository, accepts only one byte-exact remediation template, submits a fixed Cloud
Build program, and can publish those verified bytes as a draft PR when enabled. An
issue is the fallback. Neither current nor target workflow processes real customer
data in the primary demonstration, makes legal determinations, merges or deploys
code, or contacts customers.

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
3. **Current verifier gate:** only the fixed entrant-owned repository and exact
   approved candidate may execute; candidate data cannot select build commands,
   images, URLs, or destinations, and no application/GitHub secrets are mounted.
4. **Current PR gate:** no candidate reaches GitHub without a matching baseline
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
| Malicious repository content | Repository -> agent | Parse as untrusted during analysis; current executable path additionally requires the fixed entrant-owned public repository, full base SHA, allowlisted files, and exact preimage hashes | No repair/action |
| Secret exfiltration through candidate code | Verifier | Current candidate is byte-exact and contributes no commands; no runtime/GitHub secrets are mounted; dedicated build identity has only Logging write. Cloud Build still has outbound source/dependency access, so arbitrary generated code is prohibited | Cancel/reject; no PR |
| Destructive or broad patch | Model -> repository | Allowed-path policy, base/preimage hashes, file and diff limits, protected-file denial | Optional issue only |
| Candidate weakens its test | Patch -> verifier | The hidden control and fixed commands are outside patchable paths; the exact candidate test edit is supplemental and all candidate/diff hashes are locked | No PR |
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
| Future Sandbox Preview instability | Agent -> verifier | Keep the proven Cloud Build backend behind the same interface unless Sandbox passes repeated deployed reliability gates | Retain Cloud Build |

## Action-specific controls

The GitHub App is installed only on selected repositories, with short-lived,
down-scoped tokens and no Administration, Actions, Secrets, merge, or deployment
authority. The permissions design follows GitHub's
[official guidance](https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/choosing-permissions-for-a-github-app).

The current integration can create draft PRs or issues and uses evidence-only
language. PR publication is draft-only and accepts the verifier's exact bytes;
email remains a future opt-in route with only a finding summary and safe link. The
complete action policy is in
[ADR 0004](adr/0004-action-policy.md).

## Validation required before submission

- Adversarial source text cannot alter tools, destinations, or action policy.
- Metadata, localhost, private IP, and redirect-based SSRF cases are rejected.
- A patch touching protected files never reaches a verifier or remote branch.
- Failed, timed-out, missing, and stale evidence never produces a PR.
- Replaying the same event produces one run identity and one external action.
- The candidate cannot alter the fixed build program, images, commands, source URL,
  hidden control, or destination; the build mounts no runtime/GitHub secrets and its
  identity has only the documented Logging role. Record that Cloud Build dependency
  and source fetches use outbound network access.
- Email opt-out, allowlist, rate limit, and redaction tests pass if email ships.

Test results belong in [evaluation.md](evaluation.md) only after they are measured.
