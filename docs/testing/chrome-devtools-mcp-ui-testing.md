# Chrome DevTools MCP を用いた UI 自動テスト運用手順

Chrome DevTools MCP（Model Context Protocol）サーバーを使うと、エージェントが Chrome ブラウザを自動操作して UI テストを実行し、その場で計測値やエラーを取得できます。本書では Codex からの利用を前提に、WordPack for English の UI スモークテストを自動化するための体制と運用手順をまとめます。

## GitHub Actions CI による自動実行

- メインブランチ／プルリクエスト向けの CI (`.github/workflows/ci.yml`) には `UI smoke test (Chrome DevTools MCP)` ジョブが組み込まれており、バックエンド（pytest）とフロントエンド（Vitest）のジョブ完了後に自動で起動します。
- ジョブは Node.js 22 と Python 3.13 の環境をセットアップし、`tests/ui/mcp-smoke` の依存を `npm ci` で導入したのちに `npm run smoke` を実行します。
- `browser-actions/setup-chrome@v1` で Headless Chrome を取得し、`CHROME_EXECUTABLE` 環境変数としてテストスクリプトへ引き渡します。ログには MCP のナビゲーション、スクリーンショット取得、完了ステータスが出力されるため、失敗時は GitHub Actions の実行ログから詳細を確認してください。
- ローカルで挙動を再現したい場合は、後述の手順に従って `run-smoke.mjs` を実行することで CI と同じ UI スモークテストを再現できます。

## 全体像

```
Codex (MCP クライアント)
  └── chrome-devtools MCP サーバー
        └── Headless Chrome (Puppeteer 経由)
              └── WordPack フロントエンド (http://127.0.0.1:5173)
```

- Codex が `chrome-devtools` MCP サーバーに接続し、Chrome DevTools の各種ツール（クリック、フォーム入力、トレース収集など）を呼び出します。
- サーバーは puppeteer ベースで自動待機・再試行を行うため、LLM 側は手続きの記述に集中できます。
- 取得したスクリーンショット、コンソールログ、ネットワークリクエスト、パフォーマンスレポートを Codex がそのまま解析し、改善案の検証へ即座に反映できます。

## 前提条件

