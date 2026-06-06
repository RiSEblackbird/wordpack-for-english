# UI/UXレビュー報告: 全画面UI統一と生成キュー統一 2026-06-07

## 1. 概要

- 対象PR / 作業: Lexicon以外の主要画面へ共通デザインと生成キューを展開
- 変更した画面・コンポーネント: Lexicon / Reader / Examples / Explore / Shelves / Settings / WordPack詳細、生成キュー、右レール、用例カード、棚カード、WordPack詳細の補助表示
- 判定: Pass
- P0件数: 0
- P1件数: 0
- P2件数: 2

## 2. ユーザー価値

- 対象ユーザー: 英語学習者、個人辞書を反復編集するユーザー
- 利用文脈: WordPack生成中に別画面で文章、例文、関連語、棚、設定、詳細を確認する
- ユーザー目的: どの画面にいても生成状況を見失わず、同じ視覚言語で辞書作業を続ける
- 支援するタスク: 生成待ち確認、完了/失敗把握、Readerでの文章取り込み、Examples検索、Exploreでの未登録語作成、Shelves選択、Settings調整
- このUIが助ける理解・判断・行動: 現在地、最初の操作、生成中の対象、完了履歴、失敗状態、画面固有の次アクション
- このUIがなければ困る点: Lexiconだけ右側キューで他画面は右下トーストになり、画面移動時に状態表示の場所と意味が変わる
- 削るべき情報・操作: 右下トーストの重複表示、ページごとのばらばらな補助説明
- 検証仮説・成功指標: 主要7画面で `生成キュー` が1つずつ表示され、`.ntf-card` が0件で、axe違反0

## 3. 初見理解

- 何の画面か分かるか: 各画面の大見出しと1行説明で判別できる。
- 今どこか分かるか: 左サイドバーの選択状態と画面見出しで判別できる。
- 何ができるか分かるか: 上部検索/更新、メインカード、右レール補助カードで分かる。
- 最初の有意味な行動: Readerは文章貼り付け、Examplesは検索/絞り込み、ExploreはWordPack選択、Shelvesは棚選択、Settingsは設定変更、詳細は記事操作。
- 操作結果を予測できるか: 生成/再生成は右レールの生成キューへ入り、完了/失敗履歴になる。
- 失敗時に戻れるか: キュー失敗履歴、対象操作近くのalert/status、更新ボタンから再試行できる。

## 4. state matrix

| 状態 | ユーザーが見るもの | 次にできる行動 | 判定 |
|---|---|---|---|
| 通常 | 各画面の主領域 + 右側生成キュー | 検索、選択、生成、設定変更 | Pass |
| 読み込み中 | 既存の読み込み文言、キュー進行中カード | 待機、ページ移動、キュー確認 | Pass |
| 空 | EmptyState と次行動 | Lexiconで作成、検索解除、更新 | Pass |
| 検索結果なし | 検索語を短くする/更新する文言 | 条件変更 | Pass |
| 部分データ | 件数、空のWordPack、未登録をバッジで区別 | 詳細、作成、別分類確認 | Pass |
| エラー | alert / キュー失敗カード | 通信確認、再試行 | Pass |
| 入力エラー | 既存フォームの説明/disabled | 入力修正 | Pass |
| 無効 | 無効理由または補助文 | 前提操作、ログイン、選択 | Pass |
| 権限不足 | GuestLockとログイン案内 | ログイン | Pass |
| オフライン/利用不可 | 通信失敗文言とキュー失敗履歴 | 再試行 | Pass |
| 狭幅 | 右レールが本文下へ回り、Explore内部も1カラム | スクロールして同じ操作 | Pass |
| 文字拡大 | 主要領域はグリッドで折り返し | 操作継続 | Pass |
| 長文・大量データ | カード内折り返し、スクロール領域 | 検索/絞り込み | Pass |

## 5. アクセシビリティ確認

- キーボード: 既存ボタン/入力/タブ/チェックボックス構造を維持。右レールはregion、生成キューはsectionで到達可能。
- フォーカス: 既存のfocus-visibleとボタン要素を維持。
- 名前・ラベル: `生成キュー`、検索ラベル、補助regionラベル、進行状況progressbarを確認。
- 見出し・構造: 用例カードのh4飛びをh3へ修正。補助レールをasideからregionへ変更。
- コントラスト: Examples、Explore、Shelves、WordPack詳細で検出された低コントラストを修正。
- ターゲットサイズ: 主要ボタンは既存サイズを維持。狭幅では1カラム化。
- エラー・ステータス: キュー内で進行中/完了/失敗を表示。
- 自動検査: Playwright + axe-coreで対象7画面とモバイル3画面が違反0。
- 手動確認: デスクトップReader/Explore/Settings、モバイルExploreのスクリーンショットを目視確認。

## 6. 視覚階層

- 主操作: 各画面の上部に検索/更新、主領域に作業、右レールに状態を固定。
- 情報優先度: 画面目的、対象リスト、詳細/操作、生成状態の順に整理。
- グルーピング: 共通 `dictionary-workspace` と `dictionary-rail` で統一。
- 余白・密度: Lexicon寄りの密度に統一。カード半径は8px前後。
- 読みやすさ: 低コントラストの旧カード色を修正。
- 狭幅・文字拡大: Explore内部の高詳細度2カラムをモバイルで1カラムに修正。

