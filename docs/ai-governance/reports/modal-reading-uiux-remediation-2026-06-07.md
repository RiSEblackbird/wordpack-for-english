# UI/UXレビュー報告: モーダル読解エリア改善 2026-06-07

## 1. 概要

- 対象PR / 作業: WordPackプレビュー、文章プレビュー、例文詳細、削除確認モーダルの読みやすさと操作理解の改善
- 変更した画面・コンポーネント: `ExamplesSection`、`ArticleDetailModal`、`ExampleDetailModal`、`ConfirmDialogContext`、`TTSButton`、visual spec、関連テスト、`UserManual.md`
- 判定: Pass
- 未対応P0件数: 0
- 未対応P1件数: 0
- 未対応P2件数: 0

## 2. ユーザー価値

- 対象ユーザー: 例文や記事を読みながら英語表現、訳、文法解説、関連WordPackを確認する英語学習者
- 利用文脈: WordPackプレビュー、インポート済み文章のプレビュー、例文詳細、削除確認
- ユーザー目的: 長い英文・訳・解説から、まず読むべき情報と必要時だけ見る詳細を迷わず判別する
- 支援するタスク: 例文読解、解説確認、音声再生、例文からの記事作成、関連WordPack確認、学習記録、文字起こし練習、削除判断
- このUIが助ける理解・判断・行動: 英文、訳、解説、構文、品詞分解、生成メタ情報、危険操作の影響を分離して判断できる
- このUIがなければ困る点: 長い解説が単一段落で埋まり、学習者がどこから読めばよいか、どの情報が補助情報か分からなくなる
- 削るべき情報・操作: 常時表示する必要のない品詞分解、内部ID/生成パラメータ、曖昧な削除確認文、長すぎる可視音声ボタン名
- 検証仮説・成功指標: 主要モーダルで本文構造が見出し化され、詳細情報は折りたたまれ、unit / typecheck / E2E / visual が通る

## 3. 初見理解

- 何の画面か分かるか: 既存タイトルを維持し、本文内に `英文`、`日本語訳`、`解説`、`関連WordPack`、`生成・管理情報` を明示した。
- 今どこか分かるか: WordPackプレビューではカテゴリ見出しと例文番号、例文詳細では lemma/category をタイトルに表示する。
- 何ができるか分かるか: `記事を作成`、`例文を生成`、`確認済みにする`、`学習済みにする`、`文字起こしを記録` へ動詞を具体化した。
- 最初の有意味な行動: 英文を読む、音声を再生する、要点を読む、必要なら品詞分解や生成情報を開く。
- 操作結果を予測できるか: 削除確認は対象と取り消し不可の影響を本文で示し、主ボタンを `削除する` にした。
- 失敗時に戻れるか: 既存の閉じる/キャンセル導線を維持し、削除確認ではキャンセルに初期フォーカスを置く。

## 4. state matrix

| 状態 | ユーザーが見るもの | ユーザーが理解できること | 次にできる行動 | 回復手段 | a11y通知/構造 | 証跡 | 判定 |
|---|---|---|---|---|---|---|---|
| WordPack例文通常 | 英文、訳、解説、構文、品詞分解details、操作ボタン | 読む順序と詳細の深さ | 音声、削除、記事作成、コピー、詳細展開 | detailsを閉じる、モーダルを閉じる | article label、button label、details summary | visual / Vitest | Pass |
| WordPack例文長文 | 要点と構文を先出しし、品詞分解を折りたたみ | 長い解説の主旨から読める | 必要時だけ品詞分解を開く | 折りたたむ | `summary` | visual snapshot | Pass |
| 文章プレビュー通常 | タイトル、英文、訳、解説の要点、関連WordPack | 本文と補助情報の境界 | 音声、WordPackプレビュー、生成/削除 | 閉じる | section / heading | visual / Vitest | Pass |
| 文章警告あり | 高コントラストの警告ボックス | 生成時の注意が本文と別情報である | 注意を読んで続行 | 閉じる | `role="alert"` / `aria-label="インポート警告"` | visual | Pass |
| 関連WordPackなし | 空状態文 | 紐づくWordPackがまだない | Lexiconで作成する | 閉じる | heading + paragraph | Vitest | Pass |
| 生成メタ情報あり | `生成・管理情報` details | AIモデルや時刻は補助情報である | 必要時だけ開く | detailsを閉じる | `details` / `summary` / `dl` | Vitest / visual | Pass |
| 例文詳細通常 | 原文、訳、解説、詳細情報、学習記録 | 学習対象と操作エリアの境界 | 音声、学習記録、文字起こし | 閉じる | section label / headings | Vitest | Pass |
| 文字起こし未入力 | ヘルプと disabled 理由 | 何を入力すれば記録できるか | 英文入力 | 入力修正 | `aria-describedby` | Vitest | Pass |
| 文字起こし文字数差大 | 入力文字数差と条件 | なぜ保存できないか | 文字数調整 | 入力修正 | status id参照 | Vitest | Pass |
| 削除確認 | 対象、取り消し不可の注意、キャンセル、削除する | 何が消え、戻せないこと | キャンセルまたは削除 | キャンセル初期フォーカス | dialog + initial focus | Vitest / E2E | Pass |
| ゲスト/権限不足 | 既存GuestLock | 編集操作が制限される | ログイン | 閉じる | disabled説明 | 既存テスト | Pass |
| 狭幅 | modal max width と折り返し | 同じ順序で読める | 同じ操作 | スクロール | responsive layout | Playwright smoke | Pass |

