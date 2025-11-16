from __future__ import annotations

import json
import uuid
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

from google.cloud import firestore

from ..sense_title import choose_sense_title
from .common import normalize_non_negative_int
from .examples import EXAMPLE_CATEGORIES, iter_example_rows
from .wordpacks import merge_core_with_examples, split_examples_from_payload


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


class FirestoreBaseStore:
    """Firestore クライアント共通のヘルパー。"""

    def __init__(self, client: firestore.Client):
        self._client = client


class FirestoreUserStore(FirestoreBaseStore):
    """Firestore 上のユーザードキュメントを管理する。"""

    def record_user_login(
        self,
        *,
        google_sub: str,
        email: str,
        display_name: str,
        login_at: datetime | None = None,
    ) -> dict[str, str]:
        login_time = (login_at or datetime.now(UTC)).replace(microsecond=0)
        doc_ref = self._client.collection("users").document(google_sub)
        doc_ref.set(
            {
                "google_sub": google_sub,
                "email": email,
                "display_name": display_name,
                "last_login_at": login_time.isoformat(),
            },
            merge=True,
        )
        user = self.get_user_by_google_sub(google_sub)
        if user is None:  # pragma: no cover - defensive fallback
            raise RuntimeError("failed to persist user login")
        return user

    def get_user_by_google_sub(self, google_sub: str) -> dict[str, str] | None:
        doc = self._client.collection("users").document(google_sub).get()
        if not doc.exists:
            return None
        data = doc.to_dict() or {}
        return {
            "google_sub": str(data.get("google_sub") or google_sub),
            "email": str(data.get("email") or ""),
            "display_name": str(data.get("display_name") or ""),
            "last_login_at": str(data.get("last_login_at") or ""),
        }

    def delete_user(self, google_sub: str) -> None:
        self._client.collection("users").document(google_sub).delete()


