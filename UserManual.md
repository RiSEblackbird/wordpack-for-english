## WordPack for English ユーザー操作ガイド

本書は「一般ユーザー向け」と「開発者・運用者向け」を完全に分離した二部構成です。まずは Part A（一般ユーザー向け）をご覧ください。技術情報・API・環境構築は Part B に集約しています。

---

## Part A. 一般ユーザー向けガイド（IT/技術知識は不要）

### A-1. はじめに（想定読者）
- 英語学習者（日本語UIで簡単に使いたい方向け）

### A-2. はじめかた（最短）
- 必要なもの:
  - モダンブラウザ（Chrome/Edge/Safari/Firefox 最新）
  - Docker Desktop（推奨）
- 起動（まとめて開始）:
  ```bash
  # リポジトリのルートで
  docker compose up --build
  ```
  - 画面（フロントエンド）にアクセス: `http://127.0.0.1:${FRONTEND_PORT:-5173}`

### A-2-1. サインインとサインアウト
- 最初にアクセスすると Google アカウントのサインイン画面が表示されます。
- 設定の同期中でもログイン画面はそのまま表示され、画面右下に「バックエンド設定を同期中」の通知が出ます。同期完了で通知は消え、失敗時は同じ位置に再試行ボタン付き通知が表示されます。
- 「Googleでログイン」ボタンを押すとポップアップが開き、認証に成功すると自動的にアプリ本体へ遷移します。
- ログイン画面の **「Googleでログイン」ボタンの下** に「ゲスト閲覧モード」ボタンがあります。押すとログインしなくても画面を閲覧できます。
- ゲスト中は **画面右上に「ゲスト閲覧モード」バッジ** が表示され、いまは閲覧専用であることを示します。ヘッダー右側の「ログアウト」ボタンからゲスト閲覧を終了でき、ブラウザを再読み込みしてもログアウト前は同じ状態が復元されます。
- ゲスト閲覧モードでは **AIによる生成・再生成・削除**、**音声再生**、**保存や削除などの操作** は利用できません。該当ボタンは押せず、マウスを重ねると「ゲストモードではAI機能は使用できません」と表示されます。
- 見出し語/文章の入力欄、モデルやカテゴリの選択、一覧のチェックボックスや全選択/解除ボタンもゲスト中は無効化され、同じツールチップが表示されます。
- ゲスト閲覧で表示されるのは **「ゲスト公開」トグルを ON にした WordPack** と、公開対象にした Quiz のみです。WordPack単位で公開され、例文も同じ単位で表示されます。
- 例（ゲストでできる/できない）:
  - 正例: WordPack の一覧を開いて内容を読む。
  - 負例: 「削除」ボタンを押してデータを消そうとする（ゲストでは実行できません）。
- Google アカウントでメールアドレスの確認が済んでいない場合は 403 エラーになります。ID トークンの `email_verified` が `false` のまま送信されるため、Google アカウント管理画面からメールを確認して再度ログインしてください。
- 管理者が `ADMIN_EMAIL_ALLOWLIST` を設定している場合、許可リストに載っていないメールアドレスでログインしようとすると「403 Forbidden」と表示されます。別アカウントを利用するか、管理者に連絡してリストへ登録してもらってください。
- ログアウトしたい場合は画面右上の「ログアウト」ボタンを押すか、「設定」タブ最下部のログアウトボタンを押してください。押下するとバックエンドへ `/api/auth/logout` リクエストが送信され、サーバー側で HttpOnly の通常セッション Cookie とゲストセッション Cookie が失効します。まれにサーバー応答が得られない場合はクライアント側で Cookie を削除するフォールバックが働き、必ずサインイン画面へ戻ります。
- ブラウザにセッション Cookie が残っている間は、リロード後も自動的にログイン状態が復元されます。Cookie を削除した場合は再度サインインが必要です。Firebase Hosting を経由する本番環境では通常ログインとゲスト閲覧のどちらも `__session` へ同じ署名付きトークンをミラーするため、ユーザー操作は変わりません。
- ログイン時にローカルストレージへ保存されるのは表示用のユーザー情報（メールアドレスや表示名）のみであり、ID トークン自体はブラウザメモリ内に限定されます。HttpOnly なセッション Cookie が無効化されると保存済みユーザー情報も即座に破棄され、再サインインが求められます。

### A-3. 新機能（保存と辞書入口）
- 生成した WordPack は自動で保存されます
- Lexicon 画面の「保存済みWordPack」で表示・管理できます（プレビュー/生成/再生成/公開設定/削除）
  - 表示モードは「カード」「リスト（索引）」を切替可能。リストは画面幅が十分なとき2列で表示されます。
- 各WordPackカードには「開く」「音声」「語義」がまとまって表示され、例文未生成のカードには「生成」も表示されます。削除や個別の公開/非公開切替は右上のその他メニューから実行します。カードをクリックしてプレビューを開いた場合も、見出し語の右側から同じ音声再生が行えます。
- **ゲスト公開の設定**: 保存済みWordPackのカード右上にあるその他メニューから「公開にする」「非公開にする」を選びます。複数選択時は画面下部の選択バーからまとめて公開/非公開を切り替えられます。ON にするとゲスト閲覧一覧に表示され、OFF に戻すと非表示になります。

### A-4. 画面の見かた（共通）
- ヘッダー: デスクトップでは左サイドバーを常時表示し、画面上部には Lexicon の見出し、検索、作成ショートカットを優先して表示します。900px以下の狭い画面では画面左上端にハンバーガーボタンが出て、サイドバーを開閉できます。
- サイドバー: 「Lexicon / Reader / Examples / Explore / Shelves / Quiz / Settings」。十分な横幅では左側に固定表示され、ユーザー情報、GitHubリンク、ログアウトボタンも下部にまとまります。900px以下ではハンバーガーボタンを押すと左側から即座に表示され、閉じたいときはハンバーガーボタンを再度押すか、サイドバー外側の半透明な背景をタップ、または Esc キーで閉じられます。
  - ページリンクの直下に、選択中タブ専用の操作セクションが縦に並びます（設定タブのみ除外）。Lexicon の WordPack 生成は画面右側の「新しいWordPackを作成」に集約され、狭い画面では本文の下へ回り込みます。文章インポートの入力やAIモデル設定は該当タブの操作セクションで行います。
    - 共通セクションとして「音声コントロール」を常設し、音声再生スピード（0.5〜2.0倍、0.25刻み）と音量（ミュート/25%/50%/75%/100%/125%/150%/175%/200%/225%/250%/275%/300%）を即座に調整できます。ここでの設定変更はすぐに全ての音声ボタンへ反映されます。
- 初期表示: 「Lexicon」画面（メイン領域に保存済み一覧、右側に生成キューと新規作成フォーム）
- キーボード操作:
- Alt+1..8: 主要画面へ移動（1=Lexicon, 2=Settings, 3=Reader, 4=Lexicon互換, 5=Examples, 6=Explore, 7=Shelves, 8=Quiz）
  - `/`: 主要入力欄へフォーカス
- 通知表示: Lexicon / Reader / Examples / Explore / Shelves / Quiz / Settings / WordPack詳細の各画面では、右側または本文下へ回り込む「生成キュー」に進行中/完了した生成が残ります。進行中はスピナーと進捗バー、完了時はチェック付きの履歴として表示され、進行中/完了チケットが更新されると約2秒間、枠が青白く明滅します。WordPackを特定できる完了履歴はカード自体をクリックしてプレビューを開けます。必要に応じて履歴を消去できます。ページ移動/リロード後も表示は維持されます。生成/再生成/削除が完了すると保存済み一覧が自動で更新されます。
- エラー表示: 画面上部の帯、対象操作の近く、または生成キュー内の失敗履歴に原因と再試行の手がかりを表示します。

