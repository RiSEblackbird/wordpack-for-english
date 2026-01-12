# フロントエンド統合テスト（実バックエンド接続）

## 目的
- フロントエンドから実HTTPで `/api/word/pack` を叩き、画面が更新されるまでを検証する。
- MSW モックでは検知できない「バックエンド起動・実データ連携」の回帰を早期に捕捉する。

## 前提（バックエンド起動）
1. Firestore エミュレータを起動する（例: `make firestore-emulator`）。
2. バックエンドをローカル起動する（例: `DISABLE_SESSION_AUTH=true python -m uvicorn backend.main:app --app-dir apps/backend`）。
   - `DISABLE_SESSION_AUTH=true` は認証を無効化し、テストで `POST /api/word/pack` を通すために必要です。
   - 生成処理には LLM を利用するため、`.env` に `OPENAI_API_KEY` を設定してください。
   - Firestore への書き込みに必要な `FIRESTORE_PROJECT_ID` / `FIRESTORE_EMULATOR_HOST` を `.env` または環境変数で設定してください。

## テスト実行
- **正例（推奨）**:
  ```bash
  # backend を 127.0.0.1:8000 で起動している場合
  cd apps/frontend
  INTEGRATION_TEST=true BACKEND_PROXY_TARGET=http://127.0.0.1:8000 npm run test
  ```
- **負例（NG: 統合テストがスキップされる）**:
  ```bash
  # INTEGRATION_TEST が未設定のまま実行すると統合テストは skip されます
  cd apps/frontend
  npm run test
  ```

## 補足
- `INTEGRATION_TEST=true` のときは `vitest.setup.ts` で MSW を無効化し、実HTTP通信に切り替えています。
- `BACKEND_PROXY_TARGET` はバックエンドの起動先オリジンを指定します（既定: `http://127.0.0.1:8000`）。
