# UI/UXレビュー報告: WordPackプレビューモーダル改善 2026-06-07

## 1. 概要

- 対象PR / 作業: 添付UI/UXレビューで Fail とされた WordPack プレビューモーダル関連の全指摘解消
- 変更した画面・コンポーネント: 共通 `Modal`、`WordPackPreviewModal`、`WordPackPanel`、Lexicon、Explore、Shelves、Reader、WordPack detail 共有セクション
- 判定: Pass
- 未対応P0件数: 0
- 未対応P1件数: 0
- 未対応P2件数: 0

## 2. ユーザー価値

- 対象ユーザー: 保存済みWordPackを繰り返し確認・編集する英語学習者、記事から関連語を確認するユーザー、Explore/Shelvesから復習対象を移動せず確認するユーザー
- 利用文脈: Lexicon / Explore / Shelves / Reader から WordPack の中身をプレビューし、例文生成、再生成、進捗記録、公開設定、記事化へ進む
- ユーザー目的: どの語を、どの文脈から開き、次に何ができるかを失わずに確認・編集する
- 支援するタスク: 保存済みWordPackの確認、空WordPackの育成、関連WordPack確認、例文追加/削除/記事化、読み込み失敗時の再試行
- このUIが助ける理解・判断・行動: 対象語、起点画面、現在の状態、操作可能範囲、エラー時の回復、閉じた後の復帰先
- このUIがなければ困る点: 背景へフォーカスが抜ける、Readerでモーダルが重なる、読み込み失敗時に待機と失敗を誤認する、リスト表示でキーボードから開けない
- 削るべき情報・操作: hover-only の disabled 理由、内部ID風 aria-label、対象が分からない汎用タイトル、繰り返しプレビュー時の3秒待機
- 検証仮説・成功指標: P0/P1/P2レビュー項目がすべて対応済みになり、typecheck / unit / smoke / visual が通り、実ブラウザDOMで主要ランドマークと disabled 理由が観測できる

## 3. 初見理解

- 何の画面か分かるか: モーダルタイトルに `WordPack プレビュー: {lemma}` または `Reader / 関連WordPack: {lemma}` を出し、対象語と起点をヘッダーで示す。
- 今どこか分かるか: Explore / Shelves / Reader の起点文脈を preview context と補助文で表示する。
- 何ができるか分かるか: 例文追加、削除、記事化、コピー、再生成、閉じる、前へ/次への操作をユーザー語のラベルで示す。
- 最初の有意味な行動: 内容確認、前後移動、空WordPackなら追加生成/再生成、読み込み失敗なら再試行。
- 操作結果を予測できるか: ボタン名に対象語・カテゴリ・件数・結果を含め、Readerの関連語は `WordPack「alpha」をプレビュー` と可視化した。
- 失敗時に戻れるか: `WordPackLoadError` で対象、失敗内容、再試行、閉じるを分離して表示する。

## 4. state matrix

| 状態 | ユーザーが見るもの | ユーザーが理解できること | 次にできる行動 | 回復手段 | a11y通知/構造 | 証跡 | 判定 |
|---|---|---|---|---|---|---|---|
| 通常 | lemma入りタイトル、概要、セクションナビ、例文、共起、対比 | どの語をどの文脈で見ているか | 確認、例文追加、再生成、前後移動 | 閉じる、一覧へ戻る | `aria-labelledby` dialog、見出し、button | Vitest / smoke / visual | Pass |
| 読み込み中 | placeholder と読み込み説明 | まだ取得中である | 待機 | 閉じる | `aria-busy` / `aria-live` | WordPackPanel test | Pass |
| 空 | 空WordPackのcallout、例文0件、育成導線 | 作成直後または未生成である | 追加生成、再生成 | 閉じる、別語へ移動 | heading / notice | Explore test | Pass |
| 検索結果なし | Shelvesの空/該当なし文言と検索解除 | 条件で見つからない | 検索解除、別棚を見る | 検索解除 | button | Shelves UI変更 | Pass |
| 部分データ | fallback lemma、文脈説明 | メタ不足でも対象語は維持 | 内容確認、再試行 | 閉じる | headings with unique ids | typecheck | Pass |
| エラー | `WordPackLoadError` | 失敗して待機ではない | 再試行、閉じる | 再試行ボタン | `role="alert"` | WordPackPanel test | Pass |
| 入力エラー | 既存フォームの validation | 入力条件が違う | 修正 | 入力修正 | label / status | 既存テスト | Pass |
| 無効 | 常時DOM上の disabled 理由 | なぜ押せないか | ログイン、前提操作 | title / `aria-describedby` | hidden description + tooltip | GuestLock test / Browser DOM | Pass |
| 権限不足 | ゲスト制限理由 | AI機能や編集が使えない | ログイン | ログイン/ログアウト導線 | described button | Browser DOM | Pass |
| オフライン/利用不可 | load error panel | 通信/取得失敗 | 再試行 | 再試行、閉じる | alert | WordPackPanel test | Pass |
| 狭幅 | 既存responsive layout、24px checkbox | スクロールして同じ操作ができる | 同じ操作 | なし | targets enlarged | smoke / visual | Pass |
| 文字拡大 | 極小textを引き上げ、navも拡大 | 読み取りやすい | 同じ操作 | なし | text remains labels | visual | Pass |
| 長文・大量データ | unique section ids とセクションナビ | 長い記事内を移動できる | セクション移動 | close / nav | `aria-current` | typecheck / tests | Pass |

