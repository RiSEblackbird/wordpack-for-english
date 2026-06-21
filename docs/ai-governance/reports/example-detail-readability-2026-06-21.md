# 例文詳細 読みやすさ改善 UI/UXレビュー 2026-06-21

## 1. 概要

- 対象PR / 作業: 例文詳細モーダルの原文・日本語訳・解説の視覚構造改善
- 変更した画面・コンポーネント: `ExampleDetailModal`, `splitExampleExplanation`, `UserManual.md`
- 判定: Pass
- P0件数: 0
- P1件数: 0
- P2件数: 1

## 2. ユーザー価値

- 対象ユーザー: 保存済み例文を読み、英文・訳・文法解説を照合する英語学習者
- 利用文脈: Examples 画面の例文詳細モーダル、WordPack横断の用例確認
- ユーザー目的: 英文のどの文がどの日本語訳に対応するかを短時間で確認し、解説の要点と品詞分解を混同せず読む
- 支援するタスク: 例文読解、訳の照合、構文理解、学習記録、文字起こし練習
- このUIが助ける理解・判断・行動: 原文と訳を文単位の同じ行で比較でき、解説は要点・構文・品詞分解として読む順序を判断できる
- このUIがなければ困る点: 長い英文と訳を上下に目で往復し、対応範囲を記憶しながら読む必要がある。解説に品詞分解が混ざると、先に読むべき要点が埋もれる
- 削るべき情報・操作: 既存の学習記録、文字起こし、詳細情報は保持。新規の説明文は増やさず、構造化で解決した
- 検証仮説・成功指標: 例文詳細で文ペア数が表示され、要点カードに品詞分解が混入せず、desktop/mobile とも横 overflow がない

## 3. 初見理解

- 何の画面か分かるか: タイトルと `原文と日本語訳`、`解説`、`学習記録` の見出しで例文詳細だと分かる
- 今どこか分かるか: モーダルタイトルに lemma/category を表示
- 何ができるか分かるか: 原文/訳の音声再生、解説確認、品詞分解展開、詳細情報展開、学習記録、文字起こし練習
- 最初の有意味な行動: 原文と日本語訳の対応行を読む
- 操作結果を予測できるか: `品詞分解を表示` は詳細展開、学習記録ボタンは回数更新として読める
- 失敗時に戻れるか: モーダルは `閉じる` / Esc で閉じられる。API失敗は既存 status 表示で通知

## 4. state matrix

| 状態 | ユーザーが見るもの | 次にできる行動 | アクセシビリティ | 証跡 | 判定 |
|---|---|---|---|---|---|
| 通常 | 文単位の原文/訳対応行、解説カード、学習記録 | 音声再生、品詞分解展開、記録 | section/list/details/button | Playwright desktop | Pass |
| 長文 | 各文ペアがカード内で折り返し、解説は要点と品詞分解に分離 | 必要部分だけ読む | overflow-wrap / no horizontal overflow | Playwright desktop/mobile | Pass |
| 狭幅 | 原文と訳が1列に積まれ、同じ番号で対応 | 縦スクロールで読む | listitem と label を維持 | Playwright mobile | Pass |
| 文字拡大相当 | 固定幅ではなく minmax と折り返し | スクロールして読む | テキストが親要素をはみ出さない | overflow check | Pass |
| 解説なし | 原文/訳、詳細情報、学習記録だけ表示 | 読む、記録する | 不要な空見出しなし | 既存テスト | Pass |
| 品詞分解あり | 要点と details が分離 | details を展開 | native summary | Vitest / Playwright | Pass |
| 文数不一致 | 全文1ペアに fallback | 全文単位で照合 | 不確かな対応を作らない | unit test | Pass |
| API未設定/失敗 | 既存の status 文言 | 設定確認、再試行 | role=status | 既存挙動維持 | Pass |
| ゲスト | GuestLock で記録系が無効 | ログイン | disabled / tooltip | 既存テスト | Pass |

## 5. アクセシビリティ確認

- キーボード: Modal の既存 focus trap を維持。`summary` は native details、学習記録・文字起こしは button
- フォーカス: Playwright で Tab 移動後の active control に accessible name/text があることを確認
- 名前・ラベル: 原文/訳の音声 button は `原文の音声` / `日本語訳の音声` の accessible name を維持
- 見出し・構造: 原文/訳対応は `ol` + `li`、解説は section + article + details
- コントラスト: axe で dialog 内の違反なし。既存の低コントラスト操作ボタン2件も同時修正
- ターゲットサイズ: 既存 button size を維持。新規の文ペア番号は操作対象ではない
- エラー・ステータス: 既存 role=status を維持
- 自動検査: Playwright + axe-core で dialog を検査
- 手動確認: desktop/mobile screenshot を目視確認

## 6. 視覚階層

