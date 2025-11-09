# WordPack for English

英単語トレーナー。バックエンド（FastAPI）とフロントエンド（React + Vite）のモノレポです。

| WordPack | 文章インポート | 例文一覧 |
|---|---|---|
| <img width="600" alt="image" src="https://github.com/user-attachments/assets/11c5cb6c-dcb8-4ad2-9bfb-0c47bef9b0a4" /> | <img width="600" alt="image" src="https://github.com/user-attachments/assets/8fbf2d62-69e7-48f9-b7ba-7eb34e6fcd40" /> | <img width="600" alt="image" src="https://github.com/user-attachments/assets/6d01da80-3844-4641-a93c-efb7414f65d2" /> |
| <img width="600" alt="image" src="https://github.com/user-attachments/assets/7932f36a-68cb-4acd-8ce7-113a8139a8d9" /> | <img width="600" alt="image" src="https://github.com/user-attachments/assets/860e20ce-2651-4c39-891c-894b56ff7a4d" /> | <img width="600" alt="image" src="https://github.com/user-attachments/assets/4dae1671-38c7-4482-a632-4dffed49dacd" /> |
| <img width="600" alt="image" src="https://github.com/user-attachments/assets/8427f4fa-a718-4cf4-b761-e3fb90acd252" /> |  |  |

## 主な機能
- バックエンド: FastAPI / フロントエンド: React + TypeScript + Vite
- WordPack の生成・再生成・永続化
- 発音情報（IPA/音節/強勢）の付与
- 例文（Dev/CS/LLM/Business/Common）の追加・削除
- 文章インポートと関連 WordPack の紐付け
- OpenAI gpt-4o-mini-tts を用いた例文／日本語訳／インポート文章／WordPack語彙（一覧・プレビュー）の音声再生（「音声」ボタン）
- 保存済みWordPack一覧で語義タイトルを即座に確認できる「語義」ボタンと「語義一括表示」スイッチ、例文未生成のカードから直接生成できる「生成」ボタン
- WordPack・文章・例文の一覧で複数選択して一括削除できる管理機能
- 例文一覧で訳文を一括開閉できる「訳一括表示」スイッチ
- 画面左上のハンバーガーボタンで共通サイドバーを開閉し、左側からスライド表示されるメニュー経由で主要タブ（WordPack / 文章インポート / 例文一覧 / 設定）へ移動可能。メニュー項目を選択してもサイドバーは開いたままで、開いている間はサイドバーが左端に固定されます。十分な横幅がある場合はメイン画面の配置を保ったまま余白内でサイドバーが表示され、スペースが足りない場合のみメイン画面が残り幅に収まるよう自動でスライドします
- WordPack プレビューの例文中ハイライト（lemma）にマウスオーバー0.5秒で `sense_title` ツールチップ表示。対応する lemma が見つからない場合は、最小サイズのポップオーバーに「〇〇 の WordPack を生成」ボタンだけが表示されます。ボタンを押すか、該当の単語（lemma-token）をクリックすると即座に生成が始まり、完了後に「WordPack概要」ウインドウが自動で開きます

## クイックスタート

### 前提
- Python 3.13+
- Node.js 18+

### セットアップ
```bash
# Python（リポジトリルートで）
python -m venv .venv
. .venv/Scripts/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Frontend
cd apps/frontend
npm install
```

