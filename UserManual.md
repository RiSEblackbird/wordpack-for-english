## WordPack for English ユーザー操作ガイド

本書は現行実装に基づく操作ガイドです。画面上のUIの使い方、起動方法、必要な準備（ユーザー/開発者）を説明します。パネルごとに挙動・エンドポイントが異なる場合は各セクションに記載します（制約事項は末尾）。

### 想定読者
- 英語学習者（日本語UI）
- 動作確認・開発を行う開発者

### 新機能: WordPack永続化
- 生成されたWordPackは自動的にデータベースに保存されます
- 「保存済み」タブで過去に生成したWordPackを一覧表示・管理できます
- 各WordPackは「表示」「再生成」「削除」が可能です

---

## 1. 事前準備

### 1-1. ユーザー向け（最短）
- 必要環境:
  - モダンブラウザ（Chrome/Edge/Safari/Firefox 最新）
  - Docker Desktop（推奨）
- 起動（Docker 一括）:
  ```bash
  # リポジトリのルートで
  docker compose up --build
  ```
  - フロントエンド: `http://127.0.0.1:5173`
  - バックエンド: `http://127.0.0.1:8000`

### 1-2. 開発者向け（ローカル実行）
- 必要環境:
  - Python 3.11+（venv 推奨）
  - Node.js 18+
- 依存インストール:
  ```bash
  # Python
  python -m venv .venv
  . .venv/Scripts/activate   # Windows PowerShell: .venv\Scripts\Activate.ps1
  pip install -r requirements.txt

  # Frontend
  cd src/frontend
  npm install
  ```
- サービス起動（別ターミナルで）:
  ```bash
  # Backend（リポジトリルートで）
  # OpenAI API キーを設定してください（.env ファイルに OPENAI_API_KEY を追加）
  python -m uvicorn backend.main:app --reload --app-dir src

  # Frontend
  cd src/frontend
  npm run dev
  ```
ヒント（OpenAI API キー / 出力ボリューム）:
- OpenAI API キーが設定されていない場合、アプリは安全なフォールバックモードで動作します。
- 本番/実運用では `STRICT_MODE=true` を推奨（既定）。必須設定が不足している場合はエラーとなり早期に検出できます。
- テスト/オフライン開発では `STRICT_MODE=false` を設定すると、ローカルフォールバック動作を許容します。
 - WordPack の生成で情報が欠ける場合は `.env` の `LLM_MAX_TOKENS` を増やしてください（推奨 1500、状況により 1200–1800）。出力JSONの途中切れを防止します。


---

## 2. 画面構成と操作

### 2-1. 共通要素
- ヘッダー: アプリ名 `WordPack`
- ナビゲーション: 「カード / 文 / アシスト / WordPack / 設定」
- フッター: 「WordPack 英語学習」
- キーボード操作:
  - Alt+1..5: タブ切替（1=カード, 2=文, 3=アシスト, 4=WordPack, 5=設定）
  - `/`: 主要入力欄へフォーカス
- ローディング表示: 「読み込み中…」
- エラー表示: 赤帯（`role="alert"`）で表示されます

### 2-2. 設定パネル（最初に設定）
- ナビの「設定」をクリック
- フィールド: 
  - 「発音を有効化」 … WordPack の発音生成を ON/OFF（M5）
  - 「再生成スコープ」 … `全体/例文のみ/コロケのみ` から選択（M5, Enum）
- 入力後は、他パネルに移動して各機能を試してください

### 2-3. 文（自作文）パネルの使い方
1) 「文」を選択
2) 英文を入力（例: `I researches about AI.`）
3) 「チェック」をクリック
4) 結果: フィードバック（issues/revisions/mini exercise）を表示

ヒント: バックエンドは `POST /api/sentence/check` を提供します。ベースURLが `/api` の場合、そのまま動作します。

### 2-4. アシスト（段落注釈）パネルの使い方
1) 「アシスト」を選択
2) 英文の段落を貼り付け（例: `Our algorithm converges under mild assumptions.`）
3) 「アシスト」をクリック
4) 結果: 文分割＋構文情報＋語注＋パラフレーズ（OpenAI LLMによる詳細な解析）を表示

使用APIは `POST /api/text/assist` に統一済みです。接続設定は不要で、そのまま動作します。OpenAI LLM が有効な場合、各文に詳細なパラフレーズと語彙情報が付与されます。

### 2-5. カード/WordPack パネルの使い方（SRS 連携）
1) 「WordPack」を選択
2) 見出し語を入力（例: `converge`）
3) 「生成」をクリック
4) 結果: 1画面に「発音/語義/共起/対比/例文（英日ペア+文法解説）/語源/引用/信頼度/学習カード要点」を表示

セルフチェック:
- 初期状態で「学習カード要点」には 3 秒のぼかしがかかります
- カウントダウン後に自動解除、またはクリックで即解除できます

