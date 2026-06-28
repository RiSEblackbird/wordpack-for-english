# Quiz Article translation highlights UI/UX review 2026-06-28

## 1. 概要

- 対象PR / 作業: Issue #496 Quiz Article の訳文段落、文対応ハイライト、解説詳細化
- 変更した画面・コンポーネント: `/quiz`、選択中Quiz詳細、Article本文、日本語訳、採点後解説、Quiz生成プロンプト
- 判定: Pass
- P0件数: 0
- P1件数: 0
- P2件数: 0（未解決なし。PR reviewで見つかったP2 4件は追加修正済み）

## 2. ユーザー価値

- 対象ユーザー: 保存済みQuizで英文を読み、日本語訳と解説で復習する英語学習者。
- 利用文脈: Article形式の長文読解後、訳文を開いて原文との対応を確認し、採点後に根拠と誤答理由を読み返す場面。
- ユーザー目的: 英文のどの文がどの訳に対応しているかを迷わず確認し、なぜ正解/不正解なのかを本文根拠から理解する。
- 支援するタスク: 訳文確認、文単位対応確認、採点後の根拠確認、誤答復習。
- このUIが助ける理解・判断・行動: 英文と訳文の対応を同じハイライトで示し、復習時の視線移動と推測を減らす。解説生成契約は短すぎる根拠/解説/誤答理由を避ける。
- このUIがなければ困る点: 日本語訳が長い1段落に潰れると、英文の段落・文構造と照合しにくい。短い誤答理由だけでは、選択肢のどこが本文とズレたのか判断しにくい。
- 削るべき情報・操作: 新しい説明文や常時表示のヘルプは追加していない。既存の「日本語訳」展開操作内に収めた。
- 検証仮説・成功指標: 訳文展開後、英文/訳文どちらからでも同じ文ペアを hover / click / focus で確認でき、狭幅や文字拡大でも横 overflow しない。

## 3. 初見理解

- 何の画面か分かるか: `Quiz` 見出し、選択中Quizタイトル、Articleカードで長文読解画面だと分かる。
- 今どこか分かるか: 選択中Quiz詳細内のタイトル、本文カード、Section見出し、採点サマリで対象が分かる。
- 何ができるか分かるか: 本文を読む、音声を聞く、日本語訳を開く、選択肢を選んで採点する、解説を確認する。
- 最初の有意味な行動: 保存済みQuizを選ぶ、または表示中Quizの本文を読み、必要に応じて日本語訳を開く。
- 操作結果を予測できるか: `日本語訳` summary は訳文展開、`採点する` はスコアと解説表示、文 click は対応ハイライト固定として機能する。
- 失敗時に戻れるか: detailsを閉じるとハイライト状態は解除される。既存の3カラム復帰、一覧再選択、エラー表示は維持。

## 4. state matrix

