from __future__ import annotations

from pathlib import Path


def test_cloud_build_has_backend_config_and_deploy_script_uses_it() -> None:
    """
    Contract: Cloud Build must not rely on a repo-root Dockerfile being present in the remote workspace.
    We keep a dedicated Cloud Build config that explicitly uses Dockerfile.backend, and the deploy script
    must submit builds with --config to avoid 'Dockerfile: no such file or directory' failures.
    """

    config_path = Path("cloudbuild.backend.yaml")
    assert config_path.exists(), "cloudbuild.backend.yaml must exist for Cloud Build backend image"

    config_text = config_path.read_text(encoding="utf-8")
    assert "Dockerfile.backend" in config_text, "cloudbuild.backend.yaml must reference Dockerfile.backend"
    assert "_IMAGE_URI" in config_text, "cloudbuild.backend.yaml must accept _IMAGE_URI substitution"

    deploy_script = Path("scripts/deploy_cloud_run.sh").read_text(encoding="utf-8")
    assert (
        "cloudbuild.backend.yaml" in deploy_script
    ), "deploy_cloud_run.sh must use cloudbuild.backend.yaml via --config"
