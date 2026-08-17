# Claim-compiler evaluation fixtures

These are original synthetic examples written for iPromise. They cover supported deletion promises, ambiguous wording, unsupported claim families, negation, qualifiers, and indirect prompt injection.

The expected labels test the most important safety property: unsupported or ambiguous language must abstain instead of producing a false operational assurance. Only `privacy.account_deletion.v1` is executable in the MVP.

Before submission, expand this set to at least 40 examples, freeze a held-out split, run the same pinned model configuration over every example, and report only measured results.