### A-5. 設定パネル
- 「設定」タブで次を切替できます
  - 発音を有効化（ON/OFF）
  - 辞書操作（未生成語クリックで即生成、tooltip delay、生成後に開く場所、既定の表示密度）
  - 再生成スコープ（全体/用例のみ/共起のみ）
  - カラーテーマ（ダーク/ライト）
  - ログアウトボタン … 現在のセッションを即座に破棄し、バックエンド側で Cookie を無効化したうえでログイン画面に戻ります

### A-6. Examples Corpus（横断ビュー）
- 「Examples」画面では、保存済みの例文をWordPack横断の用例コーパスとして一覧できます。
- 表示:
  - 表示モード: カード/リスト を切替可
  - 並び替え: 例文の作成日時 / WordPackの更新日時 / 単語名 / カテゴリ
  - 検索: 前方一致 / 後方一致 / 部分一致（原文 英文が対象）
  - 絞り込み: カテゴリ（Dev/CS/LLM/Business/Common）
- 操作:
  - 「訳一括表示」スイッチ: 現在の一覧で全ての訳文を同時に開く/閉じる（ONの間は各カードの「訳表示」ボタンが自動的に無効になります）
  - 「訳表示」ボタン: 原文の下に日本語訳を展開/畳む
  - 「文字起こしタイピングを開く」ボタン: 詳細モーダル内に入力フォームを表示し、原文を見ながらタイピング練習します。文字数差が10文字以内になると「文字起こしを記録」ボタンで保存でき、モーダルのボタン括弧内と一覧カード/リストにある `タイピング累計: n文字` バッジが即時で更新されます。
  - 各カード/行のチェックボックスで複数の例文を選択し、「選択した例文を削除」ボタンから一括削除できます。表示中の項目のみを全選択/解除するボタンも同じ行に配置しています。
- 「音声」ボタン: OpenAI gpt-4o-mini-tts で原文を音声再生します。サイドバーの「音声コントロール」で速度と音量を共有設定でき、詳細モーダルでは原文全体と日本語訳全体を個別に再生できます。
  - 項目クリック: 詳細モーダル（文ごとに対応した原文/日本語訳、解説）を表示
  - 詳細モーダル下部の「確認済みにする」「学習済みにする」ボタンで、例文ごとの確認回数/学習済み回数を記録できます（括弧内に現在値を表示し、押すと即座に更新されます）。


### A-7. Explore（つながり探索）
- 目的: 保存済みWordPackから、関連語・共起・対比・例文由来のつながりを見つけ、未登録の語を追加できます。
- 画面上部:
  - 検索欄「lemma や語義で検索」で探索元のWordPackを絞り込みます。
  - 「更新」で保存済みWordPackと候補の状態を再取得します。
  - 「ステータスの意味」では、候補が「保存済み」「空のWordPack」「未登録」のどれかを確認できます。
- 表示モード:
  - 「関連語」: 語義や同義・反義から見つかった候補を表示します。
  - 「共起」: よく一緒に使われる語を表示します。
  - 「対比」: 比較・対立関係のある語を表示します。
  - 「例文」: 例文中に出てくる関連語を表示します。
  - 「未登録のみ」: 対応するWordPackがまだない候補だけを表示します。
- 操作:
  - 左列「WordPackを選ぶ」から探索元を選ぶと、中央列に候補、右列に件数とクイックアクションが表示されます。
  - 候補が「保存済み」の場合は「プレビュー」でWordPack概要を開けます。
  - 候補が「空のWordPack」の場合は「開いて育てる」から詳細へ進めます。
  - 候補が「未登録」で、見出し語として扱える形式の場合は「WordPackを作成」で内容未生成のWordPackを保存し、作成後にプレビューを開きます。
  - 例文全文や表現パターンなど見出し語として保存できない候補は、作成ボタンが無効になり理由が表示されます。
  - ゲスト閲覧では未登録語の作成はできません。ログインすると追加できます。

### A-7-1. Quiz（長文読解クイズ）
- 目的: 保存済み WordPack や任意 lemma を、長文読解・4択設問・根拠解説・語彙復習へつなげます。
- 画面構成:
  - 左列: Quiz 生成フォーム。出題フォーマット、生成傾向、専門性の強さ、難易度、大問数、小問数、含める WordPack / lemma を指定します。
  - 中央列: 保存済み Quiz 一覧。タイトル、出題フォーマット、生成傾向、専門性、問題数、本文数、含まれる lemma を確認できます。
  - 右列: 選択中 Quiz の本文、設問、採点サマリ、解説を表示します。狭い画面では縦に並びます。
- 操作:
  - 「生成開始」で Quiz 生成ジョブを開始します。完了すると一覧が更新され、生成された Quiz が開きます。
  - 各設問の選択肢を選び、「採点する」を押すと正答数・正答率・各問の正誤・日本語解説・本文根拠・誤答理由が表示されます。
  - 本文中でハイライトされた語を押すと、保存済み WordPack をプレビューできます。未登録語は「空で作成」または「生成開始」から WordPack へ接続できます。
  - ゲスト閲覧では Quiz の閲覧とローカル採点のみ利用できます。生成、削除、Attempt 保存、WordPack 作成/生成は実行できません。

### A-8. Lexicon / WordPack パネル（辞書記事）
1) 「Lexicon」を選択
2) 右側の「新しいWordPackを作成」に見出し語を入力（例: `converge`）。**英数字・半角スペース・ハイフン・アポストロフィのみ、最大64文字**。条件を満たさない場合は入力欄の下に赤字で説明が表示され、「作成を開始」「WordPackのみ作成」は押せません（サーバーも 422 エラーで拒否します）。画面上部の「新しいWordPack」ボタンを押すと、この入力欄へ移動します。
   - 同じスペル（大文字小文字は区別しない）の WordPack を連続で生成・保存しても、小文字化したラベルをドキュメントIDにした Firestore 側の一意制約で重複作成は行われません。既存の WordPack に統合され、`normalized_label` の単一フィールドインデックス経由で即座に検索できます。
3) 必要に応じて同じパネル内の「モデル」、`reasoning.effort`、`text.verbosity` を選択
4) 「作成を開始」をクリック
5) 1画面に「発音/語義/語源/用例（英日ペア+解説）/共起/対比/インデックス/引用/確度/辞書カード要点」を表示

- 便利なボタン:
  - 「WordPackのみ作成」… 内容生成せず空のWordPackを保存（あとで再生成で中身追加）
- 「再生成」はバックグラウンドジョブとして実行され、どの主要画面でも同じ生成キューに進行状況が表示されます。完了すると自動で最新データを読み込み、途中でページを移動しても進行が途切れません。長時間（>60秒）かかる処理でもタイムアウトしにくい設計です。
- 学習記録ボタン:
  - プレビュー内の「学習記録」セクションにある「確認済みにする」「学習済みにする」ボタンで、保存済みWordPackの確認回数/学習済み回数を記録できます。
  - 「学習済みにする」を押すと確認・学習の両方が1件ずつ加算され、保存済みWordPack一覧に表示される進捗バッジへ即座に反映されます。
