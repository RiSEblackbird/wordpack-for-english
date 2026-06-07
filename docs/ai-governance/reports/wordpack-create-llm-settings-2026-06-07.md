# UI/UXレビュー報告: WordPack作成パネルのLLM詳細設定表示 2026-06-07

## 1. 概要

- 対象PR / 作業: Lexicon右レールの「新しいWordPackを作成」領域へ `reasoning.effort` と `text.verbosity` を表示する
- 変更した画面・コンポーネント: `WordPackPanel` の作成パネル、Lexicon作成パネルCSS、WordPack作成テスト、UserManual
- 判定: Pass
- P0件数: 0
- P1件数: 0
- P2件数: 0

## 2. ユーザー価値

- 対象ユーザー: Lexiconで新しいWordPackを生成する学習者、生成品質を調整しながら反復作成するユーザー
- 利用文脈: 右側の「新しいWordPackを作成」パネルで見出し語、モデル、生成詳細を選んでWordPackを作成する
- ユーザー目的: WordPack生成前に、推論量と出力量を同じ作成導線内で調整する
- 支援するタスク: モデル選択、`reasoning.effort` 選択、`text.verbosity` 選択、生成リクエスト送信
- このUIが助ける理解・判断・行動: 生成品質と文量に関わる設定が作成操作の直前に見え、文章インポート側と同じ概念で選べる
- このUIがなければ困る点: WordPack生成だけ詳細設定の入口が見えず、モデル以外の調整ができることを発見しにくい
- 削るべき情報・操作: なし。既存の設定項目を作成領域へ表示するだけで、新しい概念や説明文は増やしていない
- 検証仮説・成功指標: inline作成パネルで2つのcomboboxが見え、選択値が `/api/word/pack` の `reasoning.effort` / `text.verbosity` に反映される

## 3. 初見理解

- 何の画面か分かるか: Lexicon見出しと右レールの「新しいWordPackを作成」で分かる
- 今どこか分かるか: 主要メニューのLexicon選択状態とページ見出しで分かる
- 何ができるか分かるか: 見出し語、モデル、`reasoning.effort`、`text.verbosity`、作成ボタンが同じ領域に並ぶ
- 最初の有意味な行動: 見出し語を入力し、必要ならモデルと詳細設定を選ぶ
- 操作結果を予測できるか: 「作成を開始」は選択したモデル/詳細設定でWordPack生成を開始する
- 失敗時に戻れるか: 入力エラーは見出し語欄近くに表示され、ゲスト時はGuestLockの無効理由が表示される

## 4. state matrix

| 状態 | ユーザーが見るもの | 次にできる行動 | 判定 |
|---|---|---|---|
| 通常 | 見出し語、モデル、`reasoning.effort`、`text.verbosity`、作成ボタン | 設定を選んで作成 | Pass |
| 読み込み中 | 既存の生成中状態で入力/選択/作成ボタンがdisabled | 完了を待つ | Pass |
| 空 | 保存済み一覧は空、右レールに作成パネル | 新しいWordPackを作成 | Pass |
| 検索結果なし | 一覧側の結果なし表示と作成パネル | 検索条件変更または作成 | Pass |
| 部分データ | 一覧や生成キューが部分表示でも作成パネルは独立 | 作成または状況確認 | Pass |
| エラー | 一覧/取得エラーは各領域に表示、作成パネル設定は維持 | 再試行または入力継続 | Pass |
| 入力エラー | 見出し語ヘルプが赤字、作成ボタンdisabled | 見出し語を修正 | Pass |
| 無効 | 生成中またはゲスト時にselect/buttonがdisabled | 待機、ログイン、または別操作 | Pass |
| 権限不足 | ゲスト時にAI機能不可の理由が各操作近くに表示 | ログインして利用 | Pass |
| オフラインまたは利用不可 | 設定同期/通信エラーは既存通知、入力内容は保持 | 再試行 | Pass |
| 狭幅 | 作成パネルが本文下へ回り、詳細設定は1列 | 縦スクロールして選択 | Pass |
| 文字拡大 | ラベルを上、selectを下に置く詳細設定レイアウト | 設定選択を継続 | Pass |
| 長文・大量データ | 生成キュー/一覧が増えても作成パネルは右レール内で表示 | 右レールをスクロールして作成 | Pass |

