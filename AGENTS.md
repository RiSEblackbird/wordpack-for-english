# AGENTS.md

この文書は、Codex がこのリポジトリで作業するときに必ず踏む実行手順を定義する。詳細な品質原則は [`docs/agent-principles.md`](docs/agent-principles.md) を参照する。

サブディレクトリに `AGENTS.md` がある場合は領域固有ルールとして追加で従う。ただし、完了報告ゲート、PR/CI 条件、blocker 基準はこのルート文書を優先する。

---

## 最重要: 完了報告ゲート

リポジトリ変更を伴う作業では、最終回答前に必ず以下を確認する。

- 作業ブランチ上である。
- 変更が commit 済みである。
- branch が origin に push 済みである。
- PR URL が存在する。ドラフト PR は完了扱いにしない。
- 最新 commit の CI 状態を確認済みである。
- CI が失敗中または未確認なら「完了」と言ってはいけない。

最終回答には必ず以下を含める。

- Branch
- PR URL
- Commit SHA
- Local verification
- CI result
- Remaining risks

調査、質問回答、レビューなどリポジトリ変更を伴わない作業では、該当しない項目を `N/A` として明示し、変更作業と誤認される完了表現を避ける。

---

## 作業開始ゲート

- 最初に作業ディレクトリ、現在ブランチ、作業ツリー、直近の git 履歴を確認する。
- スレッド最初の仕事開始時は `main` にいることを確認する。`main` 以外にいる場合は、未確認差分を保護したうえで `main` にチェックアウトする。その後、現在位置が `main` であっても必ず `git fetch origin` と `git merge --ff-only origin/main` を実行し、`origin/main` の最新状態に合わせる。
- 最新の `main` 上で、作業開始前に `codex/<目的>` 形式の作業ブランチを作成してチェックアウトする。
- 同一スレッド内で作業開始済みの場合は、既にいる作業ブランチ上で継続してよい。ただし、未確認差分がある場合は所有範囲を把握し、無関係な変更を巻き込まない。
- 長期タスクでは、先に `目標`、`完了条件`、優先度付き小タスク、再開コマンド、基本スモークテスト手順を計画として残す。
- セッション開始時は、進捗ログ、未完了 checklist、起動スクリプト、最低限の動作確認を確認し、壊れた基盤を見つけたら新規実装より先に修復する。

---

## このリポジトリの必須コマンド

変更範囲に応じて、以下から最小十分な検証を選ぶ。実行しない項目は PR と最終回答で理由を明記する。

- Backend: `PYTHONPATH=apps/backend pytest`
- Security headers: `PYTHONPATH=apps/backend pytest -q --no-cov tests/test_security_headers.py`
- Frontend typecheck: `cd apps/frontend && npx tsc -p tsconfig.json`
- Frontend tests: `cd apps/frontend && npm test -- --coverage --silent`
- Playwright smoke: `npx playwright test -c tests/e2e/playwright.config.ts tests/e2e/auth.spec.ts tests/e2e/guest.spec.ts tests/e2e/wordpack.spec.ts`
- Cloud Run 設定やデプロイスクリプト変更: `shellcheck scripts/deploy_cloud_run.sh` と `./scripts/deploy_cloud_run.sh --dry-run --env-file configs/cloud-run/ci.env --project-id ci-placeholder-project --region asia-northeast1 --service wordpack-backend`
- 文書のみの変更: `git diff --check` と、リンク先・コマンド名・移動先ファイルの目視確認を最低限行う。

依存未導入の場合は、Python は `pip install -r requirements.txt`、フロントエンドは `cd apps/frontend && npm ci`、E2E はルートと `apps/frontend` で `npm ci` を実行し、ルートで `npx playwright install --with-deps` を先に行う。

---

## Commit / PR / CI ルール

- コミットメッセージは必ず日本語で書く。1 行目に変更内容を簡潔にまとめ、補足が必要な場合のみ 2 行目以降に追記する。
- 変更は意味のある slice ごとに分け、各 slice で関連する確認を行ってから commit する。
- PR 作成前にローカルで実行可能な最小十分な検証を済ませる。
- PR 本文には、変更内容、保持した既存挙動、検証結果、未実行項目、残るリスクを記載する。
- 作業完了時は作業ブランチを push し、ドラフトではない PR を作成または更新する。
- PR 作成だけでは完了ではない。最新 head の CI 状態を確認し、失敗していればログを読んで原因を特定し、修正、commit、push、再確認を繰り返す。
- CI を通せない真の blocker がある場合のみ、完了ではなく blocker として報告する。報告には失敗している check 名、ログ上の根拠、試した修正、未完了範囲、次の最短アクションを含める。

---

## 変更時チェックリスト

1. `README.md` の更新要否を確認する。
2. 影響を受ける `docs/` 配下の文書を確認する。
3. 必要なら `.gitignore` の更新要否を確認する。
4. ルールや作業指針の不備が明らかになった場合は、対応する `AGENTS.md` の更新要否を確認する。
5. 実装、挙動、セットアップ、設計の意味が変わった場合は、関連ドキュメントを同じ変更内で更新する。

---

## テスト実装方針

- ロジック変更: まず Unit Test を追加し、境界入力、異常系、回帰条件を優先して固定する。
- モジュール間連携変更（XR入力、儀式状態遷移、export など）: 必要最小限の Integration Test を追加し、公開契約の整合を確認する。
- UI/操作フロー変更: クリティカル導線のみ E2E もしくは同等のスモークテストを追加する。
- 不具合修正時は、修正前に失敗する条件を再現する回帰テストを原則同一変更で追加する。
- テストを追加できない場合は、理由、代替検証、残存リスクを PR と最終報告に明記する。

---

## 完了の定義

作業は、次のすべてを満たしたときにのみ完了である。

- 要求された成果が実装されている、または真の阻害要因が文書化されている。
- 関連する検証が実行済みである、または未実行理由が明示されている。
- 厳格な自己レビューが完了している。
- 既知の重大問題が未報告のまま残っていない。
- 変更パッチが、慎重なメンテナであれば現実的にマージ可能な品質である。
- 完了報告ゲートの Branch / PR URL / Commit SHA / Local verification / CI result / Remaining risks を提示できる。

---

## 本リポジトリ固有ルール

- 2000行を超えない小規模開発では、原則として PR を分割せず、可能な限り大きな単位で提出する。
- ルート `AGENTS.md` は実行手順、品質ゲート、完了条件を定義し、サブディレクトリの `AGENTS.md` は領域固有の実装規約、検証コマンド、注意点を補完する。
- サブディレクトリ文書が存在する場合でも、長大タスクの進行原則（計画作成、blocker 基準、PR 作成条件、停止時整合）は本書に合わせる。
- 計画テンプレートは `plans/TEMPLATE.md` を基準とし、必要ならタスクに応じて項目を拡張する。
- 詳細な設計・品質・記述原則は [`docs/agent-principles.md`](docs/agent-principles.md) に従う。
