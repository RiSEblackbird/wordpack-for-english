# ビジュアル回帰テスト（Playwright）

## 目的
- UI の見た目の崩れを検知し、機能テストでは拾えない視覚的な回帰を防ぎます。
- E2E（機能）と分離し、見た目の差分にのみ集中したスナップショットを維持します。

## toHaveScreenshot() の実行方法
Playwright の E2E 設定を使ってビジュアル回帰シナリオだけを実行します。

### 正例（ビジュアル回帰のみを実行）
```
E2E_BASE_URL=http://127.0.0.1:5173 \
  npx playwright test -c tests/e2e/playwright.config.ts tests/e2e/visual.spec.ts
```

### 負例（E2E 設定を通さずに実行）
```
npx playwright test tests/e2e/visual.spec.ts
# → webServer 設定や成果物パスが反映されず、差分比較が不安定になる
```

`toHaveScreenshot()` は `tests/e2e/visual.spec.ts` 内で使用します。`maxDiffPixelRatio` と `threshold` の基準を揃え、スナップショットの意図を固定します。

```ts
await expect(page).toHaveScreenshot('wordpack-list.png', {
  maxDiffPixelRatio: 0.01,
  threshold: 0.2,
  mask: [page.locator('[aria-live="polite"]')],
});
```

## スナップショット更新手順（--update-snapshots）
意図した UI 変更のみ、明示的にスナップショットを更新します。

### 正例（変更が意図どおりのときのみ更新）
```
E2E_BASE_URL=http://127.0.0.1:5173 \
  npx playwright test -c tests/e2e/playwright.config.ts tests/e2e/visual.spec.ts \
  --update-snapshots
```

### 負例（原因確認なしで更新）
```
# 差分理由を確認せずに更新するのは不可
npx playwright test -c tests/e2e/playwright.config.ts tests/e2e/visual.spec.ts --update-snapshots
```

## 差分許容率の方針、マスク対象
- **差分許容率**: 既存の `visual.spec.ts` に合わせ、`maxDiffPixelRatio: 0.01` と `threshold: 0.2` を原則とします。
  - これを変更する場合は、差分の理由と影響範囲をテスト内コメントで明記してください。
- **マスク対象**: 動的に変化する領域はマスクで除外します。
  - `aria-live="polite"` のようにローディング/通知などに使う領域
  - 時刻/ランダム値などが表示される箇所
  - アニメーションやトランジションによる変化（可能な限り無効化した上で、残る部分をマスク）

> 重要: データ揺れが原因の差分は、**モック/固定データ化**または**マスク**で吸収し、見た目以外の変動をスナップショットに持ち込まないことを優先します。
