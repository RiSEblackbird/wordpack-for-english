## Summary

- Backend / Frontend 全体にまたがる大規模アーキテクチャリファクタリングを行いました。
- FastAPI の app factory、middleware stack、lifecycle、router 登録、observability を分離しました。
- application/usecase と repository 境界を導入し、router と Firestore store への直接依存を弱めました。
- WordPack / Article import の LLM prompt、JSON parser、lemma filter、生成 orchestration の責務を分離しました。
- Frontend の AppShell、auth telemetry、WordPack feature の hooks/API/types、shared API client を分割しました。
- 既存 API path、request/response shape、Firestore schema、認証・ゲスト閲覧挙動、主要 UI 挙動は維持しています。

## Major changes

### Backend

- `backend.main` を薄い entrypoint にし、`backend.app.factory` / `middleware_stack` / `routers` / `lifecycle` へ FastAPI 起動責務を移しました。
- Cloud Trace header parser と access log/metrics middleware を `backend.observability` 配下へ分離し、既存 import 互換も残しました。
- `backend.settings` package を導入し、環境変数、auth、Firestore、security、observability の設定責務を分けました。
- `backend.config` は facade として残し、`from backend.config import settings` / `Settings` の互換性を維持しました。
- `backend.infrastructure.firestore` と `backend.domain.*` に repository/record 境界を追加し、`backend.store.store` は互換 shim として維持しました。
- WordPack router から生成、lookup、空 WordPack 作成、study progress、guest public、regeneration job registry を `backend.application.wordpack` へ移しました。
- WordPackFlow の prompt builder と JSON response parser を `backend.infrastructure.llm` に分離し、code fence stripping と control character sanitize を共通化しました。
- Article import の lemma filtering を `backend.domain.article.lemma_filter` に集約し、function word / basic lemma 除外と multi-word phrase 維持を一元化しました。
- Firestore エミュレータ未起動の pytest では、実エミュレータ結合テストを除き in-memory fake client を使う互換経路を追加し、既存の実エミュレータテストの契約は維持しました。
- CI の frontend Node version を root `package.json` の engines と整合する `20.19.0` に揃えました。

### Frontend

- `src/App.tsx` を互換 entrypoint にし、実体を `src/app/App.tsx` と `ThemeApplier.tsx` に移しました。
- Google OAuth telemetry sanitization を `src/features/auth` に分離しました。
- WordPack の domain types と API helper を `src/features/wordpack` に移し、旧 `src/hooks/useWordPack.ts` から re-export できる互換性を残しました。
- `src/shared/api` に `ApiError`、`fetchJson`、FastAPI detail parse、`auth:unauthorized` event dispatch を分離しました。
- `src/lib/fetcher.ts` は既存 import path 用の compatibility re-export として維持しました。
- production path の debug `console.log` を削除しました。
- `wordpack:updated`、`wordpack:study-progress`、`auth:unauthorized` の custom event は維持しています。

### Docs / CI

- `docs/architecture.md` を追加し、分割後の backend/frontend の責務配置と互換 shim を記載しました。
- `docs/flows.md`、`docs/infrastructure.md`、`docs/環境変数の意味.md`、`README.md` の関連箇所を新構造に合わせて更新しました。
- `deploy-production.yml` は手動実行フォールバックとして残し、main push の本番デプロイは CI 内の `deploy_production` job に集約しました。

### Compatibility

- `backend.main:app` と `backend.main:create_app` を維持しました。
- `backend.config` facade を維持しました。
- `backend.store.store`、`backend.store.AppFirestoreStore`、`backend.store.firestore`、`_build_firestore_client` など既存テスト・既存 import 向けの互換 export を維持しました。
- `apps/frontend/src/App.tsx`、`src/hooks/useWordPack.ts`、`src/lib/fetcher.ts` は legacy import path として維持しました。

## Tests

- [x] `pytest`
- [x] `PYTHONPATH=apps/backend pytest`
- [x] `cd apps/frontend && npm ci`
- [x] `cd apps/frontend && npx tsc -p tsconfig.json`
- [x] `cd apps/frontend && npm test -- --coverage --silent`
- [x] `cd apps/frontend && npm run build`
- [x] `npm ci`

## Not run

- [ ] `npm run e2e`

`npm run e2e` は実行しましたが、ローカルの Playwright Chromium binary が未インストールのため、ブラウザ起動前に失敗しました。backend/frontend の web server 起動までは確認済みです。初回は system Python に `uvicorn` が無く失敗したため、backend 検証用 venv を PATH へ優先指定して再実行しましたが、最終的に Chromium binary 不足で停止しました。

## Risk areas

- Middleware 登録順序は旧挙動を維持するよう移植していますが、production proxy / CORS / security header の組み合わせは本番相当環境で再確認してください。
- Firestore repository 境界は互換 shim を残した段階的移行です。完全な store 解体は次段階の対象です。
- WordPack regeneration job は in-memory registry のまま application service へ分離しています。複数 worker / 再起動耐性は従来どおりありません。
- Article lemma filtering は domain 関数へ集約しました。filter 結果の契約は既存テストで確認していますが、実記事での候補語感は継続確認が必要です。
- AppShell/sidebar CSS は構造分割後も既存挙動を維持していますが、Playwright の視覚回帰はローカル Chromium 不足により未完了です。
- `auth:unauthorized` event dispatch は shared API へ分離しています。既存 import path は維持しています。

## Follow-up

- Playwright Chromium を導入した環境で `npm run e2e` を再実行してください。
- `backend.store.AppFirestoreStore` の完全な repository 分割は、Firestore schema を変えずに別 PR で段階的に進める余地があります。
