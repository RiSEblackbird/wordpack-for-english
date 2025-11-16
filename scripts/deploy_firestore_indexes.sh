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
    echo "[${SCRIPT_NAME}] gcloud で $INDEX_FILE の定義を $PROJECT_ID に同期します"
    python3 - "$PROJECT_ID" "$INDEX_FILE" <<'PY'
import json
import shlex
import subprocess
import sys

project_id = sys.argv[1]
index_file = sys.argv[2]

try:
    with open(index_file, "r", encoding="utf-8") as fh:
        payload = json.load(fh)
except FileNotFoundError:
    sys.stderr.write(f"[{__file__}] インデックスファイル {index_file} が開けません\n")
    sys.exit(1)
except json.JSONDecodeError as exc:
    sys.stderr.write(f"[{__file__}] JSON のパースに失敗しました: {exc}\n")
    sys.exit(1)

indexes = payload.get("indexes", [])
if not indexes:
    print("[deploy_firestore_indexes] indexes エントリが存在しません。スキップします。")
    sys.exit(0)

def normalize_enum(value: str) -> str:
    if not isinstance(value, str):
        return value
    lowered = value.lower()
    # gcloud のオプションはすべて小文字想定なので揃える
    return lowered

def build_field_config(field: dict) -> str:
    parts = []
    array_config = field.get("arrayConfig")
    if array_config:
        parts.append(f"array-config={normalize_enum(array_config)}")
    field_path = field.get("fieldPath")
    if not field_path:
        raise ValueError("fieldPath is required for each field definition")
    parts.append(f"field-path={field_path}")
    order = field.get("order")
    if order:
        parts.append(f"order={normalize_enum(order)}")
    vector_config = field.get("vectorConfig")
    if vector_config:
        inner = ",".join(f"{k}={v}" for k, v in vector_config.items())
        parts.append(f"vector-config={{{inner}}}")
    return "--field-config=" + ",".join(parts)

for index in indexes:
    collection_group = index.get("collectionGroup")
    if not collection_group:
        raise SystemExit("collectionGroup is required for every index definition")
    query_scope = normalize_enum(index.get("queryScope", "collection"))
    cmd = [
        "gcloud",
        "alpha",
        "firestore",
        "indexes",
        "composite",
        "create",
        f"--project={project_id}",
        f"--collection-group={collection_group}",
        f"--query-scope={query_scope}",
    ]
    for field in index.get("fields", []):
        cmd.append(build_field_config(field))

    index_label = f"{collection_group} ({', '.join(f.get('fieldPath', '?') for f in index.get('fields', []))})"
    print(f"[deploy_firestore_indexes] gcloud 実行: {shlex.join(cmd)}")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode == 0:
        print(f"[deploy_firestore_indexes] ✅ 作成/更新済み: {index_label}")
        continue

    stderr = proc.stderr or ""
    stdout = proc.stdout or ""
    already_exists = "ALREADY_EXISTS" in stderr or "already exists" in stderr.lower()
    if already_exists:
        print(f"[deploy_firestore_indexes] ℹ️ 既存のためスキップ: {index_label}")
        continue

    sys.stderr.write(stderr or stdout)
    sys.exit(proc.returncode)
PY
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
