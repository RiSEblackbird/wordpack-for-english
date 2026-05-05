# アーキテクチャ概要

この文書は、backend/frontend の責務配置を把握するための内部構造メモである。
API path、Firestore collection/document schema、認証・ゲスト閲覧の契約は README と各 API テストを正とし、
ここでは実装上の依存方向だけを扱う。

## Backend

FastAPI の起動構造は `backend.main` から `backend.app` 配下へ分離している。
`backend.main:app` と `backend.main:create_app` は互換 entrypoint として維持し、
実際の app 生成、middleware、router 登録、startup/shutdown は次の責務に分ける。

| モジュール | 責務 |
| --- | --- |
| `backend.app.factory` | `FastAPI` インスタンス生成と構成の接続点 |
| `backend.app.middleware_stack` | CORS、proxy、host、security、rate limit、access log の登録 |
| `backend.app.routers` | API router の include と debug router の環境制御 |
| `backend.app.lifecycle` | startup seed と provider cleanup |
| `backend.observability.*` | Cloud Trace header 解析、access log/metrics、Langfuse tracing |

設定は `backend.settings.base.Settings` に実体を置き、`backend.config` は互換 facade として残す。
既存テストや外部呼び出しが `from backend.config import settings` を使っても同じ `settings` オブジェクトを参照する。

Firestore は既存の `AppFirestoreStore` を互換実装として残しつつ、
`backend.infrastructure.firestore` に client/repository adapter、
`backend.domain.*` に typed record/repository protocol を置く。
新しい usecase は repository 境界へ寄せ、既存 router やテストで必要な `backend.store.store` は compatibility shim として維持する。

WordPack の API router は route 定義と dependency/error mapping に寄せ、
生成、lookup、空 WordPack 作成、学習進捗、guest public、再生成 job registry は `backend.application.wordpack` に置く。
LLM prompt と JSON parser は `backend.infrastructure.llm` に置き、code fence 除去と control character sanitize を共通化する。

Article import の lemma filtering は `backend.domain.article.lemma_filter` に集約する。
function word/basic lemma の除外、多語句の保持、重複排除はこの domain 関数を通す。

## Frontend

`src/App.tsx` は互換 entrypoint として `src/app/App.tsx` を re-export する。
実際の app shell、theme 適用、auth telemetry、WordPack feature は次の責務に分ける。

| モジュール | 責務 |
| --- | --- |
| `src/app` | アプリ entrypoint、theme 適用、トップレベル構成 |
| `src/features/auth` | Google OAuth telemetry と sanitization |
| `src/features/wordpack` | WordPack domain types、API helper、feature hooks/components |
| `src/shared/api` | `ApiError`、JSON fetch、FastAPI detail parse、401 event dispatch |
| `src/lib/fetcher.ts` | 既存 import path 用の compatibility re-export |

`auth:unauthorized`、`wordpack:updated`、`wordpack:study-progress` の custom event は公開契約として扱う。
旧 import path は段階移行のため残し、feature 配下への直接 import を新規コードの標準とする。
