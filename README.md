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
- 例文詳細モーダルから文字起こしタイピング練習を記録し、一覧にもバッジとして回数を反映する「文字起こしタイピング」機能
- 画面左上のハンバーガーボタンで共通サイドバーを開閉し、左側からスライド表示されるメニュー経由で主要タブ（WordPack / 文章インポート / 例文一覧 / 設定）へ移動可能。メニュー項目を選択してもサイドバーは開いたままで、開いている間はサイドバーが左端に固定されます。十分な横幅がある場合はメイン画面の配置を保ったまま余白内でサイドバーが表示され、スペースが足りない場合のみメイン画面が残り幅に収まるよう自動でスライドします
- ヘッダー右端に GitHub リンクと「ログアウト」ボタンを常設。どのタブからでもワンクリックでセッションを終了でき、共有端末の利用でも安全にサインアウトできます
- WordPack プレビューの例文中ハイライト（lemma）にマウスオーバー0.5秒で `sense_title` ツールチップ表示。対応する lemma が見つからない場合は、最小サイズのポップオーバーに「〇〇 の WordPack を生成」ボタンだけが表示されます。ボタンを押すか、該当の単語（lemma-token）をクリックすると即座に生成が始まり、完了後に「WordPack概要」ウインドウが自動で開きます

> **文章インポートの入力上限:** 1回のインポートで送信できる文章は最大 4,000 文字です。これを超えるリクエストはバックエンドが `413 Request Entity Too Large`（`error=article_import_text_too_long`）で拒否し、フロントエンドでもボタンが無効化されて警告文が表示されます。長文を扱う場合は 4,000 文字以内に分割して順番にインポートしてください。

> **音声読み上げの入力上限:** Text-to-Speech の読み上げ対象テキストは最大 500 文字です。上限を超えるとバックエンドが `413 Request Entity Too Large`（`error=tts_text_too_long`）を返し、フロントエンドでも送信前にアラートで通知されます。長文を読み上げたい場合は 500 文字以内へ調整した上で複数回に分割してください。

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
# ADMIN_EMAIL_ALLOWLIST=admin@example.com,owner@example.com
# CORS_ALLOWED_ORIGINS=http://127.0.0.1:5173,http://localhost:5173
# SESSION_SECRET_KEY=Qv6G5zH1pN8wX4rT7yL2mC9dF0sJ3kV5bR1nP7tW4qY8uZ6  # 32文字以上の乱数文字列を必ず使用
# SESSION_COOKIE_NAME=wp_session
# SESSION_COOKIE_SECURE=true  # 本番(HTTPS)のみ true。開発(HTTP)は既定で false なので設定不要
# GOOGLE_CLOCK_SKEW_SECONDS=60  # Google IDトークン検証時に許容する時計ずれ（秒）
```

ローカル開発（ENVIRONMENT=development など）では Secure 属性が既定で無効になり、HTTP サーバーでも `wp_session` Cookie が配信されます。本番で HTTPS を使う場合は `.env` または環境変数で `SESSION_COOKIE_SECURE=true` を指定してください。

特定の Google アカウントだけに利用者を絞り込みたい場合は、カンマ区切りでメールアドレスを列挙した `ADMIN_EMAIL_ALLOWLIST` を設定してください。値は小文字に正規化され、完全一致したアドレスのみが `/api/auth/google` の認証を通過します（未設定または空文字の場合は従来どおり全アカウントを許可します）。

`SESSION_SECRET_KEY` は 32 文字以上の十分に乱数性を持つ文字列を必ず指定してください。`change-me` など既知のプレースホルダーや短い値を設定すると、アプリケーション起動時に検証エラーとなり実行が停止します。外部に公開する環境では `openssl rand -base64 48` などで生成した値を `.env` へ保存し、リポジトリへコミットしない運用を徹底してください。

`CORS_ALLOWED_ORIGINS` を設定すると、指定したオリジンからのみ資格情報付き CORS を許可します。ローカル開発では `http://127.0.0.1:5173,http://localhost:5173` を指定すると従来どおりフロントエンドと連携できます。未設定の場合はワイルドカード許可となりますが、`Access-Control-Allow-Credentials` は返さないためクッキー連携が無効化されます。

フロントエンド側でも同じクライアントIDを参照できるように、`apps/frontend/.env` を作成して Vite の環境変数を指定してください。

```bash
cd apps/frontend
cp .env.example .env  # 無い場合は自作でOK
echo "VITE_GOOGLE_CLIENT_ID=12345-abcdefgh.apps.googleusercontent.com" >> .env
```

`VITE_GOOGLE_CLIENT_ID` はバックエンドの `GOOGLE_CLIENT_ID` と一致している必要があります。Google Console で発行した OAuth 2.0 Web クライアント ID を指定してください。

バックエンド・フロントエンドのどちらも起動前に `.env` と `apps/frontend/.env` を用意し、`GOOGLE_CLIENT_ID`（必要に応じて `GOOGLE_ALLOWED_HD` や `ADMIN_EMAIL_ALLOWLIST`）、`SESSION_SECRET_KEY`、`VITE_GOOGLE_CLIENT_ID` を設定しておくと、初回起動から Google ログインが有効になります。

補足（時計ずれの吸収）  
`GOOGLE_CLOCK_SKEW_SECONDS` を指定すると、Google の ID トークン検証で `iat`/`nbf`/`exp` の境界に対して指定秒数のゆとりを持たせます。既定は 60 秒で、Docker/WSL などの軽微な時計ずれによる “Token used too early” を回避できます（セキュリティ上の影響は軽微ですが、必要最小限の値にしてください）。

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

