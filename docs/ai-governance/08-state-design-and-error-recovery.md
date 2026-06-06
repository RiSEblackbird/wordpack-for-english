# State Design and Error Recovery

State design is mandatory. A UI is not complete until its non-happy paths are designed.

## 1. Required states

For each changed screen/component, classify these states:

| State | Required? | Notes |
|---|---:|---|
| default | yes | Normal usable state |
| loading | if async | Show progress or skeleton; avoid layout jump where possible |
| empty | if data can be absent | Explain why empty and next step |
| no results | if search/filter exists | Explain scope and how to broaden |
| partial data | if possible | Show what is available and what failed |
| success | if action changes data | Confirm outcome and next step |
| warning | if risk exists | Explain consequence before action |
| error | if operation can fail | Cause, impact, recovery |
| validation error | if input exists | Field-specific message and suggestion |
| disabled | if control can be unavailable | Reason and enabling condition |
| permission denied | if permissions exist | Explain permission boundary and request path if applicable |
| offline/unavailable | if network or service dependence exists | Retry and preservation behavior |

## 2. Loading state

Must answer:

- What is loading?
- Is the system still working?
- Can the user cancel or continue elsewhere?
- Is user input preserved?

Avoid indefinite spinners without context for long operations.

## 3. Empty state

Must answer:

- Is this expected?
- What data would appear here?
- What can the user do first?
- Is there a permission or setup requirement?

## 4. No-results state

Must not look like empty state.

Must answer:

- What query/filter produced no results?
- What scope was searched?
- How can the user broaden or clear filters?

## 5. Error state

Must answer:

- What failed?
- What is still safe?
- What can be retried?
- What data might be lost?
- Where can the user get help if retry fails?

## 6. Disabled state

Disabled without explanation is a usability failure.

Use:

- visible helper text,
- inline reason,
- accessible tooltip pattern,
- validation guidance,
- permission explanation.

Do not rely on hover-only explanation.

## 7. Permission denied

Must answer:

- What permission is missing?
- What is visible despite missing permission?
- Who can grant access, if known?
- What action is still available?

## 8. Error recovery severity

Use risk-based recovery:

| Risk | Required recovery |
|---|---|
| Low | retry or undo |
| Medium | confirmation, preserve input, explain impact |
| High | explicit confirmation, strong warning, audit trail if relevant |
| Irreversible | require clear object/consequence/reversibility statement |

## 9. State matrix requirement

Every UI/UX review must include a state matrix. Use `templates/state-matrix.md`.
