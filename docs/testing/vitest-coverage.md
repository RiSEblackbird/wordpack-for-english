# Vitest のカバレッジ測定と閾値

フロントエンドのユニットテストは Vitest で実行し、カバレッジ計測を行います。CI とローカルで同じ閾値を用いるため、`apps/frontend/vite.config.ts` の `test.coverage` に最小値を集約しています。

## 閾値の方針

- lines / statements: 80%
- branches: 70%
- functions: 80%

> 変更時に閾値を調整する場合は、CI ジョブと一致させるため必ず `vite.config.ts` の値を更新してください。

## 実行手順

```bash
cd apps/frontend
npm run test -- --coverage
```

- `coverage/` 配下に HTML レポートが生成され、ターミナルにはテキスト要約と `json-summary` が出力されます。
- CI では `vitest --coverage` を実行し、同じ閾値でゲートします。

### 正例

```bash
# カバレッジを出力し、閾値を満たすことを確認する
npm run test -- --coverage
```

### 負例

```bash
# カバレッジを計測しないため、閾値チェックが行われない
npm run test
```
