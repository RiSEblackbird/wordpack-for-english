from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal

from .base import FirestoreBaseRepository, firestore

RegenerateJobStatus = Literal["pending", "running", "succeeded", "failed"]


class FirestoreRegenerateJobRepository(FirestoreBaseRepository):
    """Cloud Run revision を跨いで再生成ジョブ状態を保持する。"""

    def __init__(self, client: firestore.Client):
        super().__init__(client)
        self._jobs = client.collection("regenerate_jobs")

    def create_regenerate_job(
        self,
        *,
        job_id: str,
        word_pack_id: str,
        status: RegenerateJobStatus = "pending",
    ) -> Mapping[str, Any]:
        now = self._now_iso()
        payload: dict[str, Any] = {
            "job_id": job_id,
            "word_pack_id": word_pack_id,
            "status": status,
            "result_json": None,
            "error": None,
            "created_at": now,
            "updated_at": now,
        }
        self._jobs.document(job_id).set(payload)
        return payload

    def update_regenerate_job(
        self,
        job_id: str,
        *,
        status: RegenerateJobStatus,
        error: str | None = None,
        result_json: str | None = None,
    ) -> Mapping[str, Any] | None:
        doc_ref = self._jobs.document(job_id)
        snapshot = doc_ref.get()
        if not snapshot.exists:
            return None
        updates: dict[str, Any] = {
            "status": status,
            "updated_at": self._now_iso(),
        }
        if status == "failed":
            updates["error"] = error or "再生成ジョブが失敗しました"
        elif error is not None:
            updates["error"] = error
        if result_json is not None:
            updates["result_json"] = result_json
        doc_ref.update(updates)
        updated = doc_ref.get()
        return updated.to_dict() or None

    def get_regenerate_job(self, job_id: str) -> Mapping[str, Any] | None:
        snapshot = self._jobs.document(job_id).get()
        if not snapshot.exists:
            return None
        return snapshot.to_dict() or None


FirestoreRegenerateJobStore = FirestoreRegenerateJobRepository
