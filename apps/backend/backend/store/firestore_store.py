from __future__ import annotations

import json
import uuid
from threading import Lock
from collections import defaultdict
from collections.abc import Iterable, Iterator, Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

from google.api_core import exceptions as gexc
from google.api_core.exceptions import AlreadyExists
from google.cloud import firestore

from ..logging import logger
from ..sense_title import choose_sense_title
from .common import normalize_non_negative_int
from .examples import EXAMPLE_CATEGORIES, iter_example_rows
from .wordpacks import merge_core_with_examples, split_examples_from_payload


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _extract_count_from_aggregation(
    aggregation: Sequence[Any] | None,
) -> int:
    """Extracts the numeric count from Firestore aggregation results."""

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


def _normalize_search_text(text: str | None) -> str:
    """検索用に英文を正規化（小文字化・前後空白除去）する。"""

    return str((text or "").strip()).lower()


def _extract_search_terms(normalized_text: str) -> list[str]:
    """部分一致検索のために短いN-gramとトークンを抽出する。"""

    compact = normalized_text.replace("\n", " ")
    terms: set[str] = set()
    for token in compact.replace("/", " ").replace(",", " ").split():
        stripped = token.strip()
        if stripped:
            terms.add(stripped)
    condensed = normalized_text.replace(" ", "")
    for size in (1, 2, 3):
        if len(condensed) < size:
            continue
        for idx in range(len(condensed) - size + 1):
            terms.add(condensed[idx : idx + size])
    return sorted(terms)


def _build_search_payload(en: str) -> dict[str, Any]:
    normalized = _normalize_search_text(en)
    return {
        "search_en": normalized,
        "search_en_reversed": normalized[::-1],
        "search_terms": _extract_search_terms(normalized),
    }


def _extract_example_total(
    metadata: Mapping[str, Any] | None,
) -> tuple[int, bool]:
    """examples_category_counts から合計件数を抽出し、信頼性の有無を返す。"""

    raw_counts = (metadata or {}).get("examples_category_counts")
    if not isinstance(raw_counts, Mapping):
        return 0, False
    try:
        total = sum(int(raw_counts.get(cat, 0) or 0) for cat in EXAMPLE_CATEGORIES)
    except Exception:
        return 0, False
    return max(0, total), True


