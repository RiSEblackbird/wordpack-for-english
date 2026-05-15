# Dictionary Exploration UI Redesign Plan

## Goal

wordpack-for-english の UI/UX を、学校的な学習管理アプリではなく、自由探索型の個人用英語辞書として刷新する。
Lexicon / WordPack Detail / Reader / Examples / Explore / Shelves / Settings を整備し、既存機能、特に例文中 lemma hover/click 即生成、TTS、文章インポート、ゲストモードを維持する。

## Done When

- `/`, `/lexicon`, `/wordpacks/:id`, `/reader`, `/examples`, `/explore`, `/shelves`, `/settings` が表示できる。
- 既存の WordPack 生成、空 WordPack 作成、一覧、詳細、再生成、削除、`guest_public` 切替が維持される。
- 文章インポート、記事詳細、関連 WordPack、生成＆インポート、4,000 文字上限通知が維持される。
- 例文一覧、検索、カテゴリ絞り込み、訳表示、TTS、詳細モーダル、文字起こしタイピング、単体/複数削除が維持される。
- 例文中 lemma hover/click 即生成導線が壊れていない。
- ゲストモードで AI 生成、再生成、削除、POST/DELETE、音声再生、入力操作が読み取り専用として扱われる。
- light/dark と 480px 以下の主要画面が破綻しない。
- 関連テスト、frontend build、可能な範囲の E2E/axe 確認結果を記録する。

## Priority Slices

- [ ] Plan: 目標、完了条件、再開手順、スモークテストを整える。
- [ ] Design System: shared styles と基本 UI コンポーネントを追加する。
- [ ] AppShell / Routing: 辞書型 shell、ナビ、URL route 互換、モバイル下部ナビを追加する。
- [ ] Lexicon: 検索中心の辞書入口と既存 WordPack 一覧/生成導線を再構成する。
- [ ] WordPack Detail: 辞書記事として表示し、既存詳細情報と lemma explorer を維持する。
- [ ] Reader: 文章インポートと記事/語彙接続を読解机として再構成する。
- [ ] Examples: 例文一覧を用例コーパスとして見せ、KWIC 風の表示を追加する。
- [ ] Explore: 共起・対比・未生成語を辿る探索入口を追加する。
- [ ] Shelves: 自由分類の棚・タグ UI を追加し、後続 API 拡張なしで初期体験を提供する。
- [ ] Guest / Admin / Notifications: ゲスト読み取り専用、生成状態、管理操作を新 UI に統合する。
- [ ] Tests / Docs / PR: テスト、README/docs 更新要否、PR 本文を整える。

## Resume Command

```bash
cd /Users/Taishi/Documents/GitHub/wordpack-for-english
git status --short --branch
sed -n '1,220p' plans/dictionary-exploration-ui.md
cat plans/dictionary-exploration-ui.status.json
```

## Smoke Tests

```bash
cd apps/frontend && npm test
cd apps/frontend && npm run build
npm run e2e
PYTHONPATH=apps/backend pytest
```

## Session Notes

- 2026-05-16: Redesign package を確認。既存アプリはタブ式 SPA で、既存パネルと API を維持しながら辞書型 shell と route 互換を導入する方針。
