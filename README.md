# WordPack for English

英単語トレーナー（OpenAI LLM×LangGraph）。技術・科学英文の読み・用法・発音の理解を支援します。リポジトリはバックエンド（FastAPI）とフロントエンド（React + Vite）のモノレポ構成です。

## 特徴
- バックエンド: FastAPI、構成・ルータ・簡易ログ、テストあり
- フロントエンド: React + TypeScript + Vite、単一ページ/2パネル構成（WordPack/設定）
- 発音強化（M5）: cmudict/g2p-en による IPA・音節・強勢推定（例外辞書・辞書キャッシュ・タイムアウト付きフォールバック）
- WordPack 再生成の粒度指定（M5）: 全体/例文のみ/コロケのみ の選択（Enum化済み）
- **WordPack永続化機能**: 生成されたWordPackを自動保存し、WordPackタブ下部の一覧で閲覧・削除が可能（再生成は `WordPack` セクションから実行）
- **WordPackのみ作成（新）**: 内容生成を行わず、空のWordPackを保存できます（UI: 生成ボタン横）。
- **例文UIの改善（新）**: 英文・訳文・文法解説をカード型で表示。各項目に「英/訳/解説」ラベルを付け、可読性を向上。
 - **例文の個別削除（新）**: 保存済みWordPackの詳細画面から、特定カテゴリ内の任意の例文を個別に削除できます。
 - **例文ストレージの正規化（新）**: DB内部で例文を別テーブルに分離し、部分読み込み/部分削除を高速化。API入出力は引き続き `examples` を含む完全な `WordPack` を返します（旧DB形式の自動変換は行いません）。
 - **名詞の用語解説を強化（新）**: 単語が名詞・専門用語の場合、各 `sense` に `term_core_ja`（本質・1〜2文）と `term_overview_ja`（概要・3〜5文）を追加出力・表示。用語としての概念や背景も学べます。

---

## 1. クイックスタート

### 1-1. 前提
- Python 3.11+ 推奨（requirementsは軽量）
- Node.js 18+ / pnpm or npm / (Vite)

### 1-2. 依存インストール
```bash
# Python
python -m venv .venv
. .venv/Scripts/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt  # M5: 発音で cmudict / g2p-en を使用

# Frontend
cd src/frontend
npm install
```

### 1-3. OpenAI API キーの設定
```bash
# .env ファイルを作成し、OpenAI API キーを設定
cp env.example .env
# .env ファイルを編集して OPENAI_API_KEY を設定
```

注意: アプリ実行時は OpenAI API キーを設定してください（`.env`）。ただし、テスト/CI は LLM をモックして実行するためキーは不要です。

### 1-4. バックエンド起動
```bash
# リポジトリルートで
python -m uvicorn backend.main:app --reload --app-dir src
```
- 既定ポート: `http://127.0.0.1:8000`
- ヘルスチェック: `GET /healthz`
- ヘルスチェックは Docker Compose の `healthcheck` でも監視されます（PR4）。

### 1-5. フロントエンド起動
```bash
cd src/frontend
npm run dev
```
- 既定ポート: `http://127.0.0.1:5173`
- 開発時（別ポート）の呼び分け: Vite のプロキシ（既定）により接続設定は不要です。フロントからは相対パス `/api` で呼び出します。

### 1-6. Docker で一括起動（推奨・ホットリロード対応）
```bash
# リポジトリルートで
docker compose up --build
```
- バックエンド: http://127.0.0.1:${BACKEND_PORT:-8000}
- フロントエンド: http://127.0.0.1:${FRONTEND_PORT:-5173}
- ホットリロード:
  - backend: `uvicorn --reload` + ボリュームマウント `.:/app`
  - frontend: Vite dev サーバ + ボリュームマウント `src/frontend:/app`
- フロントからの API 呼び出しは Vite のプロキシ設定で `http://backend:8000` に転送されます。

ポート競合の回避（新）:
- 既定で Backend は `8000`、Frontend は `5173` を公開します。既に使用中の場合は、以下のいずれかで上書きできます。
  - 一時的に上書き（シェル一発指定）:
    ```bash
    BACKEND_PORT=8001 FRONTEND_PORT=5174 docker compose up --build
    ```
  - `.env` で恒久設定（リポジトリ直下の `.env`）:
    ```env
    BACKEND_PORT=8001
    FRONTEND_PORT=5174
    ```
    その後、通常どおり `docker compose up --build` で起動します。