## 5. アクセシビリティ確認

- キーボード: native `select` と `button` を維持。既存テストで作成フローを確認
- フォーカス: 既存の `select:focus-visible` を維持。詳細設定も同じ作成パネルのタブ順に入る
- 名前・ラベル: `reasoning.effort` と `text.verbosity` は表示ラベルと `aria-label` が一致
- 見出し・構造: `section aria-label="新しいWordPackを作成"` と `h2` を維持
- コントラスト: 既存の作成パネルselect色を継承
- ターゲットサイズ: selectは既存の `min-height: 2.65rem` を継承
- エラー・ステータス: 入力エラー、ゲスト無効理由、生成中disabledの既存状態を維持
- 自動検査: `WordPackPanel.test.tsx`、frontend full test、Playwright smokeを実行
- 手動確認: in-app Browserでdesktop 1280x720とmobile 390x844のDOM/寸法を確認

## 6. 視覚階層

- 主操作: 「作成を開始」と「WordPackのみ作成」を既存位置に維持し、詳細設定はモデルの下へ配置
- 情報優先度: 見出し語、作成ボタン、モデル、詳細設定の順を維持
- グルーピング: モデルと詳細設定を同じ作成パネル内にまとめ、どの生成に効く設定かを明確化
- 余白・密度: desktopは詳細設定2列、狭幅は1列。追加説明文は増やしていない
- 読みやすさ: 長いラベルは詳細設定内だけラベル上/値下にして、3.6rem列へ押し込まない
- 狭幅・文字拡大: 390px幅ではパネル357px、詳細select 324px、1列で収まることを確認

## 7. コピー

- 用語: 既存のOpenAIパラメータ名 `reasoning.effort` / `text.verbosity` を、文章インポート側と同じ表記で使用
- ボタン・リンク: 変更なし
- エラー文: 変更なし
- 空状態: 変更なし
- disabled: GuestLockの「ゲストモードではAI機能は使用できません」を維持
- トーン: 技術設定名以外の説明を増やさず、既存の簡潔なフォーム文脈を維持

## 8. 熟練者効率

- 主要反復タスク: 語彙ごとにモデル/詳細設定を調整してWordPackを生成する
- 手数: 別画面へ移動せず、作成パネル内で詳細設定を選べる
- 再入力・再選択: SettingsContextの既存状態を使うため、選択値は他の生成導線と共有される
- 近道: 新規ショートカットは追加しない。既存の「新しいWordPack」フォーカス導線を維持
- 初心者向け説明の影響: 説明文を増やさず、熟練者の反復作成を妨げない
- 判定: Pass

## 9. 満足感・信頼感

- 待機中: 生成中disabledの既存挙動を維持
- 成功時: 既存の生成通知と生成キューを維持
- 失敗時: 既存のエラー表示と再試行導線を維持
- 危険操作: なし。作成は既存の保存/生成操作で、削除や公開は含まない
- データ・権限・個人情報: ゲスト時のAI機能ロックと理由表示を詳細設定にも適用
- トーン: ユーザーを責める表現なし
- 判定: Pass

## 10. 反証レビュー

- 実装を落とす観点で見つけた問題: 詳細設定をinlineにも出すだけだと、共通 `.sidebar-inline` / `.sidebar-field` の影響で長いラベルが狭い列へ押し込まれる可能性があった
- P0候補: 表示ラベル/accessible name欠落、ゲスト時に設定だけ操作できる、狭幅でselectがはみ出す。いずれも対応済み
- 証跡不足: 実ユーザー観察、実スクリーンリーダー確認、永続スクリーンショット保存は未実施
- 残リスク: `reasoning.effort` / `text.verbosity` は技術名のままなので初見には意味が分かりにくい可能性がある。ただし既存の文書・文章インポート側表記と揃えるため今回の範囲では維持

