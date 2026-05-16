## Summary

- WordPack router を `backend.routers.word` package に分割し、lookup / pack / generation / regeneration / examples / study progress / guest public / lemma lookup の責務を分けました。
- Firestore helper / mapper / repository alias を `backend.infrastructure.firestore` に追加し、`AppFirestoreStore` は legacy facade として維持しました。
- Frontend の App shell、login、sidebar、bottom nav、keyboard shortcut、CSS を `src/app` 配下へ分離しました。
- `WordPackPanel` と `ArticleImportPanel` を feature 配下へ移し、旧 component path は compatibility re-export にしました。
- `src/shared/api` と `src/shared/events` に API error parse と custom event helper を集約しました。
- 既存 API path、request/response shape、Firestore schema、認証・ゲスト閲覧挙動、URL routing、custom event 名、legacy import path は維持しています。

## Major changes

### Backend

- `backend.routers.word.__init__` を互換 facade とし、既存 tests が monkeypatch する `store`、`run_wordpack_flow`、`generate_word_pack_id`、`_regenerate_jobs` を維持しました。
- `lookup_routes.py`、`pack_routes.py`、`generation_routes.py`、`regeneration_routes.py`、`example_routes.py`、`study_progress_routes.py`、`guest_public_routes.py`、`lemma_routes.py` に endpoint を分割しました。
- `dependencies.py` で package 側の legacy monkeypatch を実行時に解決し、router 分割後も既存テストの差し替え契約を維持しました。
- `error_mapping.py` に LLM JSON parse / empty content の HTTPException mapping を集約しました。
- `backend.domain.wordpack.lemma` に lemma validator を移し、`backend.models.word._validate_lemma` は compatibility export として残しました。
- `backend.infrastructure.firestore.batch`、`search_terms`、`mappers`、`repositories` を追加し、Firestore schema を変えずに helper 境界を明確にしました。

### Frontend

- `src/app/App.tsx` は `ThemeApplier`、`AuthGate`、`AppShell` の composition に絞りました。
- `AppShell.tsx` に route/sidebar state を閉じ込め、`Header.tsx`、`Sidebar.tsx`、`BottomNav.tsx`、`LoginScreen.tsx`、`GoogleLoginCard.tsx`、`keyboardShortcuts.ts`、`navigation.ts` に分割しました。
- 旧 inline CSS を `src/app/styles/app-shell.css` と `src/app/styles/login.css` へ移しました。
- `src/components/WordPackPanel.tsx` は `src/features/wordpack/components/WordPackPanel` の re-export にし、section component を feature 配下へ切り出しました。
- `src/components/ArticleImportPanel.tsx` は `src/features/article-import/components/ArticleImportPanel` の re-export にし、article API helper を feature 配下に追加しました。
- `src/shared/api/fastapiDetail.ts` と `src/shared/events/appEvents.ts` を追加し、FastAPI error detail と custom event 名を一箇所に集約しました。

### Docs / CI

- `docs/architecture.md` と `README.md` に新しい backend/frontend module 責務、compatibility shim、維持契約を追記しました。
- 本 PR body draft を今回の分割内容に合わせて更新しました。

### Compatibility

- `backend.main:app` と `backend.main:create_app` を維持しました。
- `backend.config` facade を維持しました。
- `backend.routers.word` の legacy monkeypatch 対象を維持しました。
- `backend.store.store`、`backend.store.AppFirestoreStore`、`backend.store.firestore_store.*` を維持しました。
- `backend.models.word` と `_validate_lemma` を維持しました。
- `apps/frontend/src/App.tsx`、`src/components/WordPackPanel.tsx`、`src/components/ArticleImportPanel.tsx`、`src/hooks/useWordPack.ts`、`src/lib/fetcher.ts` は legacy import path として維持しました。
- Custom event 名 `auth:unauthorized`、`wordpack:updated`、`wordpack:study-progress`、`article:updated` を維持しました。

## Tests

- [x] `ENVIRONMENT=test FIRESTORE_EMULATOR_HOST=localhost:8080 FIRESTORE_PROJECT_ID=test-project GCP_PROJECT_ID=test-project ADMIN_EMAIL_ALLOWLIST=test@example.com SESSION_SECRET_KEY=testing-secret-key-with-32-characters python3 -m pytest` — 206 passed, 2 skipped
- [x] `ENVIRONMENT=test FIRESTORE_EMULATOR_HOST=localhost:8080 FIRESTORE_PROJECT_ID=test-project GCP_PROJECT_ID=test-project ADMIN_EMAIL_ALLOWLIST=test@example.com SESSION_SECRET_KEY=testing-secret-key-with-32-characters PYTHONPATH=apps/backend python3 -m pytest` — 206 passed, 2 skipped
- [x] `ENVIRONMENT=test FIRESTORE_EMULATOR_HOST=localhost:8080 FIRESTORE_PROJECT_ID=test-project GCP_PROJECT_ID=test-project ADMIN_EMAIL_ALLOWLIST=test@example.com SESSION_SECRET_KEY=testing-secret-key-with-32-characters PYTHONPATH=apps/backend python3 -m pytest -q --no-cov tests/test_security_headers.py` — 2 passed
- [x] `cd apps/frontend && npm ci`
- [x] `npm ci`
- [x] `cd apps/frontend && npx tsc -p tsconfig.json`
- [x] `cd apps/frontend && npm test -- --coverage --silent` — 133 passed, 1 skipped
- [x] `cd apps/frontend && npm run build`
- [x] `npm run e2e` — 9 passed
- [x] `npx playwright test -c tests/e2e/playwright.config.ts tests/e2e/auth.spec.ts tests/e2e/guest.spec.ts tests/e2e/wordpack.spec.ts` — 3 passed

## Not run

- None.

## Risk areas

- Firestore repository 境界は互換 shim を残した段階的移行です。完全な store 解体は次段階の対象です。
- WordPack regeneration job は in-memory registry のまま application service へ分離しています。複数 worker / 再起動耐性は従来どおりありません。
- AppShell/sidebar CSS は構造分割後も既存挙動を維持しています。macOS で E2E を通すため Darwin visual snapshots を追加しました。
- `auth:unauthorized` event dispatch と custom event helper は shared API/events へ分離しています。イベント名は維持しています。
- `npm ci` は成功しましたが、既存 dependency に npm audit 指摘があります。依存更新は今回のリファクタリング範囲外として未変更です。

## Follow-up

- `backend.store.AppFirestoreStore` の完全な repository 分割は、Firestore schema を変えずに別 PR で段階的に進める余地があります。
- npm audit 指摘は別タスクで依存更新方針と破壊的変更の有無を確認してください。