注意:
- コンテナ内のバックエンドは常にコンテナ内ポート `8000` で待ち受けます（ヘルスチェックも `http://127.0.0.1:8000/healthz`）。ホスト側での公開ポートのみ `BACKEND_PORT` で変更されます。

OpenAI LLM統合:
- 既定: `LLM_PROVIDER=openai`, `LLM_MODEL=gpt-4o-mini`。
- RAGは無効。OpenAI LLMが直接生成（語義/用例/フィードバック）。
- `.env` の `LLM_MAX_TOKENS` を調整（推奨1500、JSON途切れ防止）。
- 設定タブに `temperature`（0.0–1.0、既定0.6）。
- WordPackでモデル選択（gpt-4.1-mini / gpt-5-mini / gpt-4o-mini）。選択モデルと `temperature` をAPIへ（未指定は既定）。
- 注意: 現在は Chat Completions。`gpt-5-mini` の `reasoning`/`text` は未適用。安定は `gpt-4o-mini` 推奨。

---

## 2. ディレクトリ構成（抜粋）
```
app/                     # 追加のサンプルFastAPIアプリ（静的配信デモ等）
src/backend/             # 本番用FastAPIアプリ
  main.py                # ルータ登録/ログ初期化
  config.py              # 環境設定（pydantic-settings）
  logging.py             # structlog設定
  routers/               # エンドポイント群
  flows/                 # LangGraphベースの処理
  models/                # pydanticモデル（厳密化済み: Enum/Field制約/例）
  pronunciation.py       # 発音（cmudict/g2p-en優先・例外辞書/キャッシュ/タイムアウト付き）
src/frontend/            # React + Vite
  src/components/        # 2パネルのコンポーネント（WordPack/Settings）
  src/SettingsContext.tsx
static/                  # 最小UIの静的ファイル（`app/main.py`用）
```

---

## 3. API 概要
FastAPI アプリは `src/backend/main.py`。

- `GET /healthz`
  - ヘルスチェック。レスポンス: `{ "status": "ok" }`

- `GET /metrics`
  - 運用メトリクスのスナップショット。パス別に `p95_ms`, `count`, `errors`, `timeouts` を返す（M6）。
  - 併せてアクセスログは JSON 構造化で出力され、`request_complete` に以下フィールドを含みます（PR4）:
    - `request_id`, `path`, `method`, `latency_ms`, `is_error`, `is_timeout`, `client_ip`, `user_agent`

- `POST /api/word/pack`
  
