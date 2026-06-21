# 要件・詳細設計受領品質ハードニング UI/UXレビュー 2026-06-21

## 1. 概要

- 対象Issue / 作業: #462 Exploreの部分データ耐性とUI/UX受領証跡整備
- 変更した画面・コンポーネント: Explore の関係抽出ロジック、UI/UX evidence 一式
- 判定: Pass
- P0件数: 0
- P1件数: 0
- P2件数: 0

`plans/dictionary-exploration-ui.md` と `plans/dictionary-exploration-ui.status.json` では、Dictionary Exploration UI は実装済み・CI green と記録されていた。今回は客先受領前の硬化として、改修前 screenshot、ImageGen mock、実装後 screenshot、部分データ耐性テストを追加した。

## 2. ユーザー価値

- 対象ユーザー: 保存済みWordPackを個人辞書として検索・探索・育成する利用者。
- 利用文脈: Explore で既存WordPackから関連語、共起、対比、例文由来の候補を確認し、未登録語を追加する。
- ユーザー目的: 読解・用例確認中に見つかった関連語を、画面を落とさず安全に次のWordPack候補へつなげる。
- 支援するタスク: 関係候補の確認、保存済み/空/未登録の判断、作成可能候補の追加、作成不可理由の把握。
- このUIが助ける理解・判断・行動: API 詳細データに空値や旧形式が混ざっても、表示可能な候補だけを残し、ユーザーは探索作業を継続できる。
- このUIがなければ困る点: 部分データで Explore 全体が空白化またはエラー化し、どのWordPackを選んでいたか、次に何をすべきか分からなくなる。
- 削るべき情報・操作: 不正な数値、空文字、旧形式の文字列だけの contrast は関係候補として表示しない。
- 検証仮説・成功指標: 部分データでも Explore が描画され、正常な関係候補のみ表示されること。回帰テストと Playwright screenshot で確認する。

## 3. 改修前と ImageGen モック

- 改修前 screenshot:
  - `docs/ai-governance/evidence/2026-06-21-requirements-design-hardening/before-lexicon-desktop.png`
  - `docs/ai-governance/evidence/2026-06-21-requirements-design-hardening/before-explore-desktop.png`
  - `docs/ai-governance/evidence/2026-06-21-requirements-design-hardening/before-lexicon-mobile.png`
  - 同ディレクトリに Reader / Examples / Shelves / Settings / WordPack detail も保存。
- ImageGen mock:
  - `docs/ai-governance/evidence/2026-06-21-requirements-design-hardening/imagegen-lexicon-acceptance-mock.png`
  - `docs/ai-governance/evidence/2026-06-21-requirements-design-hardening/imagegen-explore-acceptance-mock.png`
- ImageGen prompt summary:
  - Lexicon: 個人辞書としての検索・一覧・作成・生成キューを、状態と主操作が分かる密度で整理する mock。
  - Explore: 選択中WordPack、関係分類、保存済み/空/未登録、作成不可理由を明確化する mock。

## 4. 実装スコープ

- `buildExploreRelations` は、文字列として扱える label/source/description だけを関係候補へ変換する。
- `collocations` / `examples` / `senses` / `contrast` が欠落、空、旧形式、または不正値を含んでも例外を出さない。
- `contrast` は現行APIの `{with, diff_ja}` に加え、旧内部名の `{with_, diff_ja}` も受ける。
- 数値、空文字、文字列だけの旧 `contrast` など、見出し語として判断できない値は表示しない。

## 5. 初見理解

- 何の画面か分かるか: Pass。Explore 見出しと説明で、保存済みWordPackのつながりを探す画面だと分かる。
- 今どこか分かるか: Pass。左ナビとページ見出し、選択中WordPack名で現在地が分かる。
- 何ができるか分かるか: Pass。関連語/共起/対比/例文/未登録のみの分類と、各カードの action label が見える。
- 最初の有意味な行動: WordPackを選ぶ、または検索欄で探索元を絞る。
- 操作結果を予測できるか: Pass。保存済みはプレビュー、未登録は作成、作成不可は理由表示。
- 失敗時に戻れるか: Pass。部分データはクラッシュさせず、表示可能な候補だけを継続表示する。

## 6. state matrix

