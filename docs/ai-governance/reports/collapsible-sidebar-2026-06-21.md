# UI/UXレビュー報告: サイドメニュー折りたたみ 2026-06-21

## 1. 概要

- 対象PR / 作業: Issue #468 サイドメニューを折りたたみ可能にする
- 変更した画面・コンポーネント: 共通AppShell、デスクトップSidebar、主要メニュー、サイドバー詳細領域、関連テスト、README、UserManual
- 判定: Pass
- P0件数: 0
- P1件数: 0
- P2件数: 0

## 2. ユーザー価値

- 対象ユーザー: デスクトップ幅でWordPackを反復利用する学習者・管理者
- 利用文脈: Lexicon、Examples、Readerなどで本文や一覧を広く見たいが、画面移動もすぐ使いたい場面
- ユーザー目的: 左メニューの文脈を残しながら、本文領域を広げて読み取りや一覧操作をしやすくする
- 支援するタスク: サイドバーを折りたたむ、アイコンメニューで画面移動する、必要時に展開して音声設定やログアウトへ戻る
- このUIが助ける理解・判断・行動: 現在地を主要メニューの選択状態で保ちつつ、表示領域の密度をユーザーが調整できる
- このUIがなければ困る点: デスクトップで本文やカード一覧を広く見たいときも、常に224pxのサイドバー幅を占有する
- 削るべき情報・操作: 折りたたみ中は詳細操作を隠し、主要メニューだけ残す。追加説明文は常設しない
- 検証仮説・成功指標: 折りたたみ後のサイドバー幅が80px以下になり、主要メニュー遷移がそのまま使える

## 3. 初見理解

- 何の画面か分かるか: WordPackの共通画面。展開時はブランドと主要メニューで分かる
- 今どこか分かるか: 現在ページは選択中メニューの強調と本文見出しで分かる
- 何ができるか分かるか: 展開時は「折りたたむ」、折りたたみ時は「展開」ボタンで状態を戻せる
- 最初の有意味な行動: 本文を広げたい時に「折りたたむ」、別画面へ行きたい時にアイコンメニューを選ぶ
- 操作結果を予測できるか: aria-label、title、表示ラベルで折りたたみ/展開の結果が分かる
- 失敗時に戻れるか: 破壊的操作ではなく、同じ場所の「展開」ボタンで即時に戻せる

## 4. state matrix

| 状態 | ユーザーが見るもの | 次にできる行動 | a11y/状態伝達 | 証跡 | 判定 |
|---|---|---|---|---|---|
| 通常 | 展開されたサイドバー、主要メニュー、音声コントロール、ページ固有操作、footer | 折りたたむ、画面移動、ログアウト | `aria-expanded=true`、sidebar `aria-hidden=false` | App.test / visual.spec | Pass |
| 折りたたみ | ブランドアイコン、展開ボタン、主要メニューアイコン | 展開、主要メニュー遷移 | `aria-expanded=false`、nav buttonのaccessible nameとtitle | App.test / guest.spec | Pass |
| 読み込み中 | サイドバーの状態は維持され、本文側が待機 | 画面移動または展開 | 既存の本文側statusを維持 | visual.spec | Pass |
| 空 | 空状態本文とサイドバー状態が独立 | 作成、条件変更、画面移動 | sidebar状態は本文空状態を隠さない | smoke / visual.spec | Pass |
| 検索結果なし | 本文側の検索なし状態、サイドバーは維持 | 条件変更、画面移動 | 既存本文コピーを維持 | smoke | Pass |
| 部分データ | 本文側の部分表示とサイドバー状態 | 表示継続、画面移動 | sidebarは部分データを空と混同しない | review | Pass |
| エラー | 本文側エラーとサイドバー状態 | 再試行、画面移動 | 既存エラー表示を維持 | smoke | Pass |
| 入力エラー | 入力欄近くの既存エラー | 入力修正、必要時に展開 | 入力エラーのhelper配置を維持 | wordpack.spec | Pass |
| 無効 | ゲストや前提不足による既存disabled | 条件確認、画面移動 | disabled理由は既存GuestLock等を維持 | guest.spec | Pass |
| 権限不足 | ゲスト制限とサイドバー状態 | ログアウト、閲覧継続 | 折りたたみ時は詳細操作を非表示、展開で確認 | guest.spec | Pass |
| オフライン/利用不可 | 通信失敗は本文側または既存toast | 再試行、画面移動 | sidebar状態は通信失敗を隠さない | review | Pass |
| 狭幅 | 900px以下は既存hamburger overlay | メニュー開閉、下部ナビ | mobileは既存 `メニューを開く/閉じる` を維持 | guest.spec | Pass |
| 文字拡大 | 折りたたみ中はアイコン操作、展開で全文ラベル | 展開して詳細確認 | 操作対象は24px超、focus visible維持 | CSS review / tests | Pass |
| 長文・大量データ | サイドバー幅を縮め本文領域を広げられる | 折りたたみ、画面移動 | navはaccessible nameを維持 | guest.spec metrics | Pass |

