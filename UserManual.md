## WordPack for English ユーザー操作ガイド

本書は現行実装に基づく操作ガイドです。画面上のUIの使い方、起動方法、必要な準備（ユーザー/開発者）を説明します。パネルごとに挙動・エンドポイントが異なる場合は各セクションに記載します（制約事項は末尾）。

### 想定読者
- 英語学習者（日本語UI）
- 動作確認・開発を行う開発者

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
  # 任意（初回のみ）RAGインデクスを投入できます（JSONL対応）:
  #   python -m backend.indexing
  #   python -m backend.indexing --word-jsonl data/word_snippets.jsonl --terms-jsonl data/domain_terms.jsonl
  python -m uvicorn backend.main:app --reload --app-dir src

  # Frontend
  cd src/frontend
  npm run dev
  ```

---

## 2. 画面構成と操作

### 2-1. 共通要素
- ヘッダー: アプリ名 `WordPack`
- ナビゲーション: 「カード / 文 / アシスト / 設定」
- フッター: 「WordPack 英語学習」
- キーボード操作:
  - Alt+1..4: タブ切替（1=カード, 2=文, 3=アシスト, 4=設定）
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
4) 結果: 文分割＋構文情報＋語注＋パラフレーズ（原文）を表示

使用APIは `POST /api/text/assist` に統一済みです。接続設定は不要で、そのまま動作します。

### 2-5. カードパネルの使い方（SRS: SQLite 永続化）
1) 「カード」を選択
2) 「カードを取得」をクリック → `GET /api/review/today` から本日のカード（最大1枚表示）を取得
3) 採点ボタンを選択 → `× わからない(0)` / `△ あいまい(1)` / `○ できた(2)`
4) 採点すると `POST /api/review/grade` が送信され、次回出題時刻が更新されます（履歴はサーバの SQLite に保存されます）

---

## 3. 使い方の流れ（例）
1) 設定パネルで発音・再生成スコープを必要に応じて調整
2) 文パネルで英文を入力して「チェック」
3) アシストパネルで段落を貼り付けて「アシスト」

---

## 4. 制約・既知の事項
- エンドポイント整合は文/アシストとも `/api/*` に統一済み
- LangGraph/RAG/LLM は M3/PR3 で RAG を導入
  - `WordPackFlow` と `ReadingAssistFlow` は ChromaDB からの近傍取得により `citations`/`confidence`（low/medium/high, Enum）を付与します（シード未投入時は空/low）
  - RAG は `rag_enabled` フラグで無効化可能。近傍クエリはレート制御/タイムアウト/リトライ/フォールバックを標準化しています。
  - `FeedbackFlow` は将来RAG/LLM統合を予定
- 日本語UIの文言は暫定で、今後統一予定
- 発音生成は `src/backend/pronunciation.py` に統一。cmudict/g2p-en が使用可能な環境で精度が向上し、未導入時は例外辞書と規則フォールバック（タイムアウト制御あり）となります（M5）。`設定` パネルの「発音を有効化」で ON/OFF 可能です。
- 復習（SRS）は SQLite で永続化されます（ファイル既定: `.data/srs.sqlite3`）。初回起動時に数枚のカードがシードされます。

運用・品質（M6）:
- `/metrics` で API パス別の p95・件数・エラー・タイムアウトを即時確認できます。
- ログは `structlog` により JSON 形式で出力され、`request_complete` に `path` と `latency_ms` が含まれます。

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

---

## 6. 参考（現状のAPI）
- `POST /api/sentence/check` … 自作文チェック（RAG 引用と `confidence` を付与）
- `POST /api/text/assist` … 段落注釈（RAG: 近傍取得で `citations`/`confidence` を付与、簡易要約を返却）
- `POST /api/word/pack` … WordPack 生成（RAG: 近傍取得で `citations`/`confidence` を付与。`pronunciation_enabled`, `regenerate_scope`(Enum) をサポート）
- `GET  /api/review/today` … 本日のカード（最大5枚）
- `POST /api/review/grade` … 採点（0/1/2）と次回時刻の更新

---

## 7. 開発メモ（導入・検証のヒント）
- テスト実行:
  ```bash
  pytest
  # または従来の明示オプション
  pytest -q --cov=src/backend --cov-report=term-missing --cov-fail-under=60
  ```
- 追加テスト（PR7）:
  - `tests/test_integration_rag.py` … Chroma に最小シード投入→ `citations`/`confidence` を統合検証
  - `tests/test_e2e_backend_frontend.py` … APIフローのE2E相当（正常/タイムアウト周辺の健全性）
  - `tests/test_load_and_regression.py` … 軽負荷スモーク（10リクエスト）とスキーマ回帰
- コード配置（抜粋）:
  - バックエンド: `src/backend`（`routers/*`, `flows/*`, `models/*`, `metrics.py`）
  - フロントエンド: `src/frontend`（React + Vite）
- 実装差し替えポイント:
  - `src/backend/providers.py` … LLM/Embedding クライアントの実体
  - `flows/*` … LangGraph ノードを本実装へ置換
  - 運用: `/metrics` で p95/件数/エラー/タイムアウトを確認可能（M6）