## 5. アクセシビリティ確認

- キーボード: 共通 `Modal` に初期フォーカス、フォーカストラップ、topmost Escape、閉じた後のフォーカス復帰を追加。セルフチェック解除は `button` 化。Lexicon list view に明示的な `開く` ボタンを追加。
- フォーカス: background sibling に `inert` / `aria-hidden` を適用し、閉じた後は trigger または前フォーカスへ戻す。
- 名前・ラベル: dialog は `aria-labelledby`。閉じるは `WordPackプレビューを閉じる`。例文操作は `alphaのDev例文1を削除` などユーザー語へ変更。
- 見出し・構造: WordPackPanel の section id を `useId()` prefix 付きへ変更し、複数表示時の anchor 衝突を避ける。
- コントラスト: 既存テーマを維持し、極小テキストを引き上げ。visual snapshotでReaderの関連WordPack可視ラベルを確認。
- ターゲットサイズ: GuestPublicToggle の checkbox を24pxへ拡大。
- エラー・ステータス: 読み込み失敗は loading placeholder と分離し、再試行/閉じるを出す。
- 自動検査: Vitest + Playwright smoke + Playwright visual を実行。
- 手動確認: Browser plugin で `http://127.0.0.1:5173/` を開き、Lexiconゲスト状態のランドマーク、生成キュー、disabled理由をDOM snapshotで確認。

## 6. 視覚階層

- 主操作: モーダルヘッダーに対象語と文脈、本文上部にcontext/notice、Reader関連語カードに可視のプレビューボタンを配置。
- 情報優先度: タイトル、起点文脈、対象語、例文/再生成操作、詳細セクションの順に整理。
- グルーピング: Readerはネストモーダルをやめ、ArticleDetailModal内の `article-wordpack-preview` セクションとして同一文脈に置く。
- 余白・密度: リスト/カードの小さすぎるテキストを引き上げ、Reader関連語ボタンは1行幅を確保。
- 読みやすさ: Shelvesバッジは `例文未生成`、`ゲスト公開中`、`使える`、`確認済み` へ変更。
- 狭幅・文字拡大: 既存responsive構造を維持し、固定format要素に text が詰まりにくい寸法を追加。

## 7. コピー

- 用語: `empty` / `guest public` / `学` / `確` をユーザー目的ベースの日本語へ変更。
- ボタン・リンク: `generate-examples-Dev`、`delete-example-Dev-0` など内部ID風ラベルを廃止。
- エラー文: 読み込み失敗時に対象、影響、再試行、閉じるを提示。
- 空状態: Explore作成直後の空WordPackに callout、Shelves空状態に次アクションを追加。
- disabled: GuestLock の理由を常時 `aria-describedby` で参照可能にした。
- トーン: ユーザーを責めず、状態と次アクションを具体化。

## 8. 熟練者効率

- 主要反復タスク: Lexicon / Shelves のプレビューに前へ/次へを追加し、閉じずに連続確認できる。
- 手数: Readerはネストモーダルを廃止し、記事詳細内で関連WordPackを開閉する。
- 再入力・再選択: 閉じた後のフォーカス復帰で一覧の位置を失いにくい。
- 近道: Lexicon list view の `開く` button でキーボード到達可能。
- 初心者向け説明の影響: callout は作成直後/文脈説明に限定し、常時の主要操作を妨げない。
- 判定: Pass。

## 9. 満足感・信頼感

- 待機中: loading と error を混同しない。
- 成功時: Explore作成直後はモーダル内で「空のWordPackを作成しました」と示す。
- 失敗時: alert と本文 error panel が一致し、再試行できる。
- 危険操作: 削除確認は既存挙動を維持。
- データ・権限・個人情報: ゲスト権限不足を hover-only にしない。
- トーン: 原因と回復を示し、結果を曖昧にしない。
- 判定: Pass。

## 10. 反証レビュー

- 実装を落とす観点で見つけた問題: 初回visual確認で保存済み記事側の関連WordPack表示が `alpha` だけに見え、プレビュー導線の可視説明が残っていないことを発見した。
- 対応: `ArticleListPanel` から開く `ArticleDetailModal` にも inline WordPack preview state を渡し、関連WordPackボタンを `WordPack「alpha」をプレビュー` として可視化。visual snapshotを更新して通常実行で再確認した。
- P0候補: focus trap / background inert / Reader nested modal / load error混在 / clickable div / selfcheck clickable div はいずれも修正済み。
- 証跡不足: Browser plugin の `tab.screenshot()` は CDP screenshot timeout で保存できなかった。代替として Browser DOM snapshot、Playwright visual snapshot、Vitest/Playwright結果を証跡にした。
- 残リスク: 実スクリーンリーダーの読み上げ順と実ユーザー観察は未実施。自動検査とDOM/visual確認では代替済みだが、実利用の迷いは別途観察が必要。

