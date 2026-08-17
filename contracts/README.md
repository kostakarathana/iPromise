# Shared contracts

`audit-run.schema.json` is the wire-level contract between the agent service and judge-facing console. It deliberately exposes runtime provenance so a local deterministic demonstration can never be mistaken for a Gemini/Google Cloud execution.

Breaking changes require coordinated console and agent updates. The final demo must show the same `AuditRun.id` in the console, persisted state, logs, verifier receipt, and external action.
