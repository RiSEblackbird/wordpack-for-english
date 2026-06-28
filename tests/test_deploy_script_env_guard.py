from __future__ import annotations

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