## 5. アクセシビリティ確認

- キーボード: 例文内の関連WordPack起動は既存の Enter / Space を維持し、削除確認はキャンセルへ初期フォーカス。
- フォーカス: 共通Modalの既存focus trapに合わせ、ConfirmDialogの `initialFocusRef` 型を null許容にしてキャンセルボタンへ渡した。
- 名前・ラベル: TTSButtonは可視ラベルを短い `音声` に保ち、`ariaLabel` で `英文の音声`、`記事本文の音声` など対象を具体化した。
- 見出し・構造: 本文、訳、解説、構文、補助メタ情報を見出し・section・details・dlで分けた。
- コントラスト: 文章警告ボックスは明背景用の暗色テキストへ固定し、visual snapshotで確認した。
- ターゲットサイズ: 既存ボタン寸法を維持し、可視ラベル長でボタンが肥大化しないようにした。
- エラー・ステータス: 文字起こし保存不可理由を status text と `aria-describedby` で表示した。
- 自動検査: Vitest、typecheck、Playwright smoke、Playwright visual を実行。
- 手動確認: visual snapshotを目視し、WordPack例文と文章警告の可読性を確認した。Browser pluginの直接ツールは discovery で利用できず、Playwrightで代替した。

## 6. 視覚階層

- 主操作: 本文近くの音声、例文カード下部の削除/記事作成/コピー、詳細下部の学習記録を維持。
- 情報優先度: 英文、訳、解説要点、構文、品詞分解、メタ情報の順に整理。
- グルーピング: 文章プレビュー本文を `article-reader` にまとめ、関連WordPackと生成情報を別セクション化。
- 余白・密度: 例文カードは小ラベルと本文を縦に分け、長文がラベル横に流れないようにした。
- 読みやすさ: 長い品詞分解を details に収納し、要点と構文を先に表示。
- 狭幅・文字拡大: 固定幅の長いボタン名を避け、本文は `max-width` と `line-height` で追いやすくした。

## 7. コピー

- 用語: `訳` を `日本語訳`、`記事化` を `記事を作成`、`生成` を `例文を生成` へ具体化。
- ボタン・リンク: 学習記録は `確認済みにする`、`学習済みにする`、文字起こしは `開く/閉じる` と `記録` に分けた。
- エラー文: 削除確認で「実行後はこの画面から取り消せません」と影響を明示。
- 空状態: 関連WordPackなしの文章プレビューに空状態文を追加。
- disabled: 文字起こし保存不可理由を表示。
- トーン: ユーザーを責めず、状態と次の行動を説明する。

## 8. 熟練者効率

- 主要反復タスク: 普段は要点だけを読み、必要なときだけ詳細を開ける。
- 手数: 文章・例文の本文操作は既存位置を維持し、補助情報だけ折りたたむ。
- 再入力・再選択: 学習記録や文字起こしの既存即時更新挙動を維持。
- 近道: 例文内の関連WordPack起動、音声、コピー、記事作成を維持。
- 初心者向け説明の影響: 説明はセクション見出しやdetails summaryに集約し、常時長文で主要操作を押し下げない。
- 判定: Pass。

## 9. 満足感・信頼感

- 待機中: 既存の読み込み状態に変更なし。
- 成功時: 記録や生成の既存通知挙動を維持。
- 失敗時: 文字起こし保存不可理由を具体化。
- 危険操作: 削除確認に対象、不可逆性、キャンセル初期フォーカス、赤い破壊ボタンを追加。
- データ・権限・個人情報: 生成メタ情報は必要時だけ開くdetailsへ移動。
- トーン: 警告、削除、保存不可理由を曖昧にしない。
- 判定: Pass。