レンマ直採点（PR2/PR3）:
- WordPack 表示中に ×/△/○ ボタンでそのまま採点できます。
- バックエンドは `POST /api/review/grade_by_lemma` を提供。カード未登録なら自動で `id = w:<lemma>` を作成し、裏面に WordPack の「学習カード要点」を設定します。
- キーボードショートカット: `1/J = ×`, `2/K = △`, `3/L = ○`
- 設定の「採点後に自動で次へ」を ON にすると、採点後に入力と表示をクリアして次語へ移りやすくなります。

登録状況とSRSメタの確認:
- WordPack 生成後、対象レンマが登録済みなら `repetitions/interval_days/due_at` が表示されます（`GET /api/review/card_by_lemma?lemma=<語>`）。
- 未登録の場合は「未登録」と表示されます。採点すると自動的に登録・更新されます。

カードタブ（従来の復習フロー）:
1) 「カード」を選択
2) 「カードを取得」をクリック → `GET /api/review/today` から本日のカード（最大1枚表示）を取得
3) 採点ボタンを選択 → `× わからない(0)` / `△ あいまい(1)` / `○ できた(2)`
4) 採点すると `POST /api/review/grade` が送信され、次回出題時刻が更新されます（履歴はサーバの SQLite に保存されます）

### 2-6. WordPack 一括表示パネルの使い方（新規）
レンマ直採点（新機能）:
- WordPack 表示中に対象レンマをそのまま採点可能です。
- バックエンドは `POST /api/review/grade_by_lemma` を提供します。
- カード未登録の場合、自動で `id = w:<lemma>` を作成し、裏面には WordPack の「学習カード要点」が入ります。
 - キーボードショートカット: `1/J = ×`, `2/K = △`, `3/L = ○`
 - 設定の「採点後に自動で次へ」を ON にすると、採点後に入力と表示をクリアして次語に移りやすくなります。

進捗の見える化（PR4）:
- 画面上部に「今日のレビュー済み件数」「残り件数」を表示します（`GET /api/review/stats`）。
- 「最近見た語」から直近5件をリンク表示します。クリックで見出し語欄に反映されます。
- セッション完了（残り0件）時は、簡易サマリ（本セッションの件数 / 所要時間）を表示します。

単語アクセス導線の強化（PR5）:
- 対比: `対比` セクションの単語をクリックすると、その語で WordPack をすぐに開けます。
- 共起: `共起` セクションの候補（VO/Adj+N/Prep+N）から語をクリックして横展開できます。
- インデックス: 画面下部に `インデックス` を追加し、`最近`（直近5件）と `よく見る`（レビュー回数上位、`GET /api/review/popular`）を表示します。クリックで入力欄に反映されます。

例文仕様（更新）:
- A1/B1/C1 は各3文、tech は5文を目安に表示（不足時は空のまま）。
- 英文は原則 約25語（±5語）。
- 各例文には任意で `文法: grammar_ja` が付与されます。

引用と確度（citations/confidence）の読み方（PR5）:
- 引用（citations）: OpenAI LLM が生成した情報の参照元。LLM生成の情報は `{"source": "openai_llm"}` として記録されます。
- 確度（confidence）: `low / medium / high`。LLM の生成品質や整合性ヒューリスティクスで調整。`high` はLLM生成が成功し詳細な情報が得られた状態、`low` はフォールバック情報のみの状態。

### 2-7. 保存済みWordPackパネルの使い方（新機能）
保存済みWordPackの管理:
1) 「保存済み」タブを選択
2) 過去に生成したWordPackがカード形式で一覧表示されます
3) 各カードには作成日時・更新日時が表示されます

操作:
- **表示**: ボタンを押すと、その場で大きめのモーダルが開き内容をプレビューできます（Esc または「閉じる」で閉じる）。
- **再生成**: カードの「再生成」ボタンをクリックすると、同じ語でWordPackを再生成し、内容を更新します
- **削除**: カードの「削除」ボタンをクリックすると、そのWordPackをデータベースから削除します

ページネーション:
- 大量のWordPackがある場合、画面下部の「前へ」「次へ」ボタンでページを移動できます
- 現在の表示件数と総件数が表示されます

---

## 3. 使い方の流れ（例）
1) 設定パネルで発音・再生成スコープを必要に応じて調整
2) 文パネルで英文を入力して「チェック」
3) アシストパネルで段落を貼り付けて「アシスト」

---

## 4. 制約・既知の事項
- エンドポイント整合は文/アシストとも `/api/*` に統一済み
- LangGraph/OpenAI LLM統合（RAG無効化）
  - `WordPackFlow`、`ReadingAssistFlow`、`FeedbackFlow` は OpenAI LLM を直接使用して `citations`/`confidence`（low/medium/high, Enum）を付与します
  - RAG機能は無効化され、ChromaDB依存を削除。OpenAI LLM が直接語義・用例・フィードバックを生成します
