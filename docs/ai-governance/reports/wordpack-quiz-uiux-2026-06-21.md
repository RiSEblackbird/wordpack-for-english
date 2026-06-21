# WordPack Quiz UI/UX review report 2026-06-21

## Result

PASS WITH LOCAL VISUAL EVIDENCE

Quiz adds a new learning surface that connects saved WordPacks to long-form reading, answer selection, scoring, evidence review, and inline WordPack actions. The UI gives first-time users a visible starting point, keeps saved quizzes and the active quiz in view, separates guest restrictions from local review, and preserves expert speed through direct list selection and inline actions.

## Scope

- Screen: `/quiz`
- Components: Quiz route/nav entry, generation form, saved Quiz list, Quiz detail, passage rendering, inline WordPack anchors, question cards, scoring summary, guest/read-only states
- Primary user goal: turn WordPack vocabulary into contextual reading practice and review evidence without leaving the app
- First meaningful action: select existing WordPacks or enter lemma, then generate a Quiz; for saved items, choose a Quiz and answer questions

## User Value

- Target user: English learners who already collect WordPacks and want contextual reading practice.
- Supported tasks: generate reading material, answer multiple-choice questions, review evidence, reopen related WordPacks, create/generate missing WordPacks.
- Decision support: the screen shows format, domain, difficulty, question count, included lemmas, unanswered count, score, and per-question correctness.
- Without this UI: users must jump between WordPack details, Reader content, and manual notes to build reading practice.

## State Matrix

| State | User-visible result | Recovery / next action | Status |
| --- | --- | --- | --- |
| Initial, no quizzes | Empty list explains that a Quiz can be generated from the left form | Select WordPacks or enter lemma | Covered |
| Initial, saved quizzes | List selects the first quiz and loads detail | Answer questions or choose another quiz | Covered |
| Loading list/detail | Loading copy appears in the affected panel | Wait or retry update | Covered |
| Generation source empty | Form shows validation text and disables start | Add WordPack or lemma | Covered |
| Generation running | Button changes to `生成中...`; notification and status message show progress | Wait for polling result | Covered |
| Generation failed | Notification and page message show retryable error | Adjust input or retry | Covered |
| Generation warning | Detail shows warning for selected lemma not found in passage | Review or regenerate with adjusted sources | Covered |
| Guest mode | Generate/delete/create buttons are GuestLock-disabled; local scoring still works without saving | Log in for persistence | Covered |
| Answering | Radios are enabled; correct answer and explanation are hidden | Select choices and grade | Covered |
| Unanswered grading | Unanswered count is visible; grading still allowed | Grade or continue answering | Covered |
| Reviewed | Score, correctness labels, evidence, explanation, wrong-choice reasons appear | Open related WordPack or retry with another Quiz | Covered |
| Existing inline WordPack | Button opens preview modal | Close preview and continue Quiz | Covered |
| Missing inline WordPack | Popover offers empty creation and generation; guest sees disabled actions | Create/generate or log in | Covered |
| Narrow viewport | Generator, list, and detail stack vertically | Scroll through panels | Browser-checked |

## Novice Simulation

1. A first-time user lands on `/quiz` and sees the page title plus the purpose: saved WordPacks become reading, answering, and evidence review.
2. The left form indicates the first action by grouping format, generation domain, difficulty, question counts, WordPack selection, and lemma input.
3. The center list shows saved Quiz metadata and included lemmas, so the selected target is clear before reading.
4. The detail panel starts with the title, format/domain/difficulty, unanswered count, and a single grading action.
5. After grading, each question exposes a text result label, the correct answer, evidence, Japanese explanation, wrong-choice reasons, and related lemma chips.

Novice result: pass. The screen explains its purpose, next action, selected target, and review path without requiring internal schema knowledge.

## Accessibility Review

- Keyboard: navigation items, form controls, radio choices, inline WordPack anchors, and popover actions are native controls.
- Focus: custom controls use visible `:focus-visible` outlines.
- Names/labels: form fields have visible labels; inline WordPack buttons include `aria-label`; question radios are grouped by `fieldset` and hidden `legend`.
- Structure: the page uses clear headings, sections, and panel labels.
- Status/error: generation messages use `role="status"` or `role="alert"`; score summary uses `aria-live`.
- Color: correctness is not color-only; labels show `正解` / `不正解` / `未回答`, and choices show text badges.
- Target size: primary actions and choice rows use stable minimum heights.

## Visual Hierarchy

- Level 1: page title and saved Quiz count.
- Level 2: generator, saved list, active Quiz detail.
- Level 3: passage, section, question cards.
- Level 4: inline WordPack status chips and explanation details.

