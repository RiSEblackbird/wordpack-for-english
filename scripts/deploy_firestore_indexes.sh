#!/usr/bin/env bash
set -euo pipefail

# Firestore のインデックスをファイルベースで同期させるためのラッパースクリプト。
# 既定の gcloud 経路は gcloud の認証だけを使い、Firestore Admin API へ直接同期する。
SCRIPT_NAME=$(basename "$0")
INDEX_FILE=${INDEX_FILE:-firestore.indexes.json}
PROJECT_ID=""
TOOL=${DEPLOY_TOOL:-gcloud}

print_usage() {
  cat <<'USAGE'
Usage: scripts/deploy_firestore_indexes.sh [--project <gcp-or-firebase-project>] [--tool gcloud|firebase] [--index-file path]

Options:
  --project, -p     Firestore/Firebase プロジェクトID。未指定時は $GOOGLE_CLOUD_PROJECT, $GCLOUD_PROJECT, $FIREBASE_PROJECT の順で探索。
  --tool, -t        同期経路を指定（既定: gcloud）。gcloud は Firestore Admin API、firebase は Firebase CLI で同期。
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

# 利用するCLIに応じて適切なデプロイ手順を分岐させる。
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
    if ! command -v python3 >/dev/null 2>&1; then
      echo "[${SCRIPT_NAME}] python3 が見つかりません。Firestore Admin API 同期には python3 が必要です。" >&2
      exit 1
    fi
    echo "[${SCRIPT_NAME}] gcloud 認証の Firestore Admin API で $INDEX_FILE の定義を $PROJECT_ID に同期します"
    python3 - "$PROJECT_ID" "$INDEX_FILE" <<'PY'
import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

project_id = sys.argv[1]
index_file = sys.argv[2]
database_id = os.environ.get("FIRESTORE_DATABASE_ID", "(default)")
api_base = os.environ.get("FIRESTORE_ADMIN_API_BASE_URL", "https://firestore.googleapis.com/v1").rstrip("/")

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
field_overrides = payload.get("fieldOverrides", [])
if not indexes and not field_overrides:
    print("[deploy_firestore_indexes] indexes / fieldOverrides エントリが存在しません。スキップします。")
    sys.exit(0)

def normalize_enum(value, default=None):
    if value is None:
        return default
    if not isinstance(value, str):
        raise ValueError(f"enum value must be a string: {value!r}")
    return value.upper()

def quote_path(value):
    return urllib.parse.quote(value, safe="")

def collection_group_path(collection_group):
    return (
        f"projects/{quote_path(project_id)}"
        f"/databases/{quote_path(database_id)}"
        f"/collectionGroups/{quote_path(collection_group)}"
    )

def field_resource_name(collection_group, field_path):
    return (
        f"projects/{project_id}"
        f"/databases/{database_id}"
        f"/collectionGroups/{collection_group}"
        f"/fields/{field_path}"
    )

def api_url(path, params=None):
    url = f"{api_base}/{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    return url

def print_and_exit(message, status=1):
    sys.stderr.write(message.rstrip() + "\n")
    sys.exit(status)

def get_access_token():
    proc = subprocess.run(
        ["gcloud", "auth", "print-access-token", "--quiet"],
        capture_output=True,
        text=True,
        env={**os.environ, "CLOUDSDK_CORE_DISABLE_PROMPTS": "1"},
    )
    if proc.returncode != 0:
        print_and_exit(proc.stderr or proc.stdout or "gcloud auth print-access-token failed", proc.returncode)
    token = proc.stdout.strip()
    if not token:
        print_and_exit("gcloud auth print-access-token did not return an access token")
    return token

access_token = get_access_token()

def request_json(method, url, body):
    data = json.dumps(body, separators=(",", ":")).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            return response.status, response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")
    except urllib.error.URLError as exc:
        print_and_exit(f"Firestore Admin API request failed: {exc}")

def error_message(response_text):
    try:
        parsed = json.loads(response_text or "{}")
    except json.JSONDecodeError:
        return response_text
    error = parsed.get("error")
    if isinstance(error, dict):
        status = error.get("status")
        message = error.get("message")
        if status and message:
            return f"{status}: {message}"
        return message or status or response_text
    return response_text

def already_exists(status, response_text):
    if status == 409:
        return True
    text = response_text.lower()
    return "already_exists" in text or "already exists" in text

def build_index_field(field):
    field_path = field.get("fieldPath")
    if not field_path:
        raise ValueError("fieldPath is required for each field definition")
    result = {"fieldPath": field_path}
    order = field.get("order")
    array_config = field.get("arrayConfig")
    vector_config = field.get("vectorConfig")
    modes = [bool(order), bool(array_config), bool(vector_config)]
    if sum(modes) != 1:
        raise ValueError(f"exactly one of order, arrayConfig, or vectorConfig is required for {field_path}")
    if order:
        result["order"] = normalize_enum(order)
    if array_config:
        result["arrayConfig"] = normalize_enum(array_config)
    if vector_config:
        result["vectorConfig"] = vector_config
    return result

def build_composite_index_body(index):
    collection_group = index.get("collectionGroup")
    if not collection_group:
        raise ValueError("collectionGroup is required for every index definition")
    body = {
        "queryScope": normalize_enum(index.get("queryScope"), "COLLECTION"),
        "fields": [build_index_field(field) for field in index.get("fields", [])],
    }
    api_scope = index.get("apiScope")
    if api_scope:
        body["apiScope"] = normalize_enum(api_scope)
    return collection_group, body

def build_single_field_index(index, field_path):
    order = index.get("order")
    array_config = index.get("arrayConfig")
    vector_config = index.get("vectorConfig")
    if order and array_config:
        raise ValueError("single-field indexes must not define both order and arrayConfig")
    if (order or array_config) and vector_config:
        raise ValueError("single-field indexes must not combine vectorConfig with order or arrayConfig")
    field = {"fieldPath": field_path}
    if order:
        field["order"] = normalize_enum(order)
    if array_config:
        field["arrayConfig"] = normalize_enum(array_config)
    if vector_config:
        field["vectorConfig"] = vector_config
    if not order and not array_config and not vector_config:
        raise ValueError("single-field indexes must define order, arrayConfig, or vectorConfig")
    body = {
        "queryScope": normalize_enum(index.get("queryScope"), "COLLECTION"),
        "fields": [field],
    }
    api_scope = index.get("apiScope")
    if api_scope:
        body["apiScope"] = normalize_enum(api_scope)
    return body

for index in indexes:
    collection_group, body = build_composite_index_body(index)
    path = collection_group_path(collection_group) + "/indexes"
    index_label = f"{collection_group} ({', '.join(f.get('fieldPath', '?') for f in index.get('fields', []))})"
    print(f"[deploy_firestore_indexes] Firestore Admin API 実行: POST collectionGroups/{collection_group}/indexes")
    status, response_text = request_json("POST", api_url(path), body)
    if 200 <= status < 300:
        print(f"[deploy_firestore_indexes] ✅ 作成リクエスト送信済み: {index_label}")
        continue
    if already_exists(status, response_text):
        print(f"[deploy_firestore_indexes] 既存のためスキップ: {index_label}")
        continue
    print_and_exit(f"Firestore Admin API composite index sync failed for {index_label}: {error_message(response_text)}")

for override in field_overrides:
    collection_group = override.get("collectionGroup")
    field_path = override.get("fieldPath")
    if not collection_group or not field_path:
        raise SystemExit("collectionGroup and fieldPath are required for every fieldOverrides entry")
    single_field_indexes = [
        build_single_field_index(single_index, field_path)
        for single_index in override.get("indexes", [])
    ]
    field_path_url = collection_group_path(collection_group) + f"/fields/{quote_path(field_path)}"
    body = {
        "name": field_resource_name(collection_group, field_path),
        "indexConfig": {"indexes": single_field_indexes},
    }
    index_label = f"{collection_group}.{field_path}"
    print(f"[deploy_firestore_indexes] Firestore Admin API 実行: PATCH collectionGroups/{collection_group}/fields/{field_path}")
    status, response_text = request_json("PATCH", api_url(field_path_url, {"updateMask": "indexConfig"}), body)
    if 200 <= status < 300:
        print(f"[deploy_firestore_indexes] ✅ fieldOverride 同期済み: {index_label}")
        continue
    print_and_exit(f"Firestore Admin API fieldOverride sync failed for {index_label}: {error_message(response_text)}")
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
esac
