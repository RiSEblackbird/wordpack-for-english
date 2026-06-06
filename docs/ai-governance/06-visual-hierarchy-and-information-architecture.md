# Visual Hierarchy and Information Architecture

The interface must guide attention intentionally.

## 1. Hierarchy order

Every screen should make this order visually legible:

1. Product/page area or screen purpose
2. Current object, filter, mode, or scope
3. Primary task or primary action
4. Required inputs
5. Secondary actions
6. Supporting details
7. Diagnostics, metadata, and rare actions

## 2. Primary action rules

- One primary action per decision area.
- Primary action label must include a result verb.
- Primary action must not be icon-only.
- Destructive primary actions require risk-appropriate confirmation or recovery.
- Disabled primary action must explain why it is unavailable.

## 3. Grouping rules

Use proximity, alignment, headings, and whitespace to communicate grouping.

Fail if users must infer relationships from implementation structure, DOM order, or hidden context.

## 4. Typography rules

- Use readable default sizes.
- Long-form text should use line height around or above 1.5.
- Avoid long all-caps text.
- Avoid long italic text, especially in Japanese.
- Keep reading-heavy line lengths manageable.
- Do not use image text except where unavoidable, such as logos.

## 5. Density rules

Dense UI is allowed only when:

- the primary task is still obvious,
- scanning order is clear,
- critical actions are not buried,
- long content does not collapse the layout,
- narrow viewport has a usable layout.

## 6. Visual affordance rules

Interactive elements must look interactive.

Reject:

- text that looks like body text but acts as a button,
- buttons that look disabled when enabled,
- disabled controls that look enabled,
- hover-only affordances for important actions,
- tiny ambiguous icons.

## 7. Information architecture rules

- Navigation labels must be mutually distinguishable.
- Tab, filter, and count scopes must be explicit.
- Breadcrumbs or equivalent orientation must exist for deep or multi-step flows.
- Search must state what it searches when scope is not obvious.
- Empty and no-results states must not be conflated.

## 8. Content stress tests

Review visual hierarchy with:

- 0, 1, many items,
- long names,
- missing metadata,
- warning and error banners,
- narrow viewport,
- translated strings,
- 200% text zoom,
- high-density real-world data.
