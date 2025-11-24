#!/usr/bin/env bash
set -euo pipefail

# このスクリプトは Cloud Run へのデプロイを自動化し、
# 1) .env/.env.deploy から設定を読み込む
# 2) Python の設定ローダーでバリデーションする
# 3) gcloud builds submit → gcloud run deploy を実行する
# --dry-run を付けると 1) と 2) のみを実行して早期検知ができます。

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "$REPO_ROOT"

# log: RFC3339 timestamp付きで情報ログを整形します。
log() {
  printf '[%s] %s\n' "$(date -u +'%Y-%m-%dT%H:%M:%SZ')" "$*"
}

# err: エラーを stderr へ出力して失敗理由を即座に共有します。
err() {
  printf 'Error: %s\n' "$*" >&2
}

usage() {
  cat <<'USAGE'
Cloud Run deployment helper

Usage:
  scripts/deploy_cloud_run.sh [options]

Options:
  --project-id <id>          GCP Project ID (fallback: PROJECT_ID in env file)
  --region <region>          Artifact Registry / Cloud Run region
  --service <name>           Cloud Run service name (default: wordpack-backend)
  --artifact-repo <path>     Artifact Registry repo path (default: wordpack/backend)
  --image-tag <tag>          Image tag (default: git rev-parse --short HEAD)
  --build-arg KEY=VALUE      Additional docker build arg (repeatable)
  --env-file <path>          Explicit env file (default: .env.deploy or .env)
  --generate-secret          Generate SESSION_SECRET_KEY via openssl if missing
  --secret-length <bytes>    Byte size for openssl rand -base64 (default: 48)
  --machine-type <type>      Cloud Build machine type (default: e2-medium)
  --timeout <duration>       Cloud Build timeout, e.g. 30m
  --dry-run                  Validate config only (skip gcloud build/deploy)
  -h, --help                 Show this help
USAGE
}

# require_cmd: コマンドが存在しない場合は即終了し、失敗を後段へ伝搬させます。
require_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    err "Required command not found: $cmd"
    exit 1
  fi
}

# ensure_gcloud: gcloud が必要な処理（フォールバック/本番デプロイ）の前に一度だけ存在を確認します。
ensure_gcloud() {
  if [[ "${GCLOUD_CMD_CHECKED:-false}" != true ]]; then
    require_cmd gcloud
    GCLOUD_CMD_CHECKED=true
  fi
}

# get_gcloud_config_value: gcloud の設定から値を安全に取得します。未設定時は空文字を返します。
get_gcloud_config_value() {
  local key="$1"
  ensure_gcloud
  local value=""
  if value="$(gcloud config get-value "$key" --format='value(.)' 2>/dev/null)"; then
    value="$(printf '%s' "$value" | tr -d '\r\n')"
  else
    value=""
  fi
  if [[ "$value" == "(unset)" ]]; then
    value=""
  fi
  printf '%s' "$value"
}

# add_env_key: Cloud Run へ渡す環境変数リストを重複なく蓄積します。
add_env_key() {
  local key="$1"
  [[ -z "$key" ]] && return 0
  DEPLOY_ENV_KEYS["$key"]=1
}

# escape_yaml_value: Cloud Run の --env-vars-file へ安全に埋め込むため、
# 文字列中の制御文字や YAML で特別な意味を持つ記号をサニタイズします。
# " をエスケープし、改行や CR を取り除くことで YAML の一行表現へ正規化します。
escape_yaml_value() {
  local raw sanitized
  raw="$(printf '%s' "$1" | tr -d '\r\n')"
  sanitized="${raw//\\/\\\\}"
  sanitized="${sanitized//"/\\"}"
  printf '%s' "$sanitized"
}

ENV_FILE=""
PROJECT_ID_ARG=""
REGION_ARG=""
SERVICE_NAME="wordpack-backend"
ARTIFACT_REPOSITORY="wordpack/backend"
IMAGE_TAG=""
SECRET_LENGTH=48
GENERATE_SECRET=false
DRY_RUN=false
MACHINE_TYPE="e2-medium"
BUILD_TIMEOUT="30m"
declare -a EXTRA_BUILD_ARGS=()