| 状態 | ユーザーが見るもの | 理解できること | 次にできる行動 | 回復手段 | 証跡 | 判定 |
|---|---|---|---|---|---|---|
| 通常 | WordPack一覧、関係カード、状態badge | 選択元と候補状態 | プレビュー/作成/分類変更 | 別WordPack選択 | `after-explore-desktop.png` | Pass |
| 読み込み中 | 既存の読み込みempty/status | 対象詳細を取得中 | 待機 | 別WordPack選択または更新 | Explore既存テスト | Pass |
| 空 | EmptyState | 候補がまだない | 別分類/別WordPack | 更新 | 既存 UI | Pass |
| 検索結果なし | 検索語に一致しない旨 | 検索条件による空 | 検索語を短くする | 検索クリア/更新 | Explore既存テスト | Pass |
| 部分データ | 有効な関係だけ表示 | 不正値は候補扱いしない | 表示された候補を使う | 更新/別WordPack | `after-explore-malformed-desktop.png` | Pass |
| エラー | alert と更新/別選択の案内 | 詳細読み込み失敗 | 更新または別WordPack | 再試行 | 既存 UI | Pass |
| 入力エラー | 検索は非破壊、作成候補は validation reason | 作成不可理由 | Lexiconで必要語を作成 | 候補変更 | Explore既存テスト | Pass |
| 無効 | 作成不可 button と理由 | なぜ押せないか | 別候補を選ぶ | Lexiconで作成 | `after-explore-desktop.png` | Pass |
| 権限不足 | GuestLock と permission reason | ログインが必要 | ログイン | ゲスト閲覧継続 | Explore既存テスト | Pass |
| オフライン/利用不可 | fetch error の alert | 読み込み不能 | 更新 | 接続回復後再試行 | 既存 UI | Pass |
| 狭幅 | 1カラム、右レールは下へ回る | 同じ操作を縦に追える | スクロール操作 | 下部ナビで移動 | `after-explore-mobile.png` | Pass |
| 文字拡大 | テキスト折り返し前提のカード | 重なりなし | 通常操作 | スクロール | screenshot目視 | Pass |
| 長文・大量データ | 不正/長文 relation はカード内で折り返す | 候補単位で読める | 分類切替 | 検索/別WordPack | malformed screenshot | Pass |

## 7. アクセシビリティ確認

- キーボード: SegmentedControl、WordPack選択、作成/プレビュー操作は native button。Playwright screenshot では選択状態と focus が視認できる。
- フォーカス: モックと実装後 screenshot で focus/selected 状態を区別。既存の button/aria-pressed を維持。
- 名前・ラベル: Relation action は `「label」のWordPackを作成` / `作成できません` / `開く` の accessible name を維持。
- 見出し・構造: ページ見出し、候補リスト、接続カード、右レールsummaryの領域構造を維持。
- コントラスト: 自動検査の `color-contrast` は jsdom 制約で除外。Playwright screenshot 目視では主要 text/action の読解不可は見つからない。
- ターゲットサイズ: 主要操作は button として十分な高さを持つ。
- エラー・ステータス: 作成不可・権限不足・detail error は可視文言で表示。
- 自動検査: `ExplorePage.test.tsx` の axe check は pass。
- 手動確認: `after-explore-desktop.png`、`after-explore-malformed-desktop.png`、`after-explore-mobile.png` を目視確認。

## 8. 視覚階層

- 主操作: 未登録語の `WordPackを作成` と保存済みの `プレビュー` がカード右側にあり、対象カードに近い。
- 情報優先度: 選択元、分類、状態badge、候補label、action の順に読める。
- グルーピング: 左列が接続元、中央が候補、右列が集計という関係を維持。
- 余白・密度: desktop は dense だが区画境界が明確。mobile は1カラムでカードが潰れていない。
- 読みやすさ: 不正値を出さないことで `undefined` や空labelを避ける。
- 狭幅・文字拡大: screenshot で重なりなし。

## 9. コピー

- 用語: `保存済み` / `空のWordPack` / `未登録` を状態guideとカードbadgeで一致。
- ボタン・リンク: 結果が分かる `WordPackを作成`、`プレビュー`、`作成不可` を維持。
- エラー文: 不正データをユーザー責任にしない。表示可能な候補だけを出す。
- 空状態: 既存の別分類/別WordPackへの案内を維持。
- disabled: 作成不可理由をカード内に表示し、tooltip依存にしない。
- トーン: ユーザーを責めず、作成できない理由を事実として示す。

## 10. 熟練者効率