## 11. 指摘一覧

| 優先度 | 箇所 | 問題 | 影響 | 修正案 | 状態 |
|---|---|---|---|---|---|
| P1 | `WordPackPanel` inline作成パネル | `creationPanelPlacement="inline"` では詳細設定が非表示 | Lexicon作成時に推論量/文量を調整できない | inlineでも詳細設定を表示 | 対応済 |
| P2 | Lexicon作成パネルCSS | 共通sidebar CSSの影響で長い詳細設定ラベルが狭い列へ入る | ラベル視認性が落ちる | 詳細設定だけ2列/1列grid、fieldは1列化 | 対応済 |

## 12. 証跡

- スクリーンショット: 永続保存なし。代替としてin-app BrowserのDOM snapshotと寸法メトリクスを記録
- トレース: Playwright smokeは成功のため失敗traceなし
- テスト結果:
  - `cd apps/frontend && npx vitest run --silent WordPackPanel.test.tsx`: Pass、11 passed
  - `cd apps/frontend && npx tsc -p tsconfig.json`: Pass
  - `cd apps/frontend && npm test -- --coverage --silent`: Pass、157 passed / 1 skipped
  - `npx playwright test -c tests/e2e/playwright.config.ts tests/e2e/auth.spec.ts tests/e2e/guest.spec.ts tests/e2e/wordpack.spec.ts`: Pass、6 passed
  - `git diff --check`: Pass
- 手動確認:
  - in-app Browser + mock API、desktop 1280x720: `新しいWordPackを作成` 内に `reasoning.effort` / `text.verbosity` comboboxを確認。詳細設定gridは `129.312px 129.328px`、パネルは `301x407`、下端691でviewport内
  - in-app Browser + mock API、mobile 390x844: 詳細設定gridは `324.234px` の1列、パネル幅357、select幅324でviewport幅内
  - ゲスト状態: 2つの詳細設定selectは他のAI操作と同じくdisabledになり、GuestLockの理由表示が付く
- 取得できなかった証跡と理由:
  - 実ユーザー観察: 外部協力が必要なため未実施
  - 実スクリーンリーダー: 今回はnative label/selectと自動/DOM確認で代替
  - real backendを使ったBrowser手動確認: Firestore emulatorなしの手動環境で一覧APIが待機したため、UI表示確認はmock APIで代替。HTTP契約はVitestとPlaywright smokeで確認

## 13. 実行した検証

- [ ] lint
- [x] typecheck
- [x] unit test
- [x] integration / e2e
- [x] accessibility check
- [x] keyboard check
- [x] responsive check
- [ ] visual regression
- [x] その他: in-app Browser DOM/寸法確認、`git diff --check`

## 14. 実行していない検証

| 未実行検証 | 理由 | 残リスク | 後続対応 |
|---|---|---|---|
| lint | repo必須コマンドにfrontend lintがなく、変更範囲はTSX/CSS/文書の小変更 | 低い。typecheck/test/diff checkで構文と主要契約は確認 | CIにlintがある場合はCI結果で確認 |
| visual regression snapshot更新 | visual snapshot対象の意図的な見た目変更ではなく、作成パネル内の既存設定表示追加 | 中低。細かな見た目差分はsnapshotでは未固定 | 必要ならLexicon visual snapshotを追加/更新 |
| 実ユーザー観察 | 外部協力が必要 | 技術設定名の理解度は未検証 | ユーザー調査やヘルプ文改善の別Issueで扱う |
| 実スクリーンリーダー | native label/selectとDOM snapshot確認で代替 | 読み上げ順の実機差は未確認 | 支援技術QA時に確認 |