- 例文表示:
  - カテゴリ例: Dev/CS/LLM/Business/Common（必要数が足りない場合は空欄のまま）
  - 各例文は「英 / 訳 / 解説」をカード型で表示し、詳細モーダルでは原文と日本語訳を文ごとの対応行で確認できます。
  - 各例文カードの「削除」ボタンを押すと画面中央に「削除確認」ダイアログが開き、対象と「実行後はこの画面から取り消せません」という注意を確認してから「削除する」または「キャンセル」を選択できます。
  - 各カード下部の「音声」ボタンで原文をその場で再生（OpenAI gpt-4o-mini-tts を使用）
  - 長い解説は「要点」「構文」を分けて表示し、品詞分解は「品詞分解を表示」から必要な時だけ展開できます。
  - 英語行にマウスを重ねると保存済みWordPackを検索してキャッシュを温めます。キャッシュ済みの語句をクリック、またはフォーカスして Enter / Space を押すと右下に「WordPack概要」ウインドウが開き、語義タイトル・主要語義（上位3件）・カテゴリ別例文数・学習カード要約・信頼度を確認できます。
- 対応する語義が登録されていない単語に触れた場合は、ツールチップが「未生成」となり、下線付き表示になります。ログイン中で、候補が見出し語の入力条件を満たす場合のみ、クリックするとその場でWordPack生成が始まり、完了と同時に「WordPack概要」ウインドウが開いて内容を確認できます。ゲスト閲覧や見出し語として扱えない候補では、生成せず理由が表示されます。
    - ウインドウ右上の「最小化」でブラウザ右端のトレイに畳めます。トレイに表示されるボタンを押すと元の位置に復元されます。
    - 左右のエッジをドラッグするとウインドウ幅を調整できます。表示順はモーダルより低い `z-index` で制御され、既存のポップアップと干渉しません。
- 語義表示（各 sense 単位）:
  - 見出し語義/定義/ニュアンス/典型パターン/類義・反義/レジスター/注意点

- セルフチェック: 「学習カード要点」は3秒のぼかし後に表示されます。表示ボタンはクリック、Enter、Spaceで即解除できます。プレビューモーダルでは反復確認を妨げないよう最初から表示されます。

- 保存済みWordPack一覧（同ページ下部）:
  - 一覧の上には「最近開いたWordPack」が表示され、直近で更新された辞書記事へすぐ戻れます。
  - 画面上部の検索欄で保存済みWordPackを部分一致検索できます。`⌘ K` / `Ctrl+K` でも検索欄へ移動できます。
  - 「すべて」「公開中」「非公開」「生成済み」「未生成」のチップで状態をすばやく絞り込めます。
  - 生成済みの WordPack をカード形式で一覧表示
  - 画面幅が狭い場合は、最近開いたWordPackが横に送れる小さな一覧になり、一覧ヘッダー（見出し、更新、表示切替、件数）が縦に収まる形で表示されます。
  - カードの「開く」ボタン、カードクリック、またはリスト表示の「開く」ボタンで大きめのモーダルプレビューを開けます。
    - データ読み込み中も一覧から取得した見出し語を `.wp-modal-lemma strong` で表示し、同じ語を入力欄に表示したプレースホルダーを併
      置して読み込み状態を明示します。
    - 読み込みに失敗した場合は、対象WordPack、原因メッセージ、再試行、プレビューを閉じる操作が同じモーダル内に表示されます。
  - 「語義一括表示」スイッチで、一覧内の語義タイトルを一括で表示/非表示（ONの間は各カード/リストの「語義」ボタンが自動的に無効になります）
- 「語義」ボタンで語義タイトルを表示/非表示に切り替え（カード表示では見出し語の下に表示されます）。カードの操作列には「開く」「音声」「語義」が並び、未生成カードでは「生成」も表示されます。削除、個別の公開/非公開切替、未生成カードの生成は右上のその他メニューからも実行できます。
  - 「音声」ボタンで見出し語（WordPackの語彙）を再生できます（カード表示/リスト表示とも同じボタンが並び、プレビューモーダルでも見出し語の右側から再生できます）
  - 例文未生成のWordPackには「生成」ボタンが表示され、押すとその場で例文生成を開始できます（処理内容は「再生成」ボタンと同じで、生成完了後は自動で一覧が最新化されます）
  - カード左上のチェックボックスで複数のWordPackを選択すると選択バーが表示され、表示中の全選択/解除、公開/非公開の一括切替、削除ができます。
  - 不要ならその他メニューまたは選択バーの「削除」で削除します。削除を押すと画面中央に「削除確認」ダイアログが開き、対象と取り消し不可の注意を確認してから「削除する」または「キャンセル」を選びます。
  - 各カードとリストには `使える {学習済み回数}` `確認済み {確認のみ回数}` バッジが表示されます。WordPackプレビューの学習記録ボタンで更新すると即座に値が反映されます。
  - 多い場合は画面下部のページネーションで移動（現在件数/総件数を表示）


### A-10. 使い方の流れ（例）
1) 設定で発音・再生成スコープなどを調整
2) WordPack を生成・保存

### A-13. 文章インポートの詳細モーダル（共通UI）
- 文章の詳細は共通モーダル `ArticleDetailModal` で表示します。
- 表示内容: 英語タイトル / 英語本文 / 日本語訳 / 解説（日本語訳の直下に表示） / 生成開始・完了の時刻（作成/更新欄に表示） / バックエンドで計測した生成所要時間 / 生成カテゴリ / AIモデル・パラメータ / 関連WordPack
- 英語タイトルの右側にある「音声」ボタンで英語本文（例文部分を含む全文）をOpenAI gpt-4o-mini-ttsで再生できます。生成モデルやAIパラメータなどの補助情報は「生成・管理情報」から確認できます。
- 関連WordPack一覧の直前には、生成開始時刻（作成欄）・生成完了時刻（更新欄）・計測済みの生成所要時間・生成カテゴリ・AIモデル/パラメータを2列レイアウトでまとめたメタ情報が表示されます（未記録の項目は「未記録」「未指定」などの表示になります）。
- インポート画面のカテゴリ選択（Dev/CS/LLM/Business/Common）は、そのまま `生成カテゴリ` として保存・表示されます。未選択はありません（初期値は `Common`）。
- 関連WordPackは常にカード表示で統一されています。
- 「文章インポート」直後のモーダルではカード上で「生成」ボタンと `WordPack「語彙」をプレビュー` ボタンが利用できます。WordPackプレビューは同じ文章詳細モーダル内の詳細ペインとして表示され、閉じても文章詳細は保持されます。
- 文章の貼り付け欄の直下に「文章をインポート」ボタン、カテゴリ選択の直下に「例文を生成して記事化」ボタンが表示されます。前者は貼り付けた文章を保存し、後者はカテゴリから例文を自動生成して記事化します。
- WordPackカードの「削除」ボタンを押すと画面中央に「削除確認」ダイアログが開き、対象と取り消し不可の注意を確認してから「削除する」または「キャンセル」を選びます。
- 「インポート済み文章」から開くプレビューでも関連WordPackの生成・削除・`WordPack「語彙」をプレビュー` が利用できます。
- インポート済み文章の一覧では、カード左上のチェックボックスで複数の記事を選択し、「選択した文章を削除」ボタンから一括削除できます。表示中のカードのみをまとめて選択/解除するボタンも同じ行にあります。

### A-11. 制約・既知の事項（ユーザー向け）
- UI文言は今後統一予定
- Firestore（エミュレータ/クラウド）は WordPack と文章の保存専用です（復習スケジュール機能はありません）

