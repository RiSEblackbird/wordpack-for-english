#!/bin/sh
# フロントエンド開発サーバー起動前に依存モジュールを保証する。
# Google OAuth 連携に必須の @react-oauth/google が存在しないケースに備え、初回起動でも失敗しないようにする。
set -e

# Google OAuth ライブラリが欠けている場合は依存を再インストールする。
if [ ! -d "node_modules/@react-oauth/google" ]; then
  echo "@react-oauth/google が見つかりません。npm install を実行します。"
  npm install
fi

exec "$@"
