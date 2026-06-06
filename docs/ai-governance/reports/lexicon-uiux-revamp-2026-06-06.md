# Lexicon UI/UX Revamp Review - 2026-06-06

## Scope

- Screen: `Lexicon`
- Change type: visible UI/UX, layout, navigation density, generation status, copy, responsive behavior
- Reviewer stance: implementation review plus counter-review against first-time user failure

## Severity Result

| Level | Result | Notes |
| --- | --- | --- |
| P0 | Clear | Purpose, first action, saved list, selected state, and generation status are visible. |
| P1 | Clear | Mobile heading wrap defect found during review and fixed. Axe violation found and fixed. |
| P2 | Accepted | Mobile filters still take vertical space, but no text fracture or page-level horizontal overflow remains. |

## State Matrix

| State | Expected user-visible behavior | Recovery / next action | Evidence |
| --- | --- | --- | --- |
| Authenticated / populated list | Recent items, saved list, counts, card actions, right-side generation/create panel are visible. | Open card, search, filter, create, or regenerate. | Playwright desktop screenshot and metrics. |
| Empty saved list | Empty message explains no saved WordPack exists and points to creating a new WordPack. | Use `新しいWordPack` / create panel. | Existing component state retained. |
| Loading list | Loading indicator remains in list region. | Wait or refresh. | Existing component state retained. |
| Search / no results | Existing filtered empty state remains tied to search controls. | Clear or change search/filter. | Existing component state retained. |
| Selection none | Bulk destructive action is hidden. | Select a card checkbox. | Unit test updated. |
| Selection active | Selection bar appears with count, select all, clear, and delete. | Clear selection or confirm delete. | Unit test updated and Playwright selection check. |
| Guest mode | Generate/delete actions remain disabled through `GuestLock`. | Sign in to use write actions. | Guest mode unit test updated. |
| Generation progress | Lexicon uses the right-side `生成キュー` instead of stacked bottom-right toasts. | Watch progress or clear completed history. | Component and screenshot review. |
| Mobile viewport | Recent list becomes compact horizontal list; header no longer fractures vertically; page has no horizontal overflow. | Scroll normally; bottom nav remains fixed. | Playwright 390x844 metrics. |

## Novice Simulation

1. First 3 seconds: the page says `Lexicon`, shows a short purpose line, and exposes `新しいWordPack`, `最近開いたWordPack`, `保存済みWordPack一覧`, and `生成キュー`.
2. First meaningful action: a user can either open a recent/saved card or press `新しいWordPack` to move to the create input.
3. Current location: sidebar highlight and main heading both identify Lexicon.
4. Operation scope: create/generation controls are separated in the right rail; saved-list controls stay inside the saved-list panel.
5. Destructive action: bulk delete is not shown until selection exists, reducing accidental scanning load.

## Accessibility Review

- Keyboard: primary actions are buttons with text labels; card menu and selection checkboxes have accessible names.
- Focus: existing focus-visible styles remain for interactive recent/card controls.
- Landmarks: right rail was changed from nested `aside` to a named section inside the main Lexicon area.
- Contrast: dark panels use light text and blue/red/green accents with non-color text labels.
- Automated check: `@axe-core/playwright` on `.app-shell` returned `violationCount: 0`.

## Visual Hierarchy Review

- Primary hierarchy: page title -> create shortcut -> recent items -> saved list -> cards.
- Secondary operations: sorting, filter, search, and selection are visually contained inside the saved-list panel.
- Right rail: generation queue and create form are visually separate from list management.
- Card styling: removed low-contrast purple card blocks; cards now use the same dark surface family as the page.
- Mobile correction: the saved-list heading previously wrapped into single-character vertical text at 390px. The header grid and mobile recent/filter density were adjusted.

## Counter-review

| Challenge | Result |
| --- | --- |
| Could a first-time user miss where to create a WordPack? | No. Top shortcut and right-side create panel both say `新しいWordPack`. |
| Could generated job status be confused with normal toasts? | Less likely. Lexicon now has a dedicated `生成キュー` with progress/completed grouping. |
| Could hidden bulk delete make multi-select undiscoverable? | Acceptable. The checkbox remains visible on cards; the bar appears immediately after selection. |
| Could mobile users see a broken heading? | Fixed after visual smoke caught vertical wrapping. |
| Could the right rail create invalid landmark nesting? | Fixed after axe reported `landmark-complementary-is-top-level`. |
| Could there be page-level horizontal overflow? | Desktop 1728px and mobile 390px checks both reported `overflowX: false`. |

## Evidence

- `cd apps/frontend && npx tsc -p tsconfig.json`
- `cd apps/frontend && npm test -- --run WordPackListPanel.header-layout.test.tsx WordPackListPanel.actions-layout.test.tsx WordPackListPanel.modal.test.tsx WordPackListPanel.bulk-delete.test.tsx WordPackListPanel.guest-mode.test.tsx WordPackListPanel.guest-public.test.tsx --silent`
- `cd apps/frontend && npm test -- --coverage --silent` (35 files passed, 1 skipped; 142 tests passed, 1 skipped)
- `git diff --check`
- Playwright visual smoke with mocked API:
  - Desktop 1728x1117: `overflowX=false`, first card at `y=572`, card size about `374x239`.
  - Mobile 390x844: `overflowX=false`, recent panel height `118`, sort controls height `211`, first card starts at `y=756`.
- Axe:
  - Before fix: 1 moderate `landmark-complementary-is-top-level` issue on `.lexicon-rail`.
  - After fix: `violationCount=0`.