### A-12. トラブルシュート（一般ユーザー向け）
- 表示が更新されない: ブラウザを更新、または一度アプリを停止して再起動
- ボタンを押しても進まない: 少し時間を置いて再試行（通信中はメッセージが表示されます）
- エラー帯が出た: 画面の指示に従って操作をやり直すか、必要に応じて管理者に連絡（画面右上などに表示されるリクエストIDがあれば併記）
- 「ID トークンを取得できませんでした。ブラウザを更新して再試行してください。」と表示された: いったんブラウザを再読み込みしてから再度ログインを試してください。何度試しても解消しない場合は、管理者に Google ログイン設定の確認を依頼してください（管理者側ではバックエンドのログに `google_login_missing_id_token` という診断メッセージが出力されています）。
- 「例文生成・記事化完了」と通知されたのに記事や WordPack が増えていない: 生成された2件の例文すべてが記事化に失敗した場合は生成キューの履歴がエラーに変わり、モーダルにも「例文を記事化できませんでした（reason_code=CATEGORY_IMPORT_FAILED_ALL）」という内容が表示されます。カテゴリ用に作成された WordPack の例文自体は保存済みなので、WordPackタブから該当語彙を開いて例文カードの「記事を作成」ボタンで個別に記事化するか、モデルや reasoning/text の設定を調整してから再度「例文を生成して記事化」を実行してください（片方だけ失敗した場合は 1 件だけ記事が追加され、通知には「一部失敗」と記録されます）。
- 「セッションの有効期限が切れました。もう一度ログインしてください。」と表示された: ログインから一定時間が経過したか、ブラウザ設定によりログイン情報が破棄されています。右上のログインボタンから再度 Google アカウントでサインインすると、WordPack やインポート済み文章の一覧が再び表示されます。

### A-14. 保存済みWordPack一覧の使い方（索引リスト表示）
- 右上の表示切替で「リスト」を選ぶと、単語帳の索引のようにテキストで一覧表示されます。
- 画面幅に余裕がある場合は2列で表示され、縦スクロールで多数の項目を素早く確認できます。
- ページサイズは既定で200件です（ページ下部のページネーションで移動）。
  - 各項目にはカテゴリ別の例文件数が表示されます。例文未生成の場合は「例文未生成」と表示されます。
  - 「語義一括表示」スイッチで全項目の語義タイトルをまとめて展開し、OFFに戻すと非表示にできます。
  - 各項目の右側に「語義」「音声」ボタンが並び、語義タイトルを同じ行で確認した上で語彙（見出し語）を再生できます。
  - 例文未生成の項目には「生成」ボタンも表示され、その場で例文生成を開始できます（生成完了後は自動で一覧を再読込します）。
  - チェックボックスで項目を選択すると操作バーが表示され、表示中のWordPackを一括選択/解除したり、選択済みの項目をまとめて公開/非公開または削除できます。

---

## Part B. 開発者・運用者向けガイド（技術情報）

本パートは開発・運用に必要な情報のみをまとめています。一般ユーザーは読む必要はありません。

#### 開発時の自動ルール（MDC）
`.cursor/rules/*.mdc` に常時適用（alwaysApply: true）の実務ルールを定義しています。
- 推論様式: `base-reasoning-and-communication.mdc`
- コーディング原則: `base-coding-principles.mdc`
- 品質ゲート/テスト基本: `base-quality-gates.mdc`
- フロントエンド検証: `frontend-testing.mdc`
- バックエンド検証: `backend-testing.mdc`
- 改修/変更管理: `maintenance-and-change-management.mdc`
- ドキュメント作成: `docs-authoring.mdc`

### B-1. ローカル実行（開発用）
- 必要環境: Python 3.13+（venv 推奨）, Node.js 20.19.0+
- 依存インストール:
  ```bash
  # Python
  python3 -m venv .venv
  # macOS / Linux
  source .venv/bin/activate
  # Windows PowerShell
  # .venv\Scripts\Activate.ps1
  # Windows (Git Bash)
  # source .venv/Scripts/activate
  python -m pip install -r requirements.txt

  # Frontend
  cd apps/frontend
  npm install
  ```
- サービス起動（別ターミナル）:
  ```bash
  # Backend（リポジトリルートで）
  # .env に OPENAI_API_KEY を設定
  # Google ログインを使う場合は GOOGLE_CLIENT_ID / SESSION_SECRET_KEY / ADMIN_EMAIL_ALLOWLIST を必要に応じて設定
  python -m uvicorn backend.main:app --reload --app-dir apps/backend

  # Frontend
  cd apps/frontend
  npm run dev
  ```
- ヒント（APIキー/出力）:
- `.env` に `OPENAI_API_KEY` と `GOOGLE_CLIENT_ID`、必要であれば `GOOGLE_ALLOWED_HD` や `ADMIN_EMAIL_ALLOWLIST`
  - `.env` の `SESSION_SECRET_KEY` は十分な長さの乱数を設定
  - テスト/CI はモックのため不要
  - 本番は `STRICT_MODE=true` 推奨（開発では `false` 可）
- 途中切れ対策に `LLM_MAX_TOKENS` を 1200–1800（推奨1500）
- セキュリティヘッダ (`SecurityHeadersMiddleware`) の調整
  - HTTPS 運用で HSTS の寿命を変えたい場合は `SECURITY_HSTS_MAX_AGE_SECONDS` を設定し、サブドメイン除外時は `SECURITY_HSTS_INCLUDE_SUBDOMAINS=false`
  - `SECURITY_CSP_DEFAULT_SRC` と `SECURITY_CSP_CONNECT_SRC` にカンマ区切りで CSP オリジンを記述（`'self'` を含めたい場合は引用符ごと入力）
  - Swagger UI など外部 CDN が必要な場合は `https://cdn.jsdelivr.net` などをリストへ追加する
- フロントエンド（`apps/frontend`）では `.env` を `apps/frontend/.env.example` からコピーしてください。リポジトリ直下で `npm run prepare:frontend-env` を実行すると、テンプレートが存在する場合のみ `.env` が自動作成され、既存ファイルは上書きされません。`VITE_GOOGLE_CLIENT_ID` をバックエンドの `GOOGLE_CLIENT_ID` と合わせ、`SESSION_COOKIE_NAME` をカスタマイズした場合のみ `VITE_SESSION_COOKIE_NAME` も更新してください（未設定でも `wp_session` / `__session` の双方をクリアします）。
- データベースは全環境で Firestore 固定です。ローカル/CI はエミュレータへ接続してください。**Docker Compose では `FIRESTORE_EMULATOR_HOST=firestore-emulator:8080`、ホスト直起動/WSL では `FIRESTORE_EMULATOR_HOST=127.0.0.1:8080`** を指定します。Cloud Firestore を使う場合のみエミュレータ設定を外して `FIRESTORE_PROJECT_ID` とサービスアカウントを指定してください。`ENVIRONMENT` は allowlist 必須化やセキュリティ既定値の切り替えにのみ使われ、データベース種別は切り替わりません。Firestore エミュレータは Java 21+ が必要なため、環境に無い場合は `scripts/start_firestore_emulator.sh` が Adoptium API から tarball を取得して Temurin 21 を導入します（HTTPS が遮断される環境では事前に Java 21 を用意してください）。

