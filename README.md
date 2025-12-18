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
- WordPack再生成は非同期ジョブ化し、ジョブIDを返して完了までポーリング（長時間処理でもUIが切れない）
- 発音情報（IPA/音節/強勢）の付与
- 例文（Dev/CS/LLM/Business/Common）の追加・削除
- 文章インポートと関連 WordPack の紐付け
- Firestore 障害時でも WordPack 検索を最大1回リトライし、必要に応じてプレースホルダー生成またはスキップ＋警告通知を行う安全策
- OpenAI gpt-4o-mini-tts を用いた例文／日本語訳／インポート文章／WordPack語彙（一覧・プレビュー）の音声再生（「音声」ボタン）
- WordPack プレビューを開くと、データ取得中でも一覧に表示されている見出し語をプレースホルダーとして即座に表示し、読み込み中である
  ことを明示する入力欄とメッセージを併置します（a11y のため `aria-live` / `aria-readonly` を設定）。
- 保存済みWordPack一覧で語義タイトルを即座に確認できる「語義」ボタンと「語義一括表示」スイッチ、例文未生成のカードから直接生成できる「生成」ボタン
- WordPack・文章・例文の一覧で複数選択して一括削除できる管理機能
- 例文一覧で訳文を一括開閉できる「訳一括表示」スイッチ
- 例文詳細モーダルから文字起こしタイピング練習を記録し、一覧にもバッジとして回数を反映する「文字起こしタイピング」機能
- 画面左上のハンバーガーボタンで共通サイドバーを開閉し、左側からスライド表示されるメニュー経由で主要タブ（WordPack / 文章インポート / 例文一覧 / 設定）へ移動可能。メニュー項目を選択してもサイドバーは開いたままで、開いている間はサイドバーが左端に固定されます。十分な横幅がある場合はメイン画面の配置を保ったまま余白内でサイドバーが表示され、スペースが足りない場合のみメイン画面が残り幅に収まるよう自動でスライドします
- ヘッダー右端に GitHub リンクと「ログアウト」ボタンを常設。どのタブからでもワンクリックでセッションを終了でき、共有端末の利用でも安全にサインアウトできます
- WordPack プレビューの例文中ハイライト（lemma）にマウスオーバー0.5秒で `sense_title` ツールチップ表示。対応する lemma が見つからない場合は、最小サイズのポップオーバーに「〇〇 の WordPack を生成」ボタンだけが表示されます。ボタンを押すか、該当の単語（lemma-token）をクリックすると即座に生成が始まり、完了後に「WordPack概要」ウインドウが自動で開きます

> **文章インポートの入力上限:** 1回のインポートで送信できる文章は最大 4,000 文字です。これを超えるリクエストはバックエンドが `413 Request Entity Too Large`（`error=article_import_text_too_long`）で拒否し、フロントエンドでもボタンが無効化されて警告文が表示されます。長文を扱う場合は 4,000 文字以内に分割して順番にインポートしてください。

> **音声読み上げの入力上限:** Text-to-Speech の読み上げ対象テキストは最大 500 文字です。上限を超えるとバックエンドが `413 Request Entity Too Large`（`error=tts_text_too_long`）を返し、フロントエンドでも送信前にアラートで通知されます。長文を読み上げたい場合は 500 文字以内へ調整した上で複数回に分割してください。

> **Firestore 障害時のフォールバック:** 文章インポート時に WordPack 検索や保存が失敗した場合でも最大1回の再試行後にプレースホルダー生成または対象レマのスキップで処理を継続します。発生した理由は API レスポンスの `warnings` およびモーダル上部の警告欄に表示されるため、後続の再生成や手動修正の判断に利用できます。

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
# ADMIN_EMAIL_ALLOWLIST=test@example.com  # ENVIRONMENT=production では必須。開発/テスト/CI ではダミー値でバリデーションを通過させる
# CORS_ALLOWED_ORIGINS=http://127.0.0.1:5173,http://localhost:5173
# TRUSTED_PROXY_IPS=35.191.0.0/16,130.211.0.0/22
# ALLOWED_HOSTS=app-1234567890-uc.a.run.app,api.example.com
# SESSION_SECRET_KEY=<paste a 32+ char random string generated via `openssl rand -base64 48 | tr -d '\n'`>
# SESSION_COOKIE_NAME=wp_session  # Firebase Hosting rewrite 経由でも __session に自動ミラーされます
# SESSION_COOKIE_SECURE=true  # 本番(HTTPS)のみ true。開発(HTTP)は既定で false なので設定不要
# SECURITY_HSTS_MAX_AGE_SECONDS=63072000  # HSTS の max-age（秒）
# SECURITY_CSP_DEFAULT_SRC='self',https://cdn.jsdelivr.net  # CSP の default-src 許可リスト
# SECURITY_CSP_CONNECT_SRC='self',https://api.example.com  # API fetch で許可する接続先
# GOOGLE_CLOCK_SKEW_SECONDS=60  # Google IDトークン検証時に許容する時計ずれ（秒）