declare -A DEPLOY_ENV_KEYS=()
declare -a IGNORE_DEPLOY_KEYS=(PROJECT_ID REGION CLOUD_RUN_SERVICE ARTIFACT_REPOSITORY IMAGE_TAG MACHINE_TYPE BUILD_TIMEOUT)
GCLOUD_CMD_CHECKED=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project-id)
      PROJECT_ID_ARG="$2"
      shift 2
      ;;
    --region)
      REGION_ARG="$2"
      shift 2
      ;;
    --service)
      SERVICE_NAME="$2"
      shift 2
      ;;
    --artifact-repo)
      ARTIFACT_REPOSITORY="$2"
      shift 2
      ;;
    --image-tag)
      IMAGE_TAG="$2"
      shift 2
      ;;
    --env-file)
      ENV_FILE="$2"
      shift 2
      ;;
    --build-arg)
      EXTRA_BUILD_ARGS+=("$2")
      shift 2
      ;;
    --generate-secret)
      GENERATE_SECRET=true
      shift 1
      ;;
    --secret-length)
      SECRET_LENGTH="$2"
      shift 2
      ;;
    --machine-type)
      MACHINE_TYPE="$2"
      shift 2
      ;;
    --timeout)
      BUILD_TIMEOUT="$2"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=true
      shift 1
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      err "Unknown option: $1"
      usage
      exit 1
      ;;
  esac
done

if [[ -z "$ENV_FILE" ]]; then
  if [[ -f ".env.deploy" ]]; then
    ENV_FILE=".env.deploy"
  elif [[ -f ".env" ]]; then
    ENV_FILE=".env"
  else
    err "Env file not found. Create .env.deploy or specify --env-file."
    exit 1
  fi
fi

if [[ ! "$SECRET_LENGTH" =~ ^[0-9]+$ ]]; then
  err "--secret-length must be numeric"
  exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
  err "Env file does not exist: $ENV_FILE"
  exit 1
fi

log "Loading environment variables from $ENV_FILE"
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

PROJECT_ID="${PROJECT_ID_ARG:-${PROJECT_ID:-}}"
REGION="${REGION_ARG:-${REGION:-}}"
if [[ -z "${ENVIRONMENT:-}" ]]; then
  ENVIRONMENT=production
fi
export ENVIRONMENT

if [[ "$GENERATE_SECRET" == true || -z "${SESSION_SECRET_KEY:-}" ]]; then
  if [[ "$GENERATE_SECRET" == false ]]; then
    log "SESSION_SECRET_KEY is missing; enabling --generate-secret automatically"
  fi
  require_cmd openssl
  SESSION_SECRET_KEY="$(openssl rand -base64 "$SECRET_LENGTH" | tr -d '\r\n')"
  export SESSION_SECRET_KEY
  log "Generated SESSION_SECRET_KEY with length $SECRET_LENGTH"
fi

if [[ -z "$PROJECT_ID" ]]; then
  PROJECT_ID="$(get_gcloud_config_value 'project')"
  if [[ -n "$PROJECT_ID" ]]; then
    log "PROJECT_ID not provided; falling back to gcloud config project: $PROJECT_ID"
  fi
fi

if [[ -z "$REGION" ]]; then
  REGION="$(get_gcloud_config_value 'run/region')"
  if [[ -n "$REGION" ]]; then
    log "REGION not provided; falling back to gcloud config run/region: $REGION"
  fi
fi

if [[ -z "$REGION" ]]; then
  REGION="$(get_gcloud_config_value 'compute/region')"
  if [[ -n "$REGION" ]]; then
    log "REGION not provided; falling back to gcloud config compute/region: $REGION"
  fi
fi

if [[ -z "$PROJECT_ID" ]]; then
  err "PROJECT_ID is required (use --project-id, set in env file, or configure gcloud)"
  exit 1
fi

if [[ -z "$REGION" ]]; then
  err "REGION is required (use --region, set in env file, or configure gcloud)"
  exit 1
fi

add_env_key "ENVIRONMENT"
add_env_key "ADMIN_EMAIL_ALLOWLIST"
add_env_key "SESSION_SECRET_KEY"
add_env_key "CORS_ALLOWED_ORIGINS"
add_env_key "TRUSTED_PROXY_IPS"
add_env_key "ALLOWED_HOSTS"