class FirestoreWordPackStore(FirestoreBaseStore):
    """WordPack 本体と lemma 情報を Firestore で管理する。"""

    def __init__(self, client: firestore.Client):
        super().__init__(client)
        self._lemmas = client.collection("lemmas")
        self._word_packs = client.collection("word_packs")
        self._examples = client.collection("examples")
        self._metadata = client.collection("metadata")

    def _ordered_word_pack_query(self) -> firestore.Query:
        """Builds a deterministic descending query for word_packs collection."""

        return self._word_packs.order_by(
            "created_at", direction=firestore.Query.DESCENDING
        )

    def _fetch_word_pack_snapshots(
        self, limit: int, offset: int
    ) -> list[firestore.DocumentSnapshot]:
        """Apply limit/offset on Firestore side and fetch matching snapshots."""

        normalized_limit = max(0, int(limit))
        normalized_offset = max(0, int(offset))
        if normalized_limit == 0:
            return []
        query = self._ordered_word_pack_query()
        if normalized_offset:
            query = query.offset(normalized_offset)
        query = query.limit(normalized_limit)
        return list(query.stream())

    def save_word_pack(self, word_pack_id: str, lemma: str, data: str) -> None:
        now = _now_iso()
        (
            core_json,
            examples,
            sense_title_raw,
            sense_candidates,
            (checked_only_count, learned_count),
            (lemma_llm_model, lemma_llm_params),
        ) = split_examples_from_payload(data)
        sense_title = choose_sense_title(
            sense_title_raw,
            sense_candidates,
            lemma=lemma,
            limit=40,
        )
        lemma_id = self._upsert_lemma(
            label=lemma,
            sense_title=sense_title,
            llm_model=lemma_llm_model,
            llm_params=lemma_llm_params,
            now=now,
        )
        pack_ref = self._word_packs.document(word_pack_id)
        existing = pack_ref.get()
        created_at = str((existing.to_dict() or {}).get("created_at") or now) if existing.exists else now
        category_counts = self._replace_examples(
            word_pack_id,
            lemma=lemma,
            sense_title=sense_title,
            examples=examples,
            updated_at=now,
        )
        pack_ref.set(
            {
                "lemma_id": lemma_id,
                "lemma_label": lemma,
                "lemma_label_lower": lemma.lower(),
                "sense_title": sense_title,
                "lemma_llm_model": lemma_llm_model,
                "lemma_llm_params": lemma_llm_params,
                "data_core": core_json,
                "created_at": created_at,
                "updated_at": now,
                "checked_only_count": normalize_non_negative_int(checked_only_count),
                "learned_count": normalize_non_negative_int(learned_count),
                "examples_category_counts": category_counts,
            }
        )

    def get_word_pack(self, word_pack_id: str) -> tuple[str, str, str, str] | None:
        doc = self._word_packs.document(word_pack_id).get()
        if not doc.exists:
            return None
        data = doc.to_dict() or {}
        rows = self._load_example_rows(word_pack_id)
        merged = merge_core_with_examples(str(data.get("data_core") or "{}"), rows)
        try:
            parsed = json.loads(merged) if merged else {}
        except Exception:
            parsed = {}
        parsed["checked_only_count"] = normalize_non_negative_int(
            data.get("checked_only_count")
        )
        parsed["learned_count"] = normalize_non_negative_int(data.get("learned_count"))
        with_progress = json.dumps(parsed, ensure_ascii=False)
        return (
            str(data.get("lemma_label") or ""),
            with_progress,
            str(data.get("created_at") or ""),
            str(data.get("updated_at") or ""),
        )

    def list_word_packs(
        self, limit: int = 50, offset: int = 0
    ) -> list[tuple[str, str, str, str, str]]:
        # Firestore 側で order_by + limit/offset を適用し、安定したページングを実現する。
        docs = self._fetch_word_pack_snapshots(limit, offset)
        items: list[tuple[str, str, str, str, str]] = []
        for doc in docs:
            data = doc.to_dict() or {}
            items.append(
                (
                    doc.id,
                    str(data.get("lemma_label") or ""),
                    str(data.get("sense_title") or ""),
                    str(data.get("created_at") or ""),
                    str(data.get("updated_at") or ""),
                )
            )
        return items

    def count_word_packs(self) -> int:
        query = self._ordered_word_pack_query()
        try:
            aggregation = query.count().get()
        except AttributeError as exc:  # pragma: no cover - defensive fallback
            msg = "Firestore client does not support aggregation queries"
            raise RuntimeError(msg) from exc
        if not aggregation:
            return 0

        result = aggregation[0]
        count_value: Any | None = None
        try:
            count_value = result["count"]  # type: ignore[index]
        except Exception:
            aggregate_fields = getattr(result, "aggregate_fields", None)
            if isinstance(aggregate_fields, Mapping):
                count_value = aggregate_fields.get("count")
        if count_value is None and getattr(result, "alias", None) == "count":
            count_value = getattr(result, "value", None)
        return int(count_value or 0)

    def list_word_packs_with_flags(
        self, limit: int = 50, offset: int = 0
    ) -> list[tuple[str, str, str, str, str, bool, Mapping[str, int], int, int]]:
        docs = self._fetch_word_pack_snapshots(limit, offset)
        results: list[tuple[str, str, str, str, str, bool, Mapping[str, int], int, int]] = []
        for doc in docs:
            data = doc.to_dict() or {}
            counts_raw = data.get("examples_category_counts") or {}
            counts = {cat: int(counts_raw.get(cat, 0)) for cat in EXAMPLE_CATEGORIES}
            total = sum(counts.values())
            checked = normalize_non_negative_int(data.get("checked_only_count"))
            learned = normalize_non_negative_int(data.get("learned_count"))
            results.append(
                (
                    doc.id,
                    str(data.get("lemma_label") or ""),
                    str(data.get("sense_title") or ""),
                    str(data.get("created_at") or ""),
                    str(data.get("updated_at") or ""),
                    total == 0,
                    counts,
                    checked,
                    learned,
                )
            )
        return results

    def delete_word_pack(self, word_pack_id: str) -> bool:
        doc_ref = self._word_packs.document(word_pack_id)
        snapshot = doc_ref.get()
        if not snapshot.exists:
            return False
        doc_ref.delete()
        self._delete_examples(word_pack_id)
        return True

    def update_word_pack_study_progress(
        self, word_pack_id: str, checked_increment: int, learned_increment: int
    ) -> tuple[int, int] | None:
        doc_ref = self._word_packs.document(word_pack_id)
        snapshot = doc_ref.get()
        if not snapshot.exists:
            return None
        data = snapshot.to_dict() or {}
        current_checked = normalize_non_negative_int(data.get("checked_only_count"))
        current_learned = normalize_non_negative_int(data.get("learned_count"))
        next_checked = max(0, current_checked + int(checked_increment))
        next_learned = max(0, current_learned + int(learned_increment))
        if next_checked != current_checked or next_learned != current_learned:
            doc_ref.update(
                {
                    "checked_only_count": next_checked,
                    "learned_count": next_learned,
                    "updated_at": _now_iso(),
                }
            )
        return next_checked, next_learned

    def find_word_pack_id_by_lemma(self, lemma: str) -> str | None:
        target = lemma.lower()
        docs = list(self._word_packs.stream())
        docs.sort(key=lambda d: str((d.to_dict() or {}).get("updated_at") or ""), reverse=True)
        for doc in docs:
            data = doc.to_dict() or {}
            if str(data.get("lemma_label_lower") or "").lower() == target:
                return doc.id
        return None

    def find_word_pack_by_lemma_ci(self, lemma: str) -> tuple[str, str, str] | None:
        target = lemma.lower()
        docs = list(self._word_packs.stream())
        docs.sort(key=lambda d: str((d.to_dict() or {}).get("updated_at") or ""), reverse=True)
        for doc in docs:
            data = doc.to_dict() or {}
            if str(data.get("lemma_label_lower") or "").lower() == target:
                return (doc.id, str(data.get("lemma_label") or ""), str(data.get("sense_title") or ""))
        return None

    def reserve_example_ids(self, count: int) -> list[int]:
        return self._allocate_example_ids(count)

    def _delete_examples(self, word_pack_id: str) -> None:
        for snapshot in list(self._examples.stream()):
            data = snapshot.to_dict() or {}
            if data.get("word_pack_id") == word_pack_id:
                snapshot.reference.delete()

    def _replace_examples(
        self,
        word_pack_id: str,
        *,
        lemma: str,
        sense_title: str,
        examples: Mapping[str, Any] | None,
        updated_at: str,
    ) -> dict[str, int]:
        self._delete_examples(word_pack_id)
        counts = {cat: 0 for cat in EXAMPLE_CATEGORIES}
        if not isinstance(examples, Mapping):
            return counts
        rows = list(iter_example_rows(examples))
        ids = self._allocate_example_ids(len(rows))
        id_iter = iter(ids)
        for (
            category,
            position,
            en,
            ja,
            grammar_ja,
            llm_model,
            llm_params,
            checked_only_count,
            learned_count,
            transcription_typing_count,
        ) in rows:
            doc_id = str(next(id_iter))
            self._examples.document(doc_id).set(
                {
                    "example_id": int(doc_id),
                    "word_pack_id": word_pack_id,
                    "category": category,
                    "position": position,
                    "en": en,
                    "ja": ja,
                    "grammar_ja": grammar_ja,
                    "llm_model": llm_model,
                    "llm_params": llm_params,
                    "checked_only_count": normalize_non_negative_int(checked_only_count),
                    "learned_count": normalize_non_negative_int(learned_count),
                    "transcription_typing_count": normalize_non_negative_int(
                        transcription_typing_count
                    ),
                    "created_at": updated_at,
                    "pack_updated_at": updated_at,
                    "lemma": lemma,
                    "sense_title": sense_title,
                }
            )
            counts[category] = counts.get(category, 0) + 1
        return counts

    def _load_example_rows(self, word_pack_id: str) -> Sequence[Mapping[str, Any]]:
        rows: list[Mapping[str, Any]] = []
        for snapshot in self._examples.stream():
            data = snapshot.to_dict() or {}
            if data.get("word_pack_id") != word_pack_id:
                continue
            rows.append(
                {
                    "category": data.get("category"),
                    "en": data.get("en"),
                    "ja": data.get("ja"),
                    "grammar_ja": data.get("grammar_ja"),
                    "llm_model": data.get("llm_model"),
                    "llm_params": data.get("llm_params"),
                    "checked_only_count": data.get("checked_only_count"),
                    "learned_count": data.get("learned_count"),
                    "transcription_typing_count": data.get("transcription_typing_count"),
                    "position": data.get("position", 0),
                }
            )
        rows.sort(
            key=lambda r: (
                str(r.get("category") or ""),
                int(r.get("position") or 0),
            )
        )
        return rows

    def _allocate_example_ids(self, count: int) -> list[int]:
        if count <= 0:
            return []
        counter_ref = self._metadata.document("example_counters")
        try:
            transaction = self._client.transaction()
        except AttributeError:  # pragma: no cover - defensive fallback
            transaction = None
        if transaction is None:
            snapshot = counter_ref.get()
            current = int((snapshot.to_dict() or {}).get("next_id", 1))
            ids = list(range(current, current + count))
            counter_ref.set({"next_id": current + count}, merge=True)
            return ids
        snapshot = transaction.get(counter_ref)
        current = int((snapshot.to_dict() or {}).get("next_id", 1))
        ids = list(range(current, current + count))
        transaction.set(counter_ref, {"next_id": current + count}, merge=True)
        transaction.commit()
        return ids

    def update_word_pack_metadata(
        self,
        word_pack_id: str,
        *,
        updated_at: str | None = None,
        category_counts: Mapping[str, int] | None = None,
    ) -> None:
        updates: dict[str, Any] = {}
        if updated_at is not None:
            updates["updated_at"] = updated_at
        if category_counts is not None:
            normalized = {cat: int(category_counts.get(cat, 0)) for cat in EXAMPLE_CATEGORIES}
            updates["examples_category_counts"] = normalized
        if updates:
            self._word_packs.document(word_pack_id).update(updates)

    def get_word_pack_metadata(self, word_pack_id: str) -> Mapping[str, Any] | None:
        snapshot = self._word_packs.document(word_pack_id).get()
        if not snapshot.exists:
            return None
        return snapshot.to_dict() or {}

    def _upsert_lemma(
        self,
        *,
        label: str,
        sense_title: str,
        llm_model: str | None,
        llm_params: str | None,
        now: str,
    ) -> str:
        original_label = str(label or "").strip()
        if not original_label:
            raise ValueError("lemma label must not be empty")
        normalized = original_label.lower()
        for snapshot in self._lemmas.stream():
            data = snapshot.to_dict() or {}
            if str(data.get("normalized_label") or "") != normalized:
                continue
            lemma_id = snapshot.id
            stored_label = str(data.get("label") or "")
            new_label = (
                stored_label
                if stored_label.lower() == original_label.lower()
                else original_label
            )
            stripped_sense = str(sense_title or "").strip()
            stored_sense = str(data.get("sense_title") or "")
            new_sense = stored_sense or stripped_sense
            new_llm_model = llm_model if llm_model is not None else data.get("llm_model")
            new_llm_params = llm_params if llm_params is not None else data.get("llm_params")
            snapshot.reference.update(
                {
                    "label": new_label,
                    "sense_title": new_sense,
                    "llm_model": new_llm_model,
                    "llm_params": new_llm_params,
                }
            )
            return lemma_id
        lemma_id = f"lm:{normalized}:{uuid.uuid4().hex[:8]}"
        self._lemmas.document(lemma_id).set(
            {
                "label": original_label,
                "normalized_label": normalized,
                "sense_title": sense_title or "",
                "llm_model": llm_model,
                "llm_params": llm_params,
                "created_at": now,
            }
        )
        return lemma_id