### B-1-1. Google OAuth クライアントの作成手順
1. [Google Cloud Console](https://console.cloud.google.com/) を開き、対象プロジェクトを作成または選択します。
2. 左メニューの「API とサービス」→「OAuth 同意画面」を開き、ユーザータイプを選択したうえでアプリ名・サポートメール・承認済みドメイン（必要に応じて）などを登録して公開ステータスにします。
3. 「API とサービス」→「認証情報」で「認証情報を作成」→「OAuth クライアント ID」を選択し、アプリケーションの種類を「ウェブアプリケーション」に設定します。
4. 「承認済みの JavaScript 生成元」にローカル開発で利用する `http://127.0.0.1:5173` と `http://localhost:5173` を追加します。HTTPS のカスタムドメインを使う場合は同様に追加します。
5. 「承認済みのリダイレクト URI」にも `http://127.0.0.1:5173` と `http://localhost:5173` を登録します。Google Identity Services のポップアップを利用するため、オリジンを合わせておくと認証が安定します。
6. 発行されたクライアント ID を控え、JSON シークレットをダウンロードする場合は `google-oauth-client-secret.json` などの名前で安全な場所に保管してください（リポジトリ直下では `.gitignore` により除外されます）。
7. `.env` に `GOOGLE_CLIENT_ID=<取得したクライアントID>`、必要なら `GOOGLE_ALLOWED_HD=<許可ドメイン>` や `ADMIN_EMAIL_ALLOWLIST=<許可メールアドレス>` を記入し、`SESSION_SECRET_KEY=<十分な長さの乱数>` を設定します。フロントエンド側では `apps/frontend/.env` に `VITE_GOOGLE_CLIENT_ID=<同じクライアントID>` を指定してください。

> **メモ:** `.env` や `apps/frontend/.env` を作成したら、バックエンド/フロントエンドを起動する前に必ず環境変数を設定してください。起動後に追加した場合は、それぞれのプロセスを再起動して読み直す必要があります。

### B-1-2. フロントエンド統合テスト（実バックエンド接続）
- 目的: `POST /api/word/pack` の実HTTP呼び出しと UI 反映までをローカルで確認します。
- 前提: バックエンドを `DISABLE_SESSION_AUTH=true` で起動し、Firestore エミュレータと `OPENAI_API_KEY` を設定してください。
- 実行例:
  - 正例:
    ```bash
    cd apps/frontend
    INTEGRATION_TEST=true BACKEND_PROXY_TARGET=http://127.0.0.1:8000 npm run test
    ```
  - 負例（統合テストが skip される）:
    ```bash
    cd apps/frontend
    npm run test
    ```
- 詳細な前提条件は `docs/testing/frontend-integration-tests.md` を参照してください。

### B-1-3. Playwright による UI スモークテスト（CI）
- GitHub Actions の CI では、PR 向けに Playwright のスモークテストを実行し、主要な UI 動線の回帰を短時間で検知します。
- スモークの対象は `auth.spec.ts` / `guest.spec.ts` / `wordpack.spec.ts` の主要導線で、成果物は CI の Artifacts から取得できます。
- UI 修正後は、Vitest (`npm run test`) と Playwright スモークの結果を確認し、回帰がないことを確認してください。

### B-1-4. Playwright による E2E テスト（ローカル実行）
- 目的: フロントエンドとバックエンドの実起動をまとめて行い、主要導線の回帰を確認します。
- 実行例:
  - 正例:
    ```bash
    E2E_BASE_URL=http://127.0.0.1:5173 npm run e2e
    ```
  - 負例（webServer 設定を通さずに起動してしまう）:
    ```bash
    npx playwright test
    ```
- テスト成果物は `playwright-report/` と `test-results/` に保存されます。
- 性能計測の閾値は `E2E_ACTION_THRESHOLD_MS`（ミリ秒、既定 15000ms）で調整できます。
- 詳細は `docs/testing/playwright-e2e.md` を参照してください。

### B-1-5. バックエンド性能回帰チェック（p95）
- 目的: `/healthz` と WordPack 生成の p95 応答時間を測定し、回帰を早期に検知します。
- 実行例:
  - 正例:
    ```bash
    API_P95_THRESHOLD_MS=1500 PYTHONPATH=apps/backend pytest -q --no-cov tests/test_api_performance.py
    ```
  - 負例（閾値が厳しすぎると回帰が無くても落ちる）:
    ```bash
    API_P95_THRESHOLD_MS=10 PYTHONPATH=apps/backend pytest -q --no-cov tests/test_api_performance.py
    ```
- CI は `.github/workflows/perf-backend.yml` で週次実行し、本番前の手動実行にも使用します。
- 詳細は `docs/testing/backend-performance.md` を参照してください。

### B-1-6. Firestore インデックス同期フロー
- `firestore.indexes.json` に `word_packs` / `examples` 用の複合インデックスを定義済みです。Cloud Firestore / Firebase エミュレータ / Firebase CLI で同じファイルを読み込めるようにしてあり、Web コンソールでの手作業登録は不要です。
- 例文コレクションは `created_at` / `pack_updated_at` / `search_en` / `search_en_reversed` / `search_terms` を組み合わせたインデックスを持ち、`order_by` + `start_after` + `limit` によるページングで 1 リクエスト最大 50 件だけを読み出します。`search_en` は小文字化、`search_en_reversed` は逆順文字列、`search_terms` は 1〜3 文字の N-gram + トークン配列で、`prefix`/`suffix`/`contains` いずれの検索モードもサーバー側で絞り込みます。`offset` はカーソル計算専用で全件読み込みは行いません。
- 本番/検証へのデプロイ:
  ```bash
  make deploy-firestore-indexes PROJECT_ID=my-gcp-project
  # Firebase CLI を使いたい場合
  make deploy-firestore-indexes PROJECT_ID=my-firebase-project TOOL=firebase
  ```
  - 内部では `scripts/deploy_firestore_indexes.sh` が JSON を展開し、gcloud ルートでは各インデックスに対して `gcloud alpha firestore indexes composite create --field-config=...` を順次実行します（`ALREADY_EXISTS` はスキップ）。Firebase ルートでは `firebase deploy --only firestore:indexes --non-interactive` を呼び出します。
- ローカルでの適用確認:
  ```bash
  make firestore-emulator  # もしくは docker compose up firestore-emulator
  # 別ターミナルでバックエンド or テストを起動
  FIRESTORE_PROJECT_ID=wordpack-local FIRESTORE_EMULATOR_HOST=127.0.0.1:8080 pytest tests/backend/test_firestore_store.py
  # 開発用データを投入したい場合
  make seed-firestore-demo
  ```
  - エミュレータ起動時に `firestore.indexes.json` が自動で読み込まれます。`Ctrl+C` で停止し、必要に応じて `FIRESTORE_EMULATOR_HOST` を付与した API/テストを実行してください。`.data_demo/wordpack.sqlite3.demo` は Firestore シード用として使用し、SQLite への直接シードは行わない運用に統一しています。ゲスト用データは `word_packs.metadata.guest_demo=true` で識別し、既にゲスト用データが存在する場合はシードがスキップされます（再投入したい場合は `scripts/seed_firestore_demo.py --force` を使用）。

### B-10. オブザーバビリティ（Langfuse）
- `.env` に `LANGFUSE_ENABLED=true` と各キーを設定し、`requirements.txt` の `langfuse` を導入してください。
- 本アプリは Langfuse v3（OpenTelemetry）を使用します。
  - HTTP 親スパン: `input`（パス/メソッド/クエリ要点）と `output`（ステータス/ヘッダ要点）を属性で付与。
  - LLM スパン: `input`（モデル・プロンプト長など）/ `output`（生成テキストの先頭〜最大40000文字）を属性で付与。
  - v2 クライアント互換パスでは `update(input=..., output=...)` を使用。
- LLM プロンプト全文の記録（任意）:
  - 既定ではプレビューのみ（`prompt_preview`）。`.env` で `LANGFUSE_LOG_FULL_PROMPT=true` を設定すると、`input.prompt` に全文（最大 `LANGFUSE_PROMPT_MAX_CHARS`）と `prompt_sha256` を付与します。
  - 機微情報の観点から、本番では原則オフのまま運用してください。
- ダッシュボードで Input/Output が空の場合:
  1) `.env` のキー/ホスト設定を確認
  2) `LANGFUSE_ENABLED=true` か確認
  3) `apps/backend/backend/observability.py` の v3 分岐が有効（`set_attribute('input'|'output', ...)` 実行）であることを確認