# Frontend（apps/frontend 配下の Vite プロジェクト）
npm run prepare:frontend-env  # apps/frontend/.env が無い場合に .env.example をコピー
# または `cp apps/frontend/.env.example apps/frontend/.env`
# VITE_GOOGLE_CLIENT_ID=12345-abcdefgh.apps.googleusercontent.com
# VITE_SESSION_COOKIE_NAME=wp_session  # バックエンドを変更しない場合は既定値のままでOK
```

ローカル開発（ENVIRONMENT=development など）では Secure 属性が既定で無効になり、HTTP サーバーでも `wp_session` Cookie が配信されます。本番で HTTPS を使う場合は `.env` または環境変数で `SESSION_COOKIE_SECURE=true` を指定してください。Firebase Hosting から Cloud Run へリライティングする構成では、`wp_session` に加えて `__session` も同じトークンで自動配信されるため、Hosting の `__session` 制約を意識せずに認証を維持できます。

バックエンドは Firestore を永続層として利用します。`FIRESTORE_EMULATOR_HOST` を指定するとローカルエミュレータへ接続し、未設定の場合は Cloud Firestore を利用します。Cloud Firestore へ接続する場合はサービスアカウント資格情報（`GOOGLE_APPLICATION_CREDENTIALS` など）と `FIRESTORE_PROJECT_ID`（または `GCP_PROJECT_ID`）を必ず設定してください。開発モードではホスト未指定でも `127.0.0.1:8080` のエミュレータを前提に接続を試みるため、ローカル作業時はエミュレータを併走させてください。

`ENVIRONMENT` と `ADMIN_EMAIL_ALLOWLIST` は連動する前提でセットアップしてください。`ENVIRONMENT=production` で allowlist が空のままデプロイすると設定バリデーションで起動が止まり、Google ログインの許可メールアドレスがひとつも無い状態を防ぎます。テストや CI では本番同等の検証を通すために `ADMIN_EMAIL_ALLOWLIST=test@example.com` のようなダミー値を必ず設定し、実運用時のみ本当の許可リストへ差し替えてください。

#### Firestore のインデックス要件
Firestore に保存する主要コレクションは `firestore.indexes.json` で複合インデックスを一括管理しています。`word_packs`（`created_at` 降順 + `__name__`）、`examples`（`word_pack_id`/`category` フィルタ + `position` / `example_id` の組み合わせ）を固定することで、バックエンドのページネーションと `Aggregation Query` の `count()` が常に安定します。`lemma_label_lower` への等価フィルタと `updated_at` 降順の `order_by` を組み合わせるクエリ用のインデックスも追加済みで、lemma 重複チェック時に最新 1 件だけを取得します。JSON ファイルはそのまま Cloud Firestore / エミュレータ / Firebase CLI で流用できるようにしてあるため、手作業で Web Console に登録する必要はありません。
`examples` ではページングと検索のために `created_at` / `pack_updated_at` / `search_en` / `search_en_reversed` / `search_terms` を組み合わせた追加インデックスを定義し、`order_by` + `start_after` + `limit` の組み合わせで常に 50 件までしか読み出さないようにしています（`offset` はカーソル取得のみに使用）。`search_en` は小文字化、`search_en_reversed` は逆順文字列、`search_terms` は 1〜3 文字の N-gram とトークン配列で、`prefix`/`suffix`/`contains` の各検索モードをサーバー側で絞り込みます。

| 操作 | コマンド | 補足 |
| --- | --- | --- |
| gcloud で本番/検証プロジェクトへ適用 | `make deploy-firestore-indexes PROJECT_ID=my-gcp-project` | `scripts/deploy_firestore_indexes.sh` が `firestore.indexes.json` を展開し、各定義ごとに `gcloud alpha firestore indexes composite create --field-config=...` を順次実行します（既存インデックスは自動でスキップ）。 |
| Firebase CLI で適用 | `make deploy-firestore-indexes PROJECT_ID=my-firebase-project TOOL=firebase` | CI/ローカルともに `firebase deploy --only firestore:indexes --non-interactive` を使うルート。 |
| エミュレータでの検証 | `firebase emulators:start --only firestore --project wordpack-local` | ルート直下の `firestore.indexes.json` を自動で読み込みます。`FIRESTORE_EMULATOR_HOST=127.0.0.1:8080` を指定して API/テストを実行してください。 |

`firebase emulators:start` を起動したターミナルには「Loaded indexes from firestore.indexes.json」のように読み込みログが表示されます。エミュレーターを止める際は `Ctrl+C` で終了し、`pytest tests/backend/test_firestore_store.py` などの Firestore ストア向けテストを再実行して差分がないことを確認してください。

`examples` の大量削除は `word_pack_id` で絞り込んだクエリに `limit` を付け、`WriteBatch`（もしくは Firebase CLI の `--recursive` オプション）でページングしながら消していくと、1 回あたり 500 件までに抑えつつ孤児ドキュメントを残さずに済みます。`AppFirestoreStore` も同じ手順で `examples` を削除するため、Cloud Console で手動クリーンアップする場合も同条件のクエリか `firebase firestore:delete --recursive` を用いると安全です。

特定の Google アカウントだけに利用者を絞り込みたい場合は、カンマ区切りでメールアドレスを列挙した `ADMIN_EMAIL_ALLOWLIST` を設定してください。値は小文字に正規化され、完全一致したアドレスのみが `/api/auth/google` の認証を通過します（未設定または空文字の場合は従来どおり全アカウントを許可します）。
Cloud Run など本番運用では `.env.deploy` に `ADMIN_EMAIL_ALLOWLIST` を必ず設定し、開発環境と同じ利用者だけがログインできるようにしてください。`ENVIRONMENT=production` かつ空のままデプロイすると、設定バリデーションの時点で起動が止まります。

`SESSION_SECRET_KEY` は 32 文字以上の十分に乱数性を持つ文字列を必ず指定してください。`change-me` など既知のプレースホルダーや短い値を設定すると、アプリケーション起動時に検証エラーとなり実行が停止します。外部に公開する環境では `openssl rand -base64 48 | tr -d '\n'` などで生成した値を `.env` へ保存し、リポジトリへコミットしない運用を徹底してください。過去にドキュメントへ掲載したサンプル値もハッシュ照合で拒否されるため、再利用は避けてください。

`CORS_ALLOWED_ORIGINS` を設定すると、指定したオリジンからのみ資格情報付き CORS を許可します。ローカル開発では `http://127.0.0.1:5173,http://localhost:5173` を指定すると従来どおりフロントエンドと連携できます。未設定の場合はワイルドカード許可となりますが、`Access-Control-Allow-Credentials` は返さないためクッキー連携が無効化されます。

