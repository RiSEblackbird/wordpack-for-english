# WordPack for English

英単語トレーナー。バックエンド（FastAPI）とフロントエンド（React + Vite）のモノレポです。

| | | |
|---|---|---|
| <img width="600" alt="image" src="https://github.com/user-attachments/assets/0e1cee28-af2a-4a0e-9eff-975cb693c50f" /> | <img width="600" alt="image" src="https://github.com/user-attachments/assets/c4b000bf-aa7c-4d94-bc6c-f639fdce515a" /> | <img width="600" alt="image" src="https://github.com/user-attachments/assets/bc3af0f4-e2e9-4d93-85ec-2ffb38a5643c" /> |

## 主な機能
- バックエンド: FastAPI / フロントエンド: React + TypeScript + Vite
- WordPack の生成・再生成・永続化
- 発音情報（IPA/音節/強勢）の付与
- 例文（Dev/CS/LLM/Business/Common）の追加・削除
- 文章インポートと関連 WordPack の紐付け
- OpenAI gpt-4o-mini-tts を用いた例文／日本語訳／インポート文章／WordPack語彙（一覧・プレビュー）の音声再生（「音声」ボタン）
- 保存済みWordPack一覧で語義タイトルを即座に確認できる「語義」ボタンと「語義一括表示」スイッチ、例文未生成のカードから直接生成できる「生成」ボタン
- WordPack・文章・例文の一覧で複数選択して一括削除できる管理機能
- 例文一覧で訳文を一括開閉できる「訳一括表示」スイッチ
- 画面左上のハンバーガーボタンで共通サイドバーを開閉し、左側からスライド表示されるメニュー経由で主要タブ（WordPack / 文章インポート / 例文一覧 / 設定）へ移動可能。メニュー項目を選択してもサイドバーは開いたままで、サイドバー幅が既存の左右余白を超えた分だけメイン画面の左端を動的に右へ寄せるためUIが重なることはありません

## クイックスタート

### 前提
- Python 3.13+
- Node.js 18+

### セットアップ
```bash
# Python（リポジトリルートで）
python -m venv .venv
. .venv/Scripts/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Frontend
cd apps/frontend
npm install
```

### 環境変数
```bash
cp env.example .env
# .env に OPENAI_API_KEY を設定
```

### 起動
```bash
# Backend（リポジトリルートで）
python -m uvicorn backend.main:app --reload --app-dir apps/backend

# Frontend
cd apps/frontend
npm run dev
```

### Docker（任意）
```bash
docker compose up --build
```
- Backend: http://127.0.0.1:8000
- Frontend: http://127.0.0.1:5173

## テスト
- Backend（Python）
```bash
pytest
```
- Frontend（Vitest）
```bash
cd apps/frontend
npm run test
```

## REST API（抜粋）
- `POST /api/word/pack` … WordPack を生成して語義タイトル・語義・例文・語源・学習カード要点を返却
- `POST /api/word/examples/bulk-delete` … 例文IDの配列を受け取り一括削除
- `POST /api/tts` … OpenAI gpt-4o-mini-tts で読み上げた音声（audio/mpeg）をストリーミング返却

## ディレクトリ
```
apps/backend/backend/   # FastAPI アプリ
apps/frontend/          # React + Vite
tests/                  # Python テスト
docs/                   # 詳細ドキュメント
```

## 追加ドキュメント
- 詳細な API・フロー・モデルは `docs/flows.md`, `docs/models.md`, `docs/環境変数の意味.md` を参照してください。
- ユーザー向け操作は `UserManual.md` を参照してください。