### B-2. アーキテクチャと実装メモ
- エンドポイント統合は `/api/*` に統一
- LangGraph/OpenAI LLM 統合
  - `WordPackFlow`、`ReadingAssistFlow`、`FeedbackFlow` は OpenAI LLM を直接使用し、`citations`/`confidence`（Enum: low/medium/high）を付与
- 発音生成は `apps/backend/backend/pronunciation.py` に統一
  - cmudict/g2p-en 利用時は精度向上、未導入時は例外辞書+規則フォールバック（タイムアウト制御）

### B-3. API 一覧（現状）
- `POST /api/auth/guest` … 署名済みゲストセッション Cookie を発行し、閲覧専用モードを開始（Firebase Hosting 経由では `__session` にも同じトークンを配信）
- `POST /api/auth/logout` … 通常ログインまたはゲスト閲覧のセッション Cookie を失効させ、匿名状態へ戻す
- `POST /api/word/pack` … WordPack 生成（語義/共起/対比/例文/語源/学習カード要点/発音RP + `citations`/`confidence`、`pronunciation_enabled`,`regenerate_scope` 対応）
- `GET /api/word?lemma=...` … lemma から保存済み WordPack を検索し、定義と例文を返却（未保存なら 404。ゲストは未登録語で 403。生成は `POST /api/word/pack` を使用）
- 追加（保存済み WordPack 関連）:
  - `POST /api/word/packs/{id}/guest-public` … WordPack のゲスト公開フラグを更新（ログイン済みユーザーのみ）
  - `DELETE /api/word/packs/{id}/examples/{category}/{index}` … 例文の個別削除
- `POST /api/tts` … OpenAI gpt-4o-mini-tts を使い、`text`/`voice` を受け取って `audio/mpeg` ストリームを返却

#### B-3-1. ゲスト閲覧 API 例
- 正例（ゲスト Cookie を発行して閲覧 API を呼び出す）
```bash
curl -i -X POST http://127.0.0.1:8000/api/auth/guest
curl -i -H "Cookie: wp_guest=<signed-token>" "http://127.0.0.1:8000/api/word?lemma=example"
```
- 負例（ゲスト Cookie で書き込み系 API を呼ぶと 403）
```bash
curl -i -X POST \
  -H "Cookie: wp_guest=<signed-token>" \
  -H "Content-Type: application/json" \
  -d '{"lemma":"example"}' \
  http://127.0.0.1:8000/api/word/packs
```
- 負例（ゲストが未登録語を検索すると 403）
```bash
curl -i -H "Cookie: wp_guest=<signed-token>" "http://127.0.0.1:8000/api/word?lemma=unknown"
```

### B-4. 保存済み WordPack の内部構造（実装メモ）
- 例文は DB で別コレクションに正規化。部分読み込み/部分削除が高速
- API の入出力は `sense_title`（語義タイトル）と `examples` を含む完全な `WordPack`
- `word_packs` コレクションには `sense_title` フィールドを持ち、一覧表示用に語義タイトルを保持します
- `word_packs.metadata.guest_public=true` の WordPack はゲスト閲覧に表示されます（例文も同じ WordPack 単位で公開）

### B-4-1. WordPack プレビューのツールチップ
- 例文中で見出し語（lemma）がハイライトされます。
- 例文中の単語にマウスを重ねると、保存済みWordPackを検索して語義タイトルをツールチップ表示します。未生成の単語はツールチップが「未生成」となり、ログイン中で見出し語の入力条件を満たす場合にクリックするとWordPack生成が開始されます。ゲスト閲覧や見出し語として扱えない候補では生成せず、画面内に理由が表示されます。
- ハイライト部分にマウスカーソルを重ねて約0.5秒待つと、語義タイトル（`sense_title`）の小さなツールチップが表示されます。
- マウスカーソルを外すとツールチップは消えます。

### B-5. 運用・監視・品質
- `/metrics` で API パス別の p95・件数・エラー・タイムアウトを確認
- ログは `structlog` による JSON 形式。`request_complete` には UUID の `request_id`/
  `path`/`latency_ms`
- レート制限: 1分あたりの上限を IP と認証済みセッション（署名付き Cookie、追加ヘッダ不要）ごとに適用（超過は `429`）
- すべての応答に `X-Request-ID`。障害報告時に併記
- 例外監視（任意）: Sentry DSN 設定があれば重大エラー送信
- LLM 機能有効時でも内部スレッドは共有プールで制御（長時間運用でのスレッド増加なし）

#### B-5-1. Cloud Run への自動デプロイ
- `scripts/deploy_cloud_run.sh` が Cloud Build → Cloud Run Deploy を一括で実行します。最初に `cp env.deploy.example .env.deploy` でテンプレートを複製し、`PROJECT_ID` や `REGION`、ドメイン情報を本番値へ置き換えてください。`.env.deploy`（または `--env-file` で指定するファイル）に `ENVIRONMENT=production` と `ADMIN_EMAIL_ALLOWLIST` / `SESSION_SECRET_KEY` / `CORS_ALLOWED_ORIGINS` / `TRUSTED_PROXY_IPS` / `ALLOWED_HOSTS` を記載してください。開発と同じ許可メールだけがログインできるように、管理者メールアドレスは必ず列挙してください。`PROJECT_ID` / `REGION` を同じファイルに含めるとコマンド引数を短縮できます。`gcloud config set project <id>` と `gcloud config set run/region <region>`（run/region が無ければ `compute/region`）を事前に設定していれば、CLI 引数や env ファイルで空のままでもフォールバックで安全に補完され、採用された値はログで確認できます。
- 実行例:
  ```bash
  ./scripts/deploy_cloud_run.sh \
    --project-id my-prod-project \
    --region asia-northeast1 \
    --service wordpack-backend \
    --artifact-repo wordpack/backend \
    --generate-secret
  ```
  - `--generate-secret` は `SESSION_SECRET_KEY` が未設定のときに `openssl rand -base64 <length>` で安全な乱数を生成します。テンプレートをコピーしただけで未記入の場合でも、このオプションを付ければ安全な値が自動で補完されます。既存値を維持したい場合は `.env.deploy` にあらかじめ貼り付けておけば上書きされません。
  - `--dry-run` を付けると設定のロード（`python -m apps.backend.backend.config`）までを実行し、gcloud コマンドをスキップします。CI では `configs/cloud-run/ci.env` を入力にして dry-run を常時実行し、必須設定の欠落をブロックしています。
  - `--image-tag`（既定: `git rev-parse --short HEAD`）、`--build-arg KEY=VALUE`、`--machine-type`、`--timeout` などで Cloud Build のパラメータを細かく制御できます。`--artifact-repo` で Artifact Registry のリポジトリを差し替え可能です。
- `make deploy-cloud-run PROJECT_ID=... REGION=...` を利用すれば、Makefile から同じスクリプトを呼び出せます。`gcloud config` に既定プロジェクト/リージョンを設定済みなら、Make 実行時の `PROJECT_ID` / `REGION` 省略も可能です。GitHub Actions の `Cloud Run config guard` ジョブでも `scripts/deploy_cloud_run.sh --dry-run` を実行しており、`shellcheck` でスクリプトの静的解析も同ジョブで通過させます。ローカルでスクリプトを更新した場合は `shellcheck scripts/deploy_cloud_run.sh` を必ず実行してください。
- GitHub Actions の本番自動デプロイは **`deploy-production.yml` ワークフロー**が担当し、**main ブランチへの push** をトリガーに実行されます。`.env.deploy` はリポジトリへコミットせず、Actions 側で `CLOUD_RUN_ENV_FILE_BASE64`（base64 化した `.env.deploy`）から復元して利用します。手動実行用のフォールバックとして `workflow_dispatch` も併用します。CI 成功を必須にする場合は main ブランチの保護ルールで CI チェックを必須化してください。
  - 正例: main への push 後に `Deploy to production` ワークフローが起動し、同じ commit SHA を本番へデプロイします。
  - 負例: main への push を行わない限り `Deploy to production` ワークフローは起動しません。

