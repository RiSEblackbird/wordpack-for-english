# WordPack for English

英単語トレーナー（OpenAI LLM×LangGraph）。技術・科学英文の読み・用法・発音の理解を支援します。リポジトリはバックエンド（FastAPI）とフロントエンド（React + Vite）のモノレポ構成です。

<img width="2015" height="1061" alt="image" src="https://github.com/user-attachments/assets/0e1cee28-af2a-4a0e-9eff-975cb693c50f" />

## 特徴
- バックエンド: FastAPI、構成・ルータ・簡易ログ、テストあり
- フロントエンド: React + TypeScript + Vite、単一ページ/2パネル構成（WordPack/設定）
- 発音強化（M5）: cmudict/g2p-en による IPA・音節・強勢推定（例外辞書・辞書キャッシュ・タイムアウト付きフォールバック）
- WordPack 再生成の粒度指定（M5）: 全体/例文のみ/コロケのみ の選択（Enum化済み）
- **WordPack永続化機能**: 生成されたWordPackを自動保存し、WordPackタブ下部の一覧で閲覧・削除が可能（再生成は `WordPack` セクションから実行）。一覧はカード表示に加えて索引風のリスト表示（2列・画面幅に応じて1/2列）に切替可能。ページサイズは既定200件。
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
  - フロントエンドでは、生成/再生成/削除の完了時に `wordpack:updated` を発火し、保存済み一覧が自動更新されます。進捗や成功/失敗は右下の通知カードに表示されます。

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

OpenAI LLM統合（Responses API）:
- 既定: `LLM_PROVIDER=openai`, `LLM_MODEL=gpt-4o-mini`。
- WordPack/文章インポートは OpenAI Responses API ベースで生成。
- `.env` の `LLM_MAX_TOKENS` を調整（推奨1500、JSON途中切れ防止）。
- UIのモデル選択（gpt-4.1-mini / gpt-5-mini / gpt-4o-mini）に応じて送信パラメータが変化:
  - gpt-5-mini（推論系）: `reasoning.effort`, `text.verbosity`（`temperature` は通常未使用）
  - gpt-4.1-mini / gpt-4o-mini（sampling系）: `temperature`（設定タブの値）
  - 未指定時はサーバ既定を使用
  - SDK未対応のパラメータは自動で外して再試行

LLM メタ情報の保存/返却:
- WordPack: 生成/再生成時に使用した `llm_model`/`llm_params` をレスポンスに含め、DBへ保存
- 文章（Article）: インポート時に使用した `llm_model`/`llm_params` を保存し、`GET /api/article/{id}` で返却

---

### 1-x. プロジェクト内の自動ルール（MDC）
本リポジトリは `.cursor/rules/*.mdc` に、生成/改修時の最小限かつ実務的なルールを常時適用（alwaysApply: true）で定義しています。

- `base-reasoning-and-communication.mdc` … 結論先出し/根拠/検算などの推論様式
- `base-coding-principles.mdc` … DRY/KISS/SoC/SRP/YAGNI/POLA/OCP と可観測性
- `base-quality-gates.mdc` … 決定性・分離・カバレッジ・意味的アサーション
- `frontend-testing.mdc` … 役割/ラベル/テキストに基づくUIテストとHTTPモック
- `backend-testing.mdc` … ドメイン厳密・契約テスト・軽量性能回帰
- `maintenance-and-change-management.mdc` … 差分駆動・契約先行・理由明記
- `docs-authoring.mdc` … README/UserManualの更新規約（現状のみを正確に記述）