class FirestoreExampleStore(FirestoreBaseStore):
    """例文に関する Firestore CRUD。"""

    def __init__(self, client: firestore.Client, wordpacks: FirestoreWordPackStore):
        super().__init__(client)
        self._examples = client.collection("examples")
        self._wordpacks = wordpacks

    def update_example_study_progress(
        self, example_id: int, checked_increment: int, learned_increment: int
    ) -> tuple[str, int, int] | None:
        doc_ref = self._examples.document(str(example_id))
        snapshot = doc_ref.get()
        if not snapshot.exists:
            return None
        data = snapshot.to_dict() or {}
        current_checked = normalize_non_negative_int(data.get("checked_only_count"))
        current_learned = normalize_non_negative_int(data.get("learned_count"))
        next_checked = max(0, current_checked + int(checked_increment))
        next_learned = max(0, current_learned + int(learned_increment))
        if next_checked != current_checked or next_learned != current_learned:
            doc_ref.update(
                {
                    "checked_only_count": next_checked,
                    "learned_count": next_learned,
                }
            )
        return (str(data.get("word_pack_id") or ""), next_checked, next_learned)

    def delete_example(self, word_pack_id: str, category: str, index: int) -> int | None:
        if index < 0:
            return None
        docs = self._examples_for_pack(word_pack_id)
        category_docs = [doc for doc in docs if doc["category"] == category]
        category_docs.sort(key=lambda d: (int(d["position"]), int(d["example_id"])))
        if index >= len(category_docs):
            return None
        target = category_docs[index]
        self._examples.document(str(target["example_id"])).delete()
        self._reindex_category(word_pack_id, category)
        self._refresh_category_counts(word_pack_id)
        return len(category_docs) - 1

    def delete_examples_by_ids(
        self, example_ids: Iterable[int]
    ) -> tuple[int, list[int]]:
        deleted = 0
        not_found: list[int] = []
        touched: set[tuple[str, str]] = set()
        for example_id in example_ids:
            doc_ref = self._examples.document(str(example_id))
            snapshot = doc_ref.get()
            if not snapshot.exists:
                try:
                    not_found.append(int(example_id))
                except (TypeError, ValueError):
                    pass
                continue
            data = snapshot.to_dict() or {}
            doc_ref.delete()
            deleted += 1
            touched.add((str(data.get("word_pack_id") or ""), str(data.get("category") or "")))
        for word_pack_id, category in touched:
            self._reindex_category(word_pack_id, category)
            self._refresh_category_counts(word_pack_id)
        return deleted, not_found

    def append_examples(
        self, word_pack_id: str, category: str, items: Sequence[Mapping[str, Any]]
    ) -> int:
        if not items:
            return 0
        docs = [doc for doc in self._examples_for_pack(word_pack_id) if doc["category"] == category]
        start_pos = max((int(doc["position"]) for doc in docs), default=-1) + 1
        now = _now_iso()
        ids = self._wordpacks.reserve_example_ids(len(items))
        id_iter = iter(ids)
        pack_meta = self._wordpacks.get_word_pack_metadata(word_pack_id) or {}
        lemma_label = str(pack_meta.get("lemma_label") or "")
        sense_title = str(pack_meta.get("sense_title") or "")
        inserted = 0
        for item in items:
            en = str((item or {}).get("en") or "").strip()
            ja = str((item or {}).get("ja") or "").strip()
            if not en or not ja:
                continue
            grammar_ja = str((item or {}).get("grammar_ja") or "").strip() or None
            llm_model = str((item or {}).get("llm_model") or "").strip() or None
            llm_params = str((item or {}).get("llm_params") or "").strip() or None
            checked_only_count = normalize_non_negative_int((item or {}).get("checked_only_count"))
            learned_count = normalize_non_negative_int((item or {}).get("learned_count"))
            transcription_typing = normalize_non_negative_int(
                (item or {}).get("transcription_typing_count")
            )
            doc_id = str(next(id_iter))
            self._examples.document(doc_id).set(
                {
                    "example_id": int(doc_id),
                    "word_pack_id": word_pack_id,
                    "category": category,
                    "position": start_pos + inserted,
                    "en": en,
                    "ja": ja,
                    "grammar_ja": grammar_ja,
                    "llm_model": llm_model,
                    "llm_params": llm_params,
                    "checked_only_count": checked_only_count,
                    "learned_count": learned_count,
                    "transcription_typing_count": transcription_typing,
                    "created_at": now,
                    "pack_updated_at": now,
                    "lemma": lemma_label,
                    "sense_title": sense_title,
                }
            )
            inserted += 1
        self._refresh_category_counts(word_pack_id)
        self._wordpacks.update_word_pack_metadata(word_pack_id, updated_at=now)
        return inserted

    def count_examples(
        self,
        *,
        search: str | None = None,
        search_mode: str = "contains",
        category: str | None = None,
    ) -> int:
        return len(
            self._filter_examples(
                search=search,
                search_mode=search_mode,
                category=category,
            )
        )

    def list_examples(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        order_by: str = "created_at",
        order_dir: str = "desc",
        search: str | None = None,
        search_mode: str = "contains",
        category: str | None = None,
    ) -> list[
        tuple[int, str, str, str, str, str, str | None, str, str | None, int, int, int]
    ]:
        items = self._filter_examples(search=search, search_mode=search_mode, category=category)
        reverse = str(order_dir).lower() == "desc"
        key_map = {
            "created_at": lambda d: str(d.get("created_at") or ""),
            "pack_updated_at": lambda d: str(d.get("pack_updated_at") or ""),
            "lemma": lambda d: str(d.get("lemma") or ""),
            "category": lambda d: str(d.get("category") or ""),
        }
        sort_key = key_map.get(order_by, key_map["created_at"])
        items.sort(key=sort_key, reverse=reverse)
        sliced = items[offset : offset + limit]
        result: list[
            tuple[int, str, str, str, str, str, str | None, str, str | None, int, int, int]
        ] = []
        for doc in sliced:
            result.append(
                (
                    int(doc["example_id"]),
                    str(doc["word_pack_id"]),
                    str(doc.get("lemma") or ""),
                    str(doc.get("category") or ""),
                    str(doc.get("en") or ""),
                    str(doc.get("ja") or ""),
                    doc.get("grammar_ja"),
                    str(doc.get("created_at") or ""),
                    str(doc.get("pack_updated_at") or ""),
                    normalize_non_negative_int(doc.get("checked_only_count")),
                    normalize_non_negative_int(doc.get("learned_count")),
                    normalize_non_negative_int(doc.get("transcription_typing_count")),
                )
            )
        return result

    def update_example_transcription_typing(
        self, example_id: int, input_length: int
    ) -> int | None:
        doc_ref = self._examples.document(str(example_id))
        snapshot = doc_ref.get()
        if not snapshot.exists:
            return None
        data = snapshot.to_dict() or {}
        try:
            normalized_length = int(input_length)
        except (TypeError, ValueError) as exc:
            raise ValueError("input length must be convertible to int") from exc
        if normalized_length <= 0:
            raise ValueError("input length must be positive")
        expected_length = len(str(data.get("en") or ""))
        if abs(expected_length - normalized_length) > 10:
            raise ValueError("input length deviates from sentence length beyond tolerance")
        current = normalize_non_negative_int(data.get("transcription_typing_count"))
        updated = current + normalized_length
        doc_ref.update({"transcription_typing_count": updated})
        return updated

    def _examples_for_pack(self, word_pack_id: str) -> list[dict[str, Any]]:
        docs: list[dict[str, Any]] = []
        for snapshot in self._examples.stream():
            data = snapshot.to_dict() or {}
            if data.get("word_pack_id") != word_pack_id:
                continue
            entry = dict(data)
            entry["category"] = str(entry.get("category") or "")
            entry["position"] = int(entry.get("position") or 0)
            example_id = entry.get("example_id")
            if example_id is None:
                example_id = int(snapshot.id) if snapshot.id.isdigit() else snapshot.id
            entry["example_id"] = example_id
            docs.append(entry)
        return docs

    def _reindex_category(self, word_pack_id: str, category: str) -> None:
        docs = [doc for doc in self._examples_for_pack(word_pack_id) if doc["category"] == category]
        docs.sort(key=lambda d: (int(d["position"]), int(d["example_id"])))
        for new_pos, doc in enumerate(docs):
            self._examples.document(str(doc["example_id"])).update({"position": new_pos})

    def _refresh_category_counts(self, word_pack_id: str) -> None:
        counts = defaultdict(int)
        for doc in self._examples_for_pack(word_pack_id):
            counts[str(doc.get("category") or "Common")] += 1
        normalized = {cat: counts.get(cat, 0) for cat in EXAMPLE_CATEGORIES}
        self._wordpacks.update_word_pack_metadata(
            word_pack_id, category_counts=normalized
        )

    def _filter_examples(
        self,
        *,
        search: str | None,
        search_mode: str,
        category: str | None,
    ) -> list[dict[str, Any]]:
        docs: list[dict[str, Any]] = []
        raw = list(self._examples.stream())
        query = str((search or "").strip())
        query_lower = query.lower()
        pack_cache: dict[str, Mapping[str, Any]] = {}
        for snapshot in raw:
            data = snapshot.to_dict() or {}
            if category and data.get("category") != category:
                continue
            en_value = str(data.get("en") or "")
            if query:
                en_lower = en_value.lower()
                if search_mode == "prefix" and not en_lower.startswith(query_lower):
                    continue
                if search_mode == "suffix" and not en_lower.endswith(query_lower):
                    continue
                if search_mode not in ("prefix", "suffix") and query_lower not in en_lower:
                    continue
            entry = dict(data)
            entry.setdefault("example_id", int(snapshot.id) if snapshot.id.isdigit() else snapshot.id)
            pack_id = str(entry.get("word_pack_id") or "")
            if pack_id and pack_id not in pack_cache:
                meta = self._wordpacks.get_word_pack_metadata(pack_id)
                if meta is None:
                    meta = {}
                pack_cache[pack_id] = meta
            meta = pack_cache.get(pack_id, {})
            if not entry.get("lemma") and meta:
                entry["lemma"] = meta.get("lemma_label")
            if meta:
                entry["pack_updated_at"] = meta.get("updated_at")
            docs.append(entry)
        return docs


