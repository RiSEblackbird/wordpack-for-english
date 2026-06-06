# Explore UI/UX review report 2026-06-06

## Result

PASS WITH RISK

The Explore screen now explains its purpose, makes the first action explicit, distinguishes candidate states, and lets users create an empty WordPack from an unregistered relation. Residual risk is limited to automated color-contrast coverage: the Vitest axe check disables `color-contrast` because jsdom does not provide canvas APIs required by axe for that rule. Visual review did not find an obvious contrast failure.

## Scope

- Screen: `/explore`
- Components: Explore page header, search/update controls, mode tabs, status guide, source list, relation cards, detail side panel, mobile layout
- Primary user goal: find useful relationships from saved WordPacks and turn missing words into saved WordPacks without leaving the screen
- First meaningful action: choose a source WordPack or search by lemma/sense title

## Finding summary

| Priority | Finding | Status | Evidence |
| --- | --- | --- | --- |
| P0 | Screen purpose and first action were unclear for new users | Resolved | Header copy, left column heading, status guide, and selected-source heading now state what to do |
| P0 | `unknown`/`empty` states were ambiguous and non-actionable | Resolved | Candidate badges now show `保存済み` / `空のWordPack` / `未登録` with distinct actions |
| P1 | Unregistered relations ended at a disabled-looking state | Resolved | `WordPackを作成` creates an empty WordPack and opens preview |
| P1 | Right panel did not summarize why the selected item mattered | Resolved | Metrics, primary open action, guidance, and quick actions added |
| P1 | Mobile tabs could wrap into unreadable vertical text or create overflow | Resolved | Mobile tabs use a compact grid; 390px browser check showed no horizontal overflow |
| P2 | English source labels were exposed in a Japanese UI | Resolved | Source labels are translated for user-facing chips |

## State matrix

| State | User-visible result | Recovery / next action | Status |
| --- | --- | --- | --- |
| Initial loaded | Source WordPack list, selected source, relation count, status guide | Choose source, switch mode, create/open candidate | Covered |
| Loading | Header button shows `更新中`; lists show loading copy | Wait or retry update | Covered |
| Empty data | List area explains that no saved WordPack exists | Create WordPack in Lexicon | Covered |
| Search no match | List says no WordPack matches the search | Change search text | Covered |
| Relation no match | Center column says no candidates in the selected mode | Switch mode or choose another source | Covered |
| Saved relation | `保存済み` badge and `プレビュー` action | Open preview | Covered |
| Empty WordPack relation | `空のWordPack` badge and `開いて育てる` action | Open detail/preview and generate content later | Covered |
| Unregistered relation | `未登録` badge and `WordPackを作成` action | Create empty WordPack, then preview | Covered |
| Create pending | Button label changes to `作成中` and is disabled | Wait | Covered |
| Create error | Alert explains the failure and retry path | Retry creation or update | Covered |
| No selected source | Right panel disables primary open action and explains selection is required | Select a source WordPack | Covered |
| Narrow viewport | Single-column stack, visible bottom nav, all tabs readable | Scroll vertically | Browser-checked |
| Keyboard focus | Buttons, tabs, search, and quick actions keep semantic controls | Tab through controls | Tested structurally; manual focus regression risk remains low |

## Novice simulation

1. A first-time user lands on Explore and reads that saved WordPack connections can be found and unregistered words can be added.
2. The left column title `WordPackを選ぶ` identifies the starting point. The selected row shows the current source.
3. The status guide explains why some candidates can be previewed while others can be created.
4. In the center column, candidate cards show relation type, state, short meaning, and exactly one primary action.
5. Selecting `WordPackを作成` on an unregistered relation creates an empty WordPack and opens the preview, confirming that the action had an effect.

Novice result: pass. The screen no longer requires understanding internal values like `unknown`, `empty`, or `synonym` before acting.

## Accessibility review

- Semantic controls: mode tabs and quick actions are buttons with `aria-pressed`; create/open actions are labeled text buttons.
- Search input has a visible label and explicit placeholder.
- Async creation feedback uses `role="status"`; create failure uses `role="alert"`.
- Disabled primary action includes nearby explanatory text.
- Candidate cards avoid icon-only primary actions.
- Automated axe check passes for the loaded Explore state with `color-contrast` disabled because jsdom lacks the required canvas implementation.

## Visual hierarchy review

- Level 1: page title and purpose.
- Level 2: search/update and status legend.
- Level 3: source list, relation list, selected source summary.
- Level 4: candidate state and action per relation.

The layout now supports a left-to-right desktop scan: choose source, inspect candidates, act on selected source. On mobile it becomes a vertical flow with tabs visible as a compact grid and no horizontal page overflow.

## Counter-review

- Attempted to disprove completion by checking desktop and mobile layout for overflow, unreadable tab labels, and wrapped button text.
- Desktop 1440x900: update button, status guide, candidate cards, and right panel did not overflow.
- Mobile 390x844: initial horizontal overflow and tab visibility issues were found and fixed. Final check showed `scrollWidth` equals document width and no offscreen elements.
- Remaining concern: quick action buttons currently change mode but do not scroll the center column into view. This is not a blocker because the changed mode is visible in the tab state and users can scroll normally on mobile.

## Verification evidence

- `cd apps/frontend && npm test -- ExplorePage --run`: passed, 3 tests.
- `cd apps/frontend && npx tsc -p tsconfig.json`: passed.
- `cd apps/frontend && npm test -- --coverage --silent`: passed, 136 tests and 1 skipped integration test.
- `npx playwright test -c tests/e2e/playwright.config.ts tests/e2e/auth.spec.ts tests/e2e/guest.spec.ts tests/e2e/wordpack.spec.ts`: passed, 3 tests.
- Browser desktop 1440x900 against local mock API: no horizontal overflow; status guide, create action, and primary open action visible.
- Browser interaction: clicking `「文脈依存の」のWordPackを作成` created an empty WordPack and opened the WordPack preview dialog.
- Browser mobile 390x844: no horizontal overflow, all mode labels readable, primary create action present.
