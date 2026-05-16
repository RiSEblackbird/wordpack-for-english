# Firestore Repository Split Plan

## Goal

Firestore collection/document schema、既存 API contract、legacy import path を維持したまま、
`backend.store.firestore_store` に残る Firestore 実装を
`backend.infrastructure.firestore.repositories` 配下の concrete repository へ移す。

## Done When

- `backend.infrastructure.firestore.repositories.*` が `backend.store.firestore_store` に依存しない。
- `backend.store.firestore_store` は旧 import path 互換の facade として残る。
- `AppFirestoreStore` は users / wordpacks / examples / articles repository を compose する。
- 旧 class 名と新 repository class 名の import 互換がテストで固定されている。
- Firestore collection/document schema、API path、request/response shape は変更しない。
- Backend pytest、security header pytest、`git diff --check` を実行し、結果を PR と最終報告に残す。

## Priority Slices

- [x] Plan: 目標、完了条件、再開手順、スモークテストを整える。
- [x] Discovery: 公開メソッド、import/monkeypatch 依存、既存 repository alias を棚卸しする。
- [x] Repository split: concrete repository 実装を infrastructure 配下へ移す。
- [x] Compatibility: store facade と旧 class/helper import を維持する。
- [x] Tests/docs: 互換 import 回帰テストと関連 docs 更新を行う。
- [ ] Verification/PR: ローカル検証、commit、push、PR、CI 確認を行う。

## Resume Command

```bash
cd /Users/Taishi/Documents/GitHub/wordpack-for-english
git status --short --branch
sed -n '1,220p' plans/firestore-repository-split.md
cat plans/firestore-repository-split.status.json
```

## Smoke Tests

```bash
PYTHONPATH=apps/backend pytest
PYTHONPATH=apps/backend pytest -q --no-cov tests/test_security_headers.py
git diff --check
```

## Session Notes

- 2026-05-16: `main` から `codex/firestore-repository-split` を作成。PR #415 Follow-up として Firestore repository 分割のみを対象にする。
- 2026-05-16: `backend.infrastructure.firestore.repositories` へ users / wordpacks / examples / articles / app_store を分割し、`backend.store.firestore_store` は互換 facade に縮退。Firestore payload helper も infrastructure 側へ移し、旧 store helper path は re-export として維持。