### Cloud Run へのデプロイ
- Cloud Run のサービスには `CORS_ALLOWED_ORIGINS` をデプロイ時の環境変数として指定し、本番ドメイン（例: `https://app.example.com,https://admin.example.com`）を列挙します。
- フロントエンドと同一ドメインでホストする場合も、バックエンドにアクセスするオリジンを完全一致で登録してください。HTTPS を使う環境では `SESSION_COOKIE_SECURE=true` も併せて指定します。
- ドメインを追加した場合は Cloud Run の再デプロイで環境変数を更新し、反映後に `OPTIONS /healthz` などで `Access-Control-Allow-Origin` ヘッダーが意図した値になっているか確認してください。

### 認証フロー
- フロントエンドへアクセスすると、まず Google アカウントでのサインイン画面が表示されます。
- 「Googleでログイン」ボタンは Google Identity Services の `GoogleLogin` コンポーネントを用いており、承認後に `credential`（ID トークン）を取得して `/api/auth/google` へ送信し、セッション Cookie を受け取ります。credential が欠落した場合は直ちにエラー帯を表示し、`/api/diagnostics/oauth-telemetry` へ状況を送信して原因調査に活用します。
- バックエンド側で `ADMIN_EMAIL_ALLOWLIST` を設定している場合、リストに含まれないメールアドレスは検証後でも即座に 403 となり、構造化ログには `google_auth_denied` / `email_not_allowlisted` が記録されます。利用者を追加したい場合はリストへメールアドレスを追記して再起動してください。
- バックエンドの構造化ログでは `google_auth_succeeded` を含むすべての Google 認証イベントで `email_hash`（および `display_name_hash`）が記録され、平文のメールアドレスや表示名は Cloud Logging へ送出されません。調査時はハッシュ値で突き合わせてください。
- ポップアップは locale=ja で描画され、共有端末でも毎回アカウント選択ダイアログが表示されます。別アカウントでログインしたい場合は表示されたポップアップで希望のアカウントを選択してください。選択後の動作は従来どおり `/api/auth/google` の検証とセッションクッキー付与で完結します。
- ヘッダー右側の「ログアウト」ボタン、または「設定」タブ下部の「ログアウト（Google セッションを終了）」ボタンから明示的にサインアウトできます。ログアウト時は `/api/auth/logout` へ通知し、バックエンドが HttpOnly セッション Cookie を失効させたうえで再びサインイン画面へ戻ります。万一バックエンドが応答しない場合はクライアント側で Cookie を削除するフォールバックが働きます。
- 既存のセッション Cookie が有効な状態でリロードした場合は、ローカルに保存されたユーザー情報を使って自動的に復元されます（Cookie が無効化されている場合は再ログインが必要です）。保存対象は表示用のユーザープロフィールのみで、ID トークンはブラウザメモリ内に限定されます。
- フロントエンドは `/api/auth/google` で受け取った ID トークンをバックエンドへ転送し、検証後に発行される HttpOnly セッションクッキーを唯一の長期セッション根拠として扱います。クライアント側は ID トークンをストレージへ保存せず、再読込時は Cookie と `/api/config` の応答から認証状態を再構築します。
- ログイン中は「設定」タブの上部にメールアドレスと表示名が表示されます。別アカウントに切り替えたい場合は一度ログアウトし、再度「Googleでログイン」ボタンから希望するアカウントを選択してください。

### トラブルシューティング
- **ID トークンが取得できない**: ログイン画面に「ID トークンを取得できませんでした。ブラウザを更新して再試行してください。」と表示された場合は、ブラウザを更新してから再度サインインしてください。それでも解消しない場合は Google OAuth のクライアント ID や承認済みオリジン設定を確認し、バックエンドのターミナルへ出力される `google_login_missing_id_token` ログで `google_client_id` や `error_category` を突き合わせて原因を特定します。テレメトリは `/api/diagnostics/oauth-telemetry` で受信した値をマスクした形で保存されるため、生のトークン値は記録されません。
- **403 Forbidden が表示される**: `ADMIN_EMAIL_ALLOWLIST` にメールアドレスが登録されていない場合は、Google 認証に成功しても即座に拒否されます。管理者に連絡して対象メールをリストへ追加してもらってください。ログには `google_auth_denied` / `email_not_allowlisted` とハッシュ化されたメールアドレスが出力されます。

#### Google 認証失敗時のログキー
- `event`: 常に `google_auth_failed` または `google_auth_denied` が設定されます。
- `reason`: 失敗理由。`invalid_token`（署名検証エラー）、`missing_claims`（`sub`/`email` が欠落）、`domain_mismatch`（許可ドメイン不一致）、`email_not_allowlisted`（許可リスト外のメールアドレス）など。
- `error`: Google SDK から受け取った例外メッセージの `repr`。署名不正などの詳細を確認できます。
- `missing_claims`: 欠落していたクレームの配列。例: `['email']`。
- `hosted_domain`: ID トークンに含まれていた `hd`（`hostedDomain`）値。
- `allowed_domain`: 設定ファイル（`GOOGLE_ALLOWED_HD`）で許可しているドメイン。`None` の場合はドメイン制限が無効。
- `email_hash`: メールアドレスを小文字化し SHA-256 でハッシュ化した先頭12文字。個人情報を露出させずに該当アカウントを突き合わせる目的で使用します。

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
- `POST /api/word/examples/{id}/transcription-typing` … 指定IDの例文について、文字起こし練習で入力した文字数を検証・加算
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
