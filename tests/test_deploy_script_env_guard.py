from __future__ import annotations

from pathlib import Path


def test_deploy_script_requires_firestore_project_id_or_gcp_project_id() -> None:
    text = Path("scripts/deploy_cloud_run.sh").read_text(encoding="utf-8")
    assert "FIRESTORE_PROJECT_ID (or GCP_PROJECT_ID)" in text
    assert "err \"FIRESTORE_PROJECT_ID (or GCP_PROJECT_ID)" in text