##### release-cloud-run ターゲット（本番リリースの順序制御）

- `make release-cloud-run PROJECT_ID=... REGION=...` を使うと、Firestore インデックス同期 → Cloud Run dry-run → 本番デプロイの順序が保証されます。`.env.deploy`（または `ENV_FILE` で指定したファイル）の存在確認に失敗した場合はその場で停止します。
- 前提条件
  - Firestore Admin / Cloud Run Admin / Artifact Registry Writer 権限を持つサービスアカウントで `gcloud auth login` または `gcloud auth activate-service-account --key-file <json>` を実行し、`gcloud auth configure-docker` も済ませておく。
  - Make 実行時に `PROJECT_ID` / `REGION` を必ず指定する（gcloud 側の既定値に依存しない）。
  - `.env.deploy` などの env ファイルを用意し、`SESSION_SECRET_KEY`・`CORS_ALLOWED_ORIGINS`・`TRUSTED_PROXY_IPS`・`ALLOWED_HOSTS` を含める。CI 用には `ENV_FILE=configs/cloud-run/ci.env` のように分離可能。
- GitHub Actions での実行例:

  ```bash
  make release-cloud-run \
    PROJECT_ID=${{ env.GCP_PROJECT_ID }} \
    REGION=${{ env.GCP_REGION }} \
    ENV_FILE=configs/cloud-run/ci.env \
    SKIP_FIRESTORE_INDEX_SYNC=true
  ```

- 既に Firestore インデックスが同期済みの検証環境では `SKIP_FIRESTORE_INDEX_SYNC=true` を指定し、Cloud Run の dry-run + 本番デプロイのみを実行できます。Dry-run (`scripts/deploy_cloud_run.sh --dry-run`) はターゲット内部で必ず実行されるため、設定エラーは gcloud 実行前に検出されます。

##### GitHub Actions 本番デプロイ用シークレットの準備

GitHub Actions で本番自動デプロイ（`deploy-production.yml`）を利用するには、以下の3つのリポジトリシークレットが必要です。未設定の場合はワークフローがエラーで停止し、不足しているシークレット名がログに出力されます。

| シークレット名 | 説明 |
|--------------|------|
| `GCP_SA_PROJECT_ID` | 本番 GCP プロジェクト ID |
| `GCP_SA_KEY` | サービスアカウント JSON キー（全体） |
| `CLOUD_RUN_ENV_FILE_BASE64` | `.env.deploy` の base64 エンコード |

###### 1. GCP_SA_PROJECT_ID（本番プロジェクトID）

1. [GCP コンソール](https://console.cloud.google.com/) を開く
2. 左上のプロジェクトセレクターから本番用プロジェクトを選択
3. プロジェクト ID（例: `my-prod-project-123456`）をコピー
4. GitHub → リポジトリ → **Settings → Secrets and variables → Actions**
5. **New repository secret** をクリック
   - Name: `GCP_SA_PROJECT_ID`
   - Secret: コピーしたプロジェクト ID
6. **Add secret** をクリック

###### 2. GCP_SA_KEY（サービスアカウントキー JSON）

Cloud Run / Artifact Registry / Firestore へのデプロイ権限を持つサービスアカウントの JSON 鍵を登録します。

**サービスアカウント作成（未作成の場合）:**

```bash
PROJECT_ID="your-prod-project-id"

# サービスアカウント作成
gcloud iam service-accounts create github-actions-deploy \
  --project="${PROJECT_ID}" \
  --display-name="GitHub Actions Deploy"
```

**必要な権限を付与:**

```bash
SA_EMAIL="github-actions-deploy@${PROJECT_ID}.iam.gserviceaccount.com"

# Cloud Run 管理者
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/run.admin"

# Artifact Registry 書き込み
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/artifactregistry.writer"

# Cloud Build 編集者（イメージビルド用）
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/cloudbuild.builds.editor"

# Cloud Build のソースアップロード（gs://<PROJECT_ID>_cloudbuild へアップロードするため）
# ※ 推奨: プロジェクト全体ではなく対象バケットに対して付与する
gcloud storage buckets add-iam-policy-binding "gs://${PROJECT_ID}_cloudbuild" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/storage.objectAdmin"

# Firestore インデックス管理（インデックス同期用）
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/datastore.indexAdmin"

# Firestore API の有効化状態確認（Firebase CLI が事前にチェックするため）
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/serviceusage.serviceUsageViewer"

# Cloud Build のログ表示（CI が “ビルド中なのに失敗扱い” で止まるのを避ける）
# まず確実に通すなら Viewer（広いが切り分けが簡単）
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/viewer"

# サービスアカウントユーザー（Cloud Run がこの SA を使うため）
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/iam.serviceAccountUser"
```

**JSON 鍵を発行:**

```bash
gcloud iam service-accounts keys create ./gcp-deploy-key.json \
  --iam-account="${SA_EMAIL}"
```

> ⚠️ **注意**: このファイルは機密情報です。`.gitignore` に含まれていることを確認し、絶対にコミットしないでください。

**GitHub シークレットに登録:**

1. GitHub → リポジトリ → **Settings → Secrets and variables → Actions**
2. **New repository secret** をクリック
3. Name: `GCP_SA_KEY`
4. Secret: `gcp-deploy-key.json` の中身全体をコピー＆ペースト
   ```bash
   # Windows PowerShell
   Get-Content .\gcp-deploy-key.json | Set-Clipboard
   
   # WSL / Linux / Mac
   cat gcp-deploy-key.json | pbcopy  # Mac
   cat gcp-deploy-key.json | xclip   # Linux
   ```
5. **Add secret** をクリック
6. **ローカルの鍵ファイルを削除**（セキュリティのため）:
   ```bash
   rm ./gcp-deploy-key.json
   ```

> 補足: ローカルに鍵ファイルを残さない運用でも、GitHub Actions が実際に使っているサービスアカウントは次の方法で確認できます。  
> - Actions ジョブ内で確認: `gcloud auth list --filter=status:ACTIVE --format="value(account)"`  
> - Cloud Logging（監査ログ）で確認: `protoPayload.methodName="google.devtools.cloudbuild.v1.CloudBuild.CreateBuild"` を検索し、`principalEmail` を確認

###### 3. CLOUD_RUN_ENV_FILE_BASE64（.env.deploy の base64 エンコード）

本番環境変数ファイルを base64 エンコードして登録します。

**.env.deploy を作成:**

```bash
cp env.deploy.example .env.deploy
```

**.env.deploy を編集（すべてのダミー値を本番値に置換）:**

```
PROJECT_ID=your-actual-prod-project-id
FIRESTORE_PROJECT_ID=your-actual-prod-project-id
GOOGLE_CLIENT_ID=your-actual-oauth-client-id.apps.googleusercontent.com
ADMIN_EMAIL_ALLOWLIST=your-email@example.com,another-admin@example.com
CORS_ALLOWED_ORIGINS=https://your-frontend-domain.web.app
ALLOWED_HOSTS=your-cloudrun-url.a.run.app,your-custom-domain.com
SESSION_SECRET_KEY=（下記で自動生成可能）
OPENAI_API_KEY=<OPENAI_API_KEY>
```

**SESSION_SECRET_KEY を生成（まだ設定していない場合）:**

```bash
openssl rand -base64 48
# 出力された値を SESSION_SECRET_KEY に貼り付け
```

**base64 エンコード:**

```bash
# Windows PowerShell
[Convert]::ToBase64String([System.IO.File]::ReadAllBytes(".\.env.deploy")) | Set-Clipboard

# WSL / Linux / Mac
base64 -w 0 .env.deploy  # 出力を手動コピー
```

**GitHub シークレットに登録:**

1. GitHub → リポジトリ → **Settings → Secrets and variables → Actions**
2. **New repository secret** をクリック
3. Name: `CLOUD_RUN_ENV_FILE_BASE64`
4. Secret: 上でコピーした base64 文字列をペースト
5. **Add secret** をクリック

###### 動作確認

1. `develop` → `main` へマージ
2. **Actions** タブで `Deploy to production` ワークフローを確認
3. `Validate deployment inputs` ステップが成功すればシークレット設定は正常
4. 失敗時はエラーメッセージで不足シークレットが特定できる

### B-6. トラブルシュート（詳細）
- 語義/例文が空になる
  - 確認するログイベント: `wordpack_generate_request` / `llm_provider_select` / `wordpack_llm_output_received` / `wordpack_llm_json_parsed` / `wordpack_examples_built` / `wordpack_senses_built` / `wordpack_generate_response`
  - チェックリスト:
    1) `.env` の `OPENAI_API_KEY`（`llm_provider_select` が `local` だと空出力）
    2) `LLM_MAX_TOKENS` を 1200–1800 に（JSON 途中切れ対策）
    3) モデルを `gpt-5.4-mini` など安定モデルへ
    4) `STRICT_MODE=true` でパース失敗を例外化して原因特定
  - strict モード:
    - LLM 失敗/空出力/パース不能で `senses`/`examples` が得られない場合は 5xx
    - `senses` と `examples` がともに空なら 502（`reason_code=EMPTY_CONTENT`、`detail.*` に原因）
    - 既定タイムアウト: `LLM_TIMEOUT_MS=60000`
  - 未解決時はログと `X-Request-ID` を添えて報告

