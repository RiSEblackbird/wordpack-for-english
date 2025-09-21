## WordPack for English ユーザー操作ガイド

本書は「一般ユーザー向け」と「開発者・運用者向け」を完全に分離した二部構成です。まずは Part A（一般ユーザー向け）をご覧ください。技術情報・API・環境構築は Part B に集約しています。

---

## Part A. 一般ユーザー向けガイド（IT/技術知識は不要）

### A-1. はじめに（想定読者）
- 英語学習者（日本語UIで簡単に使いたい方向け）

### A-2. はじめかた（最短）
- 必要なもの:
  - モダンブラウザ（Chrome/Edge/Safari/Firefox 最新）
  - Docker Desktop（推奨）
- 起動（まとめて開始）:
  ```bash
  # リポジトリのルートで
  docker compose up --build
  ```
  - 画面（フロントエンド）にアクセス: `http://127.0.0.1:${FRONTEND_PORT:-5173}`

### A-3. 新機能（保存）
- 生成した WordPack は自動で保存されます
- WordPackタブ下部の「保存済みWordPack一覧」で表示・管理できます（プレビュー/再生成/削除）
  - 表示モードは「カード」「リスト（索引）」を切替可能。リストは画面幅が十分なとき2列で表示されます。
  - 各WordPackカードの右上に「音声」ボタンがあり、語彙（見出し語）をその場で再生できます。カードをクリックしてプレビューを開いた場合も、見出し語の右側から同じ音声再生が行えます。

### A-4. 画面の見かた（共通）
- ヘッダー: アプリ名 `WordPack`
- ナビゲーション: 「WordPack / 例文一覧 / 設定」
- 初期表示: 「WordPack」タブ（見出し語入力と同ページ下部に保存済み一覧）
- キーボード操作:
- Alt+1..3: タブ切替（1=WordPack, 2=例文一覧, 3=設定）
  - `/`: 主要入力欄へフォーカス
- 通知表示（右下）: 生成の開始〜完了まで、画面右下に小さな通知カードを表示します。進行中はスピナー、成功で ✓、エラーで ✕ に切り替わります。複数件は積み重なって表示され、✕ ボタンで明示的に閉じるまで自動で消えません。ページ移動/リロード後も表示は維持されます。生成/再生成/削除が完了すると保存済み一覧が自動で更新されます。
- エラー表示: 画面上部の帯または右下の通知カードに表示（内容は同等）

### A-5. 設定パネル
- 「設定」タブで次を切替できます
  - 発音を有効化（ON/OFF）
  - 再生成スコープ（全体/例文のみ/コロケのみ）
  - temperature（0.0〜1.0、デフォルト 0.6）
  - カラーテーマ（ダーク/ライト）

### A-6. 例文一覧タブ（横断ビュー）
- 「例文一覧」タブでは、保存済みの例文をWordPack横断で一覧できます。
- 表示:
  - 表示モード: カード/リスト を切替可
  - 並び替え: 例文の作成日時 / WordPackの更新日時 / 単語名 / カテゴリ
  - 検索: 前方一致 / 後方一致 / 部分一致（原文 英文が対象）
  - 絞り込み: カテゴリ（Dev/CS/LLM/Business/Common）
- 操作:
  - 「訳一括表示」スイッチ: 現在の一覧で全ての訳文を同時に開く/閉じる（ONの間は各カードの「訳表示」ボタンが自動的に無効になります）
  - 「訳表示」ボタン: 原文の下に日本語訳を展開/畳む
- 「音声」ボタン: OpenAI gpt-4o-mini-tts で原文を音声再生（音量は端末で調整）。詳細モーダルでは原文・日本語訳それぞれの見出し右側にもボタンがあり、どちらの文も個別に再生できます。
  - 項目クリック: 詳細モーダル（原文/日本語訳/解説）を表示


### A-8. WordPack パネル（学習カード連携）
1) 「WordPack」を選択
2) 見出し語を入力（例: `converge`）
3) 必要に応じて右側の「モデル」を選択
4) 「生成」をクリック
5) 1画面に「発音/語義/語源/例文（英日ペア+解説）/共起/対比/インデックス/引用/確度/学習カード要点」を表示

