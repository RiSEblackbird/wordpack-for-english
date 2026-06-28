# UI/UXレビュー報告: サイドメニュー幅修正とReaderサイドバー整理 2026-06-28

## 1. 概要

- 対象PR / 作業: Issue #494 Reader サイドメニューの不要操作を撤去し幅崩れを直す
- 変更した画面・コンポーネント: 共通サイドメニュー、Reader、ArticleImportPanel
- 判定: Pass
- P0件数: 0
- P1件数: 0
- P2件数: 0

## 2. ユーザー価値

- 対象ユーザー: Readerで文章を読み込み、関連WordPackへつなげるログイン済みユーザー
- 利用文脈: Reader本文で文章インポートを行いながら、サイドメニューでは画面移動と音声設定を使う場面
- ユーザー目的: Reader本文の作業領域で文章インポートやカテゴリ選択を完結し、サイドメニューは現在地と共通操作の確認に使いたい
- 支援するタスク: サイドメニューでの画面移動、Reader本文での文章インポート、例文生成・記事化
- このUIが助ける理解・判断・行動: サイドメニュー上部の折りたたみ操作が幅内に収まり、Readerでは本文側のインポート導線だけを見ればよい
- このUIがなければ困る点: サイドメニュー上部の操作が切れて見え、Readerで同じインポート操作が本文とサイドメニューに重複して判断負荷が増える
- 削るべき情報・操作: Readerサイドメニュー内の文章インポート、カテゴリ選択、例文生成・記事化、モデル選択
- 検証仮説・成功指標: desktopサイドバー幅280px内でブランド行、折りたたみボタン、音声selectが収まり、Readerではサイドバー側の文章インポート領域がDOMに存在しない

## 3. 初見理解

- 何の画面か分かるか: Reader見出しと本文のPaste / import textセクションで文章読み込み画面と分かる
- 今どこか分かるか: サイドメニューのReader項目が選択状態で表示される
- 何ができるか分かるか: 本文エリアで文章貼り付け、カテゴリ選択、インポート、例文生成・記事化ができる
- 最初の有意味な行動: 本文エリアのテキストエリアに文章を貼り付ける
- 操作結果を予測できるか: 既存のボタン文言「文章をインポート」「例文を生成して記事化」を維持
- 失敗時に戻れるか: 既存のalert/status表示と入力保持を維持し、今回の削除対象はサイドバー重複UIだけ

## 4. state matrix

| 状態 | ユーザーが見るもの | 次にできる行動 | アクセシビリティ/証跡 | 判定 |
|---|---|---|---|---|
| 通常 | サイドメニュー、音声コントロール、Reader本文インポートフォーム | 画面移動、本文で文章インポート | App.test / Playwright screenshot | Pass |
| 読み込み中 | 既存のReader本文側button disabled / status | 待機、完了後詳細を確認 | 既存ArticleImportPanelテスト | Pass |
| 空 | Reader記事一覧の空状態、本文インポート導線 | 文章をインポート | Playwright screenshot | Pass |
| 検索結果なし | 今回の変更対象外。検索UIは既存挙動を維持 | 条件変更 | 影響なし | Pass |
| 部分データ | 今回の変更対象外。ArticleListPanelの既存表示を維持 | 表示継続 | 影響なし | Pass |
| エラー | 既存のalert表示 | 入力を直す、再試行 | 既存ArticleImportPanelテスト | Pass |
| 入力エラー | 文字数超過警告 | 文字数を減らす | 既存ArticleImportPanelテスト | Pass |
| 無効 | 本文側のdisabled button | 入力または処理完了を待つ | 既存ArticleImportPanelテスト | Pass |
| 権限不足 | GuestLockの既存制御 | ログインまたはゲスト閲覧継続 | 影響なし | Pass |
| オフライン/利用不可 | 既存fetch error表示 | 再試行 | 影響なし | Pass |
| 狭幅 | mobileでは既存overlay、desktopサイドバーでは折りたたみボタンが幅内 | メニュー操作 | Playwright metrics | Pass |
| 文字拡大 | 折りたたみボタンは38px固定、titleはellipsis | 操作継続 | CSS review | Pass |
| 長文・大量データ | Reader本文フォームと一覧の既存レイアウト | 本文で作業 | 影響なし | Pass |

## 5. アクセシビリティ確認

