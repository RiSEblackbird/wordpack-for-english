## WordPack for English ユーザー操作ガイド（MVP）

本書は、現状のMVP実装を前提とした操作ガイドです。画面上のUIの使い方、起動方法、必要な準備（ユーザー/開発者）を説明します。現状は一部APIがモック/最小実装であり、パネルごとに挙動・エンドポイントが異なります（制約事項を末尾に記載）。

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
  # 事前に（初回のみ）RAGの最小シードを投入できます:
  #   python -m backend.indexing --persist .chroma
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
- フィールド: 「API ベースURL」
  - 既定値: `/api`
  - 入力例（ローカル開発）: `http://127.0.0.1:8000/api`
- 入力後は、他パネルに移動して各機能を試してください

### 2-3. 文（自作文）パネルの使い方
1) 「文」を選択
2) 英文を入力（例: `I researches about AI.`）
3) 「チェック」をクリック
4) 結果: 簡易ダミーのフィードバック（issues/revisions/mini exercise）を表示

ヒント: バックエンドは `POST /api/sentence/check` を提供します。ベースURLが `/api` の場合、そのまま動作します。

### 2-4. アシスト（段落注釈）パネルの使い方
1) 「アシスト」を選択
2) 英文の段落を貼り付け（例: `Our algorithm converges under mild assumptions.`）
3) 「アシスト」をクリック
4) 結果: 文分割＋簡易構文情報＋語注（ダミー）＋パラフレーズ（原文）を表示

使用APIは `POST {APIベースURL}/text/assist` に統一済みです。`Settings` の API ベースURL を `/api`（または `http://127.0.0.1:8000/api`）に設定すればそのまま動作します。

### 2-5. カードパネルの使い方（SRS最小実装）
1) 「カード」を選択
2) 「カードを取得」をクリック → `GET /api/review/today` から本日のカード（最大1枚表示）を取得
3) 採点ボタンを選択 → `× わからない(0)` / `△ あいまい(1)` / `○ できた(2)`
4) 採点すると `POST /api/review/grade` が送信され、次回出題時刻が更新されます

---

## 3. 使い方の流れ（例）
1) 設定パネルで API ベースURL を入力
2) 文パネルで英文を入力して「チェック」
3) アシストパネルで段落を貼り付けて「アシスト」

---

## 4. 制約・既知の事項（MVP）
- エンドポイント整合は文/アシストとも `/api/*` に統一済み
- LangGraph/RAG/LLM は M3 で RAG の最小導入を実施
  - `WordPackFlow` と `ReadingAssistFlow` は ChromaDB からの近傍取得により `citations`/`confidence` を付与します（シード未投入時は空/low）
  - `FeedbackFlow` は現状ダミー（将来RAG/LLM統合）
- 日本語UIはMVP文言（用語は今後統一予定）

---

## 5. トラブルシュート
- 404 が返る
  - ベースURLとエンドポイントの組み合わせを確認（例: `…/api/sentence/check`, `…/api/text/assist`）
- CORS エラー
  - ローカル開発時はフロントを `npm run dev`、バックエンドを `uvicorn … --reload` で起動し、`Settings` で `http://127.0.0.1:8000/api` を設定
- 変更が反映されない
  - Docker利用時: `docker compose build --no-cache` を実行
  - Vite 監視が不安定: Windows では `CHOKIDAR_USEPOLLING=1` を検討（`docker-compose.yml` に環境変数追加可）

---

## 6. 参考（現状のAPI）
- `POST /api/sentence/check` … 自作文チェック（ダミーの詳細フィードバック）
- `POST /api/text/assist` … 段落注釈（M3: 近傍取得で `citations`/`confidence` を付与）
- `POST /api/word/pack` … WordPack 生成（M3: 近傍取得で `citations`/`confidence` を付与）
- `GET  /api/review/today` … 本日のカード（最大5枚）
- `POST /api/review/grade` … 採点（0/1/2）と次回時刻の更新

---

## 7. 開発メモ（導入・検証のヒント）
- テスト実行:
  ```bash
  pytest -q
  ```
- コード配置（抜粋）:
  - バックエンド: `src/backend`（`routers/*`, `flows/*`, `models/*`）
  - フロントエンド: `src/frontend`（React + Vite）
- 実装差し替えポイント:
  - `src/backend/providers.py` … LLM/Embedding クライアントの実体
  - `flows/*` … LangGraph ノードを本実装へ置換