- `POST /api/word/packs`（新）
  - 内容生成を行わず、空のWordPackを作成してIDを返します。
  - リクエスト例: `{ "lemma": "insight" }`
  - レスポンス例: `{ "id": "wp:insight:a1b2c3d4" }`
  - 周辺知識パック生成（OpenAI LLM: 語義/共起/対比/例文/語源/学習カード要点/発音RPを直接生成し `citations` と `confidence` を付与）。
  - 発音: 実装は `src/backend/pronunciation.py` に一本化。cmudict/g2p-en を優先し、例外辞書・辞書キャッシュ・タイムアウトを備えた規則フォールバックで `pronunciation.ipa_GA`、`syllables`、`stress_index` を付与。
  - 例文: Dev/CS/LLM/Business/Common 別の英日ペア配列で返却。各要素は `{ en, ja, grammar_ja?, category?, llm_model?, llm_params? }`。カテゴリ定義は次の通り：
    - `category` はサーバが付与するカテゴリEnum（`Dev|CS|LLM|Business|Common`）。後方互換のため任意。
    - `llm_model` は例文生成に使用したモデル名（任意）。
    - `llm_params` は当該リクエスト時の主要パラメータを連結した文字列（例: "temperature=0.60;reasoning.effort=minimal;text.verbosity=medium"）（任意）。
    - 既存クライアントは `en/ja/grammar_ja` のみを参照しており、UI変更は不要です。
    - Dev … ITエンジニアの開発現場（アプリ開発）の文脈
    - CS … 計算機科学の学術研究の文脈
    - LLM … LLMの応用/研究の文脈
    - Business … ビジネスの文脈
    - Common … 日常会話のカジュアルなやり取り（友人・同僚との雑談/チャット等）。ビジネス文書調の語彙（therefore, regarding, via など）は避け、軽いノリの口語（過度なスラングは不可）で、メッセや通話、待ち合わせなど身近な場面を想定。
  - 語義の拡張（本リリース）: 各 `sense` に以下の詳細フィールドを追加し、よりボリューミーに表示します。
    - `definition_ja: string?` … 日本語の定義（1–2文）
    - `nuances_ja: string?` … 使い分け/含意/文体レベル
    - `patterns: string[]` … 典型パターン
    - `synonyms: string[]` / `antonyms: string[]`
    - `register: string?` … フォーマル/口語など
    - `notes_ja: string?` … 可算/不可算や自他/前置詞選択などの注意
    - 名詞/専門用語のとき: `term_core_ja: string?`（用語の本質） / `term_overview_ja: string?`（用語の概要）。動詞・形容詞などの場合は省略可。
    - 件数: `Dev/CS/LLM` は各5文、`Business` は3文、`Common` は6文（不足時は短くなる／空許容、ダミーは入れない）。`Common` は日常会話のカジュアルな用例に限定し、フォーマル表現は避ける。
    - 長さ: 英文は原則 約75語（±5語）を目安。
    - 解説: `grammar_ja` に文法的な要点を日本語で付与（任意）。
  - リクエスト例（M5 追加パラメータ・Enum化）:
  ```json
  { "lemma": "converge", "pronunciation_enabled": true, "regenerate_scope": "all" }
  ```
    - `pronunciation_enabled`: 発音情報の生成 ON/OFF（既定 true）
    - `regenerate_scope`: `all` | `examples` | `collocations`（Enum）。
  - レスポンス例（抜粋）:
  ```json
  {
    "lemma": "converge",
    "pronunciation": {"ipa_GA":"/kənvɝdʒ/","ipa_RP":"/kənˈvɜːdʒ/","syllables":2,"stress_index":1,"linking_notes":[]},
    "senses": [{"id":"s1","gloss_ja":"集まる・収束する","patterns":["converge on N"]}]
  }
  ```
  - 追加の `senses` 詳細の例:
  ```json
  {
    "id": "s1",
    "gloss_ja": "集まる・収束する",
    "definition_ja": "複数のものが一点・一方向に向かって近づき一つにまとまること。",
    "nuances_ja": "学術文脈では系列や推定量が極限へ近づく含意が強い。",
    "patterns": ["converge on N", "converge toward N"],
    "synonyms": ["gather", "meet"],
    "antonyms": ["diverge"],
    "register": "formal",
    "notes_ja": "自動詞。数学/統計では to/toward の選択でニュアンス差あり。"
  }
  ```
  - 完全な `senses` 詳細の例:
  ```json
  {
    "id": "s1",
    "gloss_ja": "集まる・収束する",
    "definition_ja": "複数のものが一点・一方向に向かって近づき一つにまとまること。",
    "nuances_ja": "学術文脈では系列や推定量が極限へ近づく含意が強い。",
    "patterns": ["converge on N", "converge toward N"],
    "synonyms": ["gather", "meet"],
    "antonyms": ["diverge"],
    "register": "formal",
    "notes_ja": "自動詞。数学/統計では to/toward の選択でニュアンス差あり。",
    "collocations": {"general": {"verb_object": ["gain insight"], "adj_noun": ["deep insight"], "prep_noun": ["insight into N"]}, "academic": {"verb_object": ["derive insight"], "adj_noun": ["empirical insight"], "prep_noun": ["insight for N"]}},
    "contrast": [{"with":"intuition","diff_ja":"直観は体系的根拠が薄いのに対し、insight は分析や経験から得る洞察。"}],
    "examples": {
      "Dev": [
        {"en":"We gained insight after refactoring modules and reviewing logs.","ja":"モジュールのリファクタリングとログ確認の後に洞察を得た。","grammar_ja":"第3文型"}
      ],
      "CS": [
        {"en":"Under mild assumptions, an estimator gains insight about latent structure.","ja":"温和な仮定の下で推定量は潜在構造について洞察を得る。","grammar_ja":"不定詞"}
      ],
      "LLM": [
        {"en":"With better prompts, outputs converge and provide clearer insight.","ja":"プロンプト改善により出力が収束し明確な洞察が得られる。","grammar_ja":"分詞構文"}
      ],
      "Business": [
        {"en":"Metrics offer insight as systems stabilize across deployments.","ja":"デプロイを重ねるにつれメトリクスが洞察を与える。","grammar_ja":"現在形"}
      ],
      "Common": [
        {"en":"Over months, we gained insight and made a better decision.","ja":"数か月を経て洞察を得て、より良い判断を下した。","grammar_ja":"過去形"}
      ]
    },
    "etymology": {"note":"from Middle English, influenced by Old Norse.","confidence":"medium"},
    "study_card": "insight: into による対象提示。deep/valuable と相性良。",
    "citations": [{"text":"LLM-generated information for insight","meta":{"source":"openai_llm","word":"insight"}}],
    "confidence": "high"
  }
  ```
  

