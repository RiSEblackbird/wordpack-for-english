from __future__ import annotations

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


