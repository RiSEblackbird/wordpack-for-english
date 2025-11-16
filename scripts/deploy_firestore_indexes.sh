#!/usr/bin/env bash
set -euo pipefail

# Firestore の複合インデックスをファイルベースで同期させるためのラッパースクリプト。
# gcloud / Firebase CLI のどちらでも `firestore.indexes.json` を適用できるように統一している。
SCRIPT_NAME=$(basename "$0")
INDEX_FILE=${INDEX_FILE:-firestore.indexes.json}
PROJECT_ID=""
TOOL=${DEPLOY_TOOL:-gcloud}

print_usage() {
  cat <<'USAGE'
Usage: scripts/deploy_firestore_indexes.sh [--project <gcp-or-firebase-project>] [--tool gcloud|firebase] [--index-file path]

Options:
  --project, -p     Firestore/Firebase プロジェクトID。未指定時は $GOOGLE_CLOUD_PROJECT, $GCLOUD_PROJECT, $FIREBASE_PROJECT の順で探索。
  --tool, -t        利用するCLIを指定（既定: gcloud）。firebase を指定すると Firebase CLI でデプロイ。
  --index-file, -f  読み込むインデックス定義ファイル（既定: firestore.indexes.json）。
  --help, -h        このメッセージを表示。
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project|-p)
      PROJECT_ID="$2"
      shift 2
      ;;
    --tool|-t)
      TOOL="$2"
      shift 2
      ;;
    --index-file|-f)
      INDEX_FILE="$2"
      shift 2
      ;;
    --help|-h)
      print_usage
      exit 0
      ;;
    *)
      echo "[${SCRIPT_NAME}] 未知のオプション: $1" >&2
      print_usage >&2
      exit 1
      ;;
  esac
done

if [[ -z "$PROJECT_ID" ]]; then
  PROJECT_ID=${GOOGLE_CLOUD_PROJECT:-${GCLOUD_PROJECT:-${FIREBASE_PROJECT:-}}}
fi

if [[ ! -f "$INDEX_FILE" ]]; then
  echo "[${SCRIPT_NAME}] インデックスファイル $INDEX_FILE が見つかりません" >&2
  exit 1
fi

case "$TOOL" in
  gcloud)
    if ! command -v gcloud >/dev/null 2>&1; then
      echo "[${SCRIPT_NAME}] gcloud CLI が見つかりません。'pip install gcloud' ではなく Google Cloud SDK をインストールしてください。" >&2
      exit 1
    fi
    if [[ -z "$PROJECT_ID" ]]; then
      echo "[${SCRIPT_NAME}] --project か GOOGLE_CLOUD_PROJECT を指定してください" >&2
      exit 1
    fi
    echo "[${SCRIPT_NAME}] gcloud で $INDEX_FILE を $PROJECT_ID へ適用します"
    gcloud alpha firestore indexes composite create \
      --project="$PROJECT_ID" \
      --index-file="$INDEX_FILE"
    ;;
  firebase)
    if ! command -v firebase >/dev/null 2>&1; then
      echo "[${SCRIPT_NAME}] Firebase CLI(firebase-tools) が見つかりません" >&2
      exit 1
    fi
    if [[ -z "$PROJECT_ID" ]]; then
      echo "[${SCRIPT_NAME}] --project か FIREBASE_PROJECT を指定してください" >&2
      exit 1
    fi
    echo "[${SCRIPT_NAME}] Firebase CLI で $INDEX_FILE を $PROJECT_ID へ適用します"
    firebase deploy --only firestore:indexes --project "$PROJECT_ID" --non-interactive --force
    ;;
  *)
    echo "[${SCRIPT_NAME}] --tool には gcloud または firebase を指定してください" >&2
    exit 1
    ;;
endcase