### WordPack永続化API

- `GET /api/word/packs`
  - 保存済みWordPackの一覧を取得。ページネーション対応。
  - クエリ: `?limit=<int>&offset=<int>`（例: `?limit=20&offset=0`）
  - レスポンス例:
    ```json
    {
      "items": [
        {
          "id": "wp:converge:a1b2c3d4",
          "lemma": "converge",
          "created_at": "2025-01-01T12:34:56.000Z",
          "updated_at": "2025-01-01T12:34:56.000Z",
          "is_empty": true
        }
      ],
      "total": 1,
      "limit": 20,
      "offset": 0
    }
    ```

- `GET /api/word/packs/{word_pack_id}`
  - 指定されたIDのWordPackを取得。
  - レスポンス: 完全なWordPackオブジェクト（`POST /api/word/pack`と同じ形式）
  - 存在しない場合は404エラー

- `POST /api/word/packs/{word_pack_id}/regenerate`
  - 既存のWordPackを再生成。指定されたIDのWordPackを上書き更新。
  - リクエスト例: `{ "pronunciation_enabled": true, "regenerate_scope": "all" }`
  - レスポンス: 再生成されたWordPackオブジェクト

- `DELETE /api/word/packs/{word_pack_id}`
  - 指定されたIDのWordPackを削除。
  - レスポンス例: `{ "message": "WordPack deleted successfully" }`
  - 存在しない場合は404エラー

- `DELETE /api/word/packs/{word_pack_id}/examples/{category}/{index}`（新）
  - 保存済みWordPackから、特定カテゴリ（`Dev|CS|LLM|Business|Common`）の `index`（0始まり）の例文を削除。
  - レスポンス例: `{ "message": "Example deleted", "category": "Dev", "index": 0, "remaining": 4 }`
  - 存在しないID/範囲外インデックスは404、壊れた保存データは500

- `POST /api/word/packs/{word_pack_id}/examples/{category}/generate`（新）
  - 保存済みWordPackに、指定カテゴリの例文を「2件」追加生成し保存します。
  - 生成時は入力トークン削減のため、既存の例文データをプロンプトに含めません。
  - リクエスト例: `{ "model": "gpt-5-mini", "reasoning": { "effort": "minimal" }, "text": { "verbosity": "medium" } }`
  - レスポンス例: `{ "message": "Examples generated and appended", "added": 2, "category": "Dev", "items": [{"en":"...","ja":"..."}] }`
  - `model/temperature/reasoning/text` は任意。未指定時はサーバ既定（環境変数）を使用。

---

## 4. フロントエンド UI 概要
単一ページで以下の2タブを切替。初期表示は「WordPack」タブ。

