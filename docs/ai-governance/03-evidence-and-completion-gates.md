# Evidence and Completion Gates

UI/UX work is complete only when evidence exists.

## 1. Required artifacts

For any UI/UX change, produce or update:

1. UI/UX review report
2. State matrix
3. Novice simulation
4. Accessibility review
5. Visual hierarchy review
6. Counter-review
7. Completion gate report

Use templates from `docs/ai-governance/templates/`.

## 2. Completion gates

### Gate 1: Scope gate

Pass only if:

- changed screens/components are listed,
- user goal is stated,
- first meaningful action is stated,
- affected states are listed.

### Gate 2: First-time comprehension gate

Pass only if:

- screen purpose is visible,
- current scope/location is visible,
- primary action is visually discoverable,
- important consequences are explained before action.

### Gate 3: State gate

Pass only if:

- default, loading, empty, no-results, error, disabled, and permission states are intentionally designed or marked not applicable,
- each state gives a next action or clear explanation,
- error and disabled states include recovery guidance.

### Gate 4: Accessibility gate

Pass only if:

- primary task works keyboard-only or the exception is documented,
- focus is visible and not obscured,
- controls have accessible names,
- labels and instructions exist where needed,
- contrast/target/semantic checks have been performed or explicitly not run,
- no known WCAG AA blocker remains.

### Gate 5: Visual clarity gate

Pass only if:

- primary action is visually dominant,
- hierarchy is scannable,
- content density is justified,
- long content and narrow viewport are considered,
- metadata does not overwhelm task-relevant content.

### Gate 6: Counter-review gate

Pass only if:

- an adversarial review was performed,
- P0/P1/P2 findings are listed,
- unresolved risks are listed,
- the final pass/fail is justified.

## 3. Evidence quality

Good evidence:

- is specific,
- identifies exact screen/state/component,
- includes command outputs when commands were run,
- includes screenshots/traces when available,
- lists limitations.

Bad evidence:

- “looks good”,
- “should work”,
- “tested manually” with no steps,
- happy-path screenshot only,
- claiming a11y pass without keyboard and focus checks,
- claiming user validation without real users.

## 4. When evidence cannot be generated

If screenshots, browser tests, or automated accessibility checks cannot be generated:

1. Say exactly why.
2. Provide the best available substitute evidence.
3. Mark residual risk.
4. Do not mark the gate as fully passed unless the substitute evidence genuinely covers the risk.

## 5. Final pass/fail language

Use one of:

- `PASS`: No P0 remains; P1/P2 are documented or resolved.
- `PASS WITH RISK`: No P0 remains, but evidence is incomplete or P1 remains with explicit deferral.
- `FAIL`: Any P0 remains or verification was materially insufficient.

Do not invent a softer category.
