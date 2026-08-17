# ADR 0001: Product scope and Taskmaster track

- Status: Accepted
- Date: 2026-08-17
- Product: iPromise

## Context

Companies make concrete promises in privacy policies, terms, pricing pages, help
content, and product UI. Those claims drift away from actual product behavior as
code, vendors, and data flows change. Finding that drift today is slow, episodic,
and usually produces a report rather than a completed engineering action.

The [official hackathon rules](https://allthingsagentichackathon.devpost.com/rules)
require one track and reward operational utility, disciplined architecture, and a
convincing end-to-end demo. iPromise is not a chat product: its value is a
background workflow that turns an unstructured promise into evidence and a safe
downstream action.

## Decision

iPromise will enter exactly one track: **Taskmaster**.

The product contract is:

> iPromise captures what customers are promised, turns supported claims into
> executable controls, tests actual staging behavior, and creates an
> evidence-backed engineering action when behavior contradicts the promise.

The initial user is a product, privacy, or engineering owner at a software
company. The first complete control is account deletion across enumerated active
data stores. The reference scenario uses a deliberately faulty, synthetic SaaS:
the deletion endpoint removes a profile but leaves its analytics profile behind.

The product may discover several claims, but it will use only these verdicts:

- `SUPPORTED`: evidence supports only the tested scope at the observed time.
- `CONTRADICTED`: observed behavior conflicts with the captured promise.
- `INCONCLUSIVE`: evidence is missing, stale, or unavailable.
- `NOT_TESTED`: no approved executable control covers the claim.

It will never present a verdict as legal advice, certification, or proof of
general compliance.

## Primary action

A verified **draft pull request** is the principal completed action. A GitHub
issue is the fallback when a contradiction is established but a safe patch
cannot be verified. Email is an optional, rate-limited notification or digest;
it is never the core workflow. See [ADR 0004](0004-action-policy.md).

## Why this fits Taskmaster

The scheduled or manually triggered workflow captures a source, interprets a
claim, chooses from approved controls, creates synthetic data, invokes the
product, evaluates evidence, proposes and verifies a repair, and publishes a
draft PR with little or no intervention after the trigger. This is a distinct
multi-step chore with an externally visible outcome, rather than a reminder or
standard chat loop.

## Consequences

- The demo optimizes for one trustworthy vertical slice, not universal claim
  enforcement.
- Broad discovery is allowed; execution is restricted to registered controls.
- The reference SaaS and its data are synthetic and must be visibly disclosed.
- Production integrations require explicit authorization, scoped credentials,
  and a system inventory.
- Auto-merge, auto-deploy, legal conclusions, arbitrary crawling, and arbitrary
  generated commands are out of scope for the MVP.

## Success evidence

The decision is proven only when one continuous run captures the exact deletion
promise, observes the residual record, reports `CONTRADICTED`, proves a bounded
repair red-before/green-after, and creates exactly one real draft PR.
