# Cloud Run revision切替後の再生成job status 404

## 概要

| 項目 | 内容 |
|---|---|
| 発生日 | 2026-06-08 |
| 記録日 | 2026-06-13 |
| 対象 | Cloud Run `wordpack-backend` / 非同期再生成ジョブ |
| ユーザー影響 | 再生成が完了していても、生成キュー上では古い「生成中」カードとして残り、完了・失敗・再生成要否を判断しづらい |
| 状態 | PR #449 で対応済み |
| 関連PR | [#449 再生成ジョブ状態を永続化して古い生成キュー表示を回復する](https://github.com/RiSEblackbird/wordpack-for-english/pull/449) |
| 関連UI/UX報告 | [`docs/ai-governance/reports/regenerate-queue-stale-recovery-2026-06-13.md`](../ai-governance/reports/regenerate-queue-stale-recovery-2026-06-13.md) |

## 観測した事実

GCP Cloud Run logs で、次の流れを確認した。公開文書では、ログ原文、job ID、request ID、trace ID、完全なrevision名、秒単位の時刻は残さない。

1. 2026-06-08 JST の時間帯に、非同期再生成の enqueue が `202 Accepted` を返した。
2. その後 Cloud Run revision / instance が切り替わり、同じ再生成ジョブの status GET が `404 Not Found` になった。
3. 同じ WordPack の通常 GET は後日 `200 OK` で返った。

このため、生成結果そのものの消失ではなく、非同期再生成ジョブ状態をプロセスメモリだけで保持していたことが主な問題だった。

## 技術的な原因

当時の非同期再生成ジョブ状態は、Cloud Run インスタンス内のプロセスメモリにある `_regenerate_jobs` に依存していた。

Cloud Run の revision / instance が切り替わると、新しいプロセスは古いプロセスのメモリを引き継がない。非同期 enqueue は成功して `202` を返していても、status GET が別 revision / instance に到達すると job record を見つけられず `404` になり得る。

## 対応内容

PR #449 で次を実装した。

- Firestore `regenerate_jobs` に `job_id`, `word_pack_id`, `status`, `result_json`, `error`, `created_at`, `updated_at` を保存する。
- status GET は、利用可能な store が永続 job API を持つ場合、プロセスメモリではなく Firestore から job を復元する。
- `succeeded` job の結果は、現在の WordPack ドキュメントではなく、その job が保存した `result_json` snapshot から返す。
- フロントエンド通知に `jobId` を残し、20分以上経過した進行中カードは persisted job status が `succeeded` かつ `result_json` を確認できた場合だけ完了カードへ補正する。
- `jobId` がない過去通知や status / result を確認できない通知は、成功扱いにせず、一覧更新または再生成を案内する失敗カードへ移す。

## 再発確認の手順

同種の問題を疑う場合は、秘密情報やユーザー入力全文を記録せず、次の順で確認する。

1. Cloud Run logs で対象時間帯の `POST /regenerate/async` または `/packs/{word_pack_id}/regenerate/async` の `202` を探す。
2. 同じ `job_id` に紐づく status GET の `404` を探す。ただし、公開文書には実際の `job_id` を残さない。
3. status GET の service revision と enqueue 時点の revision が違うか確認する。ただし、公開文書には完全な revision 名を残さない。
4. 同じ `word_pack_id` の通常 GET が `200` で返るか確認し、生成結果の消失か job status の消失かを切り分ける。ただし、公開文書には実際の `word_pack_id` を残さない。
5. Firestore `regenerate_jobs/{job_id}` の存在、`status`, `result_json`, `error`, `updated_at` を確認する。
6. フロントエンド通知に `jobId` が保存されているか確認する。

## 再発時の判断基準

| 観測 | 判断 | 次アクション |
|---|---|---|
| enqueue は `202`、status GET は別 revision で `404`、通常 WordPack GET は `200` | job status 復元の問題 | Firestore `regenerate_jobs` と status GET 経路を確認する |
| enqueue は `202`、Firestore job は `succeeded`、`result_json` あり | UI補正対象 | 通知の `jobId` と stale card 補正を確認する |
| enqueue は `202`、Firestore job がない | 永続化前または保存失敗 | create job のログと Firestore 書き込み権限を確認する |
| status は `failed`、`error` あり | 再生成処理自体の失敗 | error 内容をマスクして原因を調査する |
| 通常 WordPack GET も `404` | WordPack自体の参照不可 | job status ではなく WordPack 保存・権限・ID を調査する |

## 残るリスク・後続課題

- `jobId` が保存されていない過去の進行中通知は、成功補正できず確認不能の失敗カードへ移る。
- Firestore `regenerate_jobs` の TTL / cleanup は未設定。状態復元を優先した最小対応のため、保存期間と削除方針は別途決める必要がある。
- Cloud Run logs の調査結果はPR #449とUI/UXレビュー報告に基づく。GCPの実ログ全文や秘匿情報はこのリポジトリに保存しない。

## 参照

- [PR #449](https://github.com/RiSEblackbird/wordpack-for-english/pull/449)
- [`docs/ai-governance/reports/regenerate-queue-stale-recovery-2026-06-13.md`](../ai-governance/reports/regenerate-queue-stale-recovery-2026-06-13.md)
- [`apps/backend/backend/routers/word/regeneration_routes.py`](../../apps/backend/backend/routers/word/regeneration_routes.py)
- [`apps/backend/backend/infrastructure/firestore/repositories/regenerate_jobs.py`](../../apps/backend/backend/infrastructure/firestore/repositories/regenerate_jobs.py)
