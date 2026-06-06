# Agent Task Prompt Template

Use this when asking an AI agent to perform UI/UX work.

```md
You are working in a repository governed by `AGENTS.md`.

Task:
[describe task]

Requirements:
- Read `AGENTS.md` first.
- If this touches UI/UX, use the `ui-ux-review` skill if available.
- Read `docs/ai-governance/02-uiux-review-framework.md` and `docs/ai-governance/03-evidence-and-completion-gates.md`.
- Do not create Cursor rules.
- Keep `CLAUDE.md` as `@AGENTS.md` only unless preserving existing non-conflicting project policy.
- Produce state matrix, novice simulation, accessibility review, visual hierarchy review, counter-review, and completion gate report.
- Do not claim verification that was not run.

Final report must include:
- files changed,
- P0/P1/P2 findings,
- evidence,
- tests run,
- tests not run,
- remaining risk.
```
