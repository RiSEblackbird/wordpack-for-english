# WordPack for English

英単語トレーナー。バックエンド（FastAPI）とフロントエンド（React + Vite）のモノレポです。

| WordPack | 文章インポート | 例文一覧 |
|---|---|---|
| <img width="600" alt="image" src="https://github.com/user-attachments/assets/11c5cb6c-dcb8-4ad2-9bfb-0c47bef9b0a4" /> | <img width="600" alt="image" src="https://github.com/user-attachments/assets/8fbf2d62-69e7-48f9-b7ba-7eb34e6fcd40" /> | <img width="600" alt="image" src="https://github.com/user-attachments/assets/6d01da80-3844-4641-a93c-efb7414f65d2" /> |
| <img width="600" alt="image" src="https://github.com/user-attachments/assets/7932f36a-68cb-4acd-8ce7-113a8139a8d9" /> | <img width="600" alt="image" src="https://github.com/user-attachments/assets/860e20ce-2651-4c39-891c-894b56ff7a4d" /> | <img width="600" alt="image" src="https://github.com/user-attachments/assets/4dae1671-38c7-4482-a632-4dffed49dacd" /> |
| <img width="600" alt="image" src="https://github.com/user-attachments/assets/8427f4fa-a718-4cf4-b761-e3fb90acd252" /> |  |  |

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
- 画面左上のハンバーガーボタンで共通サイドバーを開閉し、左側からスライド表示されるメニュー経由で主要タブ（WordPack / 文章インポート / 例文一覧 / 設定）へ移動可能。メニュー項目を選択してもサイドバーは開いたままで、開いている間はサイドバーが左端に固定されます。十分な横幅がある場合はメイン画面の配置を保ったまま余白内でサイドバーが表示され、スペースが足りない場合のみメイン画面が残り幅に収まるよう自動でスライドします
- WordPack プレビューの例文中ハイライト（lemma）にマウスオーバー0.5秒で `sense_title` ツールチップ表示。対応する lemma が見つからない場合は、最小サイズのポップオーバーに「〇〇 の WordPack を生成」ボタンだけが表示されます。ボタンを押すか、該当の単語（lemma-token）をクリックすると即座に生成が始まり、完了後に「WordPack概要」ウインドウが自動で開きます

### ユーザーロールと Google ログイン
- ログインは Google アカウントで行い、リバースプロキシや IAP が挿入するメールアドレスヘッダを利用してロールを判定します。
- `.env` の `USER_ROLE` はロール判定の既定値（`admin`/`viewer`）です。`VIEWER_EMAIL_ALLOWLIST` / `VIEWER_EMAIL_DOMAIN_ALLOWLIST` に閲覧専用ユーザーを、`ADMIN_EMAIL_ALLOWLIST` / `ADMIN_EMAIL_DOMAIN_ALLOWLIST` に管理ユーザーを列挙すると、Google ログイン時にメールアドレス単位でロールが上書きされます。
- 閲覧専用ロールでは WordPack 生成・例文生成・記事インポート・音声合成など API キーを要する操作が自動的に 403 で拒否され、フロントエンドでも該当ボタンがグレーアウトされます。

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

主要な環境変数（抜粋）:

| 変数名 | 説明 |
| --- | --- |
| `STRICT_MODE` | `true` の場合、必須設定の欠落を起動時に検出してエラーにします。 |
| `SESSION_SECRET` | `STRICT_MODE=true` で必須。セッションクッキー署名用の32バイト以上のランダム秘密鍵。 |
| `GOOGLE_OAUTH_CLIENT_ID` | `STRICT_MODE=true` で必須。Google OAuth サインイン用クライアントID。Google Cloud Console で取得します。 |
| `USER_ROLE` | ヘッダで判定できない場合に適用する既定ロール (`admin` / `viewer`)。 |

詳細は `docs/環境変数の意味.md` を参照してください。

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
- GitHub Actions の CI では Chrome DevTools MCP を利用した UI スモークテスト（`UI smoke test (Chrome DevTools MCP)` ジョブ）が自動実行されます。ローカルで同じシナリオを再現する方法は `docs/testing/chrome-devtools-mcp-ui-testing.md` を参照してください（Node.js 22 + `tests/ui/mcp-smoke/run-smoke.mjs` を用いた再現手順を含みます）。
