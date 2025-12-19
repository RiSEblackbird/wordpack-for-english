from __future__ import annotations

from pathlib import Path
import re


def _read_text(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def _assert_contains_all(text: str, needles: list[str]) -> None:
    missing = [n for n in needles if n not in text]
    assert not missing, f"Missing expected snippets: {missing}"


def _assert_contains_none(text: str, needles: list[str]) -> None:
    present = [n for n in needles if n in text]
    assert not present, f"Found forbidden snippets: {present}"


def _extract_on_block(yml: str) -> str:
    """
    Extracts the "on:" block up to the next top-level key (best-effort).
    This avoids binding tests to exact YAML formatting (inline list vs multiline list).
    """
    m = re.search(r"(?ms)^\s*on:\s*\n(.*?)(?=^\S)", yml)
    assert m, "Could not locate top-level 'on:' block"
    return m.group(1)


def test_ci_runs_on_develop_and_prs_to_develop() -> None:
    """
    Contract: develop is the default branch for day-to-day development.
    CI must run for pushes to develop and PRs targeting develop.
    """
    yml = _read_text(".github/workflows/ci.yml")
    on_block = _extract_on_block(yml)
    _assert_contains_all(on_block, ["push:", "pull_request:"])
    assert "develop" in on_block, "CI must include develop in its triggers"


def test_deploy_dry_run_is_main_only() -> None:
    """
    Contract: main is the production deployment branch.
    Anything that authenticates to GCP must not run on develop.
    """
    yml = _read_text(".github/workflows/deploy-dry-run.yml")
    on_block = _extract_on_block(yml)
    _assert_contains_all(on_block, ["push:", "pull_request:", "main"])
    assert "develop" not in on_block, "deploy-dry-run must not run on develop"
    # Sanity: ensure this workflow is actually the one touching GCP.
    _assert_contains_all(yml, ["google-github-actions/auth@v2", "setup-gcloud@v2"])


