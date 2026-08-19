# Build-story draft

Status: **prepared, not published**

This article was created to document the build of iPromise for entry into
Google's All Things Agentic Hackathon. Publish it only after the core submission
release is frozen, keep that purpose statement verbatim, and add the public
article URL to the Devpost bonus field.

## Customer promises should behave like tests

Policies, help pages, pricing copy, and product screens make commitments that
software has to uphold. The words and the implementation rarely live in the
same workflow. A team can add an analytics sink, change a background worker, or
ship a new datastore and silently leave a customer promise behind.

iPromise explores a narrow alternative: treat a supported customer promise like
a recurring integration test. The hackathon build focuses on one exact claim:
“When you delete your account, we remove your profile from our app and analytics
system within 24 hours.”

The workflow begins on a manual or scheduled event and completes without
step-by-step guidance. Gemini 3.5 Flash on Vertex AI, coordinated through Google
ADK, converts the captured sentence into a strict typed claim. Deterministic code
then verifies the quote, selects an approved control, exercises an entrant-owned
synthetic SaaS, and checks its application and analytics records.

The deliberately faulty fixture removes the application profile but leaves one
analytics profile active after the disclosed virtual deadline. iPromise reports
the scoped result as `CONTRADICTED`; it does not call the product legally
compliant or noncompliant.

The most important engineering decision was keeping the model outside the
authority boundary. Gemini interprets language, but it does not decide the
evidence verdict, choose arbitrary commands, mint credentials, or publish code.
A fixed Cloud Build verifier independently proves the expected failing baseline,
the repaired hidden control, the full regression suite, and the exact candidate
tree. Only then may the Cloud Run agent publish those exact bytes through a
least-privilege GitHub App as a draft pull request. It cannot merge or deploy.

Firestore checkpoints, leases, stable fingerprints, and remote reconciliation
make retries safe. In the final proof, one run opened a verified draft PR. A
distinct occurrence of the unchanged finding and a same-key replay both returned
that same action rather than creating duplicates.

The result is intentionally smaller than an AI compliance platform. It is one
complete Taskmaster workflow with explicit scope, synthetic evidence, bounded
authority, and a real engineering handoff. The broader product vision is to grow
a catalog of supported controls across customer-facing claims without ever
turning an unsupported promise into fabricated assurance.

Project: https://github.com/kostakarathana/iPromise

#AllThingsAgenticHackathon
