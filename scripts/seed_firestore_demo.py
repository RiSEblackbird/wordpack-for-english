#!/usr/bin/env python
"""SQLite デモデータを Firestore（エミュレータを含む）へ流し込むユーティリティ。"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sqlite-path",
        default=Path(".data_demo/wordpack.sqlite3.demo"),
        type=Path,
        help="変換元となる SQLite デモ DB のパス（既定: .data_demo/wordpack.sqlite3.demo）",
    )
    parser.add_argument(
        "--project-id",
        default=os.environ.get("FIRESTORE_PROJECT_ID", "wordpack-local"),
        help="適用先 Firestore プロジェクト ID。エミュレータの場合も指定必須（既定: wordpack-local）。",
    )
    parser.add_argument(
        "--emulator-host",
        default=os.environ.get("FIRESTORE_EMULATOR_HOST", "127.0.0.1:8080"),
        help="FIRESTORE_EMULATOR_HOST に渡すホスト:ポート（既定: 127.0.0.1:8080）。",
    )
    parser.add_argument(
        "--preserve-example-counter",
        action="store_true",
        help="example_counters をリセットせず既存のカウンタを引き継ぐ場合に指定。",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="ゲスト用データの有無に関わらずシードを実行する場合に指定。",
    )
    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    # 設定クラスは import 時点で環境変数を読むため、先に上書きしてから backend を読み込む。
    os.environ.setdefault("FIRESTORE_PROJECT_ID", str(args.project_id))
    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", str(args.project_id))
    if args.emulator_host:
        os.environ.setdefault("FIRESTORE_EMULATOR_HOST", str(args.emulator_host))

    repo_root = Path(__file__).resolve().parents[1]
    backend_root = repo_root / "apps" / "backend"
    sys.path.insert(0, str(backend_root))

    from backend.seed_firestore_demo import (
        seed_firestore_from_sqlite,
        seed_firestore_from_sqlite_if_missing_guest_demo,
    )
    from backend.store.firestore_store import AppFirestoreStore

    store = AppFirestoreStore()
    if args.force:
        wordpacks, articles = seed_firestore_from_sqlite(
            args.sqlite_path,
            store,
            reset_example_counter=not args.preserve_example_counter,
        )
    else:
        wordpacks, articles = seed_firestore_from_sqlite_if_missing_guest_demo(
            args.sqlite_path,
            store,
            reset_example_counter=not args.preserve_example_counter,
        )
        if wordpacks == 0 and articles == 0:
            print("Guest demo data already exists. Skipping seed.")
    print(f"Seeded {wordpacks} word_packs and {articles} articles into Firestore ({args.project_id}).")


if __name__ == "__main__":
    main()
