# Governance Maintenance Policy

This file controls how AI-agent rules may evolve.

## 1. Source of truth

- `AGENTS.md` is the rule origin and startup constitution.
- `docs/ai-governance/` is the detailed source of truth.
- `.agents/skills/*/SKILL.md` contains task-specific executable workflows.
- `CLAUDE.md` imports `AGENTS.md` only.
- Cursor rules are not part of this governance.

## 2. No duplication

Do not duplicate the full UI/UX rulebook into:

- `AGENTS.md`,
- `CLAUDE.md`,
- IDE rules,
- PR templates,
- README files,
- multiple skills.

Duplicate summaries cause drift. Link to the detailed docs instead.

## 3. Rule addition standard

A new rule must have at least one basis:

- accessibility standard,
- cognitive psychology or HCI research,
- design-system standard,
- observed repository defect,
- repeated review failure,
- security requirement,
- user instruction.

A new rule must be:

- specific,
- testable or reviewable,
- severity-classified when applicable,
- mapped to evidence.

## 4. Update process

When changing governance:

1. Read this file.
2. Read `references/canonical-sources.md`.
3. Identify whether the change affects AGENTS, skills, detailed docs, templates, or all.
4. Avoid duplicated bodies.
5. Update templates/checklists if the new rule requires evidence.
6. Run `scripts/verify-ai-governance.sh`.
7. Report conflicts and migration notes.

## 5. Skill maintenance

Skills must remain focused.

- Keep `SKILL.md` concise.
- Put heavy detail in `docs/ai-governance/`.
- Keep description trigger words strong and front-loaded.
- Do not add tool-specific metadata unless the maintainer explicitly asks.
- Do not add scripts unless deterministic automation is necessary.

## 6. AGENTS.md maintenance

`AGENTS.md` must stay compact.

It should contain:

- routing,
- hard gates,
- trust boundaries,
- evidence rules,
- references to detailed docs.

It should not contain:

- the full UI/UX framework,
- long research summaries,
- vendor-specific settings,
- duplicated checklists.

## 7. Review cadence

Review governance when:

- accessibility standards change,
- the design system changes,
- the agent toolchain changes,
- repeated UI/UX review defects occur,
- a repository adopts a new frontend framework,
- a major user-facing flow is added.

## 8. Deprecation

When removing a rule:

- explain why,
- identify what replaces it,
- check for references in templates/checklists/skills,
- avoid weakening P0 blockers unless maintainers explicitly approve.
