from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
FIREBASE_JSON_PATH = REPO_ROOT / "firebase.json"
FIRESTORE_INDEXES_PATH = REPO_ROOT / "firestore.indexes.json"


def test_firebase_predeploy_runs_frontend_build() -> None:
  firebase_config = json.loads(FIREBASE_JSON_PATH.read_text(encoding="utf-8"))
  hosting = firebase_config["hosting"]
  predeploy = hosting.get("predeploy")
  # Firebase Hosting の predeploy でフロントエンドのビルドを必ず実行する
  assert isinstance(predeploy, list), "hosting.predeploy should be a list of commands"
  expected_command = "npm --prefix ./apps/frontend run build"
  assert expected_command in predeploy, f"{expected_command} must be configured in hosting.predeploy"


def test_firestore_indexes_are_configured() -> None:
  firebase_config = json.loads(FIREBASE_JSON_PATH.read_text(encoding="utf-8"))
  firestore = firebase_config.get("firestore")
  assert firestore is not None, "firebase.json must define a firestore section when indexes are deployed"
  indexes_path = firestore.get("indexes")
  assert indexes_path == "firestore.indexes.json", "firestore.indexes.json must be configured for firestore indexes"


def test_lemma_field_override_has_query_scope() -> None:
  firestore_indexes = json.loads(FIRESTORE_INDEXES_PATH.read_text(encoding="utf-8"))
  overrides = firestore_indexes.get("fieldOverrides", [])
  lemma_override = next(
    (override for override in overrides if override.get("collectionGroup") == "lemmas" and override.get("fieldPath") == "normalized_label"),
    None,
  )
  assert lemma_override is not None, "lemmas.normalized_label field override must exist"
  indexes = lemma_override.get("indexes")
  assert isinstance(indexes, list) and indexes, "lemmas.normalized_label override must declare indexes"
  for single_index in indexes:
    assert single_index.get("queryScope") == "COLLECTION", "field override indexes must set queryScope explicitly"


def test_examples_cross_corpus_descending_sort_indexes_exist() -> None:
  firestore_indexes = json.loads(FIRESTORE_INDEXES_PATH.read_text(encoding="utf-8"))
  indexes = firestore_indexes.get("indexes", [])

  configured_fields = {
    tuple(
      (
        field.get("fieldPath"),
        field.get("order"),
        field.get("arrayConfig"),
      )
      for field in index.get("fields", [])
    )
    for index in indexes
    if index.get("collectionGroup") == "examples"
  }
  required = {
    ((field_name, "DESCENDING", None), ("__name__", "ASCENDING", None))
    for field_name in ("created_at", "pack_updated_at", "lemma", "category")
  }

  missing = required - configured_fields
  assert not missing, f"examples cross-corpus sort indexes are missing: {sorted(missing)}"
