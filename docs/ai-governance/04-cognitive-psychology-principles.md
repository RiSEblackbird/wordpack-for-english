# Cognitive Psychology Principles for UI/UX Review

This document converts cognitive psychology concepts into reviewable UI rules.

## 1. Cognitive load

Users have limited working memory. Interfaces must avoid unnecessary mental work.

Rules:

- Do not require users to remember values from previous screens.
- Keep multi-step flows visibly oriented with progress, breadcrumbs, or step labels.
- Group related controls and information.
- Reveal advanced options progressively.
- Prefer recognition over recall.

Review questions:

- What must the user remember?
- Can the UI show it instead?
- Does each screen have one dominant decision?
- Are irrelevant details competing with the task?

## 2. Recognition over recall

Users should recognize available actions from visible labels, layout, and affordances.

Rules:

- Do not depend on icon memorization for primary actions.
- Do not hide required actions in hover-only UI.
- Use visible labels for critical controls.
- Preserve selected context and user input across recoverable errors.

## 3. Mental models

Users interpret UI through familiar patterns.

Rules:

- Use conventional placement for common actions unless there is strong evidence not to.
- Use terms the user would use.
- Keep similar actions visually and behaviorally consistent.
- Make system status and consequences explicit.

## 4. Attention and signal-to-noise

Visual attention is limited.

Rules:

- Avoid equal visual weight for every item.
- Use hierarchy to guide the eye to title, context, primary action, and feedback.
- Suppress purely diagnostic information unless it changes user action.
- Never let badges, counts, timestamps, or internal status compete with the primary task.

## 5. Error prevention and recovery

Users make mistakes under time pressure, distraction, and uncertainty.

Rules:

- Prevent destructive mistakes before they happen.
- Make low-risk actions reversible where possible.
- Preserve user input after validation errors.
- Show error messages near the source and summarize when needed.
- Provide next steps, not just failure labels.

## 6. Decision complexity

Too many similar choices slow and weaken decisions.

Rules:

- Reduce decision points per screen.
- Separate primary, secondary, and destructive actions.
- Use progressive disclosure for rare or expert actions.
- Avoid multiple visually primary buttons in one decision area.

## 7. Spatial memory and consistency

Users build expectations from repeated placement.

Rules:

- Keep recurring navigation and actions in consistent locations.
- Avoid moving primary actions across states unless the state itself changes the task.
- Keep focus order aligned with visual order.

## 8. Review output

For cognitive review, always list:

- what the user must perceive,
- what the user must remember,
- what the user must decide,
- what the user can recover from,
- where the UI reduces or increases cognitive load.
