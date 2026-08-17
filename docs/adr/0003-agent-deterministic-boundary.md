# ADR 0003: Agent versus deterministic authority

- Status: Accepted
- Date: 2026-08-17

## Context

iPromise consumes adversarial, untrusted language and may propose repository
changes. Model interpretation is useful for semantic ambiguity, but a model must
not become the evidence oracle or privilege boundary.

## Decision

Gemini proposes interpretations and edits. Deterministic application code grants
authority and computes outcomes.

| Gemini may do | Deterministic code must do |
| --- | --- |
| Extract a structured claim from a captured source | Enforce URL/repository allowlists and block SSRF |
| Preserve and identify an exact source quotation | Verify that the quotation exists in the captured artifact |
| Normalize actor, action, object, scope, qualifiers, and deadline | Validate schemas, versions, freshness, and required evidence |
| Rank candidates from a fixed control catalog | Authorize the selected control and its tools |
| Propose bounded file edits | Enforce paths, base hashes, size limits, and protected-file policy |
| Summarize evidence for a human | Compute `SUPPORTED`, `CONTRADICTED`, or safe abstention |
| Explain a verified repair | Run fixed tests and decide whether publication is allowed |

Gemini never receives arbitrary shell authority, an unrestricted URL fetcher,
GitHub credentials, email credentials, production mutation credentials, or the
ability to mark its own output verified. Private chain-of-thought is neither
requested nor stored; the audit record contains inputs, typed outputs, tool
events, evidence, and policy decisions.

## Structured contracts

Model nodes must return versioned, strict schemas for at least:

- `PromiseClaim`: source artifact ID, exact quote, normalized terms, and proposed
  testability.
- `ControlBindingProposal`: approved control ID plus a bounded rationale.
- `PatchProposal`: base commit, allowed path, expected preimage hash, replacement
  content or bounded diff, and purpose.
- `EvidenceSummary`: prose derived only after the deterministic verdict exists.

Unexpected fields, invalid quotes, unsupported controls, stale versions, and
ambiguous required evidence fail closed to `INCONCLUSIVE` or `NOT_TESTED`.

## Repair gate

A repair can reach GitHub only when all of these are true:

1. The finding is deterministically `CONTRADICTED`.
2. The repository base commit and every edited preimage match.
3. No protected workflow, dependency lockfile, trusted control, or test harness is
   modified.
4. A clean baseline verifier produces the exact expected failure.
5. A separate clean candidate verifier passes the promise control and regression
   suite.
6. The published Git tree contains exactly the verified bytes.

No passing proof means no PR. A safely worded issue may be created instead under
the separate action policy.

## Consequences

The system can demonstrate valuable agentic reasoning without asking judges to
trust model self-assessment. It also creates clear evaluation targets: grounding,
schema validity, control-selection precision, abstention, policy enforcement, and
end-to-end action correctness.