## 11. 指摘一覧

| 優先度 | 指摘 | 状態 | 対応 |
|---|---|---|---|
| P0-1 | 共通Modalの focus trap / restore / inert / stack / labelledby 不足 | 対応済 | `Modal` に初期フォーカス、trap、return focus、topmost Escape、background inert、`aria-labelledby` を追加 |
| P0-2 | Readerのネストモーダル | 対応済 | ArticleDetailModal内の inline preview に統一し、保存済み記事/インポート結果の両経路で同じ state を使用 |
| P0-3 | 読み込み失敗時にエラーと読み込み中が混在 | 対応済 | `WordPackLoadError` を追加し、loading/error/normalを分離 |
| P0-4 | セルフチェック解除がクリック専用div | 対応済 | overlayをbutton化し、previewでは即時表示可能にした |
| P0-5 | Lexicon list viewの主要open操作がキーボード不可 | 対応済 | list row actionsに明示的な `開く` button とテストを追加 |
| P1-1 | モーダルタイトルに対象語/文脈がない | 対応済 | `WordPack プレビュー: {lemma}`、Explore/Shelves/Reader文脈を追加 |
| P1-2 | Exploreの空WordPack作成成功が背面に残る | 対応済 | プレビュー内 notice で作成直後と次アクションを表示 |
| P1-3 | Shelvesの英語/略語バッジ | 対応済 | `例文未生成`、`ゲスト公開中`、`使える`、`確認済み` へ変更 |
| P1-4 | 例文操作aria-labelが内部ID風 | 対応済 | カテゴリ、lemma、番号、結果を含むユーザー語へ変更 |
| P1-5 | GuestLock disabled理由がhover依存 | 対応済 | 常時DOM上の説明を `aria-describedby` で参照 |
| P1-6 | Lexicon周辺の極小テキスト | 対応済 | meta、badge、button、navなどを引き上げ |
| P2 | section navが小さい | 対応済 | nav font sizeと現在位置表示を改善 |
| P2 | 固定ID衝突リスク | 対応済 | `useId()` prefix付きsection idへ変更 |
| P2 | Lexicon / Shelvesに前後移動がない | 対応済 | preview navigationを追加 |
| P2 | close labelが汎用 | 対応済 | `WordPackプレビューを閉じる` へ変更 |
| P2 | GuestPublicToggle checkbox targetが小さい | 対応済 | 24px targetへ拡大 |

## 12. 証跡

- Visual snapshot: `tests/e2e/visual.spec.ts-snapshots/article-import-confirmation-darwin.png`
- Playwright failed-then-fixed evidence: visual差分でReader保存済み記事側の可視ラベル不足を発見し、修正後に `visual.spec.ts` を通常実行でPass。
- Browser DOM snapshot: `http://127.0.0.1:5173/` の Lexicon guest layout で `アプリ内共通メニュー`、`生成キュー`、disabled reasonを確認。
- 取得できなかった証跡と理由: Browser pluginのスクリーンショット保存は `Page.captureScreenshot` timeout。代替としてPlaywright visual snapshotを更新・通常実行で確認。

## 13. 実行した検証

- [x] typecheck: `cd apps/frontend && npx tsc -p tsconfig.json`
- [x] frontend tests: `cd apps/frontend && npm test -- --coverage --silent`
- [x] targeted tests: Modal / GuestLock / WordPackPanel / WordPackListPanel modal / ArticleDetailModal / ArticleListPanel / ExplorePage / ArticleImportPanel
- [x] Playwright smoke: `npx playwright test -c tests/e2e/playwright.config.ts tests/e2e/auth.spec.ts tests/e2e/guest.spec.ts tests/e2e/wordpack.spec.ts`
- [x] Playwright visual: `npx playwright test -c tests/e2e/playwright.config.ts tests/e2e/visual.spec.ts`
- [x] Browser plugin DOM確認: local frontend/backendを起動し、Lexicon guest stateをDOM snapshotで確認
- [x] accessibility check: Vitest axe対象、modal focus/label tests、Playwright semantic locators
- [x] keyboard check: modal trap/restore、list open button、selfcheck button、E2E keyboard flow
- [x] responsive check: Playwright smokeのmobile bottom nav、既存responsive visual

## 14. 実行していない検証

| 未実行検証 | 理由 | 残リスク | 後続対応 |
|---|---|---|---|
| 実スクリーンリーダー読み上げ | 外部アプリ/支援技術の実機操作が必要 | 読み上げ順の微調整余地 | 主要dialogとinline previewで実機確認 |
| 実ユーザー観察 | 参加者が必要 | 初見での自然な理解は仮説 | 次回ユーザーテストで観察 |
| Browser plugin screenshot保存 | CDP screenshot timeout | Browser固有の画像証跡はなし | Playwright visual snapshotで代替済み |