- 便利なボタン:
  - 「WordPackのみ作成」… 内容生成せず空のWordPackを保存（あとで再生成で中身追加）
- 例文表示:
  - カテゴリ例: Dev/CS/LLM/Business/Common（必要数が足りない場合は空欄のまま）
  - 各例文は「英 / 訳 / 解説」をカード型で縦に表示
  - 各カード下部の「音声」ボタンで原文をその場で再生（OpenAI gpt-4o-mini-tts を使用）
- 語義表示（各 sense 単位）:
  - 見出し語義/定義/ニュアンス/典型パターン/類義・反義/レジスター/注意点

- セルフチェック: 「学習カード要点」は3秒のぼかし後に表示（クリックで即解除）
- 採点（レンマ直採点）:
  - ×/△/○ で採点可能（未登録なら自動登録）
  - ショートカット: `1/J=×`, `2/K=△`, `3/L=○`
  - 設定の「採点後に自動で次へ」をONにすると、採点後に入力と表示をクリア

- 保存済みWordPack一覧（同ページ下部）:
  - 生成済みの WordPack をカード形式で一覧表示
  - カードをクリックで大きめのモーダルでプレビュー
  - 「語義一括表示」スイッチで、一覧内の語義タイトルを一括で表示/非表示（ONの間は各カード/リストの「語義」ボタンが自動的に無効になります）
  - 「語義」ボタンで語義タイトルを表示/非表示に切り替え（カード表示では見出し語の下に表示されます）
  - 「音声」ボタンで見出し語（WordPackの語彙）を再生できます（カード表示/リスト表示とも同じボタンが並び、プレビューモーダルでも見出し語の右側から再生できます）
  - 不要なら「削除」で削除（必要に応じて再生成も可能）
  - 多い場合は画面下部のページネーションで移動（現在件数/総件数を表示）


### A-10. 使い方の流れ（例）
1) 設定で発音・再生成スコープなどを調整
2) WordPack を生成・保存

### A-13. 文章インポートの詳細モーダル（共通UI）
- 文章の詳細は共通モーダル `ArticleDetailModal` で表示します。
- 表示内容: 英語タイトル / 英語本文 / 日本語訳 / 解説（日本語訳の直下に表示） / 生成開始・完了の時刻（作成/更新欄に表示） / バックエンドで計測した生成所要時間 / 生成カテゴリ / AIモデル・パラメータ / 関連WordPack
- 英語タイトルの右側にある「音声」ボタンで英語本文（例文部分を含む全文）をOpenAI gpt-4o-mini-ttsで再生できます。
- 関連WordPack一覧の直前には、生成開始時刻（作成欄）・生成完了時刻（更新欄）・計測済みの生成所要時間・生成カテゴリ・AIモデル/パラメータを2列レイアウトでまとめたメタ情報が表示されます（未記録の項目は「未記録」「未指定」などの表示になります）。
- インポート画面のカテゴリ選択（Dev/CS/LLM/Business/Common）は、そのまま `生成カテゴリ` として保存・表示されます。未選択はありません（初期値は `Common`）。
- 関連WordPackは常にカード表示で統一されています。
- 「文章インポート」直後のモーダルではカード上で「生成」ボタンとプレビュー（語彙名クリック）が利用できます。
- 「インポート済み文章」から開くプレビューでは閲覧専用です（WordPack操作はありません）。

### A-11. 制約・既知の事項（ユーザー向け）
- UI文言は今後統一予定
- SQLite は WordPack と文章の保存専用です（復習スケジュール機能はありません）

### A-12. トラブルシュート（一般ユーザー向け）
- 表示が更新されない: ブラウザを更新、または一度アプリを停止して再起動
- ボタンを押しても進まない: 少し時間を置いて再試行（通信中はメッセージが表示されます）
- エラー帯が出た: 画面の指示に従って操作をやり直すか、必要に応じて管理者に連絡（画面右上などに表示されるリクエストIDがあれば併記）