while IFS= read -r line || [[ -n "$line" ]]; do
  line="${line%%$'\r'}"
  [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
  if [[ "$line" =~ ^([A-Za-z_][A-Za-z0-9_]*)= ]]; then
    add_env_key "${BASH_REMATCH[1]}"
  fi
done < "$ENV_FILE"

for ignore_key in "${IGNORE_DEPLOY_KEYS[@]}"; do
  unset "DEPLOY_ENV_KEYS[$ignore_key]"
done

for required_key in ADMIN_EMAIL_ALLOWLIST SESSION_SECRET_KEY CORS_ALLOWED_ORIGINS TRUSTED_PROXY_IPS ALLOWED_HOSTS; do
  if [[ -z "${!required_key:-}" ]]; then
    err "$required_key must be set in $ENV_FILE or environment"
    exit 1
  fi
done

require_cmd git
IMAGE_TAG="${IMAGE_TAG:-$(git rev-parse --short HEAD)}"
IMAGE_URI="${REGION}-docker.pkg.dev/${PROJECT_ID}/${ARTIFACT_REPOSITORY}:${IMAGE_TAG}"

require_cmd python
log "Validating backend settings via python -m apps.backend.backend.config"
PYTHONPATH="$REPO_ROOT" python -m apps.backend.backend.config >/dev/null
log "Backend configuration validated successfully"

if [[ "$DRY_RUN" == true ]]; then
  log "Dry run mode: skipping gcloud build/deploy"
  log "Prepared image URI: $IMAGE_URI"
  exit 0
fi

if [[ "${SKIP_FIRESTORE_INDEX_SYNC:-false}" == "true" ]]; then
  log "Skipping Firestore index sync because SKIP_FIRESTORE_INDEX_SYNC=true"
else
  log "Syncing Firestore indexes via Firebase CLI before deployment"
  "${SCRIPT_DIR}/deploy_firestore_indexes.sh" --tool firebase --project "$PROJECT_ID"
fi

ensure_gcloud

log "Submitting build to Cloud Build: $IMAGE_URI"
# gcloud builds submit は Dockerfile パス指定用の --file を受け付けないため、
# リポジトリルートの Dockerfile（Dockerfile.backend へのシンボリックリンク）を利用する。
BUILD_CMD=(gcloud builds submit --project "$PROJECT_ID" --tag "$IMAGE_URI" --machine-type="$MACHINE_TYPE" --timeout="$BUILD_TIMEOUT")
if [[ ${#EXTRA_BUILD_ARGS[@]} -gt 0 ]]; then
  for build_arg in "${EXTRA_BUILD_ARGS[@]}"; do
    BUILD_CMD+=(--build-arg "$build_arg")
  done
fi
"${BUILD_CMD[@]}"

log "Preparing environment variable file for Cloud Run"
# Cloud Run では `--set-env-vars KEY=...` がカンマで分割されるため、YAML ファイル経由で一括投入する。
# mktemp で生成した一時ファイルは trap により終了時に必ず削除し、機密情報がリポジトリへ残らないようにする。
ENV_VARS_FILE="$(mktemp "${REPO_ROOT}/.cloudrun.env.XXXXXX")"
cleanup_env_file() {
  [[ -f "$ENV_VARS_FILE" ]] && rm -f "$ENV_VARS_FILE"
}
trap cleanup_env_file EXIT

mapfile -t SORTED_DEPLOY_KEYS < <(printf '%s\n' "${!DEPLOY_ENV_KEYS[@]}" | sort)
{
  for key in "${SORTED_DEPLOY_KEYS[@]}"; do
    value="${!key-}"
    [[ -z "$value" ]] && continue
    escaped="$(escape_yaml_value "$value")"
    printf '%s: "%s"\n' "$key" "$escaped"
  done
} >"$ENV_VARS_FILE"

if [[ ! -s "$ENV_VARS_FILE" ]]; then
  err "No environment variables collected for deployment"
  exit 1
fi

log "Deploying service ${SERVICE_NAME} to region ${REGION} with env file ${ENV_VARS_FILE}"
gcloud run deploy "$SERVICE_NAME" \
  --project "$PROJECT_ID" \
  --image "$IMAGE_URI" \
  --region "$REGION" \
  --allow-unauthenticated \
  --env-vars-file "$ENV_VARS_FILE"

log "Deployment completed"