## 5. アクセシビリティ確認

- キーボード: 折りたたみ/展開ボタンと主要メニューはbuttonで操作可能。折りたたみ中の詳細領域はdisabledまたは非表示
- フォーカス: 既存focus-visibleに折りたたみボタンを追加。mobile overlayのfocus復帰は既存処理を維持
- 名前・ラベル: `サイドメニューを折りたたむ` / `サイドメニューを展開`、主要メニューのaccessible nameを維持
- 見出し・構造: aside/nav/region構造を維持。折りたたみ中は詳細regionを `aria-hidden=true`
- コントラスト: 既存の濃色サイドバー上でボタン枠・文字・アイコンを同系統の高コントラストで表示
- ターゲットサイズ: 折りたたみボタン38px、nav button 2.75remで最小目安を満たす
- エラー・ステータス: 新規エラー状態は追加なし。既存本文側ステータスを維持
- 自動検査: guest.specのログイン画面axe、Playwright smoke、visual regression
- 手動確認: 実ブラウザの折りたたみ状態はPlaywright metricsで確認

## 6. 視覚階層

- 主操作: 展開時は上部の「折りたたむ」、折りたたみ時は同じ位置の「展開」
- 情報優先度: 折りたたみ時は主要メニューのみを残し、詳細操作は表示しない
- グルーピング: ブランド、折りたたみ操作、主要メニュー、詳細領域、footerの既存構造を維持
- 余白・密度: collapsed width 72pxで本文領域を広げ、nav icon railは安定寸法に固定
- 読みやすさ: 詳細テキストは展開状態でのみ表示し、折りたたみ中の詰め込みを避ける
- 狭幅・文字拡大: mobileは既存overlayへ分岐し、desktop collapsedとは混ぜない

## 7. コピー

- 用語: 既存の「サイドメニュー」を使い、mobileの「メニューを開く」と衝突しない
- ボタン・リンク: `折りたたむ` / `展開` は結果が分かる動詞
- エラー文: 新規エラーなし
- 空状態: 新規空状態なし
- disabled: 折りたたみ中の音声selectはdisabledになり、視覚的には詳細領域ごと非表示
- トーン: 状態を短く示し、警告や責任転嫁の文言は追加なし

## 8. 熟練者効率

- 主要反復タスク: 画面移動、一覧/本文閲覧、音声設定、ログアウト
- 手数: 本文を広げる操作は1クリック。折りたたみ中も画面移動は追加手数なし
- 再入力・再選択: routeや入力状態は折りたたみ操作で失われない
- 近道: アイコンレールで主要メニューを残す。既存Alt+数字ショートカットも維持
- 初心者向け説明の影響: 常設説明文を追加せず、button label/titleで意味を伝える
- 判定: Pass

## 9. 満足感・信頼感