| 状態 | ユーザーが見るもの | ユーザーが理解できること | 次にできる行動 | 回復手段 | a11y通知/構造 | 証跡 | 判定 |
|---|---|---|---|---|---|---|---|
| 通常 | Article英文、WordPack inline操作、日本語訳summary、Section設問 | 本文を読み、訳文や設問へ進める | 訳文展開、選択肢回答、採点 | detailsを閉じる、別Quiz選択 | 詳細領域は `aria-label="選択中Quiz詳細"` | Vitest / Playwright | Pass |
| 読み込み中 | 既存の「Quiz詳細を読み込み中です。」 | 詳細ロード中 | 完了待ち | 一覧更新 | 既存構造維持 | 既存実装維持 | Pass |
| 空 | 既存の「Quizを選択してください。」または保存済みなし | 表示対象がない | Quiz選択または生成 | 更新、生成 | 既存空状態文言 | 既存実装維持 | Pass |
| 検索結果なし | Quiz画面に検索UIなし | N/A | N/A | N/A | N/A | 対象外 | Pass |
| 部分データ | `body_ja` がなければ日本語訳summaryなし | 訳文がないQuizだと分かる | 英文のみで回答 | 別Quiz選択 | 不存在を空訳として偽装しない | 実装確認 | Pass |
| エラー | 既存の alert message | 一覧/詳細/採点の失敗 | 再試行または別操作 | 更新、再選択 | `role="alert"` | 既存実装維持 | Pass |
| 入力エラー | 生成フォームの「含める WordPack または lemma...」 | 生成条件不足 | WordPack/lemma入力 | 入力修正 | 既存文言 | 既存実装維持 | Pass |
| 無効 | 採点後の採点ボタン無効、生成条件不足時の生成ボタン無効 | 現在押せないこと | 復習または入力修正 | 別Quiz選択 | disabled button | 既存実装維持 | Pass |
| 権限不足 | ゲスト note / GuestLock | 保存系操作はログイン必要 | 読む、ローカル採点 | ログイン | 操作不可ボタンは既存GuestLock | Playwright guest scenario | Pass |
| オフライン/利用不可 | fetch失敗時の既存 alert | 読み込み/保存できない | 再試行 | 更新 | `role="alert"` | 既存実装維持 | Pass |
| 狭幅 | 390pxで詳細集中表示、横overflowなし | モバイル幅でも読める | 縦スクロールで読む | 3カラム復帰 | 通常DOM順 | Playwright viewport 390px | Pass |
| 文字拡大 | root font-size 20pxで横overflowなし | 文字拡大でも本文/訳文が折り返す | 読む、訳文展開 | 縦スクロール | focus-visible維持 | Playwright scaled overflow check | Pass |
| 長文・大量データ | 段落をgrid gapで分け、文は `overflow-wrap:anywhere` | 長文訳も段落単位で追える | 対応文をhover/click/focus | detailsを閉じる | focus可能な文group | Vitest paragraph/highlight test | Pass |

## 5. アクセシビリティ確認

- キーボード: 対応文は訳文展開中のみ `tabIndex=0` の group とし、focusで対応文が強調される。Enter/Spaceで固定できる。
- フォーカス: `.quiz-sentence:focus-visible` を追加。既存のinline WordPack button focusも維持。WordPack button操作は文固定ハイライトへ伝播しない。
- 名前・ラベル: 英文は `英文 N: 日本語訳と対応`、訳文は `日本語訳 N: 英文と対応` の accessible name。
- 見出し・構造: Articleカード、details summary、Section/Question構造は既存を維持。
- コントラスト: active/pinned は背景と枠線を併用し、色だけに依存しない。
- ターゲットサイズ: 文全体が対象で、語ボタンの既存targetも維持。
- エラー・ステータス: 新規エラー状態なし。既存alert/statusを変更していない。
- 自動検査: Playwright E2E内の axe check を訳文展開/ハイライト後に実行。
- 手動確認: Playwrightで hover、click、狭幅、文字拡大、3カラム復帰を確認。

## 6. 視覚階層

- 主操作: 既存の `日本語訳` summary と `採点する` を維持。新規の常時表示操作は増やしていない。
- 情報優先度: 英文本文を主、訳文は折りたたみ内、対応ハイライトは必要時だけ表示。
- グルーピング: 英文段落と訳文段落を同じ数に再構成できる場合は対応させる。
- 余白・密度: 段落間にgrid gapを入れ、訳文も同じ読み取りリズムにした。
- 読みやすさ: 長文は `overflow-wrap:anywhere` と行高を維持。
- 狭幅・文字拡大: Playwrightで横 overflow なしを確認。

## 7. コピー

- 用語: 既存の `Quiz`、`Article`、`日本語訳`、`根拠`、`日本語解説`、`誤答理由` を維持。
- ボタン・リンク: 新規ボタン文言なし。文対応は文そのもののhover/click/focusで表現。
- エラー文: 新規エラーなし。
- 空状態: 既存空状態を維持。
- disabled: 既存disabled表示を維持。
- トーン: 生成プロンプトは学習者向けに丁寧な解説を要求し、UIコピーはユーザーを責めない。

