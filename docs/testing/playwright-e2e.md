# Playwright E2E テスト

## 目的
- フロントエンドとバックエンドを同時に起動し、主要導線の回帰を E2E で確認します。
- 失敗時は trace / screenshot / video を保存し、原因解析を容易にします。

## 前提
- Node.js 22+ と Python 実行環境が利用できること。
- Firestore エミュレータを使う場合は、別ターミナルで起動しておくこと。

## 実行方法

### 正例（ローカルでフル起動）
```
E2E_BASE_URL=http://127.0.0.1:5173 npm run e2e
```

### 負例（依存サーバ未起動のまま実行）
```
npm run e2e
# → webServer の起動やヘルスチェックに失敗し、テストが開始できない
```

## 成果物
- HTML レポート: `playwright-report/`
- 失敗時の trace / screenshot / video: `test-results/`

## CI 実行
- PR 向けのスモーク（`pull_request`）: `auth.spec.ts` / `guest.spec.ts` / `wordpack.spec.ts` の主要導線のみを実行します。
- 夜間回帰（`schedule (cron: 0 2 * * *)` / `workflow_dispatch`）: Chromium で全シナリオを実行します。
- 週次クロスブラウザ（`schedule (cron: 0 3 * * 1)` / `workflow_dispatch`）: Firefox / WebKit で全シナリオを実行します。
- CI の成果物は GitHub Actions の該当ワークフロー実行ページ → Artifacts から取得できます。
  - `playwright-report/` と `test-results/` を保存し、保持期間は 90 日です。

## 補足
- `tests/e2e/playwright.config.ts` に `baseURL` や `timeout`、成果物の出力先を集約しています。
- `BACKEND_PROXY_TARGET` は Vite のプロキシ先を固定するために `127.0.0.1:8000` を使用します。
