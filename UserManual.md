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
- アプリ実行時は `.env` に `OPENAI_API_KEY` を設定してください。
- テスト/CI は LLM をモックするため、キー不要で実行されます。
- 本番/実運用では `STRICT_MODE=true` を推奨（既定）。必須設定が不足している場合はエラーとなり早期に検出できます。
- テスト/オフライン開発では `STRICT_MODE=false` を設定すると、ローカルフォールバック動作を許容します。
- WordPack の生成で情報が欠ける場合は `.env` の `LLM_MAX_TOKENS` を増やしてください（推奨 1500、状況により 1200–1800）。出力JSONの途中切れを防止します。


---

## 2. 画面構成と操作

### 2-1. 共通要素
- ヘッダー: アプリ名 `WordPack`
- ナビゲーション: 「カード / 文 / アシスト / WordPack / 保存済み / 設定」
- フッター: 「WordPack 英語学習」
- 初期表示: 「保存済み」タブ（保存済みWordPack一覧）
- キーボード操作:
  - Alt+1..6: タブ切替（1=カード, 2=文, 3=アシスト, 4=WordPack, 5=保存済み, 6=設定）
  - `/`: 主要入力欄へフォーカス
- ローディング表示: スピナー＋詳細文言（`LoadingIndicator`）。操作別に文言が変わり、経過時間（mm:ss）も表示されます。
  - 生成: 「生成処理を実行中 / LLM応答の受信と解析を待機しています…」
  - 再生成: 「再生成を実行中 / 指定スコープでLLMにより内容を再構築しています…」
  - 保存済み読み込み: 「保存済みWordPackを読み込み中 / サーバーから詳細を取得しています…」
  - 採点: 「採点を記録中 / SRSメタ・進捗を更新しています…」
- エラー表示: 赤帯（`role="alert"`）で表示されます

### 2-2. 設定パネル（最初に設定）
- ナビの「設定」をクリック
- フィールド: 
  - 「発音を有効化」 … WordPack の発音生成を ON/OFF（M5）
  - 「再生成スコープ」 … `全体/例文のみ/コロケのみ` から選択（M5, Enum）
  - 「temperature」 … 0.0〜1.0（デフォルト 0.6）。
    - 0.6–0.8（文体の多様性）、語数厳密なら 0.3–0.5
  - 「カラーテーマ」 … 「ダークカラー（既定）」/「ライトカラー」
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
3) 右側の「モデル」ドロップダウンで使用モデルを選択（gpt-4.1-mini / gpt-5-mini / gpt-4o-mini）
4) 「生成」をクリック
5) 結果: 1画面に「発音/語義/語源/例文（英日ペア+文法解説）/共起/対比/インデックス/引用/信頼度/学習カード要点」を表示（「語源」は「語義」の直後、「共起」「対比」「インデックス」は「例文」の直後に表示）

新ボタン（生成の右）:
- 「WordPackのみ作成」をクリックすると、内容の生成を行わず、空のWordPackだけを保存します。
- 後から「保存済み」一覧から開いて「再生成」で中身を埋められます。
   - 例文はカード型で表示され、各項目には「英 / 訳 / 解説」のラベルが付きます。1列で縦に積んで表示され、横並びにはなりません。
   - 語義は各 sense ごとに次を表示: 見出し語義（gloss_ja）、定義（definition_ja）、ニュアンス（nuances_ja）、典型パターン（patterns）、類義/反義、レジスター、注意点（notes_ja）

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
- インデックス: 「例文」の直後に `インデックス` を表示し、`最近`（直近5件）と `よく見る`（レビュー回数上位、`GET /api/review/popular`）を表示します。クリックで入力欄に反映されます。

語義表示の仕様（更新）:
- `definition_ja`（任意）: 1–2文で核となる定義
- `nuances_ja`（任意）: 文体/専門度/含意の説明
- `patterns`（配列）: 代表的な構文パターン
- `synonyms` / `antonyms`（配列）: 類義語/反義語
- `register`（任意）: formal/informal 等
- `notes_ja`（任意）: 可算/不可算、自他、前置詞選択など