- 日本語UIの文言は暫定で、今後統一予定
- 発音生成は `src/backend/pronunciation.py` に統一。cmudict/g2p-en が使用可能な環境で精度が向上し、未導入時は例外辞書と規則フォールバック（タイムアウト制御あり）となります（M5）。`設定` パネルの「発音を有効化」で ON/OFF 可能です。
- 復習（SRS）は SQLite で永続化されます（ファイル既定: `.data/srs.sqlite3`）。初回起動時に数枚のカードがシードされます。

運用・品質（M6）:
- `/metrics` で API パス別の p95・件数・エラー・タイムアウトを即時確認できます。
- ログは `structlog` により JSON 形式で出力され、`request_complete` に `path` と `latency_ms` が含まれます。
- LLM 機能を有効化している場合でも、内部の実行は共有スレッドプールで制御されます（アプリ終了時に自動解放）。長時間運用時のスレッド増加は発生しません。

---

## 5. トラブルシュート
- 404 が返る
  - エンドポイントのパスを確認（例: `…/api/sentence/check`, `…/api/text/assist`）
- CORS エラー
  - ローカル開発時はフロントを `npm run dev`、バックエンドを `uvicorn … --reload` で起動してください（Vite のプロキシにより接続設定は不要）
- 変更が反映されない
  - Docker利用時: `docker compose build --no-cache` を実行
  - Vite 監視が不安定: Windows では `CHOKIDAR_USEPOLLING=1` を検討（`docker-compose.yml` に環境変数追加可）
- 500 Internal Server Error（採点ボタン押下時など）
  - バックエンドログに `StateGraph.__init__() missing 1 required positional argument: 'state_schema'` と出る場合、LangGraph の API 差分が原因です。
  - 現行実装では `flows.create_state_graph()` により互換化済みです。最新に更新後も再発する場合は依存を再インストールしてください。
    ```bash
    pip install -U -r requirements.txt
    docker compose build --no-cache && docker compose up
    ```
- 500 Internal Server Error（WordPack 生成時）で `NameError: name 'CollocationLists' is not defined` と出る
  - 原因: `src/backend/flows/word_pack.py` で `CollocationLists`（および `ContrastItem`）のインポート抜け。
  - 対応: 最新版では修正済み。ローカルは `git pull` → 再起動、Docker は `docker compose build --no-cache && docker compose up` を実行してください。
- Docker 起動時に Pydantic の ValidationError（`Extra inputs are not permitted`）が出る
  - `.env` に旧サンプルや別アプリのキー（例: `API_KEY`, `ALLOWED_ORIGINS`）が残っている可能性があります。
  - 現行のバックエンド設定（`src/backend/config.py`）は未使用キーを無視するよう修正済みです（`extra="ignore"`）。再起動して問題が解消するか確認してください。
- 500 Internal Server Error で `ValidationError: 1 validation error for ContrastItem with Field required` が出る
  - 原因: Pydantic v2 のエイリアス設定が未適用で、`contrast` 要素の `with` が内部フィールド `with_` にマッピングされず必須エラーになっていました。
  - 対応: `src/backend/models/word.py` の `ContrastItem` を `model_config = ConfigDict(populate_by_name=True)` へ修正済み。最新版へ更新し再起動（Docker は `docker compose build --no-cache && docker compose up`）。
  - 補足: API レスポンスの `contrast` は `[{"with": string, "diff_ja": string}]` の形で返ります。

---

## 6. 参考（現状のAPI）
- `POST /api/sentence/check` … 自作文チェック（OpenAI LLM による詳細な文法・スタイル分析と `confidence` を付与）
- `POST /api/text/assist` … 段落注釈（OpenAI LLM: 文の解析・パラフレーズ・語彙情報を直接生成し `citations`/`confidence` を付与）
- `POST /api/word/pack` … WordPack 生成（OpenAI LLM: 語義/共起/対比/例文/語源/学習カード要点/発音RP を直接生成し `citations`/`confidence` を付与。`pronunciation_enabled`, `regenerate_scope`(Enum) をサポート）
- `GET  /api/review/today` … 本日のカード（最大5枚）
- `POST /api/review/grade` … 採点（0/1/2）と次回時刻の更新

---

## 7. 運用のヒント（PR4）
- レート制限: 1分あたりの上限を IP と `X-User-Id`（任意ヘッダ）ごとに適用します。超過時は `429` が返ります。時間を開けて再試行してください。
- リクエストID: すべての応答に `X-Request-ID` が付きます。問題報告時に併記いただくと調査が容易です。
- 監視: `/metrics` でパス別の p95/件数/エラー/タイムアウトを確認できます。
- 例外監視（任意）: 管理者が Sentry DSN を設定している場合、重大なエラーは自動送信されます。