### A-14. 保存済みWordPack一覧の使い方（索引リスト表示）
- 右上の表示切替で「リスト」を選ぶと、単語帳の索引のようにテキストで一覧表示されます。
- 画面幅に余裕がある場合は2列で表示され、縦スクロールで多数の項目を素早く確認できます。
- ページサイズは既定で200件です（ページ下部のページネーションで移動）。
  - 各項目にはカテゴリ別の例文件数が表示されます。例文未生成の場合は「例文未生成」と表示されます。
  - 「語義一括表示」スイッチで全項目の語義タイトルをまとめて展開し、OFFに戻すと非表示にできます。
  - 各項目の右側に「語義」「音声」ボタンが並び、語義タイトルを同じ行で確認した上で語彙（見出し語）を再生できます。

---

## Part B. 開発者・運用者向けガイド（技術情報）

本パートは開発・運用に必要な情報のみをまとめています。一般ユーザーは読む必要はありません。

#### 開発時の自動ルール（MDC）
`.cursor/rules/*.mdc` に常時適用（alwaysApply: true）の実務ルールを定義しています。
- 推論様式: `base-reasoning-and-communication.mdc`
- コーディング原則: `base-coding-principles.mdc`
- 品質ゲート/テスト基本: `base-quality-gates.mdc`
- フロントエンド検証: `frontend-testing.mdc`
- バックエンド検証: `backend-testing.mdc`
- 改修/変更管理: `maintenance-and-change-management.mdc`
- ドキュメント作成: `docs-authoring.mdc`

### B-1. ローカル実行（開発用）
- 必要環境: Python 3.11+（venv 推奨）, Node.js 18+
- 依存インストール:
  ```bash
  # Python
  python -m venv .venv
  . .venv/Scripts/activate   # Windows PowerShell: .venv\Scripts\Activate.ps1
  pip install -r requirements.txt

  # Frontend
  cd apps/frontend
  npm install
  ```
- サービス起動（別ターミナル）:
  ```bash
  # Backend（リポジトリルートで）
  # .env に OPENAI_API_KEY を設定
  python -m uvicorn backend.main:app --reload --app-dir apps/backend

  # Frontend
  cd apps/frontend
  npm run dev
  ```
- ヒント（APIキー/出力）:
  - `.env` に `OPENAI_API_KEY`
  - テスト/CI はモックのため不要
  - 本番は `STRICT_MODE=true` 推奨（開発では `false` 可）
  - 途中切れ対策に `LLM_MAX_TOKENS` を 1200–1800（推奨1500）

### B-10. オブザーバビリティ（Langfuse）
- `.env` に `LANGFUSE_ENABLED=true` と各キーを設定し、`requirements.txt` の `langfuse` を導入してください。
- 本アプリは Langfuse v3（OpenTelemetry）を使用します。
  - HTTP 親スパン: `input`（パス/メソッド/クエリ要点）と `output`（ステータス/ヘッダ要点）を属性で付与。
  - LLM スパン: `input`（モデル・プロンプト長など）/ `output`（生成テキストの先頭〜最大40000文字）を属性で付与。
  - v2 クライアント互換パスでは `update(input=..., output=...)` を使用。
- LLM プロンプト全文の記録（任意）:
  - 既定ではプレビューのみ（`prompt_preview`）。`.env` で `LANGFUSE_LOG_FULL_PROMPT=true` を設定すると、`input.prompt` に全文（最大 `LANGFUSE_PROMPT_MAX_CHARS`）と `prompt_sha256` を付与します。
  - 機微情報の観点から、本番では原則オフのまま運用してください。
- ダッシュボードで Input/Output が空の場合:
  1) `.env` のキー/ホスト設定を確認
  2) `LANGFUSE_ENABLED=true` か確認
  3) `apps/backend/backend/observability.py` の v3 分岐が有効（`set_attribute('input'|'output', ...)` 実行）であることを確認

### B-2. アーキテクチャと実装メモ
- エンドポイント統合は `/api/*` に統一
- LangGraph/OpenAI LLM 統合
  - `WordPackFlow`、`ReadingAssistFlow`、`FeedbackFlow` は OpenAI LLM を直接使用し、`citations`/`confidence`（Enum: low/medium/high）を付与
  - ChromaDB 依存は削除
