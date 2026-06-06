# Accessibility and Inclusive Design

Accessibility is not optional polish. It is a completion gate for user-facing work.

## 1. Baseline

Use WCAG 2.2 AA as the minimum baseline unless the repository has stricter requirements. Consider cognitive accessibility guidance even when WCAG testable criteria do not fully cover the issue.

## 2. Mandatory checks

### Keyboard

- Primary task can be completed using keyboard only.
- Focus order matches visual and logical order.
- No keyboard trap.
- Modals, menus, popovers, and drawers manage focus correctly.

### Focus

- Focus indicator is visible.
- Focus is not hidden behind sticky headers, dialogs, or overlays.
- Focus style is consistent.
- Focus is not conveyed by color alone.

### Names, roles, values

- Controls have accessible names.
- Icon buttons have explicit labels.
- Visible labels are included in accessible names when applicable.
- Custom controls expose role, state, and value.

### Semantics

- Page and regions have meaningful headings.
- Heading order is logical.
- Landmarks are used when useful.
- Lists, tables, forms, and buttons use appropriate semantics.

### Contrast and visual perception

- Normal text contrast: at least 4.5:1.
- Large text contrast: at least 3:1.
- Meaningful icons, boundaries, and focus indicators: at least 3:1 where applicable.
- Do not convey state by color alone.

### Target size

- Pointer targets meet at least 24×24 CSS px or a valid exception.
- Touch-oriented interfaces should prefer 44–48 px/dp or larger.
- Adjacent destructive and safe actions need enough separation.

### Text and layout

- Text can resize without loss of content or function.
- Long-form content uses readable line height.
- Long lines are avoided for reading-heavy content.
- Content reflows without horizontal scrolling except where genuinely required.

### Motion

- Avoid flashing content.
- Avoid unnecessary motion for critical feedback.
- Respect reduced-motion preferences where motion exists.

### Errors and forms

- Required fields are identified.
- Validation errors identify the field and issue.
- Suggestions are provided when known.
- User input is preserved after errors.
- Authentication and repeated-entry flows avoid unnecessary memory burden.

## 3. Automated checks

Use available tools when present:

- axe or equivalent rendered-DOM checker,
- eslint accessibility plugin where relevant,
- browser tests for keyboard flow,
- Storybook accessibility checks,
- visual regression for focus and state snapshots.

Automated accessibility checks are not sufficient by themselves. They do not replace keyboard review, state review, or cognitive walkthrough.

## 4. P0 accessibility failures

- Keyboard primary task failure.
- Invisible or obscured focus.
- Missing accessible name for actionable control.
- Icon-only primary action with no visible label.
- Contrast below minimum for essential text or controls.
- Error message not programmatically or visually associated with input.
- Status update not perceivable.
- Drag-only action with no accessible alternative.
- Authentication or verification requiring memory/puzzle without accessible alternative.