- 404 が返る
  - パスを確認（例: WordPack生成は `…/api/word/pack`）

- CORS エラー
  - ローカル開発では Frontend を `npm run dev`、Backend を `uvicorn … --reload` で起動（Vite プロキシで接続設定不要）

- 変更が反映されない
  - Docker: `docker compose build --no-cache`
  - Vite 監視: Windows は `CHOKIDAR_USEPOLLING=1`（`docker-compose.yml` で設定可）

#### B-6-1. Langfuse のトレースが記録されない
- 現在は Langfuse v3（OpenTelemetry）対応済みです。
- 症状: `WARNING ... langfuse_trace_api_missing` が出続ける／最初の数件のみ表示され以後が出ない場合、依存の不整合か環境変数の誤設定が考えられます。
- 対応: `docker compose build --no-cache && docker compose up` を実行。必要に応じて `LANGFUSE_PUBLIC_KEY/SECRET_KEY/HOST` を再確認し、プロジェクトと日付フィルタを正しく選択してください。古い v2 を利用する場合は `requirements.txt` を v2 に固定してご利用ください。

#### B-1-1. ポート競合の回避（Docker）
- 既定ポートが使用中で起動できない場合は、ホスト公開ポートを環境変数で上書きできます。
  - 一時的に上書き:
    ```bash
    BACKEND_PORT=8001 FRONTEND_PORT=5174 docker compose up --build
    ```
  - `.env` に固定（推奨）:
    ```env
    BACKEND_PORT=8001
    FRONTEND_PORT=5174
    ```
    以後は通常どおり `docker compose up --build`。
- コンテナ内バックエンドの実ポートは常に `8000` 固定です（ヘルスチェック含む）。

- 500 Internal Server Error（文章インポート時など）
  - ログに `StateGraph.__init__() missing 1 required positional argument: 'state_schema'`
  - 対応: `flows.create_state_graph()` で互換化済み。再発時は依存を再インストール
    ```bash
    pip install -U -r requirements.txt
    docker compose build --no-cache && docker compose up
    ```

- 500 Internal Server Error（WordPack 生成時）で `reason_code=PARAM_UNSUPPORTED`
  - 原因: Responses API へ送る任意パラメータが、選択モデルの現行仕様で拒否されている可能性があります。
  - 対応: 最新版では `response_format` を送らず `text.format` を使い、`reasoning` / `text.verbosity` が拒否された場合は自動で外して再試行します。古い環境では最新版へ更新し、必要なら `pip install -U openai` 後に再起動してください。

- 500 Internal Server Error で `ValidationError: 1 validation error for ContrastItem with Field required`
  - 原因: Pydantic v2 のエイリアス設定未適用により `with` → `with_` マッピング不全
  - 対応: `apps/backend/backend/models/word.py` の `ContrastItem` に `model_config = ConfigDict(populate_by_name=true)`（適用済み）。最新版へ更新し再起動（Docker は再ビルド推奨）
  - 補足: API レスポンスの `contrast` は `[{"with": string, "diff_ja": string}]`

### B-7. 運用のヒント（PR4）
- レート制限/リクエストID/監視（p95, 件数, エラー, タイムアウト）/例外監視（Sentry）などを運用ルールとして維持
- Langfuse（任意）: `.env` に `LANGFUSE_ENABLED=true`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST`, `LANGFUSE_RELEASE` を設定すると、HTTP/LLM のトレースが送信されます。
  - Strict モード時は上記キーと `langfuse` パッケージが必須。欠落時は起動でエラーになります。

## 文章インポートの使い方

1. 画面上部のタブから「文章インポート」を選択します。
2. テキストエリアに文章（日本語/英語）を貼り付けます。
   - 1回のインポートで扱えるのは最大 4,000 文字です。超過するとボタンが無効化され、警告文が表示されます。
   - API に直接リクエストする場合も同じ制限が適用され、`413 Request Entity Too Large` として `error=article_import_text_too_long` が返ります。
3. モデルとパラメータを選択します。
   - モデル: 「gpt-5.4-mini / gpt-5.4-nano」から選択
   - どちらのモデルでも `reasoning.effort` と `text.verbosity` を指定します。
4. 「インポート」をクリックします。
5. 右下に進捗通知が表示され、完了後にモーダルで詳細が開きます。
   - 英語タイトル、英語本文（原文そのまま）、日本語訳、解説が表示されます。
   - 下部に関連するWordPackがカードで並びます。
   - Firestore への接続が不安定な場合、モーダル上部に警告欄が出ます。プレースホルダー生成済みかスキップされたレマを確認し、必要に応じて「生成」ボタンや再インポートで復旧してください。
     - 「生成」ボタンで当該WordPackの内容を生成できます（既存は再生成）。
       - 通信エラー時の注意: サーバの厳格モードでは LLM 出力の JSON が壊れていると 502 になります（詳細メッセージに `reason_code=LLM_JSON_PARSE` とヒントが表示されます）。時間を置く、モデル/設定（reasoning.effort/text.verbosity）を見直すなどで再試行してください。
     - カードの語彙名をクリックするとWordPack詳細モーダルが開きます。
6. 「インポート済み文章」一覧から、保存済みの文章を再表示できます。不要になった記事は削除してください（削除ボタンを押すと画面中央に「削除確認」が表示され、対象と取り消し不可の注意を確認してから「削除する」または「キャンセル」を選びます）。

補足: 「例文を生成して記事化」ボタンでも、上記で選択したモデル/パラメータが反映されます。
