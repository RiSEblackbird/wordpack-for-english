# Vitest のカバレッジ測定と閾値

フロントエンドのユニットテストは Vitest で実行し、カバレッジ計測を行います。CI とローカルで同じ閾値を用いるため、`apps/frontend/vite.config.ts` の `test.coverage` に最小値を集約しています。

## 閾値の方針

- **lines / statements**: 80%
- **branches**: 70%
- **functions**: 66%（段階的引き上げ計画あり）

> 変更時に閾値を調整する場合は、CI ジョブと一致させるため必ず `vite.config.ts` の値を更新してください。

### Functions カバレッジの段階的改善計画

現状の functions カバレッジは 66.37% です。無理な閾値設定や形式的テストの追加を避け、重要機能から優先的にテストを拡充していくため、以下の段階的な引き上げを計画します：

1. **Phase 1（現在）**: 66%  
   - 現状をベースラインとして CI を安定化
2. **Phase 2**: 70%  
   - 低カバレッジの重要コンポーネント（ArticleListPanel, ExampleListPanel, src/lib/set.ts）にテスト追加
3. **Phase 3**: 75%  
   - 中カバレッジのコンポーネント（TTSButton, WordPackPanel, wordpack/* セクション）を拡充
4. **Phase 4（目標）**: 80%  
   - 全体的な関数テストの網羅性を最終目標値まで引き上げ

### 優先的にテストすべき箇所

現時点で functions カバレッジが低く、かつ主要なユーザーフローに関わる箇所：

- `src/components/ArticleListPanel.tsx` (28.57%)  
  - 記事一覧表示・検索・フィルタリング機能
- `src/components/ExampleListPanel.tsx` (46.15%)  
  - 例文表示・フィルタリング・ソート機能
- `src/lib/set.ts` (33.33%)  
  - Set 操作のユーティリティ関数群
- `src/components/TTSButton.tsx` (60%)  
  - 音声再生制御（エラーハンドリング含む）
- `src/components/SettingsPanel.tsx` (42.85%)  
  - 設定パネルの各種トグル・状態管理
- `src/components/wordpack/OverviewSection.tsx` (25%)  
  - 単語パック概要セクションの表示制御

### 閾値引き上げの判断基準

次の Phase に進む際は以下を満たすことを推奨：
1. 現行閾値を継続して 1ヶ月以上クリア
2. 上記「優先的にテストすべき箇所」の該当ファイルにテストを追加済み
3. CI で安定してグリーンを維持（Flaky テストが無い状態）

## 実行手順

\`\`\`bash
cd apps/frontend
npm run test -- --coverage
\`\`\`

- \`coverage/\` 配下に HTML レポートが生成され、ターミナルにはテキスト要約と \`json-summary\` が出力されます。
- CI では \`vitest --coverage\` を実行し、同じ閾値でゲートします。

### 正例

\`\`\`bash
# カバレッジを出力し、閾値を満たすことを確認する
npm run test -- --coverage
\`\`\`

### 負例

\`\`\`bash
# カバレッジを計測しないため、閾値チェックが行われない
npm run test
\`\`\`