例文仕様（更新）:
- カテゴリ定義:
  - Dev … ITエンジニアの開発現場（アプリ開発）の文脈
  - CS … 計算機科学の学術研究の文脈
  - LLM … LLMの応用/研究の文脈
  - Business … ビジネスの文脈
  - Common … 日常会話のカジュアルなやり取り（友人・同僚との雑談/チャット等）。ビジネス文書調の語彙（therefore, regarding, via など）は避け、軽いノリの口語で自然なトーンに（過度なスラング・下品な表現は不可）。
- 件数: Dev/CS/LLM は各5文、Business は3文、Common は6文を目安に表示（不足時は空のまま）。Common はカジュアルな日常会話用例に限定（フォーマル表現は避ける）。
- 英文は原則 約75語（±5語）。
- 各例文には任意で `文法: grammar_ja` が付与されます。UI上は「解説」としてカード下部にまとまって表示されます。
- 付加メタデータ（任意）: `category`（`Dev|CS|LLM|Business|Common` のいずれか）、`llm_model`（生成に用いたモデル名）、`llm_params`（主要パラメータを連結した文字列）。既存UIは `en/ja/grammar_ja` のみを参照するため、表示は従来どおりです。

引用と確度（citations/confidence）の読み方（PR5）:
- 引用（citations）: OpenAI LLM が生成した情報の参照元。LLM生成の情報は `{"source": "openai_llm"}` として記録されます。
- 確度（confidence）: `low / medium / high`。LLM の生成品質や整合性ヒューリスティクスで調整。`high` はLLM生成が成功し詳細な情報が得られた状態、`low` はフォールバック情報のみの状態。

### 2-7. 保存済みWordPackパネルの使い方（更新）
保存済みWordPackの管理:
1) 「保存済み」タブを選択
2) 過去に生成したWordPackがカード形式で一覧表示されます
3) 各カードには作成日時・更新日時が表示されます

操作:
- **カードをクリック**: その場で大きめのモーダルが開き内容をプレビューできます（Esc または「閉じる」で閉じる）。
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
- 語義/例文が「なし」になる
  - バックエンドの構造化ログを確認します（標準出力）。主なイベント:
    - `wordpack_generate_request`（入力確認）
    - `llm_provider_select`（`openai` になっているか）
    - `wordpack_llm_output_received`（`output_chars` が 0/極小でないか）
    - `wordpack_llm_json_parsed`（`has_senses`/`has_examples`）
    - `wordpack_examples_built` / `wordpack_senses_built`（件数）
    - `wordpack_generate_response`（`senses_count`/`examples_total`/`has_definition_any`）
  - 改善のためのチェックリスト:
    1) `.env` に `OPENAI_API_KEY` が設定されているか（`llm_provider_select` が `local` だと LLM 出力は空になります）
    2) `.env` の `LLM_MAX_TOKENS` を 1200–1800 に引き上げる（JSON 途中切れ対策）
    3) モデルを `gpt-4o-mini` など JSON 出力が安定したものに設定
    4) `STRICT_MODE=true` で実行してパース失敗を例外化し、根因を特定
  - strict モードの挙動:
    - LLM がタイムアウト/失敗、または空出力/パース不能で `senses`/`examples` が得られない場合はエラー（5xx）になります。
    - さらに、`senses` と `examples` がともに空の場合は 502 を返し、詳細を `detail.message/reason_code/diagnostics/hint` に含めます（`reason_code=EMPTY_CONTENT`）。
    - 既定の LLM タイムアウトは 60 秒（`LLM_TIMEOUT_MS=60000`）。必要に応じて `.env` で調整してください。
  - それでも改善しない場合は、ログ付きで `X-Request-ID` を添えて報告してください。
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
- 500 Internal Server Error（WordPack 生成時）で `TypeError: Responses.create() got an unexpected keyword argument 'reasoning'` と出る
  - 原因: SDK/モデルの組み合わせにより `reasoning`/`text` パラメータが未サポートな場合があります。
  - 現行実装の対応: 当該パラメータを自動で外して再試行します（strict モードでは最終失敗時に `reason_code=PARAM_UNSUPPORTED` でエラー化）。
  - 対応策: モデルを `gpt-4o-mini` 等に変更するか、OpenAI SDK を最新版へ更新してください（`pip install -U openai`）。
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