- 主要反復タスク: WordPack選択、分類切替、未登録語作成、保存済みプレビュー。
- 手数: 今回の変更で手数増加なし。
- 再入力・再選択: 部分データで画面が落ちないため、選択状態を失いにくい。
- 近道: 既存のクイックアクションを維持。
- 初心者向け説明の影響: 状態guideは短く、作業領域を押し潰していない。
- 判定: Pass。

## 11. 満足感・信頼感

- 待機中: 既存の loading/empty 表示を維持。
- 成功時: 作成成功時の preview notice は既存維持。
- 失敗時: 部分データは失敗画面にせず、使える情報だけを表示。
- 危険操作: 今回は削除/公開/送信の変更なし。
- データ・権限・個人情報: 固定サンプルデータのみ。公開文書に秘密値や本番ログ原文は含めていない。
- トーン: 不正値をユーザーに見せず、作業継続を優先。
- 判定: Pass。

## 12. 反証レビュー

- 実装を落とす観点で見つけた問題: 旧形式 `contrast` が文字列だけの場合、以前は `undefined.trim` 相当で画面を落とす余地があった。
- 対応: 関係抽出時に文字列labelのみ採用し、現行 `{with}` と旧 `{with_}` を受ける。表示対象でない値は無視する。
- P0候補: 部分データで Explore が空白化するリスク。対応済み。
- 証跡不足: 実ユーザーテスト、スクリーンリーダー実機確認は未実施。
- 残リスク: 正当な旧 `contrast` 文字列に見出し語が含まれていても自動復元しない。見出し語として確定できないため、誤作成防止を優先した。

## 13. 指摘一覧

| 優先度 | 箇所 | 問題 | 影響 | 修正案 | 状態 |
|---|---|---|---|---|---|
| P0 | Explore relation extraction | 部分/旧形式 detail で例外化する余地 | Explore が空白化し探索を継続できない | 文字列labelだけ採用し、不正値を無視する | 対応済 |

## 14. 証跡

- スクリーンショット:
  - `docs/ai-governance/evidence/2026-06-21-requirements-design-hardening/after-explore-desktop.png`
  - `docs/ai-governance/evidence/2026-06-21-requirements-design-hardening/after-explore-malformed-desktop.png`
  - `docs/ai-governance/evidence/2026-06-21-requirements-design-hardening/after-explore-mobile.png`
- ImageGen:
  - `docs/ai-governance/evidence/2026-06-21-requirements-design-hardening/imagegen-lexicon-acceptance-mock.png`
  - `docs/ai-governance/evidence/2026-06-21-requirements-design-hardening/imagegen-explore-acceptance-mock.png`
- テスト結果:
  - `npm test -- ExplorePage/exploreRelations.test.ts ExplorePage/ExplorePage.test.tsx`: pass, 7 tests.
  - `npx tsc -p tsconfig.json`: pass.
  - `npm test -- --coverage --silent`: pass, 163 passed, 1 skipped.
  - `npx playwright test -c tests/e2e/playwright.config.ts tests/e2e/auth.spec.ts tests/e2e/guest.spec.ts tests/e2e/wordpack.spec.ts`: pass, 6 tests.
- 手動確認:
  - 改修前 screenshot 取得後に ImageGen mock を生成。
  - 実装後 screenshot を desktop / malformed detail / mobile で目視確認。
- 取得できなかった証跡と理由:
  - 実ユーザーテスト: 今回は実施環境と被験者がないため未実施。
  - 実スクリーンリーダー確認: ローカル自動検査と構造確認に限定。

## 15. 実行した検証

- [x] typecheck
- [x] unit test
- [x] frontend coverage
- [x] Playwright smoke
- [x] screenshot
- [x] accessibility check
- [x] keyboard/focus構造確認
- [x] responsive check
- [x] visual review
- [x] 公開セキュリティチェックリスト確認

## 16. 実行していない検証

| 未実行検証 | 理由 | 残リスク | 後続対応 |
|---|---|---|---|
| Backend full pytest | 変更は frontend の relation extraction と UI/UX証跡のみ | backend 契約自体の回帰は今回直接確認していない | backend 変更時に実行 |
| 実ユーザーテスト | 現行セッションで実ユーザー検証環境がない | 迷いや満足感はAIレビュー止まり | 必要なら受領前UATで確認 |
| 実スクリーンリーダー | ローカル自動検査と構造確認に限定 | 読み上げ順の実機差 | a11y監査時に追加 |
