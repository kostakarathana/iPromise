# ADR 0004: PR-first action policy

- Status: Accepted; email transport provider not yet selected
- Date: 2026-08-17

## Context

iPromise should be dead simple: when evidence justifies action, it normally pushes
work into the engineering system as a draft PR. Issues and email are useful only
when a PR is unsafe, impossible, or needs attention. Unbounded notifications and
unverified patches would undermine both utility and trust.

## Decision

Use this action order:

1. **Draft pull request — primary.** Create only after deterministic
   red-before/green-after verification. Never merge or deploy automatically.
2. **GitHub issue — secondary.** Create when a contradiction is established but a
   safe repair cannot be generated or verified, or when the affected behavior is
   outside the authorized repository. Link evidence without exposing secrets or
   synthetic-user identifiers.
3. **Email — occasional notification.** Send only for an opted-in high-severity
   finding, a configured digest, or repeated workflow failure requiring an owner.
   Email never replaces the durable finding record.

The integration provider for email remains unresolved. No documentation may claim
email delivery until an end-to-end receipt is captured.

## Authorization

Connecting a repository includes an explicit policy that pre-authorizes read-only
analysis and, if selected, creation of draft PRs and issues. The UI must show the
selected repository, allowed paths, action types, recipients, and notification
frequency. Changing those boundaries requires a human.

| Action | Default | Required gate |
| --- | --- | --- |
| Capture authorized public/staging source | Allowed | URL allowlist and safe-fetch policy |
| Run synthetic test against authorized staging target | Allowed | Registered control and synthetic identity |
| Create draft PR | Allowed only when configured | Contradiction, policy-valid patch, verification receipt |
| Create issue | Allowed only when configured | Contradiction and a recorded reason PR is unavailable |
| Send email | Off | Opt-in, recipient allowlist, severity/digest rule, rate limit |
| Merge, deploy, contact customers, change policy copy | Prohibited | Not available in the MVP |

## Idempotency and reconciliation

- The current issue fingerprint combines the bound repository ID, exact source
  version and quote, control ID, verdict, and normalized semantic evidence. It
  excludes run IDs, timestamps, synthetic subject IDs, and artifact paths so an
  unchanged finding across scheduled runs reconciles to one issue.
- Patch/PR identity binds the repository ID, base commit, source URL, exact diff,
  and candidate/preimage hashes; a moved base invalidates the verifier receipt.
- Branches use `ipromise/promise-drift-<20-hex-fingerprint>`.
- PRs and issues contain a hidden iPromise action marker.
- Retries first reconcile existing branches, PRs, issues, and delivery receipts.
- A transactional Firestore issue-intent lease serializes the issue path. Draft PRs
  derive the same branch/marker from the exact repair fingerprint, then reconcile
  remote Git refs and PRs before every write. Duplicate events and concurrent or
  distinct runs with an unchanged exact repair converge on the existing action.
- Email uses a finding/event/digest idempotency key and a configured cooldown.

## Content policy

PRs and issues include the exact promise, tested scope, observed behavior, evidence
links, affected code, verifier result, limitations, and run ID. They must not say
“compliant,” “illegal,” or “violation” as a legal conclusion. Emails use fixed
templates and minimal metadata; raw captured documents, customer data, secrets,
model prompts, and code patches are excluded.

## Failure behavior

If publication times out after the remote may have accepted it, the run enters
reconciliation rather than creating a replacement. If the repository base moved,
the candidate is stale and must be regenerated and reverified. If notification
delivery fails, the finding remains durable and the agent records a retryable
notification failure without changing its evidence verdict.
