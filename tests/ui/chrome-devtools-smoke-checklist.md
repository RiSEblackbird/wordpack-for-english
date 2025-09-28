# Chrome DevTools MCP UI スモークテスト チェックリスト

Codex が `chrome-devtools` MCP サーバーを利用して WordPack フロントエンドのスモークテストを自動化する際の観点をまとめます。テスト結果に基づき改善を行ったら、本チェックリストを再実行して回帰がないか確認してください。

## 事前準備

- フロントエンド: `npm run preview -- --host 127.0.0.1 --port 5173` で起動済み。
- バックエンド: UI の描画に必要な API が稼働している（Docker Compose または `uvicorn`）。
- Codex が `chrome-devtools` MCP サーバーへ接続済み。

## 検証観点

| 番号 | 目的 | 操作 | 期待結果 | MCP の主なツール |
|------|------|------|-----------|--------------------|
| 1 | 初期表示の確認 | `navigate_page` でトップへ遷移し、`wait_for` で `WordPack` 見出しを待つ | サイドバーと WordPack 一覧が描画される | `navigate_page`, `wait_for`, `take_screenshot` |
| 2 | サイドバー展開の検証 | `click` でハンバーガーを押下し、`wait_for` で `.sidebar[aria-hidden="false"]` を待つ | サイドバーが開き、`.app-shell.sidebar-open` が付与される | `click`, `wait_for`, `evaluate_script` |
| 3 | タブ切り替えの確認 | 「設定」→「例文一覧」→「WordPack」を切り替える | 各タブの主要コンテンツが表示され、サイドバーが閉じない | `click`, `wait_for` |
| 4 | WordPack カードの詳細表示 | 一覧中の最初のカードを `click` → モーダル表示を確認 | モーダルに WordPack プレビューが表示され、閉じるボタンで閉じられる | `click`, `wait_for`, `take_screenshot` |
| 5 | UI エラー検知 | 画面操作後にログを収集 | コンソールエラー・失敗リクエストがない | `list_console_messages`, `list_network_requests` |

## 判定とフォローアップ

1. 各ステップで期待結果を満たしているか Codex に判定させる。
2. 期待結果を満たさない場合は、発生したログ／スクリーンショットを分析し、原因となる React/Vite のコードを修正する。
3. 修正後は Vitest (`npm run test`) を実行し、ユニットテストの退行がないことを確認する。
4. 同じ MCP テストシナリオを再実行して改善が反映されたか再確認する。

## 更新時の注意

- UI の `data-testid` や `aria-label` を変更した場合は、本チェックリストと `tests/ui/prompts/codex-smoke-test.md` を同時に更新してください。
- テスト対象を追加する場合は新しい番号を付けて行を追加し、Codex が順番に実行できるよう操作手順を明確に記述します。