- 主操作: この画面の主行動は読むことなので、原文/訳対応行を最初に配置
- 情報優先度: 原文/訳ペア、解説要点、品詞分解、詳細情報、学習記録の順
- グルーピング: 同じ文番号内に原文と訳を近接配置。解説は要点カードと details に分離
- 余白・密度: 文ペアごとに border と余白を持たせ、長文でも行の境界が追える
- 読みやすさ: 品詞分解が要点カードに混ざらない
- 狭幅・文字拡大: 640px 以下では原文/訳を縦積みにし、対応番号を維持

## 7. コピー

- 用語: `原文と日本語訳`, `要点`, `構文`, `品詞分解を表示` を使用
- ボタン・リンク: 音声ボタンは対象を明示。学習記録・文字起こし文言は既存維持
- エラー文: 既存エラー文を変更なし
- 空状態: 解説なしの場合は解説 section を出さない
- disabled: 文字起こしの disabled 理由は既存維持
- トーン: ユーザーを責める文言なし

## 8. 熟練者効率

- 主要反復タスク: 保存済み例文を開いて英文/訳/解説を確認する
- 手数: 照合のための操作は増やしていない。読む領域の構造だけ改善
- 再入力・再選択: なし
- 近道: 原文/訳の全体音声ボタンを上部に集約
- 初心者向け説明の影響: 説明文を追加せず、番号と配置で理解を支援
- 判定: Pass

## 9. 満足感・信頼感

- 待機中: 対象外。既存の一覧 loading を維持
- 成功時: 学習記録の成功 status を維持
- 失敗時: API失敗 status を維持
- 危険操作: なし
- データ・権限・個人情報: 新規送信なし。文字起こし入力送信の既存仕様は維持
- トーン: 長文を責めず、読む単位を分ける設計
- 判定: Pass

## 10. 反証レビュー

- 実装を落とす観点で見つけた問題: 文数が一致しない場合に誤った1対1対応を作るリスクがあったため、全文1ペアに fallback
- P0候補: dialog 内 color contrast 違反を axe で検出。学習記録/文字起こしボタンの文字色を修正済み
- 証跡不足: 実ユーザーテストは未実施
- 残リスク: 代表的な略語、技術語、バージョン表記は保護した。未知の省略表記では sentence split が完全ではない可能性があるが、文数不一致時は全文ペアに fallback し、内容は失わない

## 11. 指摘一覧

| 優先度 | 箇所 | 問題 | 影響 | 修正案 | 状態 |
|---|---|---|---|---|---|
| P0 | 例文詳細 dialog | 既存の学習記録/文字起こしボタンが axe color-contrast 違反 | 低視力環境で操作文言が読みにくい | 文字色を濃くする | 対応済 |
| P1 | 原文/訳 | 上下に分かれ、対応範囲を目で追いにくい | 読解時の照合負荷が高い | 文単位ペア行に変更 | 対応済 |
| P1 | 解説 | 品詞分解と要点が同じ段落に混ざる | 読み始める場所が分かりにくい | 要点カードと品詞分解 details に分離 | 対応済 |
| P2 | 文分割 | 略語やバージョン表記で sentence split が誤る可能性 | 誤った対応行が出る | 代表的な略語、`Node.js` 系、数値バージョンを保護し、回帰テストを追加 | 対応済 |

## 12. 証跡

- スクリーンショット: `/tmp/wordpack-example-detail-readability-desktop.png`, `/tmp/wordpack-example-detail-readability-mobile.png`（ローカル証跡、未コミット）
- トレース: なし
- テスト結果: Vitest targeted, typecheck, Playwright browser check
- 手動確認: desktop/mobile screenshot で文ペア、要点カード、品詞分解 details、横 overflow なしを確認
- 取得できなかった証跡と理由: 実ユーザーテストはこの作業範囲外

## 13. 実行した検証

- [x] typecheck: `cd apps/frontend && npx tsc -p tsconfig.json`
- [x] unit test: `cd apps/frontend && npm test -- --run src/components/ExampleDetailModal.test.tsx src/lib/exampleExplanation.test.ts --silent`
- [x] accessibility check: Playwright + axe-core dialog check, violations 0
- [x] keyboard check: Playwright で Tab 後の focus target に accessible name/text があることを確認
- [x] responsive check: Playwright desktop 1180x900 / mobile 390x844
- [x] visual regression: local screenshots saved outside repository
- [x] その他: Browser metrics で文ペア数2、要点への品詞分解混入なし、horizontal overflow 0。略語・バージョン表記の分割保護を unit test で確認

## 14. 実行していない検証

| 未実行検証 | 理由 | 残リスク | 後続対応 |
|---|---|---|---|
| 実ユーザーテスト | ローカル実装・PR範囲では実施不可 | 実利用での照合速度改善は定量未確認 | 必要ならユーザー観察または操作計測を追加 |
| 全LLM出力パターンの網羅 | 生成文の表記揺れが広いため deterministic に網羅できない | 未知の省略表記や一部の解説で分類が完全でない可能性 | 必要なら生成側に構造化フィールドを追加する Issue を検討 |
