from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

import pytest
from google.cloud import firestore

# ルート（apps/backend 配下）をテストから直接解決できるようにする。
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "apps" / "backend"))
import backend.store.firestore_store as firestore_module
from tests.firestore_fakes import (
    FakeAggregationQuery,
    FakeAggregationResult,
    FakeCollectionReference,
    FakeDocumentReference,
    FakeDocumentSnapshot,
    FakeFirestoreClient,
    FakeQuery,
    FakeTransaction,
)

AppFirestoreStore = firestore_module.AppFirestoreStore

@pytest.fixture()
def firestore_store() -> AppFirestoreStore:
    return AppFirestoreStore(client=FakeFirestoreClient())


def test_firestore_word_pack_roundtrip(firestore_store: AppFirestoreStore) -> None:
    payload = {
        "lemma": "Converge",
        "sense_title": "まとまる",
        "examples": {
            "Dev": [
                {"en": "Converge the commits", "ja": "コミットをまとめる", "checked_only_count": 2},
                {"en": "Signals converge", "ja": "信号が収束する"},
            ]
        },
    }
    firestore_store.save_word_pack("wp-1", payload["lemma"], json.dumps(payload, ensure_ascii=False))

    stored = firestore_store.get_word_pack("wp-1")
    assert stored is not None
    lemma, data_json, created_at, updated_at = stored
    assert lemma == "Converge"
    assert created_at <= updated_at
    data = json.loads(data_json)
    assert data["examples"]["Dev"][0]["en"] == "Converge the commits"
    assert data["examples"]["Dev"][0]["checked_only_count"] == 2


def test_firestore_example_progress_and_deletion(firestore_store: AppFirestoreStore) -> None:
    payload = {
        "lemma": "Refine",
        "examples": {
            "Dev": [{"en": "Refine the UI", "ja": "UIを磨く"}],
            "CS": [{"en": "Refine search", "ja": "検索精度を上げる"}],
        },
    }
    firestore_store.save_word_pack("wp-2", payload["lemma"], json.dumps(payload, ensure_ascii=False))
    listed = firestore_store.list_examples(limit=10)
    assert len(listed) == 2
    first_example_id = listed[0][0]

    pack_id, next_checked, next_learned = firestore_store.update_example_study_progress(
        first_example_id, 3, 1
    )
    assert pack_id == "wp-2"
    assert next_checked == 3
    assert next_learned == 1

    remaining = firestore_store.delete_example("wp-2", "Dev", 0)
    assert remaining == 0
    counts = firestore_store.wordpacks.list_word_packs_with_flags(limit=1)[0][6]
    assert counts["Dev"] == 0
    assert counts["CS"] == 1


