---
name: kev-decision
description: Use local Kev for probability-based classification, routing, and ordered scoring, or a Kev second opinion. Coding judgments are experimental and require independent verification.
---

Read `.agents/skills/kev-decision/SKILL.md` from the repository root and follow its
shared workflow. The `kev` MCP server exposes `kev_models`, `kev_decide`, and
`kev_check_permutations` (Claude Code may prefix tool names with `mcp__kev__`).
Use those tools to address the user's request. If the server is unavailable, consult
`docs/codex-local.md`; do not substitute invented results.