`TRUSTED_PROXY_IPS` は `ProxyHeadersMiddleware` に渡す信頼済みプロキシ（IP または CIDR）の一覧です。Cloud Run を HTTPS ロードバランサ経由で公開している場合、Google Cloud Load Balancer の送信元レンジ `35.191.0.0/16,130.211.0.0/22` を列挙すると `X-Forwarded-For` から実クライアント IP を復元できます。複数のプロキシをチェーンしている場合は、外側から順にすべての信頼区間を指定してください。`ENVIRONMENT=production` でこの変数を省略した場合でも安全のために同レンジが自動適用されますが、Cloud Run 以外の経路を挟むなら自前の CIDR へ差し替えてください。空文字列などで未設定のまま起動すると、RateLimit が全リクエストをロードバランサ由来とみなしてしまうため起動が失敗します。

`ALLOWED_HOSTS` は Starlette の `TrustedHostMiddleware` で許可するホスト名です。Cloud Run 既定ホスト（`app-xxxx.a.run.app`）に加えて、利用中のカスタムドメイン（例: `api.example.com`）を列挙してください。ワイルドカードのまま運用すると Host ヘッダ偽装に弱くなるため、本番環境では必ず明示したドメインのみに絞り込みます。`ENVIRONMENT=production` で `ALLOWED_HOSTS` が未設定（空）または `*` を含むと FastAPI 起動前に設定バリデーションが `ValueError` を投げ、Cloud Run のデフォルト URL もしくはカスタムドメインを `.env` / 環境変数で明示するまで進行しません。

バックエンドは `SecurityHeadersMiddleware` で HSTS / CSP / X-Frame-Options / X-Content-Type-Options / Referrer-Policy / Permissions-Policy を強制付与します。HTTPS 運用時に HSTS の寿命を調整したい場合は `SECURITY_HSTS_MAX_AGE_SECONDS` を設定し、`SECURITY_HSTS_INCLUDE_SUBDOMAINS=false` や `SECURITY_HSTS_PRELOAD=true` でディレクティブを切り替えてください。CSP のオリジンは `SECURITY_CSP_DEFAULT_SRC`・`SECURITY_CSP_CONNECT_SRC` にカンマ区切りで指定します。Swagger UI などで外部 CDN を利用する場合は `'self'`（引用符付き）に加えて `https://cdn.jsdelivr.net` などを列挙してください。

フロントエンド側でも同じクライアントIDを参照できるように、`apps/frontend/.env.example` を `apps/frontend/.env` としてコピーしてください。ルートディレクトリで `npm run prepare:frontend-env` を実行するとテンプレートを自動で複製します（`.env` が存在する場合は上書きしません）。