def test_contains_search_prefers_specific_term(
    firestore_store: AppFirestoreStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = {
        "lemma": "Chunk",
        "examples": {
            "Dev": [
                {"en": "Analyze xyz value", "ja": "xyzの値を分析する"},
            ]
        },
    }
    firestore_store.save_word_pack(
        "wp-search", payload["lemma"], json.dumps(payload, ensure_ascii=False)
    )

    firestore_store.examples._examples.reset_query_log()
    firestore_store.list_examples(search="yz", search_mode="contains")

    filters = firestore_store.examples._examples.query_log[0]["filters"]
    assert ("search_terms", "array_contains", "yz") in filters


def test_list_word_packs_paginates_via_firestore_query(
    firestore_store: AppFirestoreStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    timestamps = iter(
        [
            "2024-01-01T00:00:01+00:00",
            "2024-01-01T00:00:02+00:00",
            "2024-01-01T00:00:03+00:00",
        ]
    )
    monkeypatch.setattr(firestore_module, "_now_iso", lambda: next(timestamps))

    for idx, lemma in enumerate(["Alpha", "Beta", "Gamma"], start=1):
        firestore_store.save_word_pack(
            f"wp-{idx}",
            lemma,
            json.dumps({"lemma": lemma, "examples": {}}, ensure_ascii=False),
        )

    first_page = firestore_store.list_word_packs(limit=2, offset=0)
    assert [row[1] for row in first_page] == ["Gamma", "Beta"]

    second_page = firestore_store.list_word_packs(limit=2, offset=2)
    assert [row[1] for row in second_page] == ["Alpha"]

    flagged_page = firestore_store.list_word_packs_with_flags(limit=1, offset=1)
    assert [row[1] for row in flagged_page] == ["Beta"]


def test_count_word_packs_uses_server_side_aggregation(
    firestore_store: AppFirestoreStore,
) -> None:
    for idx, lemma in enumerate(["Delta", "Echo"], start=1):
        firestore_store.save_word_pack(
            f"pack-{idx}",
            lemma,
            json.dumps({"lemma": lemma, "examples": {}}, ensure_ascii=False),
        )

    total = firestore_store.count_word_packs()
    assert total == 2
    assert firestore_store.wordpacks._word_packs.count_calls == 1


def test_find_word_pack_lookup_uses_filtered_query(
    firestore_store: AppFirestoreStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    """lemma 検索が limit(1) 付きのフィルタクエリになることを確認する。"""

    timestamps = iter(
        [
            "2024-05-01T10:00:00+00:00",
            "2024-05-02T11:00:00+00:00",
        ]
    )
    monkeypatch.setattr(firestore_module, "_now_iso", lambda: next(timestamps))

    payload = {"lemma": "LemmaX", "sense_title": "x", "examples": {}}
    firestore_store.save_word_pack(
        "wp-old", payload["lemma"], json.dumps(payload, ensure_ascii=False)
    )

    payload_new = {"lemma": "lemmax", "sense_title": "new", "examples": {}}
    firestore_store.save_word_pack(
        "wp-new", payload_new["lemma"], json.dumps(payload_new, ensure_ascii=False)
    )

    collection = firestore_store.wordpacks._word_packs
    collection.reset_query_log()

    result = firestore_store.find_word_pack_id_by_lemma("  LEMMAX  ")

    assert result == "wp-new"
    log = collection.query_log
    assert len(log) == 1
    assert ("lemma_label_lower", "==", "lemmax") in log[0]["filters"]
    assert log[0]["limit"] == 1
    assert log[0]["size"] == 1


def test_find_word_pack_with_metadata_uses_filtered_query(
    firestore_store: AppFirestoreStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    """find_word_pack_by_lemma_ci もフィルタ + limit で絞り込むことを検証する。"""

    timestamps = iter(
        [
            "2024-06-01T09:00:00+00:00",
            "2024-06-02T10:00:00+00:00",
        ]
    )
    monkeypatch.setattr(firestore_module, "_now_iso", lambda: next(timestamps))

    payload = {"lemma": "Resilient", "sense_title": "old", "examples": {}}
    firestore_store.save_word_pack(
        "wp-first", payload["lemma"], json.dumps(payload, ensure_ascii=False)
    )

    payload_new = {"lemma": "resilient", "sense_title": "latest", "examples": {}}
    firestore_store.save_word_pack(
        "wp-second", payload_new["lemma"], json.dumps(payload_new, ensure_ascii=False)
    )

    collection = firestore_store.wordpacks._word_packs
    collection.reset_query_log()

    found = firestore_store.find_word_pack_by_lemma_ci("resilient")

    assert found is not None
    assert found[0] == "wp-second"
    assert found[1].lower() == "resilient"
    assert len(collection.query_log) == 1
    entry = collection.query_log[0]
    assert ("lemma_label_lower", "==", "resilient") in entry["filters"]
    assert entry["limit"] == 1
    assert entry["size"] == 1


def test_store_factory_switches_to_firestore(monkeypatch: pytest.MonkeyPatch) -> None:
    import backend.store as store_module

    monkeypatch.setattr(store_module.settings, "environment", "production")

    sentinel = object()
    monkeypatch.setattr(store_module, "AppFirestoreStore", lambda: sentinel)
    new_store = store_module._create_store()
    assert new_store is sentinel


def test_example_queries_limit_scanned_documents(
    firestore_store: AppFirestoreStore,
) -> None:
    """大量データ下でも対象パックの件数だけを走査することを検証する。"""

    categories = ["Dev", "CS"]
    per_category = 10
    for idx in range(1, 16):
        lemma = f"Lemma-{idx}"
        payload = {
            "lemma": lemma,
            "examples": {
                cat: [
                    {"en": f"{cat} example {idx}-{n}", "ja": f"{cat} ja {idx}-{n}"}
                    for n in range(per_category)
                ]
                for cat in categories
            },
        }
        firestore_store.save_word_pack(
            f"mass-{idx}", lemma, json.dumps(payload, ensure_ascii=False)
        )

    target_pack = "mass-3"
    collection = firestore_store.examples._examples
    collection.reset_query_log()

    remaining = firestore_store.delete_example(target_pack, "Dev", 0)
    assert remaining == per_category - 1

    log = collection.query_log
    assert len(log) >= 3
    first, second, third = log[:3]

    assert ("word_pack_id", "==", target_pack) in first["filters"]
    assert ("category", "==", "Dev") in first["filters"]
    assert first["size"] == per_category

    assert ("word_pack_id", "==", target_pack) in second["filters"]
    assert ("category", "==", "Dev") in second["filters"]
    assert second["size"] == per_category - 1

    assert ("word_pack_id", "==", target_pack) in third["filters"]
    assert all(f[0] != "category" for f in third["filters"])
    total_examples_in_pack = per_category * len(categories) - 1
    assert third["size"] == total_examples_in_pack


def test_list_examples_paginates_on_server_side(
    firestore_store: AppFirestoreStore,
) -> None:
    """例文一覧のページングが Firestore クエリの limit/start_after に収まることを検証する。"""

    pack_id = "paging-pack"
    total_examples = 120
    payload = {
        "lemma": "Paginate",
        "examples": {
            "Dev": [
                {"en": f"Example {idx}", "ja": f"例文 {idx}"}
                for idx in range(total_examples)
            ]
        },
    }
    firestore_store.save_word_pack(
        pack_id, payload["lemma"], json.dumps(payload, ensure_ascii=False)
    )

    collection = firestore_store.examples._examples
    collection.reset_query_log()

    page = firestore_store.list_examples(limit=50, offset=50)

    assert len(page) == 50
    assert collection.query_log, "expected queries to be recorded"
    assert len(collection.query_log) == 2
    assert max(entry["size"] for entry in collection.query_log) <= 50
    assert sum(entry["size"] for entry in collection.query_log) <= 100