## 7. コピー

- 用語: 「生成キュー」「進行中」「完了」を全画面で統一。
- ボタン・リンク: Shelvesの `Open` を「開く」へ変更。
- エラー文: 既存の原因/回復手段文言を維持。
- 空状態: Shelvesの検索結果なしに「検索語を短くするか、一覧を更新」を追加。
- disabled: Exploreの作成不可理由、GuestLockを維持。
- トーン: ユーザーを責めない文言を維持。

## 8. 熟練者効率

- 主要反復タスク: 生成状態確認の場所を全画面で右レールへ固定。
- 手数: ページ移動後に右下通知を探す必要を削減。
- 再入力・再選択: 既存の検索/設定保持を維持。
- 近道: 既存ショートカット、検索、更新、クイックアクションを維持。
- 初心者向け説明の影響: 補助説明は右レールカードに寄せ、主作業を妨げない。
- 判定: Pass。

## 9. 満足感・信頼感

- 待機中: 進行中件数、対象語、モデル、経過時間、進捗バーを表示。
- 成功時: 完了履歴と対象語を表示。
- 失敗時: 失敗状態とメッセージを同じキュー内に表示。
- 危険操作: 削除確認など既存挙動を維持。
- データ・権限・個人情報: GuestLock、ログアウト導線を維持。
- トーン: 失敗時も通信確認/再試行に誘導。
- 判定: Pass。

## 10. 反証レビュー

- 実装を落とす観点で見つけた問題: 初回実装ではExploreモバイルが2カラムのまま潰れ、axeで複数のコントラスト違反が出た。
- P0候補: モバイルExploreの内容潰れ、低コントラスト、キュー表示の画面差。
- 対応: Exploreモバイル1カラム化、right railのregion化、低コントラスト修正、AppShellの旧トースト削除。
- 証跡不足: 実ユーザーテストは未実施。
- 残リスク: 下部ナビは既存の固定表示で、全スクロール位置の手動確認は未網羅。

## 11. 指摘一覧

| 優先度 | 箇所 | 問題 | 影響 | 修正案 | 状態 |
|---|---|---|---|---|---|
| P0 | 生成通知 | Lexiconだけ右レール、他画面は右下トースト | 状態表示の場所が画面で変わる | 全主要画面へ共通生成キュー | 対応済 |
| P0 | Explore mobile | 内部2カラムが潰れる | 初見で読めず操作しにくい | 狭幅で1カラム化 | 対応済 |
| P0 | Examples/Shelves/Detail | コントラスト違反 | 読めないユーザーが出る | 色トークンとチップ色を修正 | 対応済 |
| P1 | Reader/Examples/Settings | 画面骨格がLexiconと不統一 | 品質差、現在地の理解低下 | 共通workspace/railへ統一 | 対応済 |
| P2 | モバイル下部ナビ | 固定ナビが一部スクロール位置で本文に重なる可能性 | 読み進め時に一時的に隠れる | 後続でbottom navの表示方式を再検討 | 未対応 |
| P2 | 実ユーザーテスト | AIレビューと自動検査のみ | 実利用の迷いは未検証 | ユーザーテストで補完 | 未対応 |

## 12. 証跡

- ImageGen参照: `docs/ai-governance/evidence/2026-06-07-ui-unification/imagegen-unified-ui-reference.png`
- デスクトップスクリーンショット:
  - `implemented-lexicon.png`
  - `implemented-reader.png`
  - `implemented-examples.png`
  - `implemented-explore.png`
  - `implemented-shelves.png`
  - `implemented-settings.png`
  - `implemented-detail.png`
- モバイルスクリーンショット:
  - `implemented-mobile-reader.png`
  - `implemented-mobile-explore.png`
  - `implemented-mobile-settings.png`
- 自動検査: Playwrightで7画面の `生成キュー` 表示が各1件、`.ntf-card` が0件、axe違反0。
- 取得できなかった証跡と理由: 実ユーザー観察は未実施。

## 13. 実行した検証

- [x] typecheck: `cd apps/frontend && npx tsc -p tsconfig.json`
- [x] frontend tests: `cd apps/frontend && npm test -- --coverage --silent`
- [x] Playwright smoke: `npx playwright test -c tests/e2e/playwright.config.ts tests/e2e/auth.spec.ts tests/e2e/guest.spec.ts tests/e2e/wordpack.spec.ts`
- [x] diff check: `git diff --check`
- [x] accessibility check: Playwright + axe-core、Lexicon / Reader / Examples / Explore / Shelves / Settings / WordPack詳細、違反0
- [x] responsive check: 390px幅でReader / Explore / Settings、違反0
- [x] visual regression相当: Playwrightスクリーンショット保存と目視確認
- [x] ImageGen: 共通右レール案を生成し、実装参照として保存

## 14. 実行していない検証

| 未実行検証 | 理由 | 残リスク | 後続対応 |
|---|---|---|---|
| 実ユーザーテスト | 今回は実装と自動/目視検証が対象 | 初見説明の自然さは仮説 | ユーザー観察で補完 |
| 全モバイル画面の全スクロール位置目視 | 代表3画面で確認 | 固定下部ナビの一部重なり | 後続でbottom navの仕様改善 |