## 10. 反証レビュー

- 実装を落とす観点で見つけた問題: visual確認で文章警告ボックスの文字色が白系のまま明背景へ乗り、コントラスト不足になっていた。
- 対応: `.ai-warnings` に暗色テキストと濃いborderを指定し、更新後のvisual snapshotで読み取れることを確認。
- P0候補: 長い解説の常時表示、削除確認の曖昧さ、音声ボタン名の肥大化、警告コントラスト不足を確認し対応済み。
- 証跡不足: 実スクリーンリーダー確認と実ユーザー観察は未実施。Browser pluginの直接操作ツールは discovery で利用できず、Playwright smoke / visual / Vitestで代替。
- 残リスク: 例文解説のAI出力フォーマットが想定外の場合、完全な分類ではなく要点側に寄る可能性がある。全文は失わない実装で代替済み。

## 11. 指摘一覧

| 優先度 | 箇所 | 問題 | 影響 | 修正案 | 状態 |
|---|---|---|---|---|---|
| P1 | WordPackプレビュー例文 | 英文、訳、解説、品詞分解が密に並ぶ | 読み始める場所が分かりにくい | ブロック化、見出し化、品詞分解details化 | 対応済 |
| P1 | 文章プレビュー | 本文、訳、解説、メタ情報の優先度が近い | 本文読解より補助情報が目立つ | 本文section化、生成情報details化 | 対応済 |
| P1 | 例文詳細 | 学習記録と文字起こしの条件が曖昧 | 保存できない理由が分からない | ヘルプ、状態文、disabled理由を追加 | 対応済 |
| P1 | 削除確認 | `はい/いいえ` と不可逆性不足 | 危険操作の予測が弱い | `削除する/キャンセル` と影響説明 | 対応済 |
| P1 | 文章警告 | 明背景に白系文字 | 警告が読めない | 暗色テキストを固定 | 対応済 |
| P2 | 音声ボタン | 対象がスクリーンリーダーで曖昧 | 複数音声ボタンの区別が弱い | 可視名は短く、aria名を具体化 | 対応済 |
| P2 | 関連WordPack空状態 | 空の理由が見えない | 未取得と未関連を誤認 | 空状態文を追加 | 対応済 |

## 12. 証跡

- Visual snapshot: `tests/e2e/visual.spec.ts-snapshots/wordpack-preview-examples-darwin.png`
- Visual snapshot: `tests/e2e/visual.spec.ts-snapshots/article-import-confirmation-darwin.png`
- テスト結果: `npm test -- --coverage --silent` で 153 passed / 1 skipped
- E2E結果: `npx playwright test -c tests/e2e/playwright.config.ts tests/e2e/auth.spec.ts tests/e2e/guest.spec.ts tests/e2e/wordpack.spec.ts` で 4 passed
- Visual結果: `npx playwright test -c tests/e2e/playwright.config.ts tests/e2e/visual.spec.ts` で 5 passed
- 取得できなかった証跡と理由: Browser plugin直接操作ツールは discovery で利用できず、Playwrightで実ブラウザ確認を代替。

## 13. 実行した検証

- [x] typecheck: `cd apps/frontend && npx tsc -p tsconfig.json`
- [x] frontend tests: `cd apps/frontend && npm test -- --coverage --silent`
- [x] Playwright smoke: `npx playwright test -c tests/e2e/playwright.config.ts tests/e2e/auth.spec.ts tests/e2e/guest.spec.ts tests/e2e/wordpack.spec.ts`
- [x] Playwright visual: `npx playwright test -c tests/e2e/playwright.config.ts tests/e2e/visual.spec.ts`
- [x] accessibility check: modal / label / alert / details / disabled reason をVitestとvisualで確認
- [x] keyboard check: 削除確認初期フォーカス、例文内button/role、既存E2E導線
- [x] responsive check: Playwright smokeのmobile guest flow
- [x] visual regression: WordPackプレビュー例文エリアと文章プレビューを含むsnapshot
- [x] その他: `git diff --check`

## 14. 実行していない検証

| 未実行検証 | 理由 | 残リスク | 後続対応 |
|---|---|---|---|
| 実スクリーンリーダー読み上げ | 外部支援技術の実機確認が必要 | 読み上げ順の微調整余地 | 主要dialogで実機確認 |
| 実ユーザー観察 | 参加者が必要 | 初見での自然な迷いは仮説 | 次回ユーザーテストで観察 |
| Backend full pytest | フロントエンドUI、docs、E2Eのみの変更でバックエンドロジックなし | バックエンド単体の未検証 | バックエンド変更時に実行 |
