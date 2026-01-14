# Lighthouse CI

## 目的
- WordPack の主要ページに対して Lighthouse を週次で計測し、性能/ベストプラクティス/SEO/PWA の品質を継続監視します。

## 計測対象ページ
- `WORDPACK_LIST_URL`（保存済み WordPack 一覧の URL を指定）

## しきい値（カテゴリ別）
| カテゴリ | しきい値 (minScore) |
| --- | --- |
| Performance | 0.80 |
| Best Practices | 0.90 |
| SEO | 0.90 |
| PWA | 0.60 |

## 実行方法

### CI（GitHub Actions）
- ワークフロー: `.github/workflows/lighthouse-ci.yml`
- 必要なシークレット:
  - `WORDPACK_LIST_URL`: 計測対象 URL
  - `LHCI_GITHUB_APP_TOKEN`: Lighthouse CI GitHub App のトークン（レポート投稿用）
- 実行コマンド:
  ```bash
  lhci autorun
  ```

### ローカル
1. `WORDPACK_LIST_URL` を指定します。
2. GitHub へ投稿しない場合は `LHCI_UPLOAD__TARGET=filesystem` を指定します。

```bash
WORDPACK_LIST_URL=https://example.com/wordpacks \
LHCI_UPLOAD__TARGET=filesystem \
lhci autorun
```

レポートは `.lighthouseci/` と `lhci-results.json` に出力されます。

## 例
- 正例: `WORDPACK_LIST_URL` に HTTPS の本番 URL を設定して計測する。
- 負例: `WORDPACK_LIST_URL` 未設定のまま実行し、計測対象が空で失敗する。
