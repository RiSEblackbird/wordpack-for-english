# PR 433 review risk audit 2026-06-06

## Scope

- PR: https://github.com/RiSEblackbird/wordpack-for-english/pull/433
- Reviewed threads:
  - `apps/frontend/src/pages/ExplorePage/index.tsx`: relation labels were posted directly as lemmas.
  - `apps/frontend/src/pages/ExplorePage/index.tsx`: guest users could see enabled unknown-relation create actions.
- Audit target: repository-wide risk of user-visible write actions that either bypass client-side lemma validation or invite guest users into backend-rejected write actions.

## Review feedback handled in this branch

| Area | Risk | Action |
| --- | --- | --- |
| Explore relation creation | Example sentences and expression patterns could be sent to `POST /api/word/packs` as lemmas. | Shared `validateLemmaInput` now gates Explore creation, and `examples` / `pattern` relations are explicitly non-creatable with visible reasons. |
| Explore guest mode | Guest users could click `WordPackを作成`, then receive a 403 from the backend. | Explore now disables unknown-relation create actions for guests, shows a visible permission reason, and keeps the guest-lock affordance. |

## Repository-wide audit method

- Searched frontend write calls: `method: POST|PUT|PATCH|DELETE`, `generateWordPack`, `createEmptyWordPack`, `regenerateWordPack`, `updateGuestPublic`, `delete*`, `import*`.
- Searched guest protection: `GuestLock`, `isGuest`, `aria-disabled`, role-based custom buttons.
- Searched lemma validation: `lemmaValidation`, `LEMMA_ALLOWED_PATTERN`, `validate_lemma`, `WordPackCreateRequest`.
- Checked backend contracts:
  - `apps/backend/backend/models/word.py`
  - `apps/backend/backend/domain/wordpack/lemma.py`
  - `tests/test_api.py`
  - `tests/backend/test_guest_mode_middleware.py`

## Audit findings

| Severity | Location | Finding | User impact | Recommended follow-up |
| --- | --- | --- | --- | --- |
| P1 | `apps/frontend/src/components/wordpack/ExamplesSection.tsx` and `apps/frontend/src/features/wordpack/components/WordPackPanel/WordPackPanelContainer.tsx` | Example text tokens can trigger `triggerUnknownLemmaGeneration` from a custom `role="button"` row. This path is not protected by `GuestLock` and does not use client-side lemma validation before calling `generateWordPack`. | A guest can activate an unknown token and get a backend 403 instead of a permission explanation. A very long token could also fail only after the request. | Add guest and `validateLemmaInput` guards to `triggerUnknownLemmaGeneration`, expose a visible/announced reason, and update tests for guest + invalid token paths. |
| P2 | `apps/frontend/src/hooks/useWordPack.ts` | `generateWordPack(lemma)` and `createEmptyWordPack(lemma)` accept arbitrary strings and rely on callers/backend validation. The main form now validates, but hook-level callers can still bypass it. | Future callers may repeat the Explore bug by passing non-lemma strings. Backend remains safe, but UI could offer actions that fail late. | Consider central hook-level validation or a typed helper that returns a rejected status before network calls. |

## Areas checked with no matching risk found

| Area | Result |
| --- | --- |
| Lexicon / WordPack generation form | Uses `useWordPackForm` and now the shared `validateLemmaInput`; controls are wrapped in `GuestLock`. |
| Explore | Review feedback fixed in this branch. Invalid example/pattern candidates and guest creation are disabled before network calls. |
| WordPack list | Delete, regenerate, and guest-public update controls are guest-locked; they operate on existing WordPack IDs, not arbitrary lemmas. |
| Article import and article detail | Import, generate, regenerate, and delete controls are guest-locked; related WordPack actions operate on existing IDs. |
| Article list and example list | Destructive selection and delete actions are guest-locked; no arbitrary lemma creation path found. |
| Example detail modal | Study progress and typing-record writes are guest-locked; no arbitrary lemma creation path found. |
| TTS | Text length is checked client-side and the action is guest-locked. |
| Backend | `WordPackCreateRequest` / `WordPackRequest` enforce lemma length and character constraints; guest write middleware rejects write APIs with 403. |

## Current status

- P0: none found after the Explore review fixes.
- P1: one existing cross-repo issue remains in the example-token unknown generation path.
- P2: one architectural hardening opportunity remains in `useWordPack` write helpers.

The remaining P1/P2 items are outside the two PR review threads that were fixed here and are intentionally reported for follow-up direction rather than silently expanding this change.