class FirestoreArticleStore(FirestoreBaseStore):
    """記事と WordPack リンクを Firestore で管理する。"""

    def __init__(self, client: firestore.Client):
        super().__init__(client)
        self._articles = client.collection("articles")
        self._article_word_packs = client.collection("article_word_packs")

    def save_article(
        self,
        article_id: str,
        **kwargs: Any,
    ) -> None:
        now = _now_iso()
        related_word_packs = kwargs.pop("related_word_packs", None)
        created_at = kwargs.pop("created_at", None)
        updated_at = kwargs.pop("updated_at", None)
        generation_started_at = kwargs.pop("generation_started_at", None)
        generation_completed_at = kwargs.pop("generation_completed_at", None)
        generation_duration_ms = kwargs.pop("generation_duration_ms", None)
        doc_ref = self._articles.document(article_id)
        existing = doc_ref.get()
        stored = existing.to_dict() if existing.exists else {}
        payload = {
            "title_en": kwargs.get("title_en"),
            "body_en": kwargs.get("body_en"),
            "body_ja": kwargs.get("body_ja"),
            "notes_ja": kwargs.get("notes_ja"),
            "llm_model": kwargs.get("llm_model"),
            "llm_params": kwargs.get("llm_params"),
            "generation_category": kwargs.get("generation_category"),
            "created_at": created_at or stored.get("created_at") or now,
            "updated_at": updated_at or now,
            "generation_started_at": generation_started_at or stored.get("generation_started_at") or created_at or now,
            "generation_completed_at": generation_completed_at or stored.get("generation_completed_at") or updated_at or now,
            "generation_duration_ms": (
                int(generation_duration_ms)
                if generation_duration_ms is not None
                else stored.get("generation_duration_ms")
            ),
        }
        doc_ref.set(payload, merge=True)
        if related_word_packs is not None:
            for snapshot in list(self._article_word_packs.stream()):
                data = snapshot.to_dict() or {}
                if data.get("article_id") == article_id:
                    snapshot.reference.delete()
            for wp_id, lemma, status in related_word_packs:
                link_id = f"{article_id}:{wp_id}"
                self._article_word_packs.document(link_id).set(
                    {
                        "article_id": article_id,
                        "word_pack_id": wp_id,
                        "lemma": lemma,
                        "status": status,
                        "created_at": now,
                    }
                )

    def get_article(
        self,
        article_id: str,
    ) -> tuple[
        str,
        str,
        str,
        str | None,
        str | None,
        str | None,
        str | None,
        str,
        str,
        str | None,
        str | None,
        int | None,
        list[tuple[str, str, str]],
    ] | None:
        doc = self._articles.document(article_id).get()
        if not doc.exists:
            return None
        data = doc.to_dict() or {}
        related: list[tuple[str, str, str]] = []
        for snapshot in self._article_word_packs.stream():
            link = snapshot.to_dict() or {}
            if link.get("article_id") != article_id:
                continue
            related.append(
                (
                    str(link.get("word_pack_id") or ""),
                    str(link.get("lemma") or ""),
                    str(link.get("status") or ""),
                )
            )
        return (
            str(data.get("title_en") or ""),
            str(data.get("body_en") or ""),
            str(data.get("body_ja") or ""),
            data.get("notes_ja"),
            data.get("llm_model"),
            data.get("llm_params"),
            data.get("generation_category"),
            str(data.get("created_at") or ""),
            str(data.get("updated_at") or ""),
            data.get("generation_started_at"),
            data.get("generation_completed_at"),
            data.get("generation_duration_ms"),
            related,
        )

    def list_articles(self, limit: int = 50, offset: int = 0) -> list[tuple[str, str, str, str]]:
        docs = list(self._articles.stream())
        docs.sort(key=lambda d: str((d.to_dict() or {}).get("created_at") or ""), reverse=True)
        sliced = docs[offset : offset + limit]
        return [
            (
                doc.id,
                str((doc.to_dict() or {}).get("title_en") or ""),
                str((doc.to_dict() or {}).get("created_at") or ""),
                str((doc.to_dict() or {}).get("updated_at") or ""),
            )
            for doc in sliced
        ]

    def count_articles(self) -> int:
        return sum(1 for _ in self._articles.stream())

    def delete_article(self, article_id: str) -> bool:
        doc_ref = self._articles.document(article_id)
        snapshot = doc_ref.get()
        if not snapshot.exists:
            return False
        doc_ref.delete()
        for link in list(self._article_word_packs.stream()):
            data = link.to_dict() or {}
            if data.get("article_id") == article_id:
                link.reference.delete()
        return True