- キーボード: サイドメニュー折りたたみボタンはbuttonのまま、Reader本文の入力・checkbox・buttonも既存どおり到達可能
- フォーカス: `.sidebar-collapse-toggle:focus-visible` を既存CSSで維持
- 名前・ラベル: 折りたたみボタンは可視テキストを削除したが `aria-label` と `title` で「サイドメニューを折りたたむ」を維持
- 見出し・構造: aside/nav/region構造を維持。Readerのサイドバー重複sectionだけを非表示ではなく未描画にした
- コントラスト: 色変更なし
- ターゲットサイズ: 折りたたみボタンは38px四方
- エラー・ステータス: ArticleImportPanel本文側の既存role status/alertを維持
- 自動検査: `npm test -- --coverage --silent`
- 手動確認: PlaywrightでdesktopサイドバーとReaderを確認

## 6. 視覚階層

- 主操作: Readerの文章インポート主操作を本文エリアに集約
- 情報優先度: サイドメニューは共通navと音声設定に絞り、Reader固有の重複操作を削除
- グルーピング: Readerのカテゴリ・モデル・AIパラメータは本文フォーム内にまとまる
- 余白・密度: サイドメニューのブランド行はWordPackタイトルと38pxボタンに収まる
- 読みやすさ: 折りたたみボタンの可視文字切れをなくし、title/ariaで意味を補完
- 狭幅・文字拡大: `.sidebar-title` はellipsis、折りたたみボタンは固定幅で横にはみ出さない。サイドバー実用幅を280pxへ広げ、右端に余白を残す

## 7. コピー

- 用語: 既存の「サイドメニュー」「Reader」「文章をインポート」を維持
- ボタン・リンク: 本文側の操作ラベルは変更なし
- エラー文: 変更なし
- 空状態: 変更なし
- disabled: 変更なし
- トーン: 重複操作を減らし、警告や不安を増やしていない

## 8. 熟練者効率

- 主要反復タスク: Reader本文で文章貼り付け、カテゴリ選択、インポートまたは例文生成・記事化
- 手数: 本文側の手数は変更なし
- 再入力・再選択: ArticleImportPanelの状態管理は維持
- 近道: 今回は追加なし。重複UI削除で迷いを減らす
- 初心者向け説明の影響: サイドバー重複フォームを消し、本文側の説明だけにした
- 判定: Pass

## 9. 満足感・信頼感

- 待機中: 既存のstatus/notificationを維持
- 成功時: 既存の詳細モーダル表示を維持
- 失敗時: 既存のalertを維持
- 危険操作: なし
- データ・権限・個人情報: データ送信フローは本文側に維持し、サイドバー重複送信導線のみ削除
- トーン: ユーザーを責める文言なし
- 判定: Pass

## 10. 反証レビュー

- 実装を落とす観点で見つけた問題: サイドバーから可視ラベルを削ることで意味が失われる可能性があるため、`aria-label` と `title` の維持、38px target sizeを確認した
- P0候補: Reader本文側まで削ると主要タスク不能になるが、本文textarea存在をApp.testとPlaywrightで確認した
- 証跡不足: 実ユーザーテストは未実施
- 残リスク: native titleはタッチ環境で常に見える説明ではないが、desktopサイドバー上部のchevron buttonとして既存の位置とaria nameを維持している

## 11. 指摘一覧

| 優先度 | 箇所 | 問題 | 影響 | 修正案 | 状態 |
|---|---|---|---|---|---|
| P0 | なし | なし | なし | なし | 対応済 |

## 12. 証跡

- スクリーンショット: local Playwrightで `/tmp/wordpack-sidebar-after.png` と `/tmp/wordpack-reader-after.png` を取得
- トレース: なし
- テスト結果: `npx tsc -p tsconfig.json`、`npm test -- --silent src/App.test.tsx`、`npm test -- --coverage --silent`、`git diff --check`
- 手動確認: Playwright metricsで sidebar width 280px、title scrollWidth 147 / clientWidth 147、collapse toggle right 255.02px、playback / volume select right 260.63px、brand scrollWidth 249 / clientWidth 249、Reader body textarea true、sidebar textarea false、sidebar import region false
- 取得できなかった証跡と理由: 実ユーザーテストはこの変更範囲では未実施

## 13. 実行した検証

- [x] typecheck
- [x] unit test
- [x] accessibility check
- [x] keyboard check
- [x] responsive check
- [x] visual screenshot
- [x] document publication safety review

## 14. 実行していない検証

| 未実行検証 | 理由 | 残リスク | 後続対応 |
|---|---|---|---|
| full Playwright smoke suite | backendを含むE2E環境を起動していないため。今回のUI確認はPlaywrightのAPIモックとDOMメトリクスで実施 | 認証や実APIを含むE2E regressionsはCI側確認に委ねる | PR CIで確認 |
| 実ユーザーテスト | 小規模な重複UI削除とレイアウト修正であり、今回は自動/手動検証に限定 | 実利用での認知負荷改善の定量値は未計測 | 必要なら別途ユーザー確認 |