Desktop uses a three-column work layout for repeated scanning. Tablet collapses detail beneath generator/list. Mobile stacks all panels and keeps fixed-format controls from resizing unexpectedly.

## Expert Efficiency

- Repeat generation keeps default values and allows direct lemma paste.
- Saved Quiz cards are one-click selection targets.
- Attempt state remains in the detail panel while opening WordPack previews.
- Inline WordPack actions avoid switching to Lexicon for missing terms.
- Existing `Alt+8` shortcut reaches Quiz without changing older shortcut numbers.

Judgment: pass. Introductory text is short and does not block repeated use.

## Trust And Satisfaction

- Waiting: generation status is visible both in notification and page message.
- Success: generated Quiz is selected after list refresh.
- Failure: generation errors remain retryable and do not create partial UI state.
- Destructive action: delete uses a confirmation explaining attempts are also removed.
- Guest state: locked operations use the existing GuestLock pattern; local scoring explicitly says it was not saved.
- Safety: prompt policy avoids official test reproduction and unsafe technical instructions.

Judgment: pass with one residual risk: generation jobs are in-memory as designed for MVP, so instance recycle can lose job status.

## Counter-Review

- P0 attempt: could a user misunderstand guest scoring as saved? Mitigation: guest note appears above content and grading status says results were not saved.
- P0 attempt: are correct answers visible before grading? Mitigation: explanation and correct badges render only after an attempt result exists.
- P0 attempt: are inline WordPack actions keyboard reachable? Mitigation: inline anchors are buttons and missing-word actions are buttons in a popover.
- P1 attempt: could a specified lemma silently disappear from generated text? Mitigation: source lemma with no occurrence gets a warning in Quiz detail.
- P1 attempt: could occurrence data absence make links disappear? Mitigation: frontend fallback matching highlights lemma occurrences when no explicit occurrence is present.
- Evidence gap: live LLM output quality was not exhaustively evaluated in local tests; schema and prompt constraints are covered, but content quality remains dependent on provider behavior.

## Findings

| Priority | Finding | Status | Evidence |
| --- | --- | --- | --- |
| P0 | Quiz route/nav absent | Resolved | `/quiz`, sidebar, bottom nav, `Alt+8` added |
| P0 | Guest operations could be confused with saved actions | Resolved | GuestLock plus local-only scoring message |
| P1 | Missing source lemma warning absent | Resolved | Flow warning and UI warning list |
| P1 | Inline links depended only on stored occurrence positions | Resolved | fallback lemma matching added |
| P1 | Mobile bottom nav was fixed at 5 columns | Resolved | auto-fit grid handles added Quiz item |

## Verification Evidence

- Baseline screenshots captured before implementation: local-only evidence, not committed.
- ImageGen mock variants generated before implementation: desktop generator/list/detail, desktop taking/review, mobile responsive; local-only evidence, not committed.
- Backend targeted tests: `FIRESTORE_EMULATOR_HOST=127.0.0.1:8787 FIRESTORE_PROJECT_ID=test-project GCP_PROJECT_ID=test-project PYTHONPATH=apps/backend pytest -q --no-cov tests/backend/test_quiz_models.py tests/backend/test_quiz_flow.py tests/backend/test_quiz_api.py tests/backend/test_firestore_store.py` passed, 34 tests.
- Backend full tests: `FIRESTORE_EMULATOR_HOST=127.0.0.1:8787 FIRESTORE_PROJECT_ID=test-project GCP_PROJECT_ID=test-project PYTHONPATH=apps/backend pytest -q --no-cov` passed.
- Frontend typecheck: `npx tsc -p tsconfig.json` in `apps/frontend` passed.
- Frontend tests: `npm test -- --coverage --silent` in `apps/frontend` passed, 163 passed and 1 skipped.
- Frontend build: `npm run build` in `apps/frontend` passed.
- E2E smoke: `npx playwright test -c tests/e2e/playwright.config.ts tests/e2e/auth.spec.ts tests/e2e/guest.spec.ts tests/e2e/wordpack.spec.ts` passed, 6 tests.
- Browser visual checks: desktop and mobile Playwright checks completed with no horizontal overflow and screenshots saved outside the repository.
- Diff hygiene: `git diff --check` passed.

## Not Executed

| Check | Reason | Residual risk | Follow-up |
| --- | --- | --- | --- |
| Live provider quality audit across all format/domain pairs | Requires real LLM calls and content review beyond deterministic CI | Generated content may vary in pedagogical quality | Add curated fixture review or provider-backed smoke when credentials are available |