| 項目 | 内容 |
|------|------|
| Node.js | 22.12.0 以上 |
| npm | 最新安定版 |
| Chrome | 安定版またはそれ以上 |
| Codex CLI | [公式ドキュメント](https://github.com/openai/codex/blob/main/docs/advanced.md#model-context-protocol-mcp) を参照してセットアップ |

> **メモ:** Docker コンテナ内で UI テストを実施する場合は、Chrome の sandbox を無効化するか、`--isolated` オプションで一時プロファイルを利用します。

## MCP サーバーの登録

Codex CLI から Chrome DevTools MCP サーバーを追加します。毎回最新版を利用できるよう `@latest` を指定します。

```bash
codex mcp add chrome-devtools -- npx chrome-devtools-mcp@latest --headless=true --isolated=true
```

- `--headless=true`: UI 表示なしで Chrome を起動し、CI やサーバー環境でも利用できるようにします。
- `--isolated=true`: テストごとに一時プロファイルを作成し、キャッシュやセッション状態の汚染を防ぎます。

## WordPack フロントエンドの起動

Chrome DevTools MCP がアクセスする対象として、フロントエンドをローカルで起動します。

```bash
cd apps/frontend
npm install
npm run build
npm run preview -- --host 127.0.0.1 --port 5173
```

- `npm run preview` はビルド済みアセットを提供するため、本番に近い挙動を再現できます。
- Codex が `navigate_page` ツールで `http://127.0.0.1:5173` を開きます。ポート変更時は後述のプロンプトテンプレートも更新してください。

### Node.js 22 + `run-smoke.mjs` による自動スモークテスト

WordPack リポジトリには、Chrome DevTools MCP と Headless Chrome を使って UI スモークテストを自動実行するランナー `tests/ui/mcp-smoke/run-smoke.mjs` を用意しています。Node.js 22.12 以上と Chrome 安定版を前提に、以下の手順で実行します。

1. **Chrome のインストール**（未導入の場合）

   ```bash
   sudo apt-get update
   sudo apt-get install -y google-chrome-stable
   ```

   別ディストリビューションを利用している場合は、`CHROME_EXECUTABLE=/path/to/chrome` を設定して Chrome バイナリのパスを指定してください。

2. **Node.js 22 系の利用**（`chrome-devtools-mcp` が Node 22 以降必須のため）

   ```bash
   # 例: .local/node-22 に展開した Node 22 を利用する場合
   export PATH="${PWD}/.local/node-22/bin:$PATH"
   ```

3. **スモークテストの実行**

   ```bash
   node tests/ui/mcp-smoke/run-smoke.mjs
   ```

   - スクリプトは以下を自動で行います。
     - `STRICT_MODE=false` のバックエンド (FastAPI) を起動し、SQLite データベースを `Seeded WordPack` 1 件で初期化。
     - Vite 開発サーバーを `http://127.0.0.1:5173` で起動し、Chrome プロキシターゲットを自動設定。
     - `google-chrome-stable --headless` を `--remote-debugging-port=9222` で起動し、`chrome-devtools-mcp` へ接続。
     - WordPack 一覧・設定タブ・例文一覧タブを MCP ツールで巡回し、主要 UI が表示されることを検証。
   - 実行中は `[backend]`, `[frontend]`, `[chrome]` の各プレフィックスでログが出力され、成功すると `✅ UI smoke test completed successfully` が表示されます。
   - 失敗した場合は詳細なスタックトレースとともにプロセスが停止し、終了時にバックエンド・フロントエンド・Chrome を自動的にクリーンアップします。

> **メモ:** CI や別環境で実行する場合、`CHROME_EXECUTABLE`、`OPENAI_API_KEY` 等の環境変数を必要に応じて上書きしてください。スクリプトは Node.js 22 の `npm` を優先的に利用するため、PATH に Node22 の `bin/` を先頭追加しておくと安全です。

## UI スモークテストのシナリオ

`tests/ui/chrome-devtools-smoke-checklist.md` に、Codex が Chrome DevTools MCP で検証すべき観点を記載しています。基本シナリオは以下の通りです。

1. アプリのトップページに遷移し、サイドバーと WordPack 一覧が描画されること。
2. サイドバーのタブ切り替え（例: 「例文一覧」→「設定」）が動作すること。
3. WordPack 保存済みカードを開き、モーダルで語義タイトルが表示されること。
4. 主要コンポーネントのコンソールエラーが出ていないこと。
5. UI 崩れがないことをスクリーンショットで保存すること。

## Codex からの実行フロー

Codex に渡すプロンプト例は `tests/ui/prompts/codex-smoke-test.md` にまとめています。概要は次のとおりです。

1. `chrome-devtools` MCP サーバーを使用するよう明示する。
2. `new_page` → `navigate_page` で対象 URL を開く。
3. `wait_for` で主要なセレクタ（例: `data-testid="wordpack-list"`）が描画されるまで待機する。
4. `click` / `fill` などの操作ツールで UI フローを巡回する。
5. `list_console_messages`, `take_screenshot`, `list_network_requests` で状態を収集する。
6. 結果を Codex に解釈させ、改善点を洗い出したうえで修正 PR を作成する。

Codex が同じフローを再実行できるよう、**セレクタは `data-testid` / `aria-label` 等の安定要素を利用**してください。将来 UI 改修を行う際はチェックリストとプロンプトのセレクタを更新します。

## テスト結果の評価と改善ループ

1. **結果取得:** Codex は `take_screenshot` や `list_console_messages` の出力を受け取り、スクリーンショットとログを保存します。
2. **自己評価:** 収集したデータを Codex に要約させ、想定との乖離（レイアウト崩れ、未描画、ネットワークエラー等）を特定します。
3. **改善実装:** Codex に検出内容を入力し、該当するフロントエンドコード（React/Vite）を修正させます。修正後は Vitest による単体テストも実行し、ユニットレベルの退行を防ぎます。
4. **再テスト:** 改修直後に同じ MCP スモークテストを繰り返し、改善が反映されたことと新たな問題が発生していないことを確認します。

## CI・自動化への展開

- 既定の GitHub Actions CI では `UI smoke test (Chrome DevTools MCP)` ジョブが自動実行されます。追加で独自の CI/CD（例: ステージング環境デプロイ前検証）を構築する際も、Node.js 22・Chrome・`npm run smoke` の 3 点セットを用意すれば同じテストを再利用できます。
- `codex mcp run` を直接呼び出す場合や他 CI サービスを利用する場合は、Headless Chrome がインストール済みのベースイメージを選定し、`--headless` と `--isolated` オプションを有効化すると安定します。
- 追加で Lighthouse 等のパフォーマンステストを行いたい場合は、Codex に `performance_start_trace` → `performance_stop_trace` を実行させ、レポートを保存して解析させることができます。

## トラブルシュート

| 症状 | 対処 |
|------|------|
| MCP サーバーが起動しない | `npx chrome-devtools-mcp@latest --help` でヘルプを確認。Chrome がインストールされているか、サンドボックスが有効になっていないかを確認してください。 |
| Chrome との接続に失敗する | `--browserUrl` で既存のデバッグポートに接続するか、`--channel=canary` など別チャネルを試してください。 |
| セレクタが見つからない | UI 更新時に `tests/ui/chrome-devtools-smoke-checklist.md` と `tests/ui/prompts/codex-smoke-test.md` のセレクタを更新し、再実行します。 |
| Codex がログを解析できない | `list_console_messages` の結果をテキストで貼り付け、Codex に具体的なエラーの意味と改善案を説明させます。 |

## 次のステップ

- スモークテスト以外にも、WordPack 作成フローや例文インポートなど複雑な動線をテスト対象に追加する場合は、チェックリストとプロンプトを追加し、Codex が利用できるよう Pull Request に含めてください。
- 取得したスクリーンショットはリポジトリの `static/ui-test-artifacts/` などに保存し、回帰検知に役立てることを推奨します。

---

Chrome DevTools MCP による UI 自動テスト体制を整えることで、Codex が自律的に UI の品質を把握し、修正から再検証までを短時間で反復できます。上記手順に従って運用を開始してください。