- WordPack（`WordPackPanel.tsx`）
  - 見出し語を入力→`生成`。使用API: `POST /api/word/pack`
  - 1画面で「発音/語義/語源/例文/共起/対比/インデックス/引用/信頼度/学習カード要点」を表示（「語源」は「語義」の直後、「共起」「対比」「インデックス」は「例文」の直後に表示）。
  - 例文はカード型（英/訳/解説ラベル付き）で、レベルごとに1列で縦に積んで表示します（横並びにしません）。
  - セルフチェック: 初期は学習カード要点に3秒のぼかしが入り、クリックで即解除可能。
  - 単語アクセス導線（PR5）: 「対比」や「共起」から横展開リンクで他語へ移動。「例文」の直後に「インデックス（最近/よく見る）」を表示。
  - **永続化機能**: 生成されたWordPackは自動的にデータベースに保存され、同ページ下部に保存済み一覧を表示。再生成ボタンで内容を更新可能。

- 設定（`SettingsPanel.tsx`）
  - 発音の有効/無効トグル（M5）
  - 再生成スコープ選択（`全体/例文のみ/コロケのみ`）（M5, Enum）
  - （採点機能は廃止しました）

アクセシビリティ/操作:
- Alt+1..2 でタブ切替（1=WordPack, 2=設定）。`/` で主要入力へフォーカス
- ローディング/通知
  - 生成系の処理（WordPack生成・再生成・例文追加生成・空のWordPack作成）は、画面右下の小さな通知カードに統一しました。従来の画面内ローディング表示や完了時の画面遷移は廃止しています。
  - 通知カードは以下の仕様です：
    - 進行中: スピナー
    - 成功: チェックマーク（✓）
    - 失敗: ✕
    - 右端に✕ボタン（手動で閉じるまで自動クローズしません）
    - 右下に積み重ねて表示（複数同時進行に対応）
    - ページを移動/リロードしても表示を維持（ローカル永続化）
  - 一覧取得など軽量な非生成系では状況に応じて画面内の `role="status"` を用いる場合があります。

---

## 5. テスト
`pytest` による統合/E2E/負荷・回帰テストを含みます。
```bash
pytest
# もしくは従来同様の明示オプション
pytest -q --cov=src/backend --cov-report=term-missing --cov-fail-under=60
```
- カバレッジ閾値は `pytest.ini` に設定（60%）。必要に応じて上書き可。
- テスト構成:
  - `tests/test_api.py` … API基本動作（LangGraph/Chroma はスタブ）
  - `tests/test_integration_rag.py` … LangGraph/Chroma 統合（最小シードで近傍と `citations`/`confidence` を検証）
  - `tests/test_e2e_backend_frontend.py` … フロント→バックE2E相当のAPIフロー（正常/異常系の健全性）
  - `tests/test_load_and_regression.py` … 軽負荷スモークとスキーマ回帰チェック
    - PR4 追加: RAG 有効/無効の双方で基本SLA（少数リクエストで5秒以内）を検証。`X-Request-ID` ヘッダの付与も確認。

注意:
- 統合テストはローカルの Chroma クライアント（`chromadb`）を利用し、フィクスチャでテスト専用ディレクトリに最小シードを投入します（環境変数 `CHROMA_PERSIST_DIR` を内部使用）。
- RAG は `settings.rag_enabled` に従います。既定 `True`。
- LLM プロバイダはアプリ内でシングルトンとしてキャッシュされ、タイムアウト/リトライの実行には共有スレッドプールを使用します。FastAPI のシャットダウンイベントで安全に解放されます。

---

## 6. 設定/環境変数
- `src/backend/config.py`
  - 共通:
    - `environment`
    - `llm_provider` … `openai` | `local`
    - `llm_model` … 既定 `gpt-5-mini`（OpenAIを使う場合は実在モデルに置換推奨: 例 `gpt-4o-mini`）
    - `llm_timeout_ms` / `llm_max_retries`
    - `embedding_provider` … 既定 `openai`
    - `embedding_model` … 既定 `text-embedding-3-small`
  - RAG/Chroma:
    - `rag_enabled`, `rag_timeout_ms`, `rag_max_retries`, `rag_rate_limit_per_min`
    - `chroma_persist_dir`, `chroma_server_url`
  - APIキー:
    - `openai_api_key`
    - `voyage_api_key`（将来）
  - SRS（SQLite）
    - `srs_db_path`, `srs_max_today`
  - `.env` を読み込みます。サンプル: `env.example`
  - 運用/監視（PR4）
    - `rate_limit_per_min_ip`, `rate_limit_per_min_user` … API レート制限（IP/ユーザ毎・毎分）
    - `sentry_dsn` … Sentry DSN（設定すると例外を自動送信）