```bash
# ルートで実行
npm run prepare:frontend-env
# 既に .env がある場合や手動で書き換える場合は apps/frontend/.env.example を直接編集してください
```

`VITE_GOOGLE_CLIENT_ID` はバックエンドの `GOOGLE_CLIENT_ID` と一致している必要があります。Google Console で発行した OAuth 2.0 Web クライアント ID を指定してください。`AuthContext.tsx` は `VITE_SESSION_COOKIE_NAME` が未設定でも `wp_session`/`__session` の両方をフォールバックで削除するため、FastAPI 側の `SESSION_COOKIE_NAME` をカスタマイズしたときだけ `.env` を更新すれば十分です。

バックエンド・フロントエンドのどちらも起動前に `.env` と `apps/frontend/.env` を用意し、`GOOGLE_CLIENT_ID`（必要に応じて `GOOGLE_ALLOWED_HD` や `ADMIN_EMAIL_ALLOWLIST`）、`SESSION_SECRET_KEY`、`VITE_GOOGLE_CLIENT_ID`、（必要なら）`VITE_SESSION_COOKIE_NAME` を設定しておくと、初回起動から Google ログインが有効になります。

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

#### Backend イメージのビルドと単体起動
```bash
# Cloud Run と同じ Dockerfile.backend を使って API 用イメージを作成
docker build -f Dockerfile.backend -t wordpack-backend .

# Firestore を利用する本番挙動を再現したい場合はプロジェクトIDを指定
docker run --rm -p 8000:8000 -e FIRESTORE_PROJECT_ID=my-project wordpack-backend
```
- Firestore は全環境共通で利用します。ローカル検証では `FIRESTORE_EMULATOR_HOST=127.0.0.1:8080` を付与してエミュレータへ接続してください。Cloud Firestore を使う場合は `FIRESTORE_PROJECT_ID`（もしくは `GCP_PROJECT_ID`）とサービスアカウントを `-v $PWD/gcp-service-account.json:/secrets/sa.json -e GOOGLE_APPLICATION_CREDENTIALS=/secrets/sa.json` のように渡してください。
- `CMD` は `uvicorn backend.main:app --host 0.0.0.0 --port 8000 --app-dir apps/backend` に固定しているため、`docker run` でそのまま FastAPI を起動できます。

#### docker compose
```bash
docker compose up --build
```
- Backend: http://127.0.0.1:8000
- Frontend: http://127.0.0.1:5173
- `apps/frontend/docker-entrypoint.sh` が起動時に依存を確認し、`node_modules/@react-oauth/google` が不足している場合は自動で `npm install` を実行します。このため、新しいフロントエンド依存を追加してもコンテナの再ビルドは不要です。

### Cloud Run へのデプロイ
`scripts/deploy_cloud_run.sh` が Cloud Run 用イメージのビルドからデプロイまでを自動化します。まずはテンプレートを複製して、本番用の `.env.deploy` を作成してください。

```bash
cp env.deploy.example .env.deploy
# コピー後に PROJECT_ID などを本番値へ置き換える
```

`.env.deploy`（もしくは `--env-file` で指定したファイル）に本番環境の設定をまとめ、`ADMIN_EMAIL_ALLOWLIST` / `SESSION_SECRET_KEY` / `CORS_ALLOWED_ORIGINS` / `TRUSTED_PROXY_IPS` / `ALLOWED_HOSTS` を必ず明示します。複数のホストやオリジンはカンマ区切りで並べるだけで構いません（デプロイスクリプトが `--env-vars-file` 形式へ変換するため追加エスケープ不要）。`SESSION_SECRET_KEY` は `./scripts/deploy_cloud_run.sh --generate-secret` を付けて実行すると不足時に `openssl rand -base64 <length>` で安全な値へ自動補完できます。

```env
# .env.deploy の例
ENVIRONMENT=production
PROJECT_ID=my-prod-project
REGION=asia-northeast1
CLOUD_RUN_SERVICE=wordpack-backend
ARTIFACT_REPOSITORY=wordpack/backend
SESSION_SECRET_KEY=<後述の --generate-secret か openssl rand -base64 48 で生成>
CORS_ALLOWED_ORIGINS=https://app.example.com,https://admin.example.com
TRUSTED_PROXY_IPS=35.191.0.0/16,130.211.0.0/22
ALLOWED_HOSTS=app-xxxx.a.run.app,api.example.com
GOOGLE_CLIENT_ID=123456.apps.googleusercontent.com
OPENAI_API_KEY=sk-xxxxx
```

