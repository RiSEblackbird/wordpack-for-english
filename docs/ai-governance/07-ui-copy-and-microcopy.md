# UI Copy and Microcopy Rules

UI copy is part of the interface, not decoration.

## 1. User-language rule

Use the user’s words, not internal implementation terms.

Reject:

- internal model names,
- database field names,
- status codes without explanation,
- unexplained abbreviations,
- product-specific jargon on first exposure.

## 2. Action label rule

Action labels must state the result.

Prefer:

- “Create list”
- “Save changes”
- “Invite member”
- “Retry upload”

Avoid vague labels:

- “OK”
- “Submit” when result is unclear
- “Apply” when scope is unclear
- icon-only controls for important actions

## 3. Error message rule

Every actionable error should include:

1. What happened.
2. Why, if known.
3. What is affected.
4. What the user can do next.

Do not write only:

- “Error”
- “Failed”
- “Something went wrong”
- “Invalid input”

## 4. Empty state rule

An empty state must explain:

- why it is empty,
- whether this is expected,
- what the user can do next,
- what will appear after data exists.

Do not use the same copy for empty, no-results, permission-denied, and error states.

## 5. Disabled state rule

Disabled controls must communicate:

- why the control is disabled,
- what enables it,
- whether the user has permission,
- whether waiting, selection, input, or plan/account state is required.

If explanation cannot be placed inline, use nearby helper text or an accessible tooltip pattern.

## 6. Confirmation rule

For destructive or irreversible actions, copy must state:

- object affected,
- consequence,
- reversibility,
- recovery if any.

## 7. Consistency rule

Use one label for one concept. Do not alternate between synonyms unless the distinction is meaningful to users.

Maintain a local terminology list when the repository has repeated domain terms.
