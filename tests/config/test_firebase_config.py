from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
FIREBASE_JSON_PATH = REPO_ROOT / "firebase.json"


def test_firebase_predeploy_runs_frontend_build() -> None:
  firebase_config = json.loads(FIREBASE_JSON_PATH.read_text(encoding="utf-8"))
  hosting = firebase_config["hosting"]
  predeploy = hosting.get("predeploy")
  # Firebase Hosting の predeploy でフロントエンドのビルドを必ず実行する
  assert isinstance(predeploy, list), "hosting.predeploy should be a list of commands"
  expected_command = "npm --prefix ./apps/frontend run build"
  assert expected_command in predeploy, f"{expected_command} must be configured in hosting.predeploy"