準備ができたら次のコマンドでデプロイします。テンプレートをコピーした直後で `SESSION_SECRET_KEY` が空の場合は、`--generate-secret` を付けることで不足分を `openssl rand -base64 <length>` で自動生成できます。`gcloud config set project <id>` や `gcloud config set run/region <region>`（未設定時は `compute/region`）で既定値を登録しておくと、`--project-id` / `--region` を省略した際に CLI 設定から自動的に補完され、フォールバックで採用された値はスクリプトのログにも出力されます。

```bash
./scripts/deploy_cloud_run.sh \
  --project-id my-prod-project \
  --region asia-northeast1 \
  --service wordpack-backend \
  --artifact-repo wordpack/backend \
  --generate-secret
```

- スクリプトは `.env.deploy` を読み込んだあとに `python -m apps.backend.backend.config` を実行し、Pydantic 設定の検証に失敗した場合は `gcloud builds submit` へ進む前に停止します。`TRUSTED_PROXY_IPS` と `ALLOWED_HOSTS` を省略したまま `ENVIRONMENT=production` で実行すると検証段階で即座にエラーになります。
- `--dry-run` を指定すると gcloud コマンドを実行せずに設定のみ検証します。CI では `configs/cloud-run/ci.env` を使ってこのモードを呼び出し、欠落した環境変数を早期検知しています。
- `--image-tag`（既定: `git rev-parse --short HEAD`）、`--build-arg KEY=VALUE`、`--machine-type`、`--timeout` で Cloud Build の詳細を調整できます。Artifact Registry のリポジトリパスは `--artifact-repo` で差し替えられます。
- `make deploy-cloud-run PROJECT_ID=... REGION=...` を実行すると同じスクリプトが呼び出されます。`gcloud config set project ...` / `gcloud config set run/region ...` を済ませていれば、Makefile 実行時の `PROJECT_ID` / `REGION` も省略できます。CI/CD では `gcloud auth login` / `gcloud auth configure-docker` の完了を前提としてください。
- デプロイスクリプトは Cloud Build を実行する前に `scripts/deploy_firestore_indexes.sh --tool firebase --project <PROJECT_ID>` を自動で叩き、`firestore.indexes.json` の内容を Firebase CLI 経由で本番プロジェクトへ反映します。`firebase-tools` が未インストールだとこの段階で停止するため、事前に導入しておくか、CI 等で同期済みの場合は `SKIP_FIRESTORE_INDEX_SYNC=true ./scripts/deploy_cloud_run.sh ...` のように環境変数を付けて同期フェーズをスキップしてください。

#### release-cloud-run（Firestore インデックス同期 + Cloud Run デプロイ）

`make release-cloud-run` は Firestore インデックスの同期 → Cloud Run 用 dry-run → 本番デプロイの順序を固定し、`.env.deploy`（もしくは `ENV_FILE` で指定したファイル）が見つからない場合は即座に停止します。Dry-run で Pydantic 設定を検証してから Cloud Build/Run を実行するため、GitHub Actions でも設定ミスの検知が容易です。

GitHub Actions では `deploy-dry-run.yml` が pull_request と main ブランチへの push で `make release-cloud-run` を `SKIP_FIRESTORE_INDEX_SYNC=true` / `DRY_RUN=true` 付きで実行し、`configs/cloud-run/ci.env` を用いた設定検証を自動化します。GCP のサービスアカウントキーはリポジトリシークレット `GCP_SA_KEY` に保存し、`google-github-actions/auth` で ADC として読み込んでから `setup-gcloud` に引き渡してください。

- 前提条件
  - `PROJECT_ID` と `REGION` を Make 実行時に必ず指定する（gcloud の既定値には依存しません）。
  - Firestore Admin / Cloud Run Admin / Artifact Registry Writer 権限を持つサービスアカウントで `gcloud auth login` または `gcloud auth activate-service-account` を済ませ、`gcloud auth configure-docker` も完了させておく。
- `.env.deploy` など本番用の env ファイルを準備し、`ADMIN_EMAIL_ALLOWLIST` / `SESSION_SECRET_KEY` / `CORS_ALLOWED_ORIGINS` / `TRUSTED_PROXY_IPS` / `ALLOWED_HOSTS` を必ず含める（`ENV_FILE` でパスを切り替え可能）。開発環境と同じメールアドレスだけが Cloud Run でも認証を通過することを確認してください。
- `ENVIRONMENT=production` では `ADMIN_EMAIL_ALLOWLIST` が空のままだと Pydantic 設定の検証で即座に失敗し、Google ログインの許可対象が不明な状態で本番デプロイへ進むことを防ぎます。CI では `configs/cloud-run/ci.env` にダミーの許可アドレス（例: `ci-admin@example.com`）を入れた上で dry-run を実行し、本番と同じ必須性チェックを通しています。
- 使い方

