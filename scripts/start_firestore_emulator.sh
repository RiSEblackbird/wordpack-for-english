#!/usr/bin/env bash
set -euo pipefail

# Firestore エミュレータを firebase-tools で起動し、firebase.json / firestore.indexes.json を自動読み込みする。
# 既存の firebase-tools がなければ npx 経由で取得し、--import/--export-on-exit でデータも永続化する。

SCRIPT_NAME=$(basename "$0")
PROJECT_ID=${FIRESTORE_PROJECT_ID:-wordpack-local}
EMULATOR_PORT=${FIRESTORE_EMULATOR_PORT:-8080}
BIND_ADDR="127.0.0.1"
IMPORT_DIR=${FIRESTORE_EMULATOR_DATA:-firestore-emulator-data}

print_usage() {
  cat <<'USAGE'
Usage: scripts/start_firestore_emulator.sh [--project-id <id>] [--port <port>] [--bind <addr>] [--import-dir <path>]

Options:
  --project-id   Firestore/Firebase プロジェクト ID（エミュレータでも必須、既定: wordpack-local）
  --port         エミュレータの公開ポート（既定: 8080）
  --bind         バインド先アドレス（既定: 127.0.0.1。Docker で公開したい場合は 0.0.0.0）
  --import-dir   --import/--export-on-exit に使うディレクトリ（既定: firestore-emulator-data）
  --help         このヘルプを表示
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project-id)
      PROJECT_ID="$2"
      shift 2
      ;;
    --port)
      EMULATOR_PORT="$2"
      shift 2
      ;;
    --bind)
      BIND_ADDR="$2"
      shift 2
      ;;
    --import-dir)
      IMPORT_DIR="$2"
      shift 2
      ;;
    --help|-h)
      print_usage
      exit 0
      ;;
    *)
      echo "[${SCRIPT_NAME}] Unknown option: $1" >&2
      print_usage >&2
      exit 1
      ;;
  esac
done

if [[ ! -f "firebase.json" ]]; then
  echo "[${SCRIPT_NAME}] firebase.json が見つかりません。リポジトリルートで実行してください。" >&2
  exit 1
fi
if [[ ! -f "firestore.indexes.json" ]]; then
  echo "[${SCRIPT_NAME}] firestore.indexes.json が見つかりません。" >&2
  exit 1
fi

mkdir -p "$IMPORT_DIR"

export FIRESTORE_EMULATOR_HOST="${BIND_ADDR}:${EMULATOR_PORT}"
echo "[${SCRIPT_NAME}] FIRESTORE_EMULATOR_HOST=${FIRESTORE_EMULATOR_HOST}"
echo "[${SCRIPT_NAME}] firebase.json / firestore.indexes.json を読み込み、Firestore エミュレータを起動します。"
echo "[${SCRIPT_NAME}] データは '${IMPORT_DIR}' に --import/--export-on-exit で永続化されます。"

cmd=(
  npx
  firebase
  emulators:start
  --only
  firestore
  --project
  "$PROJECT_ID"
  --import
  "$IMPORT_DIR"
  --export-on-exit
  --host
  "$BIND_ADDR"
  --port
  "$EMULATOR_PORT"
)

exec "${cmd[@]}"