def _coerce_firestore_snapshot(
    candidate: Any,
) -> firestore.DocumentSnapshot | None:
    """Normalize Firestore transaction.get results (snapshot or generator) into a snapshot."""

    if candidate is None:
        return None
    if hasattr(candidate, "exists"):
        return candidate  # type: ignore[return-value]
    if isinstance(candidate, Iterator):
        return next(candidate, None)
    if isinstance(candidate, Iterable) and not isinstance(candidate, (str, bytes, Mapping)):
        iterator = iter(candidate)
        return next(iterator, None)
    return None


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

    _EXAMPLE_DELETE_BATCH_SIZE = 450
    _WORD_PACK_LOOKUP_RETRIES = 1

    def __init__(self, client: firestore.Client):
        super().__init__(client)
        self._lemmas = client.collection("lemmas")
        self._word_packs = client.collection("word_packs")
        self._examples = client.collection("examples")
        self._metadata = client.collection("metadata")
        # lemma upsert の局所衝突を避けるための簡易ロック
        self._lemma_write_lock = Lock()

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
        existing_data = existing.to_dict() or {}
        existing_examples_total, counts_confident = _extract_example_total(existing_data)
        created_at = (
            str(existing_data.get("created_at") or now) if existing.exists else now
        )
        category_counts = self._replace_examples(
            word_pack_id,
            lemma=lemma,
            sense_title=sense_title,
            examples=examples,
            updated_at=now,
            existing_example_total=existing_examples_total,
            is_total_confident=counts_confident,
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
        return _extract_count_from_aggregation(aggregation)

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
        data = snapshot.to_dict() or {}
        existing_total, is_confident = _extract_example_total(data)
        should_delete_examples = not is_confident or existing_total > 0
        if should_delete_examples:
            self._delete_examples(
                word_pack_id, expected_count=existing_total if is_confident else None
            )
        doc_ref.delete()
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

    def find_word_pack_id_by_lemma(
        self, lemma: str, *, diagnostics: bool = False
    ) -> str | None | tuple[str | None, bool]:
        """大文字小文字を無視した lemma で WordPack ID を検索する。"""

        target = str(lemma or "").strip().lower()
        last_error: Exception | None = None

        for attempt in range(self._WORD_PACK_LOOKUP_RETRIES + 1):
            try:
                # lemma_label_lower の等価フィルタと更新日時降順の複合クエリで最新1件のみを取得し、全件走査を避ける。
                query = (
                    self._word_packs.where("lemma_label_lower", "==", target)
                    .order_by("updated_at", direction=firestore.Query.DESCENDING)
                    .limit(1)
                )
                for doc in query.stream():
                    return (doc.id, last_error is not None) if diagnostics else doc.id
                return (None, last_error is not None) if diagnostics else None
            except gexc.GoogleAPIError as exc:
                last_error = exc
                logger.warning(
                    "firestore_wordpack_lookup_retry",
                    lemma=target,
                    attempt=attempt + 1,
                    error=str(exc),
                    error_class=exc.__class__.__name__,
                )
                continue
            except Exception as exc:  # pragma: no cover - defensive guardrail
                last_error = exc
                logger.error(
                    "firestore_wordpack_lookup_error",
                    lemma=target,
                    attempt=attempt + 1,
                    error=str(exc),
                    error_class=exc.__class__.__name__,
                )
                break

        if last_error is not None:
            logger.error(
                "firestore_wordpack_lookup_give_up",
                lemma=target,
                attempts=self._WORD_PACK_LOOKUP_RETRIES + 1,
                error=str(last_error),
                error_class=last_error.__class__.__name__,
            )
        return (None, last_error is not None) if diagnostics else None

    def find_word_pack_by_lemma_ci(self, lemma: str) -> tuple[str, str, str] | None:
        target = str(lemma or "").strip().lower()
        # 最新の WordPack を 1 件だけ取得するため、Firestore 側の order_by + limit で走査量を抑える。
        query = (
            self._word_packs.where("lemma_label_lower", "==", target)
            .order_by("updated_at", direction=firestore.Query.DESCENDING)
            .limit(1)
        )
        for doc in query.stream():
            data = doc.to_dict() or {}
            return (
                doc.id,
                str(data.get("lemma_label") or ""),
                str(data.get("sense_title") or ""),
            )
        return None

    def reserve_example_ids(self, count: int) -> list[int]:
        return self._allocate_example_ids(count)

    def _delete_examples(self, word_pack_id: str, *, expected_count: int | None = None) -> None:
        """対象 WordPack の例文だけをページングしながら削除する。

        Firestore のバッチ上限（500件）に合わせて limit 付きクエリを繰り返し、
        1 回のコミットで触るドキュメント数を O(k) に抑える。expected_count が
        0 の場合はクエリ自体を発行しないことで無駄な読み出しを避ける。
        """

        if expected_count is not None and max(0, int(expected_count)) == 0:
            return

        batch_size = max(1, int(self._EXAMPLE_DELETE_BATCH_SIZE))
        base_query = (
            self._examples.where("word_pack_id", "==", word_pack_id)
            .order_by("__name__")
        )
        query = base_query.limit(batch_size)

        while True:
            snapshots = list(query.stream())
            if not snapshots:
                break

            batch = self._client.batch()
            for snapshot in snapshots:
                batch.delete(snapshot.reference)
            batch.commit()

            if len(snapshots) < batch_size:
                break
            query = base_query.start_after(snapshots[-1]).limit(batch_size)

    def _replace_examples(
        self,
        word_pack_id: str,
        *,
        lemma: str,
        sense_title: str,
        examples: Mapping[str, Any] | None,
        updated_at: str,
        existing_example_total: int | None = None,
        is_total_confident: bool = False,
    ) -> dict[str, int]:
        # 例文数が 0 だと確実に分かっている場合のみ削除クエリを省略し、それ以外では安全側に倒す。
        should_delete_existing = not is_total_confident or existing_example_total not in (None, 0)
        if should_delete_existing:
            self._delete_examples(
                word_pack_id,
                expected_count=existing_example_total if is_total_confident else None,
            )
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
                    **_build_search_payload(en),
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

        def _allocate_without_transaction() -> list[int]:
            snapshot = counter_ref.get()
            current = int((snapshot.to_dict() or {}).get("next_id", 1))
            ids = list(range(current, current + count))
            counter_ref.set({"next_id": current + count}, merge=True)
            return ids

        try:
            transaction = self._client.transaction()
        except AttributeError:  # pragma: no cover - defensive fallback
            transaction = None
        except Exception as exc:  # pragma: no cover - best-effort guard
            logger.warning(
                "firestore_allocate_ids_transaction_failed",
                error=str(exc),
                error_class=exc.__class__.__name__,
                stage="init",
            )
            transaction = None

        if transaction is None:
            return _allocate_without_transaction()

        try:
            transaction._begin()
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.warning(
                "firestore_allocate_ids_transaction_failed",
                error=str(exc),
                error_class=exc.__class__.__name__,
                stage="begin",
            )
            return _allocate_without_transaction()

        try:
            snapshot = _coerce_firestore_snapshot(transaction.get(counter_ref))
            current_payload = (snapshot.to_dict() if snapshot is not None else {}) or {}
            current = int(current_payload.get("next_id", 1))
            ids = list(range(current, current + count))
            transaction.set(counter_ref, {"next_id": current + count}, merge=True)
            transaction._commit()
            return ids
        except (ValueError, gexc.GoogleAPIError) as exc:
            try:
                transaction._rollback()
            except Exception:  # pragma: no cover - rollback best-effort
                pass
            logger.warning(
                "firestore_allocate_ids_transaction_failed",
                error=str(exc),
                error_class=exc.__class__.__name__,
                stage="body",
            )
        except Exception as exc:  # pragma: no cover - defensive guard
            try:
                transaction._rollback()
            except Exception:  # pragma: no cover - rollback best-effort
                pass
            logger.warning(
                "firestore_allocate_ids_transaction_failed",
                error=str(exc),
                error_class=exc.__class__.__name__,
                stage="body",
            )
        return _allocate_without_transaction()

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
        """正規化済みの lemma を単一ドキュメントへ upsert する。

        - 正規化ラベル（小文字化）を Firestore ドキュメントIDとして優先採用し、
          lookup を O(1) 化する。
        - 既存データ（旧ID形式）は normalized_label インデックスを用いた単一件
          クエリで探し、互換性を維持する。
        - create + exists チェックで同時書き込みによる重複作成を防ぎ、
          競合時は既存ドキュメントを再利用する。
        """
        original_label = str(label or "").strip()
        if not original_label:
            raise ValueError("lemma label must not be empty")
        normalized = original_label.lower()
        normalized_ref = self._lemmas.document(normalized)
        normalized_snapshot = normalized_ref.get()

        def _update_existing(snapshot: firestore.DocumentSnapshot) -> str:
            data = snapshot.to_dict() or {}
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
            # normalized_label を確実に維持するため merge で更新する
            snapshot.reference.set(
                {
                    "label": new_label,
                    "normalized_label": normalized,
                    "sense_title": new_sense,
                    "llm_model": new_llm_model,
                    "llm_params": new_llm_params,
                },
                merge=True,
            )
            return snapshot.id

        if normalized_snapshot.exists:
            return _update_existing(normalized_snapshot)

        existing_snapshot = next(
            iter(
                self._lemmas.where("normalized_label", "==", normalized)
                .limit(1)
                .stream()
            ),
            None,
        )
        if existing_snapshot is not None:
            return _update_existing(existing_snapshot)

        payload = {
            "label": original_label,
            "normalized_label": normalized,
            "sense_title": sense_title or "",
            "llm_model": llm_model,
            "llm_params": llm_params,
            "created_at": now,
        }
        try:
            transaction = self._client.transaction()
        except AttributeError:  # pragma: no cover - defensive fallback
            transaction = None
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.warning(
                "firestore_upsert_lemma_transaction_failed",
                label=original_label,
                normalized_label=normalized,
                error=str(exc),
                error_class=exc.__class__.__name__,
                stage="init",
            )
            transaction = None

        if transaction is not None:
            try:
                transaction._begin()
            except Exception as exc:  # pragma: no cover - defensive guard
                logger.warning(
                    "firestore_upsert_lemma_transaction_failed",
                    label=original_label,
                    normalized_label=normalized,
                    error=str(exc),
                    error_class=exc.__class__.__name__,
                    stage="begin",
                )
                transaction = None

        if transaction is not None:
            try:
                with self._lemma_write_lock:
                    snapshot = _coerce_firestore_snapshot(transaction.get(normalized_ref))
                    if snapshot is not None and snapshot.exists:
                        transaction._rollback()
                        return _update_existing(snapshot)
                    try:
                        transaction.create(normalized_ref, payload)
                    except AlreadyExists:
                        transaction._rollback()
                        existing = normalized_ref.get()
                        if existing.exists:
                            return _update_existing(existing)
                transaction._commit()
                return normalized_ref.id
            except (ValueError, gexc.GoogleAPIError) as exc:
                try:
                    transaction._rollback()
                except Exception:  # pragma: no cover - rollback best-effort
                    pass
                logger.warning(
                    "firestore_upsert_lemma_transaction_failed",
                    label=original_label,
                    normalized_label=normalized,
                    error=str(exc),
                    error_class=exc.__class__.__name__,
                    stage="body",
                )
            except Exception as exc:  # pragma: no cover - defensive guard
                try:
                    transaction._rollback()
                except Exception:  # pragma: no cover - rollback best-effort
                    pass
                logger.warning(
                    "firestore_upsert_lemma_transaction_failed",
                    label=original_label,
                    normalized_label=normalized,
                    error=str(exc),
                    error_class=exc.__class__.__name__,
                    stage="body",
                )

        try:
            normalized_ref.create(payload)
            return normalized_ref.id
        except AlreadyExists:
            fallback_snapshot = normalized_ref.get()
            if fallback_snapshot.exists:
                return _update_existing(fallback_snapshot)
            legacy_snapshot = next(
                iter(
                    self._lemmas.where("normalized_label", "==", normalized)
                    .limit(1)
                    .stream()
                ),
                None,
            )
            if legacy_snapshot is not None:
                return _update_existing(legacy_snapshot)
            # create が競合し、かつ再取得でも無い場合は新IDで再生成しておく
            lemma_id = f"lm:{normalized}:{uuid.uuid4().hex[:8]}"
            self._lemmas.document(lemma_id).set(payload)
            return lemma_id


class FirestoreExampleStore(FirestoreBaseStore):
    """例文に関する Firestore CRUD。"""

    def __init__(self, client: firestore.Client, wordpacks: FirestoreWordPackStore):
        super().__init__(client)
        self._examples = client.collection("examples")
        self._wordpacks = wordpacks

    def _build_examples_query(
        self, *, word_pack_id: str | None = None, category: str | None = None
    ) -> firestore.Query | firestore.CollectionReference:
        """Create a query that narrows down examples by pack/category."""

        query: firestore.Query | firestore.CollectionReference = self._examples
        if word_pack_id:
            query = query.where("word_pack_id", "==", word_pack_id)
        if category:
            query = query.where("category", "==", category)
        return query

    def _apply_search_filters(
        self,
        query: firestore.Query | firestore.CollectionReference,
        *,
        search: str | None,
        search_mode: str,
    ) -> tuple[firestore.Query | firestore.CollectionReference, str | None]:
        """検索条件を Firestore の where 節で表現し、必要な order_by キーを返す。"""

        normalized = _normalize_search_text(search)
        if not normalized:
            return query, None
        if search_mode == "prefix":
            upper_bound = normalized + "\uf8ff"
            query = query.where("search_en", ">=", normalized).where(
                "search_en", "<=", upper_bound
            )
            return query, "search_en"
        if search_mode == "suffix":
            reversed_query = normalized[::-1]
            upper_bound = reversed_query + "\uf8ff"
            query = query.where("search_en_reversed", ">=", reversed_query).where(
                "search_en_reversed", "<=", upper_bound
            )
            return query, "search_en_reversed"
        terms = _extract_search_terms(normalized)
        if not terms:
            return query, None

        most_specific_term = max(terms, key=lambda term: (len(term), term))
        query = query.where("search_terms", "array_contains", most_specific_term)
        return query, None

    def _paginate_ordered_query(
        self,
        query: firestore.Query | firestore.CollectionReference,
        *,
        primary_order: str,
        secondary_order: str | None,
        direction: firestore.Query.DESCENDING | firestore.Query.ASCENDING,
        offset: int,
        limit: int,
    ) -> list[firestore.DocumentSnapshot]:
        """order_by + start_after + limit を組み合わせたページングを適用する。"""

        ordered = query.order_by(primary_order, direction=direction)
        if secondary_order and secondary_order != primary_order:
            ordered = ordered.order_by(secondary_order, direction=direction)
        ordered = ordered.order_by("__name__", direction=direction)
        cursor: firestore.DocumentSnapshot | None = None
        if offset:
            cursor = None
            for snap in ordered.limit(offset).stream():
                cursor = snap
            if cursor is None:
                return []
            ordered = ordered.start_after(cursor)
        return list(ordered.limit(limit).stream())

    def _normalize_example_snapshot(
        self, snapshot: firestore.DocumentSnapshot
    ) -> dict[str, Any]:
        """Convert snapshot data into a normalized dict for downstream use."""

        data = snapshot.to_dict() or {}
        entry = dict(data)
        entry["category"] = str(entry.get("category") or "")
        entry["position"] = int(entry.get("position") or 0)
        entry["word_pack_id"] = str(entry.get("word_pack_id") or "")
        example_id = entry.get("example_id")
        if example_id is None:
            raw_id = snapshot.id
            example_id = int(raw_id) if str(raw_id).isdigit() else raw_id
        entry["example_id"] = example_id
        return entry

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
        query = (
            self._build_examples_query(word_pack_id=word_pack_id, category=category)
            .order_by("position")
            .order_by("example_id")
        )
        category_docs = [
            self._normalize_example_snapshot(snapshot) for snapshot in query.stream()
        ]
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
        last_snapshot = next(
            iter(
                self._build_examples_query(
                    word_pack_id=word_pack_id, category=category
                )
                .order_by("position", direction=firestore.Query.DESCENDING)
                .limit(1)
                .stream()
            ),
            None,
        )
        last_position = (
            int((last_snapshot.to_dict() or {}).get("position") or -1)
            if last_snapshot is not None
            else -1
        )
        start_pos = last_position + 1
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
                    **_build_search_payload(en),
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
        word_pack_id: str | None = None,
    ) -> int:
        base_query = self._build_examples_query(
            word_pack_id=word_pack_id, category=category
        )
        filtered_query, _order_hint = self._apply_search_filters(
            base_query, search=search, search_mode=search_mode
        )
        try:
            aggregation = filtered_query.count().get()
        except AttributeError:
            aggregation = None
        else:
            return _extract_count_from_aggregation(aggregation)
        return sum(1 for _ in filtered_query.stream())

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
        word_pack_id: str | None = None,
    ) -> list[
        tuple[int, str, str, str, str, str, str | None, str, str | None, int, int, int]
    ]:
        normalized_limit = max(0, int(limit))
        normalized_offset = max(0, int(offset))
        if normalized_limit == 0:
            return []

        direction = firestore.Query.DESCENDING
        if str(order_dir).lower() == "asc":
            direction = firestore.Query.ASCENDING

        order_map = {
            "created_at": "created_at",
            "pack_updated_at": "pack_updated_at",
            "lemma": "lemma",
            "category": "category",
        }
        requested_order = order_map.get(order_by, "created_at")
        base_query = self._build_examples_query(
            word_pack_id=word_pack_id, category=category
        )
        filtered_query, search_order = self._apply_search_filters(
            base_query, search=search, search_mode=search_mode
        )
        primary_order = search_order or requested_order
        snapshots = self._paginate_ordered_query(
            filtered_query,
            primary_order=primary_order,
            secondary_order=requested_order if search_order else None,
            direction=direction,
            offset=normalized_offset,
            limit=normalized_limit,
        )

        pack_cache: dict[str, Mapping[str, Any]] = {}
        results: list[
            tuple[int, str, str, str, str, str, str | None, str, str | None, int, int, int]
        ] = []
        for snapshot in snapshots:
            entry = self._normalize_example_snapshot(snapshot)
            pack_id = str(entry.get("word_pack_id") or "")
            if pack_id and pack_id not in pack_cache:
                pack_cache[pack_id] = (
                    self._wordpacks.get_word_pack_metadata(pack_id) or {}
                )
            meta = pack_cache.get(pack_id, {})
            if not entry.get("lemma") and meta:
                entry["lemma"] = meta.get("lemma_label")
            if meta and not entry.get("pack_updated_at"):
                entry["pack_updated_at"] = meta.get("updated_at")
            results.append(
                (
                    int(entry["example_id"]),
                    pack_id,
                    str(entry.get("lemma") or ""),
                    str(entry.get("category") or ""),
                    str(entry.get("en") or ""),
                    str(entry.get("ja") or ""),
                    entry.get("grammar_ja"),
                    str(entry.get("created_at") or ""),
                    str(entry.get("pack_updated_at") or ""),
                    normalize_non_negative_int(entry.get("checked_only_count")),
                    normalize_non_negative_int(entry.get("learned_count")),
                    normalize_non_negative_int(entry.get("transcription_typing_count")),
                )
            )
        return results

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
        query = self._build_examples_query(word_pack_id=word_pack_id)
        for snapshot in query.stream():
            docs.append(self._normalize_example_snapshot(snapshot))
        return docs

    def _reindex_category(self, word_pack_id: str, category: str) -> None:
        query = (
            self._build_examples_query(word_pack_id=word_pack_id, category=category)
            .order_by("position")
            .order_by("example_id")
        )
        docs = [self._normalize_example_snapshot(snapshot) for snapshot in query.stream()]
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

    def find_word_pack_id_by_lemma(
        self, lemma: str, *, diagnostics: bool = False
    ) -> str | None | tuple[str | None, bool]:
        return self.wordpacks.find_word_pack_id_by_lemma(
            lemma, diagnostics=diagnostics
        )

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