```bash
# Firestoreインデックス同期 → Cloud Run dry-run → 本番デプロイ
make release-cloud-run \
  PROJECT_ID=my-prod-project \
  REGION=asia-northeast1 \
  ENV_FILE=.env.deploy

# Cloud Run のリクエストタイムアウトを明示する場合（例: 360s）
make release-cloud-run \
  PROJECT_ID=my-prod-project \
  REGION=asia-northeast1 \
  ENV_FILE=.env.deploy \
  RUN_TIMEOUT=360s

# GitHub Actions 等でインデックス同期を省略し、CI専用 env を使う場合
make release-cloud-run \
  PROJECT_ID=${{ env.GCP_PROJECT_ID }} \
  REGION=${{ env.GCP_REGION }} \
  ENV_FILE=configs/cloud-run/ci.env \
  SKIP_FIRESTORE_INDEX_SYNC=true
```

- `SKIP_FIRESTORE_INDEX_SYNC=true` を付けると Firestore 側を更新せず Cloud Run デプロイのみを実行します（既にインデックスを同期済みの CI/CD 環境向け）。
- `RUN_TIMEOUT=360s` のように指定すると Cloud Run のリクエストタイムアウト（`gcloud run deploy --timeout`）を明示できます。
- release-cloud-run は先に `make deploy-firestore-indexes` を呼び出してから `SKIP_FIRESTORE_INDEX_SYNC=true` を付けて `scripts/deploy_cloud_run.sh` を実行します。CI などでインデックス同期自体を省略したい場合は `SKIP_FIRESTORE_INDEX_SYNC=true make release-cloud-run PROJECT_ID=... REGION=...` のように指定してください。
- Dry-run (`scripts/deploy_cloud_run.sh --dry-run`) は必ず本番デプロイの直前に走るため、設定エラーは gcloud コマンドの前で検知されます。
- `ENV_FILE` を省略した場合でも `.env.deploy` の存在確認を行い、欠落しているとターゲットが失敗します。

Cloud Run を外部 HTTP(S) ロードバランサ経由で公開する場合は `TRUSTED_PROXY_IPS=35.191.0.0/16,130.211.0.0/22` を設定（または既定値のまま維持）して `X-Forwarded-For` を信頼してください。このレンジを登録しておくと、アクセスログや RateLimit が Google Cloud Load Balancer の固定 IP ではなく実際のクライアント IP を記録できます。独自のプロキシを挟む構成では、その CIDR を Cloud Run の環境変数で必ず明示してください。

### Firebase Hosting でのリライト構成
Cloud Run の API を Firebase Hosting のフロントエンドと同一ドメインで公開する場合は、`firebase.json` に `/api` 向けリライトを定義しておくと CORS 設定を最小限にできます。`apps/frontend/dist` を Hosting に配置する例を示します。

```json
{
  "hosting": {
    "public": "apps/frontend/dist",
    "ignore": ["firebase.json", "**/.*", "**/node_modules/**"],
    "rewrites": [
      {
        "source": "/api{,/**}",
        "run": {
          "serviceId": "wordpack-backend",
          "region": "asia-northeast1"
        }
      },
      { "source": "/**", "destination": "/index.html" }
    ]
  }
}
```

1. `firebase deploy --only hosting`（WSL 上のリポジトリルートで実行）を叩くと、`hosting.predeploy` で `npm --prefix ./apps/frontend run build` が自動実行され、そのまま `/api` 配下のリライト設定と静的ファイルのアップロードまで完了します。
2. 同一オリジンになるため、`CORS_ALLOWED_ORIGINS` に Hosting ドメイン（例: `https://<project>.web.app`）を列挙し、`ALLOWED_HOSTS` にも同じドメインを追加すれば Cookie を安全に共有できます。

成功例（WSL 内）:
```bash
taishi@DESKTOP-GIVL2DT:/mnt/d/Users/mokut/Documents/GitHub/wordpack-for-english$ firebase deploy --only hosting
```

失敗例（PowerShell 直叩き。WSL で実行しないと `npm --prefix ./apps/frontend run build` が Windows パスを解決できず失敗する）:
```powershell
PS D:\Users\mokut\Documents\GitHub\wordpack-for-english> firebase deploy --only hosting
# → node_modules の検出に失敗するため推奨しない
```

### Firestore エミュレータを使ったローカルテスト
Firestore エミュレータを併用すれば本番相当のデータフローをローカルで検証できます。

1. Firebase CLI をインストールし、別ターミナルで `firebase emulators:start --only firestore --project wordpack-local` を起動。
2. API を起動する環境で `FIRESTORE_PROJECT_ID=wordpack-local FIRESTORE_EMULATOR_HOST=127.0.0.1:8080` を設定し、`python -m uvicorn backend.main:app --app-dir apps/backend` を実行します（サービスアカウントは不要）。
3. テストも `FIRESTORE_EMULATOR_HOST=127.0.0.1:8080 FIRESTORE_PROJECT_ID=wordpack-local pytest tests/backend/test_firestore_store.py` のように実行すれば、Fake クライアントだけでなく実際のエミュレータ相手の結合テストを追加できます。