class AppFirestoreStore:
    """Firestore 版のアプリ永続化ストア。"""

    def __init__(self, *, client: firestore.Client | None = None) -> None:
        self._client = client or firestore.Client()
        self.users = FirestoreUserStore(self._client)
        self.wordpacks = FirestoreWordPackStore(self._client)
        self.examples = FirestoreExampleStore(self._client, self.wordpacks)
        self.articles = FirestoreArticleStore(self._client)

    # --- Users ---
    def record_user_login(
        self,
        *,
        google_sub: str,
        email: str,
        display_name: str,
        login_at: datetime | None = None,
    ) -> dict[str, str]:
        return self.users.record_user_login(
            google_sub=google_sub,
            email=email,
            display_name=display_name,
            login_at=login_at,
        )

    def get_user_by_google_sub(self, google_sub: str) -> dict[str, str] | None:
        return self.users.get_user_by_google_sub(google_sub)

    def delete_user(self, google_sub: str) -> None:
        self.users.delete_user(google_sub)

    # --- WordPacks ---
    def save_word_pack(self, word_pack_id: str, lemma: str, data: str) -> None:
        self.wordpacks.save_word_pack(word_pack_id, lemma, data)

    def get_word_pack(self, word_pack_id: str) -> tuple[str, str, str, str] | None:
        return self.wordpacks.get_word_pack(word_pack_id)

    def list_word_packs(self, limit: int = 50, offset: int = 0) -> list[tuple[str, str, str, str, str]]:
        return self.wordpacks.list_word_packs(limit=limit, offset=offset)

    def count_word_packs(self) -> int:
        return self.wordpacks.count_word_packs()

    def list_word_packs_with_flags(
        self, limit: int = 50, offset: int = 0
    ) -> list[tuple[str, str, str, str, str, bool, Mapping[str, int], int, int]]:
        return self.wordpacks.list_word_packs_with_flags(limit=limit, offset=offset)

    def delete_word_pack(self, word_pack_id: str) -> bool:
        return self.wordpacks.delete_word_pack(word_pack_id)

    def update_word_pack_study_progress(
        self, word_pack_id: str, checked_increment: int, learned_increment: int
    ) -> tuple[int, int] | None:
        return self.wordpacks.update_word_pack_study_progress(
            word_pack_id, checked_increment, learned_increment
        )

    def find_word_pack_id_by_lemma(self, lemma: str) -> str | None:
        return self.wordpacks.find_word_pack_id_by_lemma(lemma)

    def find_word_pack_by_lemma_ci(self, lemma: str) -> tuple[str, str, str] | None:
        return self.wordpacks.find_word_pack_by_lemma_ci(lemma)

    # --- Examples ---
    def update_example_study_progress(
        self, example_id: int, checked_increment: int, learned_increment: int
    ) -> tuple[str, int, int] | None:
        return self.examples.update_example_study_progress(
            example_id, checked_increment, learned_increment
        )

    def delete_example(self, word_pack_id: str, category: str, index: int) -> int | None:
        return self.examples.delete_example(word_pack_id, category, index)

    def delete_examples_by_ids(
        self, example_ids: Iterable[int]
    ) -> tuple[int, list[int]]:
        return self.examples.delete_examples_by_ids(example_ids)

    def append_examples(
        self, word_pack_id: str, category: str, items: Sequence[Mapping[str, Any]]
    ) -> int:
        return self.examples.append_examples(word_pack_id, category, items)

    def count_examples(
        self,
        *,
        search: str | None = None,
        search_mode: str = "contains",
        category: str | None = None,
    ) -> int:
        return self.examples.count_examples(search=search, search_mode=search_mode, category=category)

    def list_examples(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        order_by: str = "created_at",
        order_dir: str = "desc",
        search: str | None = None,
        search_mode: str = "contains",
        category: str | None = None,
    ) -> list[
        tuple[int, str, str, str, str, str, str | None, str, str | None, int, int, int]
    ]:
        return self.examples.list_examples(
            limit=limit,
            offset=offset,
            order_by=order_by,
            order_dir=order_dir,
            search=search,
            search_mode=search_mode,
            category=category,
        )

    def update_example_transcription_typing(
        self, example_id: int, input_length: int
    ) -> int | None:
        return self.examples.update_example_transcription_typing(example_id, input_length)

    # --- Articles ---
    def save_article(self, article_id: str, **kwargs: Any) -> None:
        self.articles.save_article(article_id, **kwargs)

    def get_article(
        self, article_id: str
    ) -> tuple[
        str,
        str,
        str,
        str | None,
        str | None,
        str | None,
        str | None,
        str,
        str,
        str | None,
        str | None,
        int | None,
        list[tuple[str, str, str]],
    ] | None:
        return self.articles.get_article(article_id)

    def list_articles(self, limit: int = 50, offset: int = 0) -> list[tuple[str, str, str, str]]:
        return self.articles.list_articles(limit=limit, offset=offset)

    def count_articles(self) -> int:
        return self.articles.count_articles()

    def delete_article(self, article_id: str) -> bool:
        return self.articles.delete_article(article_id)