- 発音生成は `apps/backend/backend/pronunciation.py` に統一
  - cmudict/g2p-en 利用時は精度向上、未導入時は例外辞書+規則フォールバック（タイムアウト制御）

### B-3. API 一覧（現状）
- `POST /api/word/pack` … WordPack 生成（語義/共起/対比/例文/語源/学習カード要点/発音RP + `citations`/`confidence`、`pronunciation_enabled`,`regenerate_scope` 対応）
- 追加（保存済み WordPack 関連）:
  - `DELETE /api/word/packs/{id}/examples/{category}/{index}` … 例文の個別削除
- `POST /api/tts` … OpenAI gpt-4o-mini-tts を使い、`text`/`voice` を受け取って `audio/mpeg` ストリームを返却

### B-4. 保存済み WordPack の内部構造（実装メモ）
- 例文は DB で別テーブルに正規化。部分読み込み/部分削除が高速
- API の入出力は `sense_title`（語義タイトル）と `examples` を含む完全な `WordPack`
- `word_packs` テーブルには `sense_title` 列を新設し、一覧表示用に語義タイトルを保持します

### B-5. 運用・監視・品質
- `/metrics` で API パス別の p95・件数・エラー・タイムアウトを確認
- ログは `structlog` による JSON 形式。`request_complete` に `path`/`latency_ms`
- レート制限: 1分あたりの上限を IP と `X-User-Id`（任意ヘッダ）ごとに適用（超過は `429`）
- すべての応答に `X-Request-ID`。障害報告時に併記
- 例外監視（任意）: Sentry DSN 設定があれば重大エラー送信
- LLM 機能有効時でも内部スレッドは共有プールで制御（長時間運用でのスレッド増加なし）

### B-6. トラブルシュート（詳細）
- 語義/例文が空になる
  - 確認するログイベント: `wordpack_generate_request` / `llm_provider_select` / `wordpack_llm_output_received` / `wordpack_llm_json_parsed` / `wordpack_examples_built` / `wordpack_senses_built` / `wordpack_generate_response`
  - チェックリスト:
    1) `.env` の `OPENAI_API_KEY`（`llm_provider_select` が `local` だと空出力）
    2) `LLM_MAX_TOKENS` を 1200–1800 に（JSON 途中切れ対策）
    3) モデルを `gpt-4o-mini` など安定モデルへ
    4) `STRICT_MODE=true` でパース失敗を例外化して原因特定
  - strict モード:
    - LLM 失敗/空出力/パース不能で `senses`/`examples` が得られない場合は 5xx
    - `senses` と `examples` がともに空なら 502（`reason_code=EMPTY_CONTENT`、`detail.*` に原因）
    - 既定タイムアウト: `LLM_TIMEOUT_MS=60000`
  - 未解決時はログと `X-Request-ID` を添えて報告

- 404 が返る
  - パスを確認（例: WordPack生成は `…/api/word/pack`）

- CORS エラー
  - ローカル開発では Frontend を `npm run dev`、Backend を `uvicorn … --reload` で起動（Vite プロキシで接続設定不要）

- 変更が反映されない
  - Docker: `docker compose build --no-cache`
  - Vite 監視: Windows は `CHOKIDAR_USEPOLLING=1`（`docker-compose.yml` で設定可）

#### B-6-1. Langfuse のトレースが記録されない
- 現在は Langfuse v3（OpenTelemetry）対応済みです。
- 症状: `WARNING ... langfuse_trace_api_missing` が出続ける／最初の数件のみ表示され以後が出ない場合、依存の不整合か環境変数の誤設定が考えられます。
- 対応: `docker compose build --no-cache && docker compose up` を実行。必要に応じて `LANGFUSE_PUBLIC_KEY/SECRET_KEY/HOST` を再確認し、プロジェクトと日付フィルタを正しく選択してください。古い v2 を利用する場合は `requirements.txt` を v2 に固定してご利用ください。

