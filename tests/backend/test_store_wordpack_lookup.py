"""AppFirestoreStore.find_word_pack_id_by_lemma の挙動を直接検証する。"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "backend"))

from backend.store import AppFirestoreStore  # noqa: E402
from tests.firestore_fakes import FakeFirestoreClient  # noqa: E402


def test_find_word_pack_id_by_lemma_handles_case_and_spacing():
    """大文字小文字や前後の空白を揃えても同じ WordPack ID を返すことを確認する。"""

    store = AppFirestoreStore(client=FakeFirestoreClient())
    payload = {
        "lemma": "NormalizeMe",
        "sense_title": "normalize me",
        "examples": {},
    }

    store.save_word_pack("wp-normalize", payload["lemma"], json.dumps(payload, ensure_ascii=False))

    lowercase_hit = store.find_word_pack_id_by_lemma("normalizeme")
    padded_hit = store.find_word_pack_id_by_lemma("  NORMALIZEME  ")

    assert lowercase_hit == "wp-normalize"
    assert padded_hit == "wp-normalize"
