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
| Example-token unknown generation | Example text tokens could trigger WordPack generation without guest or lemma guards. | Unknown-token generation now checks guest mode and shared lemma validation before network calls, and reports visible/announced reasons when blocked. |
| WordPack write helpers | `generateWordPack` and `createEmptyWordPack` could be called with unvalidated arbitrary strings. | The hook now validates and normalizes lemmas before starting notifications or network calls. |

## Repository-wide audit method

- Searched frontend write calls: `method: POST|PUT|PATCH|DELETE`, `generateWordPack`, `createEmptyWordPack`, `regenerateWordPack`, `updateGuestPublic`, `delete*`, `import*`.
- Searched guest protection: `GuestLock`, `isGuest`, `aria-disabled`, role-based custom buttons.
- Searched lemma validation: `lemmaValidation`, `LEMMA_ALLOWED_PATTERN`, `validate_lemma`, `WordPackCreateRequest`.
- Checked backend contracts:
  - `apps/backend/backend/models/word.py`
  - `apps/backend/backend/domain/wordpack/lemma.py`
  - `tests/test_api.py`
  - `tests/backend/test_guest_mode_middleware.py`

## Audit findings after remediation

| Severity | Location | Finding | User impact | Status |
| --- | --- | --- | --- | --- |
| P1 | `apps/frontend/src/components/wordpack/ExamplesSection.tsx` and `apps/frontend/src/features/wordpack/components/WordPackPanel/WordPackPanelContainer.tsx` | Example text tokens can trigger `triggerUnknownLemmaGeneration` from a custom `role="button"` row. This path was not protected by `GuestLock` and did not use client-side lemma validation before calling `generateWordPack`. | A guest could activate an unknown token and get a backend 403 instead of a permission explanation. A very long token could also fail only after the request. | Resolved. Guest and invalid candidates are blocked before write requests; tooltip/status copy explain the reason. |
| P2 | `apps/frontend/src/hooks/useWordPack.ts` | `generateWordPack(lemma)` and `createEmptyWordPack(lemma)` accepted arbitrary strings and relied on callers/backend validation. | Future callers could repeat the Explore bug by passing non-lemma strings. Backend remained safe, but UI could offer actions that fail late. | Resolved. Hook-level validation stops invalid values before notifications or network calls. |

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

- P0: none found after the Explore review fixes and follow-up remediation.
- P1: none remaining from this audit.
- P2: none remaining from this audit.

The previously reported P1/P2 items were remediated in this branch after follow-up approval.