- 待機中: sidebar状態は本文の読み込みを邪魔しない
- 成功時: 折りたたみは即時に幅が変わり、同じ位置のボタンで戻せる
- 失敗時: 新規失敗状態なし。操作は非破壊で可逆
- 危険操作: ログアウトは折りたたみ中に隠し、展開中の既存導線へ戻す
- データ・権限・個人情報: 追加のデータ送信なし。認証/guest契約は変更なし
- トーン: 不安を煽るコピーなし
- 判定: Pass

## 10. 反証レビュー

- 実装を落とす観点で見つけた問題: desktop collapseを既存mobile open stateに混ぜるとinert/focus復帰が壊れるため、desktop専用stateとして分離した
- P0候補: 折りたたみ中に詳細操作へTab移動できる、主要メニュー名が支援技術へ伝わらない、mobile hamburgerが壊れる
- 証跡不足: 実ユーザーテストは未実施。AI/自動ブラウザ検証に限定
- 残リスク: Linux環境の見え方はCI visual regressionで最終確認する

## 11. 指摘一覧

| 優先度 | 箇所 | 問題 | 影響 | 修正案 | 状態 |
|---|---|---|---|---|---|
| P1 | Sidebar state | mobile開閉stateとdesktop折りたたみstateを共有するとfocus/inertが壊れる | mobile overlayやkeyboard操作が退行する | desktop専用stateをAppShellに追加 | 対応済 |
| P1 | 折りたたみ中の詳細操作 | 非表示でもfocus可能だとキーボード利用者が迷う | 見えない操作へ到達する | 詳細領域を非表示/aria-hidden、select disabled、footer tabIndex=-1 | 対応済 |
| P1 | 主要メニュー | アイコンだけで意味が伝わらない可能性 | 初見理解とa11y低下 | accessible nameを維持し、折りたたみ時にtitleを付与 | 対応済 |

## 12. 証跡

- スクリーンショット: `tests/e2e/visual.spec.ts` の5画面 `toHaveScreenshot` が差分許容内でPass
- トレース: Playwright成功時のtraceは保存していない
- テスト結果: typecheck、frontend unit、guest E2E、standard smoke、visual regressionがPass
- 手動確認: 代替としてPlaywright metricsで折りたたみ後のsidebar width、main left、詳細領域display、nav遷移を確認
- 取得できなかった証跡と理由: 実ユーザー観察は未実施。ローカル成功時スクリーンショットは成果物として追跡しない

## 13. 実行した検証

- [ ] lint: このrepoにfrontend lintコマンドなし
- [x] typecheck: `cd apps/frontend && npx tsc -p tsconfig.json`
- [x] unit test: `cd apps/frontend && npm test -- --coverage --silent`
- [x] integration / e2e: `npx playwright test -c tests/e2e/playwright.config.ts tests/e2e/auth.spec.ts tests/e2e/guest.spec.ts tests/e2e/wordpack.spec.ts`
- [x] accessibility check: guest E2Eのaxe checkとrole/name中心の操作確認
- [x] keyboard check: App.testでbutton契約、guest.specで折りたたみ後のnav遷移
- [x] responsive check: 900px以下の既存hamburger/mobile bottom nav E2E
- [x] visual regression: `npx playwright test -c tests/e2e/playwright.config.ts tests/e2e/visual.spec.ts`
- [x] その他: `npx playwright test -c tests/e2e/playwright.config.ts tests/e2e/guest.spec.ts`

## 14. 実行していない検証

| 未実行検証 | 理由 | 残リスク | 後続対応 |
|---|---|---|---|
| Backend full pytest | backend契約・APIを変更していない | 低 | CIのBackend testsで確認 |
| Security headers pytest | security headersを変更していない | 低 | CIのSecurity headersで確認 |
| Cloud Run dry-run | deploy/script/configを変更していない | 低 | CIのCloud Run config guardで確認 |
| 実ユーザーテスト | ローカル開発タスク範囲外 | 初見でアイコン意味を見落とす可能性 | 必要ならユーザーテストや利用ログで確認 |
