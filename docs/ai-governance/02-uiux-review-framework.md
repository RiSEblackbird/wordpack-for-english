# UI/UX Review Framework

This framework turns design judgment into an AI-executable review protocol. Its priority is uncompromising usability for first-time users.

## 1. Prime directive

A user-facing interface must make the following clear without documentation:

1. What is this?
2. Where am I?
3. What can I do?
4. What should I do first?
5. What changed?
6. What happens next?
7. What can I do if it fails?

If the interface cannot answer these questions, it is not ready.

## 2. Definition of “first-time user friendly”

An interface is first-time user friendly only when a user can:

- identify the page or component purpose from visible cues,
- recognize the primary action,
- understand required input,
- predict the result of the action,
- recover from common mistakes,
- distinguish normal, empty, loading, error, disabled, and permission states,
- complete the primary task using keyboard-only interaction,
- read the content without excessive density, jargon, or visual competition.

## 3. Review passes

Run these passes for every UI/UX change.

### Pass A: Screen purpose and first action

Answer:

- What is the screen/component for?
- Who is the likely first-time user?
- What is the first meaningful action?
- Is the primary action visible without searching?
- Does the UI explain the current scope, selected object, filter, tab, or mode?

Fail if the answer requires source-code knowledge or prior product knowledge.

### Pass B: Cognitive walkthrough

For a novice user attempting the primary task:

1. Will they know what goal they can accomplish here?
2. Will they see the correct control?
3. Will they understand that the control performs the intended action?
4. After acting, will they understand the feedback?
5. If wrong, can they recover without losing work?

### Pass C: State design

Review every relevant state:

- default,
- loading,
- empty,
- no results,
- partial data,
- success,
- warning,
- error,
- validation error,
- disabled,
- permission denied,
- offline/unavailable,
- long content,
- narrow viewport,
- zoomed text.

Each state must communicate:

- what happened,
- why it matters,
- what the user can do next,
- whether the system is still working,
- whether user data is safe.

### Pass D: Visual hierarchy

The screen must have a clear hierarchy:

1. Purpose / title
2. Current context / scope
3. Primary action
4. Secondary actions
5. Supporting information
6. Metadata and diagnostics

Fail if metadata, badges, counts, or internal status visually compete with the primary task.

### Pass E: Accessibility and inclusive design

Use WCAG 2.2 AA as the minimum baseline. Apply cognitive accessibility guidance beyond WCAG where it improves comprehension.

Minimum checks:

- keyboard access,
- no keyboard trap,
- visible focus,
- focus not obscured,
- accessible names,
- labels and instructions,
- semantic headings,
- status messages,
- contrast,
- target size,
- error identification,
- error suggestion,
- no color-only meaning,
- text resizing and reflow,
- reduced motion where relevant.

### Pass F: Copy and terminology

UI copy must use user language, not implementation language.

Every action label must answer:

- What happens if I click this?
- What object does it affect?
- Is the action reversible?

Every error must answer:

- What happened?
- Why did it happen if known?
- What is affected?
- What can I do now?

### Pass G: Content stress

Test mentally or visually with:

- long Japanese text,
- long English text,
- mixed-width strings,
- missing optional data,
- many items,
- zero items,
- one item,
- long names,
- narrow viewport,
- 200% zoom or equivalent text enlargement,
- slow network,
- repeated validation errors.

### Pass H: Automation and evidence

Use available repository tooling. Examples:

- lint,
- typecheck,
- unit tests,
- integration tests,
- browser tests,
- accessibility tests,
- visual regression tests.

If tooling does not exist, document the gap and perform manual reasoning with evidence.

### Pass I: Counter-review

Run an adversarial review that tries to reject the work. It must search for P0 blockers, not praise the design.

## 4. Severity model

### P0: Cannot complete

P0 means the change must not be considered complete.

- first-time user cannot understand purpose,
- first meaningful action is unclear,
- current scope/location is unclear,
- primary action is icon-only or visually buried,
- state design conflates loading/empty/no-results/error/disabled/permission-denied,
- errors lack recovery,
- disabled states lack explanation,
- keyboard task completion fails,
- focus is missing or obscured,
- accessible names or labels are missing,
- contrast or target size minimums fail,
- destructive actions lack appropriate prevention or recovery,
- evidence artifacts are missing,
- verification is falsely claimed.

### P1: Must fix before merge unless explicitly deferred

- inconsistent terminology,
- weak empty state,
- unclear helper text,
- excessive visual density,
- secondary actions competing with primary action,
- poor responsive behavior that has a workaround,
- non-blocking a11y issue with clear remediation,
- missing screenshot for a non-critical state.

### P2: Improvement opportunity

- polish issues,
- minor spacing inconsistency,
- clearer microcopy,
- better grouping,
- stronger progressive disclosure,
- future automation opportunity.

## 5. Numeric minimums

Use these defaults unless the repository has stricter standards.

| Area | Minimum |
|---|---|
| Body text | Prefer 16px or equivalent; smaller only when justified and still readable |
| Long-form line height | At least 1.5 |
| Paragraph spacing | Prefer at least 1.5× line height between paragraphs in long-form content |
| Japanese line length | Aim around 40 full-width characters for long-form text when applicable |
| Text contrast | WCAG AA: 4.5:1 normal text, 3:1 large text |
| Non-text contrast | At least 3:1 for meaningful UI graphics and component boundaries |
| Pointer target | WCAG 2.2 AA: at least 24×24 CSS px or valid spacing/exception |
| Touch-friendly target | Prefer 44–48px/dp when touch is expected |
| Focus indicator | Clearly visible, consistent, not obscured, not color-only |
| Motion | Avoid essential information conveyed only by motion; respect reduced motion |

## 6. Design anti-patterns

Reject or flag:

- icon-only primary actions,
- placeholder-as-label forms,
- “Something went wrong” without recovery,
- disabled button with no reason,
- empty state with no next step,
- tab/filter count without scope,
- status badge that does not explain consequences,
- visual hierarchy based only on color,
- hover-only disclosure,
- hidden destructive side effects,
- multiple primary buttons in one decision area,
- tiny click targets,
- dense cards with equal visual weight for every datum,
- implementation terms exposed to users,
- relying on memory across multi-step flows.

## 7. Required output

Every UI/UX review must produce:

- screen purpose summary,
- primary user task,
- first meaningful action,
- state matrix,
- cognitive walkthrough,
- accessibility review,
- visual hierarchy review,
- copy review,
- counter-review,
- P0/P1/P2 findings,
- evidence list,
- tests run / not run,
- final pass/fail.