既存の `minimum.mdc` 等は上記へ統合済みです。

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
  - クエリ: `?limit=<int>&offset=<int>`（例: `?limit=200&offset=0`）
  - レスポンス例:
    ```json
    {
      "items": [
        {
          "id": "wp:converge:a1b2c3d4",
          "lemma": "converge",
          "created_at": "2025-01-01T12:34:56.000Z",
          "updated_at": "2025-01-01T12:34:56.000Z",
          "is_empty": true,
          "examples_count": {"Dev":0, "CS":0, "LLM":0, "Business":0, "Common":0}
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
  - リクエスト例: `{ "pronunciation_enabled": true, "regenerate_scope": "all" }`（空オブジェクト `{}` も可。※ボディ必須）
  - レスポンス: 再生成されたWordPackオブジェクト
  - エラー（strictモード）:
    - LLM出力のJSON解析に失敗: `502`（`reason_code=LLM_JSON_PARSE`, `hint` と `diagnostics.lemma` を含む）

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

- `GET /api/word/examples`（新）
  - 例文をWordPack横断で一覧取得。
  - クエリ:
    - `limit=<int>`（1–200, 既定50）
    - `offset=<int>`（0–）
    - `order_by=created_at|pack_updated_at|lemma|category`（既定: `created_at`）
    - `order_dir=asc|desc`（既定: `desc`）
    - `search=<string>` + `search_mode=prefix|suffix|contains`（英文に対する検索）
    - `category=Dev|CS|LLM|Business|Common`（任意）
  - レスポンス例:
    ```json
    {
      "items": [
        {
          "id": 123,
          "word_pack_id": "wp:insight:a1b2c3",
          "lemma": "insight",
          "category": "Dev",
          "en": "We gained insight after refactoring modules and reviewing logs.",
          "ja": "モジュールのリファクタリングとログ確認の後に洞察を得た。",
          "grammar_ja": "第3文型",
          "created_at": "2025-01-01T12:34:56.000Z",
          "word_pack_updated_at": "2025-01-02T08:00:00.000Z"
        }
      ],
      "total": 1,
      "limit": 50,
      "offset": 0
    }
    ```

---

## 4. フロントエンド UI 概要
単一ページで以下のタブを切替。初期表示は「WordPack」タブ。

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
 
 - 例文一覧（`ExampleListPanel.tsx`）（新）
   - 保存済みの例文をWordPack横断で一覧表示（カード/リスト切替）。
   - 並び替え（例文作成日時/WordPack更新/単語名/カテゴリ）、検索（前方/後方/部分一致）、カテゴリ絞り込み。
   - カード/リストに「訳表示」ボタンを備え、原文下に日本語訳を展開。
   - クリックで詳細モーダル（原文/訳/解説）を表示。

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
  - `tests/test_integration_rag.py` … LangGraph統合（OpenAI LLMで `citations`/`confidence` を検証）
  - `tests/test_e2e_backend_frontend.py` … フロント→バックE2E相当のAPIフロー（正常/異常系の健全性）
  - `tests/test_load_and_regression.py` … 軽負荷スモークとスキーマ回帰チェック
    - PR4 追加: 基本SLA（少数リクエストで5秒以内）を検証。`X-Request-ID` ヘッダの付与も確認。

フロントエンド単体テスト（Vitest/jsdom）:
- `src/frontend/vitest.setup.ts` で `window.matchMedia` のポリフィルを提供しています。jsdom には `matchMedia` がないため、コンポーネントの幅検知（`(min-width: 900px)`）でエラーにならないようにしています。
- ポリフィルは `addEventListener`/`removeEventListener` とレガシー `addListener`/`removeListener` の双方に対応するダミー実装です（常に `matches=false`）。UIロジックは初期値に依存せず、レンダリング後の振る舞いをアサートしてください。

注意:
- 統合テストはローカルの Chroma クライアント（`chromadb`）を利用し、フィクスチャでテスト専用ディレクトリに最小シードを投入します（環境変数 `CHROMA_PERSIST_DIR` を内部使用）。
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
  - Chroma:
    - `chroma_persist_dir`, `chroma_server_url`
  - APIキー:
    - `openai_api_key`
    - `voyage_api_key`（将来）
  - ストレージ（SQLite）
    - `srs_db_path`, `srs_max_today`（SRSカード/WordPack/記事を同一DBに保存）
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

Langfuse を有効化すると、HTTP リクエストと LLM 呼び出しのトレース/スパンが送信されます。

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
- 本リポジトリでは、Langfuse v3 のスパン属性として `input` と `output` を付与します（HTTP 親スパンはリクエストの要点とレスポンスの要点、LLM スパンはプロンプト長や結果テキストなど）。
- v2 クライアント互換時は `trace/span.update(input=..., output=...)` を使用します。
- ダッシュボードに Input/Output が表示されない場合は、`LANGFUSE_ENABLED=true` とキー設定、ならびに `src/backend/observability.py` が v3 分岐で `set_attribute('input'|'output', ...)` を実行していることを確認してください。

#### 6-2-1. 文章インポート（ArticleImportFlow）のトレース
- `POST /api/article/import` は `ArticleImportFlow` によって LangGraph スタイルでオーケストレーションされ、各ステップに Langfuse スパンが付与されています。
  - `article.title.prompt` / `article.title.llm`: 短い英語タイトル生成
  - `article.translation.prompt` / `article.translation.llm`: 日本語訳生成（忠実訳）
  - `article.explanation.prompt` / `article.explanation.llm`: 日本語解説生成（1–3文）
  - `article.lemmas.prompt` / `article.lemmas.llm`: 教育的な lemmas/句の抽出（JSON配列）
  - `article.filter_lemmas`: lemmas の簡易フィルタ
  - `article.link_or_create_wordpacks`: 既存 WordPack 紐付け / 空パック新規作成
  - `article.save_article`: 記事保存とメタ取得
- ルータ層では親スパン `ArticleImportFlow` を開始し、その子として `article.flow.run` を貼ったうえでフロー本体を実行します。
- 図は `docs/flows.md` の「ArticleImportFlow（文章インポート）」を参照してください。

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

## 文章インポート機能

- フロントエンド: 新タブ「文章インポート」から、テキストエリアに文章を貼り付けて「インポート」を実行します。
- バックエンド: `/api/article/import` でインポート処理を行い、以下をDBに保存します。
  - 英語タイトル/英語本文/日本語訳/解説
  - 抽出語のWordPack関連（既存がなければ空のWordPackを自動作成）
- 一覧: `/api/article` で記事一覧、`/api/article/{id}` で詳細取得、`DELETE /api/article/{id}` で削除。
- 関連WordPackカードの「生成」ボタンで `/api/word/packs/{word_pack_id}/regenerate` を呼び出し、生成完了後はUIが自動更新されます。
 - フロントエンドの詳細表示は共通モーダル `ArticleDetailModal` を用いて実装しています。`ArticleImportPanel` と `ArticleListPanel` の双方で同一のUI/挙動を共有し、日本語訳の直下に解説 `notes_ja` が表示されます。関連WordPackは常にカード表示で統一し、インポート直後は再生成/プレビュー操作が可能、一覧からの表示は閲覧専用です。

### 文章インポートのエラーハンドリング（重要）
- 各役割（タイトル/訳/解説/lemmas）は独立プロンプトで生成します。lemmas は JSON 配列、他は素のテキストを期待します（コードフェンスは自動剥離）。
- lemmas のJSON解析に失敗した場合は lemmas を空扱いの上でフィルタを適用します（ダミーは生成しません）。
- 最終的に「日本語訳が空」かつ「lemmas が空」の場合は 502 を返し、記事は保存しません。
- これにより、無内容な記事や関連語を持たない記事が保存される回りくどい失敗パスを排除しています。
