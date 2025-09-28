# Codex 用 Chrome DevTools MCP スモークテスト プロンプト

以下の文章を Codex に送信すると、Chrome DevTools MCP を経由して WordPack フロントエンドのスモークテストが実行できます。プロンプトは UI 更新に合わせて適宜調整してください。

---

```
目的: chrome-devtools MCP サーバーを使い、WordPack for English フロントエンドのスモークテストを自動実行して結果を解析する。

前提:
- フロントエンドは http://127.0.0.1:5173 で `npm run preview -- --host 127.0.0.1 --port 5173` により起動済み。
- バックエンド API は UI 表示に十分なダミーデータを返せる状態。
- chrome-devtools MCP サーバーは headless + isolated モードで接続済み。

手順:
1. `chrome-devtools` MCP サーバーで新しいページを開き、http://127.0.0.1:5173 に遷移する。
   - `new_page`
   - `navigate_page` (url: "http://127.0.0.1:5173/")
   - `wait_for` (text: "WordPack")
   - `take_screenshot` (selector: "body", save=true)
2. ハンバーガーボタンでサイドバーを開き、開閉状態を検証する。
   - `click` (selector: "button.hamburger-toggle")
   - `wait_for` (selector: ".sidebar[aria-hidden=\"false\"]")
   - `evaluate_script` で `document.querySelector('.app-shell').classList.contains('sidebar-open')` が true であることを確認
3. サイドバーから「設定」「例文一覧」「WordPack」の順にタブを切り替え、主要 UI が表示されることを確認する。
   - `click` (selector: "nav[aria-label=\"主要メニュー\"] button", text: "設定")
   - `wait_for` (text: "カラーテーマ")
   - `click` (selector: "nav[aria-label=\"主要メニュー\"] button", text: "例文一覧")
   - `wait_for` (text: "例文一覧")
   - `click` (selector: "nav[aria-label=\"主要メニュー\"] button", text: "WordPack")
   - `wait_for` (selector: "[data-testid=\"wp-card\"]")
4. WordPack カードの詳細モーダルを開いて内容を確認する。
   - `click` (selector: "[data-testid=\"wp-card\"]", index: 0)
   - `wait_for` (selector: "[role=\"dialog\"][aria-label=\"WordPack プレビュー\"]")
   - `take_screenshot` (selector: "[role=\"dialog\"][aria-label=\"WordPack プレビュー\"]", save=true)
   - `click` (selector: "[role=\"dialog\"][aria-label=\"WordPack プレビュー\"] button[aria-label=\"閉じる\"]")
5. 画面操作後の状態を収集する。
   - `list_console_messages`
   - `list_network_requests`
6. 収集したログ・スクリーンショットを解析し、UI の不具合や改善点があれば列挙する。
   - UI 崩れ、未描画、エラー応答などがある場合は該当する React/Vite のコード位置を推定し、修正方針をまとめる。
7. 必要に応じて追加の操作やスクリーンショットを撮影し、原因調査を深掘りする。
8. すべての結果を要約し、改善施策と再テスト手順を提案する。

出力フォーマット:
- スモークテスト実行ログ（どの MCP ツールを呼び出したか、ステータス）
- スクリーンショット保存パス
- コンソールログ／ネットワークログの要約
- 発見された問題の一覧と改善提案
- 改善後に再実行する際のチェックリスト（tests/ui/chrome-devtools-smoke-checklist.md を参照）
```

---

このプロンプトを送信すると Codex が自動で MCP ツールを連続実行し、テスト結果をまとめた上で改善案を提示します。改善の実装後は再び同じプロンプトを利用し、回帰がないか確認してください。