## 8. 熟練者効率

- 主要反復タスク: Quizを選び、本文を読み、訳文を開き、設問に答え、解説を確認する。
- 手数: 訳文展開は従来と同じ1操作。文対応は hover だけでも確認可能で、click固定もできる。
- 再入力・再選択: Quiz選択、回答、集中表示状態の既存保持を壊していない。文対応の展開/固定状態はQuiz単位で分離し、別Quizへ切り替えた時に前の状態を引き継がない。
- 近道: keyboard focusとEnter/Space固定に対応。
- 初心者向け説明の影響: 追加説明を常時表示していないため、熟練者の読み進めを妨げない。
- 判定: Pass

## 9. 満足感・信頼感

- 待機中: 既存の読み込み状態を維持。
- 成功時: 採点後のスコアと解説表示を維持。
- 失敗時: 既存alertで失敗を通知。
- 危険操作: 今回の変更に危険操作はない。削除/公開操作は既存導線を変更していない。
- データ・権限・個人情報: 新規送信データなし。文対応は保存済みQuiz本文/訳文のクライアント表示のみ。
- トーン: 解説は丁寧に、誤答理由は不正解の選択肢だけを具体的に説明する生成契約へ更新。正答理由を誤答理由欄へ混ぜない。
- 判定: Pass

## 10. 反証レビュー

- 実装を落とす観点で見つけた問題: 旧データで英文/訳文の文数が完全一致しない場合、対応は同じ順序の範囲までになる。誤対応を避けるため、訳文段落の再構成は全文の文数が一致する時に限定した。
- PR reviewで追加確認した問題: inline WordPack button clickが文固定に伝播する可能性、同じpassage idを持つ別Quizへの状態混入、正答理由が誤答理由欄へ混ざる生成契約、`API v2.0` のようなピリオドを含む英文分割の誤りを確認し、すべて修正した。
- 文分割の残リスク: 英文は `Intl.Segmenter` を優先し、未対応環境だけ既存regex fallbackを使う。fallback環境では一部の略語や特殊表記で分割精度が落ちる可能性が残る。
- P0候補: keyboardで対応確認できない問題は focus/Enter/Space対応で解消。色だけ依存は枠線併用で回避。狭幅/文字拡大 overflow はE2Eで確認。
- 証跡不足: 実ユーザーテストは未実施。AI/自動検証での確認に留まる。
- 残リスク: LLM生成が文数対応を崩す場合、UIは順序ベースで可能な範囲だけ対応する。プロンプトで同じ段落・文順を要求したが、生成品質はLLM依存。

## 11. 指摘一覧

| 優先度 | 箇所 | 問題 | 影響 | 修正案 | 状態 |
|---|---|---|---|---|---|
| P0 | Quiz訳文 | 旧表示では訳文が長い1段落になり、英文段落と対応しにくい | 原文/訳文照合に時間がかかる | 英文段落の文数に合わせて訳文段落を再構成 | 対応済 |
| P0 | Quiz訳文 | 文単位の原文/訳文対応が見えない | どの訳がどの英文に対応するか推測が必要 | hover/click/focusで同じ文ペアをハイライト | 対応済 |
| P1 | Quiz解説生成 | 根拠/解説/誤答理由が短すぎる | 復習時に判断根拠が不足する | 生成プロンプトで具体量と内容要件を追加 | 対応済 |
| P2 | inline WordPack操作 | WordPack buttonクリックが親文の固定ハイライトも切り替える可能性 | 語の確認中に意図しない文固定が残る | interactive child clickを文固定から除外し、button/popoverで伝播を止める | 対応済 |
| P2 | Quiz切替 | 同じpassage idの別Quizで展開/固定状態が残る可能性 | 別Quizの文対応を誤認する | Article component keyをQuiz id + passage idにする | 対応済 |
| P2 | 誤答理由 | 正答理由まで `wrong_choice_explanations_ja` に含める契約だった | UI上の「誤答理由」に正答説明が混じる | 不正解選択肢だけを含め、correct_choice_idを除外する契約へ修正 | 対応済 |
| P2 | 英文分割 | `API v2.0` などのピリオドで文が分割される可能性 | 対応ハイライトが文単位でずれる | 英文は `Intl.Segmenter` を優先し、回帰テストに小数点表記を追加 | 対応済 |

