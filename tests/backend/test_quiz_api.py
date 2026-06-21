from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient

from tests.firestore_fakes import FakeFirestoreClient
from tests.test_api import _reload_backend_app

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "apps" / "backend"))


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    backend_main = _reload_backend_app(
        monkeypatch,
        strict=False,
        firestore_client=FakeFirestoreClient(),
    )
    return TestClient(backend_main.app)


def _quiz_payload(*, quiz_id: str = "quiz:api", guest_public: bool = False) -> dict:
    return {
        "id": quiz_id,
        "title_en": "Reliable API Deployments",
        "format_profile": "single_passage",
        "generation_domain": "technical",
        "domain_intensity": "standard",
        "difficulty": "medium",
        "passages": [
            {
                "id": "p1",
                "order": 1,
                "kind": "article",
                "title": "Deployment review",
                "body_en": "Teams mitigate latency by adding a fallback.",
                "body_ja": "チームはフォールバックを追加してレイテンシを軽減する。",
                "speaker_labels": [],
            }
        ],
        "notes_ja": "根拠を本文から確認します。",
        "sections": [
            {
                "id": "s1",
                "order": 1,
                "title": "Reading",
                "description_ja": "本文理解",
                "passage_ids": ["p1"],
                "questions": [
                    {
                        "id": "q1",
                        "order": 1,
                        "type": "detail",
                        "prompt": "What reduces latency?",
                        "choices": [
                            {"id": "A", "text": "A fallback"},
                            {"id": "B", "text": "A redesign"},
                            {"id": "C", "text": "A delay"},
                            {"id": "D", "text": "A meeting"},
                        ],
                        "correct_choice_id": "A",
                        "explanation": {
                            "explanation_ja": "fallback が latency を軽減する根拠です。",
                            "evidence_passage_id": "p1",
                            "evidence_text": "mitigate latency by adding a fallback",
                            "evidence_start": 6,
                            "evidence_end": 43,
                            "wrong_choice_explanations_ja": {"B": "本文にありません。"},
                            "related_lemmas": ["mitigate", "latency", "fallback"],
                        },
                    }
                ],
            }
        ],
        "related_word_packs": [
            {
                "word_pack_id": "wp:mitigate",
                "lemma": "mitigate",
                "status": "existing",
                "is_empty": False,
                "occurrences": [{"passage_id": "p1", "start": 6, "end": 14}],
                "warning": None,
            }
        ],
        "source_word_pack_ids": ["wp:mitigate"],
        "source_lemmas": ["mitigate"],
        "topic_seed": "API deploy",
        "avoid_topics": [],
        "llm_model": "gpt-5.4-mini",
        "llm_params": "reasoning.effort=minimal;text.verbosity=medium",
        "guest_public": guest_public,
        "created_at": "2024-01-01T00:00:00+00:00",
        "updated_at": "2024-01-02T00:00:00+00:00",
    }


def _seed_quiz(quiz_id: str = "quiz:api") -> None:
    from backend.store import store as backend_store

    payload = _quiz_payload(quiz_id=quiz_id)
    backend_store.save_quiz(
        quiz_id,
        payload,
        payload["related_word_packs"],
    )


def test_quiz_list_and_detail_endpoints_return_saved_quiz(client: TestClient) -> None:
    _seed_quiz()

    listed = client.get("/api/quiz")
    assert listed.status_code == 200
    body = listed.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == "quiz:api"
    assert body["items"][0]["question_count"] == 1

    detail = client.get("/api/quiz/quiz:api")
    assert detail.status_code == 200
    quiz = detail.json()
    assert quiz["title_en"] == "Reliable API Deployments"
    assert quiz["related_word_packs"][0]["lemma"] == "mitigate"


def test_quiz_detail_rehydrates_missing_word_pack_link(client: TestClient) -> None:
    from backend.store import store as backend_store

    payload = _quiz_payload(quiz_id="quiz:rehydrate")
    payload["related_word_packs"].append(
        {
            "word_pack_id": None,
            "lemma": "fallback",
            "status": "missing",
            "is_empty": False,
            "occurrences": [{"passage_id": "p1", "start": 35, "end": 43}],
            "warning": None,
        }
    )
    backend_store.save_quiz(
        "quiz:rehydrate",
        payload,
        payload["related_word_packs"],
    )
    backend_store.save_word_pack(
        "wp:fallback",
        "fallback",
        json.dumps({"lemma": "fallback", "examples": {}}, ensure_ascii=False),
    )

    detail = client.get("/api/quiz/quiz:rehydrate")

    assert detail.status_code == 200
    links = {link["lemma"]: link for link in detail.json()["related_word_packs"]}
    assert links["fallback"]["word_pack_id"] == "wp:fallback"
    assert links["fallback"]["status"] == "existing"
    assert links["fallback"]["is_empty"] is True


def test_quiz_attempt_endpoint_scores_and_persists_attempt(client: TestClient) -> None:
    _seed_quiz()

    response = client.post(
        "/api/quiz/quiz:api/attempts",
        json={
            "answers": [{"question_id": "q1", "selected_choice_id": "A"}],
            "elapsed_ms": 12000,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["score"] == 1
    assert body["total"] == 1
    assert body["percentage"] == 100.0

    attempts = client.get("/api/quiz/quiz:api/attempts")
    assert attempts.status_code == 200
    saved = attempts.json()
    assert saved[0]["score"] == 1
    assert saved[0]["elapsed_ms"] == 12000


def test_quiz_delete_removes_saved_quiz(client: TestClient) -> None:
    _seed_quiz()

    response = client.delete("/api/quiz/quiz:api")
    assert response.status_code == 200
    assert client.get("/api/quiz/quiz:api").status_code == 404
