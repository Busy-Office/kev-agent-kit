---
name: kev-decision
description: Use the local Kev MCP tools for probability-based classification, routing, and ordered scoring, or when the user asks for a Kev second opinion. Coding judgments are experimental and require independent verification.
---

# Kev decisions

Call `kev_models` to confirm which checkpoint is loaded. If unavailable, report that
Kev could not contribute. The local API normally runs at http://127.0.0.1:8008.
For setup and troubleshooting, see
https://github.com/Busy-Office/kev-agent-kit/blob/main/docs/setup.md.
Do not assume the current working directory contains the Kev checkout.

Use `kev_decide` with a concise state and 1–16 independent questions:

- `noul`: instructions, optional true/false criteria; returns probability of yes.
- `choice`: instructions and a map from option names to descriptions. Include an
  unknown/insufficient-evidence option when appropriate. Returns a choice and distribution.
- `score`: instructions and an ordered list of levels. Returns an expected
  zero-based level, not a percentage.

Put shared evidence in state. Questions cannot see sibling questions. Supply only
context relevant to the judgment; large requests may truncate model context.
Batch questions about the same evidence in one call.

Keep the original probability distribution when explaining a result. Choice
confidence is rescaled relative to uniform probability; it is not measured accuracy.
Score confidence is an approximation, and response probabilities are rounded.
No universal confidence cutoff has been validated for this coding workflow.

For an ambiguous or important choice, `kev_check_permutations` can test option-order
sensitivity; start with three passes. It costs several inferences and does not prove
correctness. Coding risk, CI diagnosis, and code-review judgments are out-of-domain
experiments: verify with source evidence and tests. Kev output does not authorize
changes or replace user approval. If the user only wants advice, keep it advisory.
