# デプロイ手順

この文書は Cloud Run、Firebase Hosting、GitHub Actions 本番デプロイ、`.env.deploy`、IAM、dry-run の手順をまとめます。監視と復旧は [OPERATIONS.md](../OPERATIONS.md) を正本にします。

## 全体像

- backend は `Dockerfile.backend` でビルドし、Cloud Run にデプロイします。
- frontend は React + Vite の build artifact を Firebase Hosting に配置します。
- Firestore の複合インデックスは `firestore.indexes.json` を Firebase CLI または gcloud 経由で同期します。
- GitHub Actions の本番デプロイは `main` への push と `workflow_dispatch` をトリガーにします。
- PR では本番デプロイ job を作らず、Cloud Run config guard の dry-run で設定ミスを検知します。

## 事前準備

必要な CLI:

- `gcloud`
- `firebase-tools`
- Docker
- Node.js 20.19.0+
- Python 3.13

初回は次を済ませます。

```bash
gcloud auth login
gcloud auth configure-docker
firebase login
```

## `.env.deploy`

本番向け設定は `.env.deploy` にまとめます。テンプレートから複製し、実値は環境に合わせて置き換えます。

```bash
cp env.deploy.example .env.deploy
```

最低限確認する項目:

- `ENVIRONMENT=production`
- `PROJECT_ID`
- `FIRESTORE_PROJECT_ID`
- `REGION`
- `CLOUD_RUN_SERVICE`
- `ARTIFACT_REPOSITORY`
- `SESSION_SECRET_KEY`
- `ADMIN_EMAIL_ALLOWLIST`
- `CORS_ALLOWED_ORIGINS`
- `TRUSTED_PROXY_IPS`
- `ALLOWED_HOSTS`
- `GOOGLE_CLIENT_ID`
- `OPENAI_API_KEY`

`.env.deploy` は secrets を含むため、リポジトリへコミットしません。`SESSION_SECRET_KEY` は十分に長い乱数を使い、既知のサンプル値や短い値を使わないでください。

## Cloud Run dry-run

本番デプロイ前に、設定検証だけを実行できます。

```bash
./scripts/deploy_cloud_run.sh \
  --dry-run \
  --env-file .env.deploy \
  --project-id <project-id> \
  --region asia-northeast1 \
  --service wordpack-backend
```

この段階で Pydantic 設定、必須環境変数、Cloud Run 向け env 変換を確認します。`ENVIRONMENT=production` で `ADMIN_EMAIL_ALLOWLIST`、`TRUSTED_PROXY_IPS`、`ALLOWED_HOSTS` などが不足している場合は、gcloud 実行前に失敗します。

## Cloud Run デプロイ

直接スクリプトを使う場合:

```bash
./scripts/deploy_cloud_run.sh \
  --project-id <project-id> \
  --region asia-northeast1 \
  --service wordpack-backend \
  --artifact-repo wordpack/backend \
  --generate-secret
```

Makefile から実行する場合:

```bash
make deploy-cloud-run PROJECT_ID=<project-id> REGION=asia-northeast1
```

`--generate-secret` は `SESSION_SECRET_KEY` が未設定のときだけ乱数値を補完します。既存値を維持したい場合は `.env.deploy` にあらかじめ設定しておきます。

## release-cloud-run

本番リリースでは `make release-cloud-run` を使うと、Firestore インデックス同期、Cloud Run dry-run、本番デプロイの順序を固定できます。

```bash
make release-cloud-run \
  PROJECT_ID=<project-id> \
  REGION=asia-northeast1 \
  ENV_FILE=.env.deploy
```

Cloud Run のリクエストタイムアウトを明示する場合:

```bash
make release-cloud-run \
  PROJECT_ID=<project-id> \
  REGION=asia-northeast1 \
  ENV_FILE=.env.deploy \
  RUN_TIMEOUT=360s
```

既に Firestore インデックスを同期済みの CI/CD 環境では、次のように同期を省略できます。

```bash
SKIP_FIRESTORE_INDEX_SYNC=true make release-cloud-run \
  PROJECT_ID=<project-id> \
  REGION=asia-northeast1 \
  ENV_FILE=configs/cloud-run/ci.env
```

## Firebase Hosting

Firebase Hosting は frontend の静的ファイルと `/api/**` rewrite を担当します。`firebase.json` では `apps/frontend/dist` を public directory とし、API は Cloud Run へ rewrite します。

```json
{
  "hosting": {
    "public": "apps/frontend/dist",
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

通常は GitHub Actions の `deploy-production.yml` が Cloud Run の後に Hosting も更新します。手動運用時だけ次を使います。

```bash
firebase deploy --only hosting --project <firebase-project-id>
```

## GitHub Actions 本番デプロイ

本番自動デプロイは `.github/workflows/deploy-production.yml` が担当します。

- `main` への push で起動します。
- 手動実行用に `workflow_dispatch` もあります。
- PR では本番 deploy job を作りません。
- CI 成功を必須にする場合は、GitHub の branch protection で必要な check を指定します。

必要な repository secrets:

| Secret | 用途 |
|---|---|
| `GCP_SA_PROJECT_ID` | 本番 GCP project ID |
| `GCP_SA_KEY` | デプロイ用 service account JSON |
| `CLOUD_RUN_ENV_FILE_BASE64` | `.env.deploy` を base64 化した値 |

Firebase CLI は Firestore index 同期と Firebase Hosting 更新に使います。workflow 内では `GCP_SA_KEY` で Google Cloud に認証した後、`gcloud auth print-access-token` で短命 token を発行し、実行中の job にだけ `FIREBASE_TOKEN` として渡します。長期保存する `FIREBASE_TOKEN` secret は使いません。

サービスアカウントに必要な代表ロール:

- `roles/run.admin`
- `roles/artifactregistry.writer`
- `roles/cloudbuild.builds.editor`
- `roles/datastore.indexAdmin`
- `roles/serviceusage.serviceUsageViewer`
- `roles/iam.serviceAccountUser`

Cloud Build のソースアップロードやログ閲覧には、環境によって Cloud Storage / Cloud Build viewer 系の追加権限が必要です。権限は最小権限を基本とし、広い `roles/viewer` は切り分け目的に限ります。

## 検証

デプロイ後は次を確認します。

```bash
curl -fsS https://<api-host>/healthz
curl -fsS https://<api-host>/metrics
```

あわせて次を確認します。

- Cloud Run revision が想定 commit の image を使っている
- Firebase Hosting release が更新されている
- `/api/**` rewrite が Cloud Run へ届く
- Google ログイン、ゲスト閲覧、保存済み WordPack 一覧、WordPack 詳細、生成、TTS のうち変更影響範囲が動く

障害時の rollback と監視観点は [OPERATIONS.md](../OPERATIONS.md) を参照してください。