Cloud Run や Firebase Hosting へ出荷する前に、上記の手順で Firestore 統合を通しで確認すると移行時のトラブルを減らせます。

### 認証フロー
- フロントエンドへアクセスすると、まず Google アカウントでのサインイン画面が表示されます。
- 「Googleでログイン」ボタンは Google Identity Services の `GoogleLogin` コンポーネントを用いており、承認後に `credential`（ID トークン）を取得して `/api/auth/google` へ送信し、セッション Cookie を受け取ります。credential が欠落した場合は直ちにエラー帯を表示し、`/api/diagnostics/oauth-telemetry` へ状況を送信して原因調査に活用します。
- バックエンド側で `ADMIN_EMAIL_ALLOWLIST` を設定している場合、リストに含まれないメールアドレスは検証後でも即座に 403 となり、構造化ログには `google_auth_denied` / `email_not_allowlisted` が記録されます。利用者を追加したい場合はリストへメールアドレスを追記して再起動してください。
- Google が返す ID トークンで `email_verified` が `true` でない場合は本人確認が完了していないと判断し、403 で拒否します。ログには `google_auth_denied` / `email_unverified` とハッシュ化済みメールアドレスが残るため、問い合わせ対応時はこの値をもとに利用者へメールアドレスの確認手続きを案内してください。
- バックエンドの構造化ログでは `google_auth_succeeded` を含むすべての Google 認証イベントで `email_hash`（および `display_name_hash`）が記録され、平文のメールアドレスや表示名は Cloud Logging へ送出されません。調査時はハッシュ値で突き合わせてください。
- ポップアップは locale=ja で描画され、共有端末でも毎回アカウント選択ダイアログが表示されます。別アカウントでログインしたい場合は表示されたポップアップで希望のアカウントを選択してください。選択後の動作は従来どおり `/api/auth/google` の検証とセッションクッキー付与で完結します。
- ヘッダー右側の「ログアウト」ボタン、または「設定」タブ下部の「ログアウト（Google セッションを終了）」ボタンから明示的にサインアウトできます。ログアウト時は `/api/auth/logout` へ通知し、バックエンドが HttpOnly セッション Cookie を失効させたうえで再びサインイン画面へ戻ります。万一バックエンドが応答しない場合はクライアント側で Cookie を削除するフォールバックが働きます。
- 既存のセッション Cookie が有効な状態でリロードした場合は、ローカルに保存されたユーザー情報を使って自動的に復元されます（Cookie が無効化されている場合は再ログインが必要です）。保存対象は表示用のユーザープロフィールのみで、ID トークンはブラウザメモリ内に限定されます。
- フロントエンドは `/api/auth/google` で受け取った ID トークンをバックエンドへ転送し、検証後に発行される HttpOnly セッションクッキーを唯一の長期セッション根拠として扱います。クライアント側は ID トークンをストレージへ保存せず、再読込時は Cookie と `/api/config` の応答から認証状態を再構築します。
- React 側の `AuthContext` も ID トークンを公開しておらず、利用側のコンポーネントはユーザープロフィールとセッション有無のみを参照します。これにより、コンポーネント経由でのトークン露出（XSS など）を未然に防ぎます。
- ログイン中は「設定」タブの上部にメールアドレスと表示名が表示されます。別アカウントに切り替えたい場合は一度ログアウトし、再度「Googleでログイン」ボタンから希望するアカウントを選択してください。

### トラブルシューティング
- **ID トークンが取得できない**: ログイン画面に「ID トークンを取得できませんでした。ブラウザを更新して再試行してください。」と表示された場合は、ブラウザを更新してから再度サインインしてください。それでも解消しない場合は Google OAuth のクライアント ID や承認済みオリジン設定を確認し、バックエンドのターミナルへ出力される `google_login_missing_id_token` ログで `google_client_id` や `error_category` を突き合わせて原因を特定します。テレメトリは `/api/diagnostics/oauth-telemetry` で受信した値をマスクした形で保存されるため、生のトークン値は記録されません。
- **403 Forbidden が表示される**: `ADMIN_EMAIL_ALLOWLIST` にメールアドレスが登録されていない場合は、Google 認証に成功しても即座に拒否されます。管理者に連絡して対象メールをリストへ追加してもらってください。ログには `google_auth_denied` / `email_not_allowlisted` とハッシュ化されたメールアドレスが出力されます。
- **403 Forbidden（メール未確認）**: 利用者の Google アカウントで「メールアドレスの確認」が完了していない場合、ID トークンの `email_verified` が `false`（または欠落）となり 403 が返ります。Google アカウントのセキュリティ設定からメール確認を済ませたうえで再試行してください。構造化ログには `google_auth_denied` / `email_unverified` が記録されます。
- **生成＆インポートが成功通知なのに記事/WordPackが増えない**: `/api/article/generate_and_import` は内部で例文2件を記事化しますが、両方のインポートが失敗すると 502 / `reason_code=CATEGORY_IMPORT_FAILED_ALL` を返すようになりました。Cloud Logging には `category_example_import_failed` と `category_generate_import_failed_all` が連続して出力されるため、失敗した例文インデックスと例外クラスを確認してから WordPack 側の例文を手動でインポートするか、設定（LLMモデル/temperatureなど）を見直して再実行してください。1件でも記事化できた場合は 200 を返しつつ `category_generate_import_partial_success` を警告ログに残すので、成功数と失敗数をログで把握できます。

