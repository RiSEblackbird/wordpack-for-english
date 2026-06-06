# WordPack example token UI/UX remediation 2026-06-06

## Result

PASS WITH RISK

Example-token unknown WordPack generation now distinguishes normal, permission-denied, and invalid-lemma states before write requests. P0/P1 findings from the follow-up audit are resolved. Residual risk is limited to the existing jsdom axe canvas limitation for color contrast and the existing dense example-card interaction model.

## Scope

- Components:
  - `ExamplesSection`
  - `useLemmaTooltip`
  - `WordPackPanel`
  - `useWordPack`
- User types: authenticated users and guest users viewing WordPack examples.
- Primary task: inspect an example sentence, discover whether a token already has a WordPack, and generate a missing WordPack only when allowed.
- First meaningful action: hover or focus/click an example token after opening a WordPack detail.

## Finding summary

| Priority | Finding | Status | Evidence |
| --- | --- | --- | --- |
| P1 | Guest users could activate an unknown example token and reach a backend 403. | Resolved | Guest token activation now shows a permission alert and sends no `POST /api/word/pack`. |
| P1 | Long or invalid token text could be sent as a lemma and fail late. | Resolved | Token activation now uses shared `validateLemmaInput`; invalid tokens show `作成不可` tooltip and alert. |
| P2 | `generateWordPack` and `createEmptyWordPack` accepted arbitrary strings from future callers. | Resolved | Hook-level validation stops invalid values before notifications or network calls. |

## State matrix

| State | User-visible result | Recovery / next action | Status |
| --- | --- | --- | --- |
| Saved token | Tooltip shows the saved WordPack sense title; activation opens the overview window. | Continue reading or inspect overview. | Covered |
| Unknown valid token, authenticated | Tooltip shows `未生成`; activation starts WordPack generation and then opens overview. | Wait for generation status/notification. | Covered |
| Unknown valid token, guest | Tooltip shows `未生成（ログインが必要）`; activation shows an alert explaining login is required. | Log in before generating. | Covered |
| Unknown invalid token | Tooltip starts with `作成不可`; activation shows an alert explaining the lemma rule. | Choose a valid word or use the normal Lexicon input. | Covered |
| Empty pending token | No generation starts. | Hover/select a concrete token. | Covered by guard |
| Network/generation error | Existing generation error message remains in the status area. | Retry after the error guidance. | Existing behavior |
| Narrow viewport | Example cards remain vertical; token text wraps within the card. | Scroll vertically. | Browser-checked |
| Keyboard activation | Example row remains focusable; Enter/Space triggers the same guarded path. | Use Tab then Enter/Space. | Covered structurally |

## Novice simulation

1. Persona assumption: a first-time logged-in learner reviewing generated example sentences.
2. Task: click a word in an example sentence that does not yet have a WordPack.
3. First impression after 3 seconds: saved words show a meaning tooltip; unknown words are underlined and marked `未生成`.
4. Predicted first action: click the underlined unknown token.
5. Confusion: guest users might expect the click to work because the row is interactive.
6. Recovery path: guest users now see a permission alert; invalid words show a validation alert.
7. Result: pass. The user no longer needs to infer backend 403 or lemma rules from a failed request.

## Accessibility review

- Existing example rows keep `role="button"` and keyboard activation through Enter/Space.
- Tooltip text is visible on hover and the blocked action also writes a persistent `role="alert"` message.
- The permission-denied and validation states do not rely on color alone: tooltip/status text names the reason.
- Hook-level validation prevents silent notification spinners for values that cannot be accepted.
- Remaining accessibility risk: the example sentence row is still a dense custom interactive area rather than separate token buttons. This change reduces failure states without refactoring that larger interaction model.

## Visual hierarchy review

- The primary content remains the example sentence and translation; blocked reasons appear only when the user engages an unknown token.
- `未生成（ログインが必要）` and `作成不可: ...` are short enough to fit the existing tooltip pattern.
- Persistent alerts appear in the established WordPack status area, so feedback is not hidden inside the sentence text.
- The change does not add a new always-visible instruction block, avoiding extra density in example cards.

## Counter-review

- P0 check: no user-visible write action proceeds without permission or lemma validation.
- P1 check: the guest state now has a visible/announced reason and does not rely on backend 403.
- P1 check: invalid candidate state now has a specific reason and no late network failure.
- Evidence gap: browser verification covers normal responsive rendering and targeted tests cover blocked states, but no visual screenshot artifact is attached to this report.

## Verification evidence

- `cd apps/frontend && npm test -- WordPackPanel useWordPack.loadWordPack.abort --run`: passed, 11 tests and 1 skipped integration test.
- `cd apps/frontend && npx tsc -p tsconfig.json`: passed.
- Browser interaction check with intercepted API: passed.
  - Guest unknown token showed `未生成（ログインが必要）` and a login-required alert.
  - Guest unknown token sent no `POST /api/word/pack`.
  - Invalid long token showed `作成不可` and the shared validation alert.
  - Invalid long token sent no `POST /api/word/pack`.
  - Desktop guest and mobile invalid states had no horizontal overflow.
- `cd apps/frontend && npm test -- --coverage --silent`: passed, 142 tests and 1 skipped test.
- `npx playwright test -c tests/e2e/playwright.config.ts tests/e2e/auth.spec.ts tests/e2e/guest.spec.ts tests/e2e/wordpack.spec.ts`: passed, 3 tests.
- `git diff --check`: passed.
- CI checks: to be checked on the PR after push.
