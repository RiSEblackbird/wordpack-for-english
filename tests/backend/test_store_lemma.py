import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "backend"))

from backend.store import AppSQLiteStore  # noqa: E402


def _row(conn: sqlite3.Connection) -> sqlite3.Row:
    cur = conn.execute("SELECT * FROM lemmas LIMIT 1;")
    row = cur.fetchone()
    assert row is not None
    return row


def test_upsert_preserves_original_label(tmp_path):
    db_path = tmp_path / "lemma-case.sqlite3"
    store = AppSQLiteStore(str(db_path))

    now = datetime.now(UTC).isoformat()
    with store._conn() as conn:  # pylint: disable=protected-access
        lemma_id = store._upsert_lemma(  # pylint: disable=protected-access
            conn,
            label="Converge",
            sense_title="Sense Title",
            llm_model="gpt-x",
            llm_params="{\"temperature\": 0.2}",
            now=now,
        )
        row = _row(conn)
        assert row["id"] == lemma_id
        assert row["label"] == "Converge"
        assert row["sense_title"] == "Sense Title"
        assert row["llm_model"] == "gpt-x"
        assert row["llm_params"] == "{\"temperature\": 0.2}"

        store._upsert_lemma(  # pylint: disable=protected-access
            conn,
            label="converge",
            sense_title="",
            llm_model=None,
            llm_params=None,
            now=now,
        )
        row = _row(conn)
        assert row["label"] == "Converge"
        assert row["sense_title"] == "Sense Title"
        assert row["llm_model"] == "gpt-x"
        assert row["llm_params"] == "{\"temperature\": 0.2}"


def test_upsert_does_not_override_existing_sense_title(tmp_path):
    db_path = tmp_path / "lemma-sense-title.sqlite3"
    store = AppSQLiteStore(str(db_path))

    now = datetime.now(UTC).isoformat()
    with store._conn() as conn:  # pylint: disable=protected-access
        store._upsert_lemma(  # pylint: disable=protected-access
            conn,
            label="Accelerate",
            sense_title="初速を上げる",
            llm_model=None,
            llm_params=None,
            now=now,
        )

        store._upsert_lemma(  # pylint: disable=protected-access
            conn,
            label="accelerate",
            sense_title="速度を増す",
            llm_model="gpt-5",
            llm_params="{\"foo\": 1}",
            now=now,
        )

        row = _row(conn)
        assert row["label"] == "Accelerate"
        assert row["sense_title"] == "初速を上げる"
        assert row["llm_model"] == "gpt-5"
        assert row["llm_params"] == "{\"foo\": 1}"