## 12. 証跡

- スクリーンショット: 成功時trace内にDOM snapshotを取得。スクリーンショット単体は未コミット。
- トレース: `test-results/guest-ゲストモード-Quiz本文と問題を全幅表示へ切り替えられる/trace.zip`
- テスト結果:
  - `cd apps/frontend && npm test -- QuizPage.test.tsx`: 5 passed
  - `cd apps/frontend && npx tsc -p tsconfig.json`: passed
  - `cd apps/frontend && npm test -- --coverage --silent`: 39 files passed / 1 skipped, 175 passed / 1 skipped, coverage 87.39%
  - `PYTHONPATH=apps/backend pytest -q --no-cov tests/backend/test_quiz_models.py tests/backend/test_quiz_flow.py tests/backend/test_quiz_api.py tests/backend/test_quiz_generation_jobs.py tests/backend/test_quiz_prompt_policy.py`: 14 passed
  - `npx playwright test -c tests/e2e/playwright.config.ts tests/e2e/guest.spec.ts -g "Quiz本文と問題を全幅表示へ切り替えられる" --trace on`: 1 passed
  - PR review対応後の再確認: `cd apps/frontend && npm test -- QuizPage.test.tsx`: 5 passed
  - PR review対応後の再確認: `PYTHONPATH=apps/backend pytest -q --no-cov tests/backend/test_quiz_prompt_policy.py`: 1 passed
  - PR review対応後の再確認: `cd apps/frontend && npx tsc -p tsconfig.json`: passed
  - PR review対応後の再確認: `npx playwright test -c tests/e2e/playwright.config.ts tests/e2e/guest.spec.ts -g "Quiz本文と問題を全幅表示へ切り替えられる" --trace on`: 1 passed
- 手動確認: Playwright上で訳文展開、英文hover、訳文click固定、3カラム集中表示、390px幅、root font-size 20pxの横overflowなしを確認。
- 取得できなかった証跡と理由: 実ユーザーテストは実施していない。生成LLMの実出力サンプルは外部API呼び出しを避けたため未取得。

## 13. 実行した検証

- [x] typecheck
- [x] unit test
- [x] integration / e2e
- [x] accessibility check
- [x] keyboard check
- [x] responsive check
- [x] visual regression相当のtrace確認
- [x] その他: `git diff --check`、公開セキュリティチェックリスト目視

## 14. 実行していない検証

| 未実行検証 | 理由 | 残リスク | 後続対応 |
|---|---|---|---|
| 実ユーザーテスト | この変更範囲では自動/手動ブラウザ検証を優先 | 実利用時の対応発見性は未計測 | 必要なら学習セッション観察で確認 |
| 実LLM生成サンプル確認 | 外部API呼び出しを避け、プロンプト契約と既存Fake LLMテストで確認 | LLMが段落/文順ルールを破る可能性 | 生成結果の品質Issueが出たらサンプルで追検証 |
| backend全体pytestの完全成功 | ローカル環境でGoogle auth/session/proxy系22件が既存環境起因で失敗。Quiz関連14件は通過し、coverage閾値自体は到達 | CI環境で同じ auth 系が失敗する場合は別対応が必要 | PR CIで確認し、失敗時は該当ログを読んで切り分け |
