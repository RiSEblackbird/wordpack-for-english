# Large Architecture Refactor Plan

## Goal

WordPack for English の既存 API contract、Firestore schema、認証/ゲスト挙動、主要 UI 挙動を維持しながら、backend/frontend の責務境界を大きく整理する。

## Done When

- `backend.main:app` と `backend.main:create_app` が引き続き利用できる。
- 既存 API path と request/response shape が維持される。
- Firestore collection/document schema と guest/auth 挙動が維持される。
- frontend のトップレベルタブ、sidebar、header、WordPackPanel の主要挙動が維持される。
- debug `console.log` が production path から除去される。
- backend pytest、frontend typecheck/test/build を可能な限り実行し、未実行理由を PR body に記録する。

## Priority Slices

- [x] CI/toolchain: frontend Node version を root engines と整合させる。
- [x] Backend app: FastAPI factory、middleware、routers、lifecycle、observability を分割する。
- [x] Backend settings: `backend.config` 互換を保ちつつ settings package へ分割する。
- [x] Backend store: Firestore client/repository 境界と typed records を導入する。
- [x] Backend wordpack/article: router から usecase/service/domain/LLM helper へ責務を移す。
- [x] Frontend app shell: App.tsx、layout、auth telemetry、CSS を分割する。
- [x] Frontend wordpack: API/types/hooks/components を feature 配下へ分割する。
- [x] Tests/docs: 回帰テスト、README/docs 更新要否、PR body を整える。

## Resume Command

```bash
cd /Users/Taishi/Documents/GitHub/wordpack-for-english
git status --short --branch
sed -n '1,220p' plans/large-architecture-refactor.md
cat plans/large-architecture-refactor.status.json
```

## Smoke Tests

```bash
PYTHONPATH=apps/backend pytest
cd apps/frontend && npx tsc -p tsconfig.json
cd apps/frontend && npm test -- --coverage --silent
cd apps/frontend && npm run build
```

## Session Notes

- 2026-05-05: Initial scan confirmed large target files: `backend/main.py`, `backend/config.py`, `routers/word.py`, `flows/article_import.py`, `App.tsx`, `useWordPack.ts`.
- 2026-05-06: Large refactor implementation completed locally. Backend pytest and frontend typecheck/test/build pass. Playwright E2E could start servers but browser binary is not installed locally.