#### Google 認証失敗時のログキー
- `event`: 常に `google_auth_failed` または `google_auth_denied` が設定されます。
- `reason`: 失敗理由。`invalid_token`（署名検証エラー）、`missing_claims`（`sub`/`email` が欠落）、`domain_mismatch`（許可ドメイン不一致）、`email_not_allowlisted`（許可リスト外のメールアドレス）、`email_unverified`（Google 側でメール確認が未完了）など。
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
- `GET /api/word?lemma=...` … lemma を指定して最新の WordPack から定義と例文を返却（見つからなければ自動生成）
- `POST /api/word/examples/bulk-delete` … 例文IDの配列を受け取り一括削除
- `POST /api/word/examples/{id}/transcription-typing` … 指定IDの例文について、文字起こし練習で入力した文字数を検証・加算
- `POST /api/tts` … OpenAI gpt-4o-mini-tts で読み上げた音声（audio/mpeg）をストリーミング返却
- `GET /_debug/headers` … デバッグ用: FastAPI が受信した Host / X-Forwarded-* / URL / クライアント IP をそのまま JSON で返却。Firebase Hosting → Cloud Run 経由のヘッダ付け替え確認や、リバースプロキシ配下の疎通検証に利用できる（運用環境でも有効だが目立たないパスとして公開）。

ローカルで `/api/config` と同じアプリに統合されていることを確認する場合は、`uvicorn backend.main:app --app-dir apps/backend --reload` で起動し、別ターミナルから `curl -H "Host: backend.internal" -H "X-Forwarded-Host: public.example.com" -H "X-Forwarded-Proto: https" http://127.0.0.1:8000/_debug/headers` を実行するとレスポンスに受信ヘッダが反映されます。

### WordPack 生成時の入力制約
- 見出し語（`lemma`）は **英数字・半角スペース・ハイフン・アポストロフィのみ** で、1〜64文字。
- Firestore のパス制約に抵触する記号（`/` や制御文字など）が含まれると、FastAPI が 422 Unprocessable Entity を返却します。エラー詳細の `loc` が `lemma` を指すことを確認してください。
- WordPack の保存IDは `wp:{32桁の16進UUID}` 形式です（旧形式のIDもそのまま利用可能です）。
- lemma 保存時は正規化（小文字化）したラベルを Firestore のドキュメントIDとして採用し、`normalized_label` の単一フィールドインデックスによって O(1) 参照を維持しています。旧形式の lemma ID も `normalized_label` で1件だけを引くクエリで互換運用し、同じ lemma を同時に保存しようとした場合でも create/exists チェック付きで重複作成を防ぎます。

## ディレクトリ
```
apps/backend/backend/   # FastAPI アプリ
apps/frontend/          # React + Vite
tests/                  # Python テスト
docs/                   # 詳細ドキュメント
```

## 追加ドキュメント
- 詳細な API・フロー・モデルは `docs/flows.md`, `docs/models.md`, `docs/環境変数の意味.md` を参照してください。
- インフラ構成図は `docs/infrastructure.md` を参照してください。
- ユーザー向け操作は `UserManual.md` を参照してください。
- GitHub Actions の CI では Chrome DevTools MCP を利用した UI スモークテスト（`UI smoke test (Chrome DevTools MCP)` ジョブ）が自動実行されます。ローカルで同じシナリオを再現する方法は `docs/testing/chrome-devtools-mcp-ui-testing.md` を参照してください（Node.js 22 を用い、ルートディレクトリで `npm run smoke` または `tests/ui/mcp-smoke/run-smoke.mjs` を実行する手順を含みます）。Chrome 未インストール環境でも安定版 Chrome の自動取得を試み、許可されない場合は OSS Chromium へのフォールバックを順番に実施します。いずれもダウンロードできなかった場合は `CHROME_EXECUTABLE` で既存バイナリを指定しない限りローカル実行のみスキップする挙動です。