### Google OAuth クライアントの準備
1. [Google Cloud Console](https://console.cloud.google.com/) にアクセスし、対象プロジェクトを作成または選択します。
2. 左側メニューの「API とサービス」→「OAuth 同意画面」でユーザータイプを選択し、アプリ名・サポートメールなどを登録して公開ステータスまで設定します。
3. 「API とサービス」→「認証情報」から「認証情報を作成」→「OAuth クライアント ID」を選び、アプリケーションの種類に「ウェブアプリケーション」を指定します。
4. 「承認済みの JavaScript 生成元」には `http://127.0.0.1:5173` と `http://localhost:5173` を追加します（HTTPS 環境を用意済みなら該当 URL も追加）。
5. 「承認済みのリダイレクト URI」には `http://127.0.0.1:5173` と `http://localhost:5173` を追加します。Google Identity Services のポップアップ版を使うため、同一オリジンを登録しておくとローカル開発でのログインが安定します。
6. 生成されたクライアント ID を控え、JSON シークレットをダウンロードする場合は `google-oauth-client-secret.json` などの名称で保管してください（`.gitignore` によって Git 管理外になります）。

### 環境変数
```bash
cp env.example .env
# .env に OPENAI_API_KEY を設定
# Google ログインを利用する場合は以下も設定（ドメイン制限は任意）
# GOOGLE_CLIENT_ID=12345-abcdefgh.apps.googleusercontent.com
# GOOGLE_ALLOWED_HD=example.com
# SESSION_SECRET_KEY=change-me-to-random-value
# SESSION_COOKIE_NAME=wp_session
# SESSION_COOKIE_SECURE=true  # 本番(HTTPS)のみ true。開発(HTTP)は既定で false なので設定不要
```

ローカル開発（ENVIRONMENT=development など）では Secure 属性が既定で無効になり、HTTP サーバーでも `wp_session` Cookie が配信されます。本番で HTTPS を使う場合は `.env` または環境変数で `SESSION_COOKIE_SECURE=true` を指定してください。

フロントエンド側でも同じクライアントIDを参照できるように、`apps/frontend/.env` を作成して Vite の環境変数を指定してください。

```bash
cd apps/frontend
cp .env.example .env  # 無い場合は自作でOK
echo "VITE_GOOGLE_CLIENT_ID=12345-abcdefgh.apps.googleusercontent.com" >> .env
```

`VITE_GOOGLE_CLIENT_ID` はバックエンドの `GOOGLE_CLIENT_ID` と一致している必要があります。Google Console で発行した OAuth 2.0 Web クライアント ID を指定してください。

バックエンド・フロントエンドのどちらも起動前に `.env` と `apps/frontend/.env` を用意し、`GOOGLE_CLIENT_ID`（必要に応じて `GOOGLE_ALLOWED_HD`）、`SESSION_SECRET_KEY`、`VITE_GOOGLE_CLIENT_ID` を設定しておくと、初回起動から Google ログインが有効になります。

### 起動
```bash
# Backend（リポジトリルートで）
python -m uvicorn backend.main:app --reload --app-dir apps/backend

# Frontend
cd apps/frontend
npm run dev
```

### Docker（任意）
```bash
docker compose up --build
```
- Backend: http://127.0.0.1:8000
- Frontend: http://127.0.0.1:5173
- `apps/frontend/docker-entrypoint.sh` が起動時に依存を確認し、`node_modules/@react-oauth/google` が不足している場合は自動で `npm install` を実行します。このため、新しいフロントエンド依存を追加してもコンテナの再ビルドは不要です。

### 認証フロー
- フロントエンドへアクセスすると、まず Google アカウントでのサインイン画面が表示されます。
- 「Googleでログイン」ボタンを押下するとポップアップが開き、承認後に `/api/auth/google` へ ID トークンを送信してセッション Cookie を取得します。
- 画面右上の「設定」タブにある「ログアウト（Google セッションを終了）」ボタンから明示的にサインアウトできます。ログアウト時は `/api/auth/logout` へ通知した上でセッション Cookie を削除し、再びサインイン画面へ戻ります。
- 既存のセッション Cookie が有効な状態でリロードした場合は、ローカルに保存されたユーザー情報を使って自動的に復元されます（Cookie が無効化されている場合は再ログインが必要です）。
- ログイン中は「設定」タブの上部にメールアドレスと表示名が表示されます。別アカウントに切り替えたい場合は一度ログアウトし、再度「Googleでログイン」ボタンから希望するアカウントを選択してください。

## テスト
- Backend（Python）
```bash
pytest
```
- Frontend（Vitest）
```bash
cd apps/frontend
npm run test
```

## REST API（抜粋）
- `POST /api/word/pack` … WordPack を生成して語義タイトル・語義・例文・語源・学習カード要点を返却
- `POST /api/word/examples/bulk-delete` … 例文IDの配列を受け取り一括削除
- `POST /api/tts` … OpenAI gpt-4o-mini-tts で読み上げた音声（audio/mpeg）をストリーミング返却

## ディレクトリ
```
apps/backend/backend/   # FastAPI アプリ
apps/frontend/          # React + Vite
tests/                  # Python テスト
docs/                   # 詳細ドキュメント
```

## 追加ドキュメント
- 詳細な API・フロー・モデルは `docs/flows.md`, `docs/models.md`, `docs/環境変数の意味.md` を参照してください。
- ユーザー向け操作は `UserManual.md` を参照してください。
- GitHub Actions の CI では Chrome DevTools MCP を利用した UI スモークテスト（`UI smoke test (Chrome DevTools MCP)` ジョブ）が自動実行されます。ローカルで同じシナリオを再現する方法は `docs/testing/chrome-devtools-mcp-ui-testing.md` を参照してください（Node.js 22 を用い、ルートディレクトリで `npm run smoke` または `tests/ui/mcp-smoke/run-smoke.mjs` を実行する手順を含みます）。Chrome 未インストール環境でも安定版 Chrome の自動取得を試み、許可されない場合は OSS Chromium へのフォールバックを順番に実施します。いずれもダウンロードできなかった場合は `CHROME_EXECUTABLE` で既存バイナリを指定しない限りローカル実行のみスキップする挙動です。
