from __future__ import annotations

import os
import subprocess
from pathlib import Path


def test_deploy_script_requires_firestore_project_id_or_gcp_project_id() -> None:
    """デプロイスクリプトが Firestore 接続用プロジェクト ID の pre-flight チェックを持つことを確認。

    バックエンド config.py と同じエイリアス（FIRESTORE_PROJECT_ID, GCP_PROJECT_ID,
    GOOGLE_CLOUD_PROJECT, PROJECT_ID）を許容するチェックが存在することを検証する。
    """
    text = Path("scripts/deploy_cloud_run.sh").read_text(encoding="utf-8")
    # 派生ロジックが存在すること
    assert "FIRESTORE_PROJECT_ID:-${GCP_PROJECT_ID:-${GOOGLE_CLOUD_PROJECT:-${PROJECT_ID" in text
    # エラーメッセージに全エイリアスが列挙されていること
    assert "FIRESTORE_PROJECT_ID, GCP_PROJECT_ID, GOOGLE_CLOUD_PROJECT, or PROJECT_ID" in text


def test_release_cloud_run_stops_when_index_sync_fails(tmp_path: Path) -> None:
    fake_cloud_run = tmp_path / "fake_cloud_run.sh"
    fake_cloud_run.write_text(
        "#!/usr/bin/env bash\n"
        "echo CLOUD_RUN_SCRIPT_RAN\n"
        "exit 0\n",
        encoding="utf-8",
    )
    fake_cloud_run.chmod(0o755)

    proc = subprocess.run(
        [
            "make",
            "-s",
            "release-cloud-run",
            "PROJECT_ID=demo-project",
            "REGION=asia-northeast1",
            "ENV_FILE=configs/cloud-run/ci.env",
            "TOOL=invalid",
            f"CLOUD_RUN_SCRIPT={fake_cloud_run}",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    combined_output = proc.stdout + proc.stderr

    assert proc.returncode != 0
    assert "--tool には gcloud または firebase を指定してください" in combined_output
    assert "CLOUD_RUN_SCRIPT_RAN" not in combined_output


def test_gcloud_index_sync_applies_field_overrides(tmp_path: Path) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    gcloud_log = tmp_path / "gcloud.log"
    fake_gcloud = fake_bin / "gcloud"
    fake_gcloud.write_text(
        "#!/usr/bin/env bash\n"
        "printf '%s\\n' \"$*\" >> \"${GCLOUD_LOG}\"\n"
        "exit 0\n",
        encoding="utf-8",
    )
    fake_gcloud.chmod(0o755)

    index_file = tmp_path / "firestore.indexes.json"
    index_file.write_text(
        """{
  "indexes": [
    {
      "collectionGroup": "examples",
      "queryScope": "COLLECTION",
      "fields": [
        { "fieldPath": "category", "order": "ASCENDING" },
        { "fieldPath": "created_at", "order": "DESCENDING" }
      ]
    }
  ],
  "fieldOverrides": [
    {
      "collectionGroup": "lemmas",
      "fieldPath": "normalized_label",
      "indexes": [
        { "order": "ASCENDING", "queryScope": "COLLECTION" }
      ]
    }
  ]
}
""",
        encoding="utf-8",
    )

    proc = subprocess.run(
        [
            "scripts/deploy_firestore_indexes.sh",
            "--project",
            "demo-project",
            "--tool",
            "gcloud",
            "--index-file",
            str(index_file),
        ],
        check=False,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "PATH": f"{fake_bin}:{os.environ['PATH']}",
            "GCLOUD_LOG": str(gcloud_log),
        },
    )

    combined_output = proc.stdout + proc.stderr
    assert proc.returncode == 0, combined_output

    calls = gcloud_log.read_text(encoding="utf-8").splitlines()
    assert any("alpha firestore indexes composite create" in call for call in calls)
    assert any(
        "firestore indexes fields update normalized_label" in call
        and "--collection-group=lemmas" in call
        and "--index=order=ascending" in call
        for call in calls
    )