### 6-1. env.example（サンプル）
`env.example` を参考に `.env` を作成してください。特に以下の新設定があります。

- `LLM_PROVIDER`（既定: `openai`）
  - OpenAI LLMを使用する場合は `openai` を設定。
  - テスト/オフライン開発では `local` に設定することで、ローカルフォールバック動作を許容します。
- `OPENAI_API_KEY`
  - OpenAI API キーを設定してください。設定されていない場合は安全なフォールバックモードで動作します。
- `STRICT_MODE`（既定: `true`）
  - 本番/実運用では `true` を推奨。必須設定が不足している場合はフォールバックせずエラーにします（Fail-Fast）。
  - テスト/オフライン開発では `false` に設定することで、ローカル/ダミー挙動を許容します。
 - `LLM_MAX_TOKENS`（既定: `900`）
   - WordPack のJSONが途中で切れないよう、十分なトークン数を確保してください。

補足（互換キーの無視）:
- 旧サンプル/別アプリ由来のキー（例: `API_KEY`/`ALLOWED_ORIGINS` など）が `.env` に残っていても、`src/backend/config.py` は未使用の環境変数を無視する設定になっています（`extra="ignore"`）。
- そのため Docker 環境でも、未使用キーが存在して起動が失敗することはありません。

### 6-2. Langfuse の有効化（任意）

Langfuse を有効化すると、HTTP リクエスト・LLM 呼び出し・RAG 近傍検索のトレース/スパンが送信されます。

1) `.env` に以下を設定（`env.example` 参照）:
```
LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=...   # Langfuse Project の Public Key
LANGFUSE_SECRET_KEY=...
LANGFUSE_HOST=https://cloud.langfuse.com  # 自ホストの場合はそのURL
LANGFUSE_RELEASE=wordpack-api@0.3.0
```
2) 依存が未導入ならインストール:
```
pip install -r requirements.txt
```
3) 起動後、Langfuse のダッシュボードでトレースを確認できます。

注意:
- Langfuse v3（OpenTelemetryベース）に対応しました。`requirements.txt` は v3 系を利用します。旧 v2 を使う場合は依存を固定し、`observability.py` の v3 分岐を無効化してください。

Strict モード（`STRICT_MODE=true`）で `LANGFUSE_ENABLED=true` のとき、上記キーと `langfuse` パッケージは必須です（不足時は起動エラー）。

#### Input / Output の表示について
- 本リポジトリでは、Langfuse v3 のスパン属性として `input` と `output` を付与します（HTTP 親スパンはリクエストの要点とレスポンスの要点、LLM/RAG スパンはプロンプト長や結果テキストなど）。
- v2 クライアント互換時は `trace/span.update(input=..., output=...)` を使用します。
- ダッシュボードに Input/Output が表示されない場合は、`LANGFUSE_ENABLED=true` とキー設定、ならびに `src/backend/observability.py` が v3 分岐で `set_attribute('input'|'output', ...)` を実行していることを確認してください。

フルプロンプトの記録（任意・デフォルト無効）:
- 既定では LLM スパンの `input` はサマリ（`prompt_chars` と `prompt_preview`）のみを送信します。
- デバッグ目的でプロンプト全文を Langfuse に送るには `.env` に以下を設定:
  ```env
  LANGFUSE_LOG_FULL_PROMPT=true
  LANGFUSE_PROMPT_MAX_CHARS=40000
  ```
- 有効化時、スパン `input` に `prompt`（最大 `LANGFUSE_PROMPT_MAX_CHARS`）と `prompt_sha256` が含まれます。秘匿性の観点から本番では原則オフにしてください。

##### ノイズ抑制（/healthz など）
- 監視用の軽量エンドポイントはノイズになりやすいため、既定で `settings.langfuse_exclude_paths = ["/healthz", "/health", "/metrics*"]` を除外しています。
- 完全一致または接頭一致（末尾`*`）に一致したパスはトレースを生成しません。`.env` から上書きしたい場合は、コード側の既定を編集するか、将来的な環境変数対応をご利用ください。