#### B-1-1. ポート競合の回避（Docker）
- 既定ポートが使用中で起動できない場合は、ホスト公開ポートを環境変数で上書きできます。
  - 一時的に上書き:
    ```bash
    BACKEND_PORT=8001 FRONTEND_PORT=5174 docker compose up --build
    ```
  - `.env` に固定（推奨）:
    ```env
    BACKEND_PORT=8001
    FRONTEND_PORT=5174
    ```
    以後は通常どおり `docker compose up --build`。
- コンテナ内バックエンドの実ポートは常に `8000` 固定です（ヘルスチェック含む）。

- 500 Internal Server Error（採点時など）
  - ログに `StateGraph.__init__() missing 1 required positional argument: 'state_schema'`
  - 対応: `flows.create_state_graph()` で互換化済み。再発時は依存を再インストール
    ```bash
    pip install -U -r requirements.txt
    docker compose build --no-cache && docker compose up
    ```

- 500 Internal Server Error（WordPack 生成時）で `TypeError: Responses.create() got an unexpected keyword argument 'reasoning'`
  - 原因: SDK/モデルの組み合わせで `reasoning`/`text` 未サポート
  - 現行: 当該パラメータを自動で外して再試行（strict では最終失敗時に `reason_code=PARAM_UNSUPPORTED`）
  - 対応: モデルを `gpt-4o-mini` 等へ変更、または `pip install -U openai`

- 500 Internal Server Error で `ValidationError: 1 validation error for ContrastItem with Field required`
  - 原因: Pydantic v2 のエイリアス設定未適用により `with` → `with_` マッピング不全
  - 対応: `apps/backend/backend/models/word.py` の `ContrastItem` に `model_config = ConfigDict(populate_by_name=true)`（適用済み）。最新版へ更新し再起動（Docker は再ビルド推奨）
  - 補足: API レスポンスの `contrast` は `[{"with": string, "diff_ja": string}]`

### B-7. 運用のヒント（PR4）
- レート制限/リクエストID/監視（p95, 件数, エラー, タイムアウト）/例外監視（Sentry）などを運用ルールとして維持
- Langfuse（任意）: `.env` に `LANGFUSE_ENABLED=true`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST`, `LANGFUSE_RELEASE` を設定すると、HTTP/LLM のトレースが送信されます。
  - Strict モード時は上記キーと `langfuse` パッケージが必須。欠落時は起動でエラーになります。

## 文章インポートの使い方

1. 画面上部のタブから「文章インポート」を選択します。
2. テキストエリアに文章（日本語/英語）を貼り付けます。
3. モデルとパラメータを選択します。
   - モデル: 「gpt-5-mini / gpt-5-nano / gpt-4.1-mini / gpt-4o-mini」から選択
   - gpt-5-mini / gpt-5-nano を選ぶと `reasoning.effort` と `text.verbosity` の選択欄が表示されます（推論系）。
   - それ以外のモデルは `temperature`（設定タブの値）で制御されます（sampling系）。
4. 「インポート」をクリックします。
5. 右下に進捗通知が表示され、完了後にモーダルで詳細が開きます。
   - 英語タイトル、英語本文（原文そのまま）、日本語訳、解説が表示されます。
   - 下部に関連するWordPackがカードで並びます。
     - 「生成」ボタンで当該WordPackの内容を生成できます（既存は再生成）。
       - 通信エラー時の注意: サーバの厳格モードでは LLM 出力の JSON が壊れていると 502 になります（詳細メッセージに `reason_code=LLM_JSON_PARSE` とヒントが表示されます）。時間を置く、モデル/設定（verbosity/temperature）を見直すなどで再試行してください。
     - カードの語彙名をクリックするとWordPack詳細モーダルが開きます。
6. 「インポート済み文章」一覧から、保存済みの文章を再表示できます。不要になった記事は削除してください。

補足: 「生成＆インポート」ボタン（カテゴリ指定で例文を自動生成して記事化）でも、上記で選択したモデル/パラメータが反映されます。gpt-5-mini / gpt-5-nano は `reasoning`/`text`、その他は `temperature` が送信されます。

