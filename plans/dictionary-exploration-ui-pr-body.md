## Summary

- UI/UXを自由探索型の個人用英語辞書へ刷新
- 学校的な学習管理UIは導入していない
- WordPackを辞書記事として再構成
- Reader / Examples / Explore / Shelvesを追加または刷新
- 例文中hover/click即生成機能を維持
- ゲストモード制約を維持

## Major changes

### Design System

- `src/shared/styles` に辞書UI向けのtokens/reset/layout/utilitiesを追加
- `src/shared/ui` にShell、Card、Button、Field、EmptyState、StatusPillなどの共通部品を追加
- 既存コンポーネントの中核ロジックを残し、外側の情報設計と画面構造を刷新

### AppShell / Routing

- `src/app/routes.ts` で主要画面のパスとラベルを集約
- `/lexicon`、`/wordpacks/:id`、`/reader`、`/examples`、`/explore`、`/shelves`、`/settings` を追加
- サイドバーとモバイル下部ナビで辞書探索の導線を整理

### Lexicon

- 既存のWordPack検索・生成・一覧をLexicon画面へ再配置
- 空WordPack作成、再生成、bulk delete、guest read-onlyの既存挙動を維持
- 既存テスト互換のアクセシブルラベルを維持

### WordPack Detail

- `/wordpacks/:id` で開ける辞書記事型の詳細画面を追加
- 既存の発音、意味、例文、関連情報、TTS、再生成導線を維持
- 学校的な「学習」表現を「辞書」「用例」「使える」系の表現へ置換

### Reader

- Article import / Article list をReader画面として再構成
- 読んだ文章から語を拾う探索導線に寄せつつ、既存の取り込み挙動を維持

### Examples

- 既存のExamples listをExamples Corpus画面として再構成
- 例文からlemmaをhover/clickしてWordPackを即生成する既存経路を保持

### Explore

- 関連語、品詞、接辞、語源を眺める探索画面の初期UIを追加
- 既存データから辞書探索を広げる入口として実装

### Shelves

- 辞書の棚としてWordPackを整理する画面を追加
- ローカルの棚ドラフトを作成・保存できる初期状態を実装

### Guest / Admin / Notifications

- 既存のゲスト読み取り専用制約、`guest_public`、通知、カスタムイベントの接続は維持
- 管理系・認証系の挙動は今回のUI刷新で変更していない

## Preserved behavior

- WordPack生成/再生成
- 空WordPack作成
- Article import
- Examples list
- TTS
- Guest read-only
- hover/click lemma generation
- bulk delete
- guest_public
- custom events

## Tests

- [x] `cd apps/frontend && npx tsc -p tsconfig.json`
- [x] `cd apps/frontend && npm test`
- [x] `cd apps/frontend && npm run build`
- [ ] `SESSION_SECRET_KEY=codex-test-secret-key-32-characters FIRESTORE_PROJECT_ID=wordpack-ci FIRESTORE_EMULATOR_HOST=127.0.0.1:8080 PYTHONPATH=apps/backend .data/codex-test-venv/bin/pytest -q`
- [ ] `PATH="$PWD/.data/codex-test-venv/bin:$PATH" npm run e2e`

## Not run

- Backend pytestは実行したが、今回のUI変更範囲外の既存失敗で完走しなかった。
  - `tests/test_api.py::test_word_lookup`
  - `tests/test_github_actions_branch_policy.py::test_deploy_dry_run_is_main_only`
  - `tests/test_github_actions_branch_policy.py::test_deploy_production_runs_only_on_main_push_and_deploys_tested_commit`
- E2Eは実行したが、Playwright Chromiumが `/Users/Taishi/Library/Caches/ms-playwright/chromium-1134` に未インストールのためブラウザ起動前に停止した。
- フルブラウザのaxe確認はE2E環境未整備のため未実施。既存コンポーネントテスト内のaxeチェックは通過している。

## Risk areas

- ExploreとShelvesは初期UIで、Shelvesはローカルの棚ドラフト保存まで。
- ルーティングは軽量な独自ルーターで、react-router等への移行は含めていない。
- WordPack一覧の既存モーダル/プレビュー挙動は維持し、詳細ページへの直接URLを追加した形。
- Backend pytestには今回のUI刷新と独立した既存失敗が残っている。
- E2E確認はPlaywright Chromiumのインストール後に再実行が必要。
