#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

EXCLUDED_DIRS = {
    ".git",
    "node_modules",
    ".venv",
    "dist",
    "build",
    "coverage",
    "htmlcov",
    "playwright-report",
    "test-results",
    ".cache",
    ".firebase",
    "firestore-emulator-data",
    ".data",
    ".data_demo",
    ".chroma",
    "終了済みor参考ドキュメント",
}

TEXT_SUFFIXES = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".mjs",
    ".cjs",
    ".json",
    ".jsonc",
    ".yml",
    ".yaml",
    ".toml",
    ".md",
    ".txt",
    ".ini",
    ".cfg",
    ".sh",
    ".bash",
    ".zsh",
    ".css",
    ".html",
}

EXPLICIT_FILES = {
    "Dockerfile",
    "Dockerfile.backend",
    "Dockerfile.frontend",
    "Makefile",
    ".dockerignore",
    ".gitignore",
    ".env.example",
    ".env.ci",
    "env.deploy.example",
    "requirements.txt",
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "firebase.json",
    "firestore.indexes.json",
}

BLOCKED_RANGES = [
    (0x202A, 0x202E, "bidi control"),
    (0x2066, 0x2069, "bidi isolate"),
    (0x200B, 0x200F, "zero-width/control formatting"),
    (0xFE00, 0xFE0F, "variation selector"),
    (0xE0100, 0xE01EF, "variation selector supplement"),
    (0xFEFF, 0xFEFF, "byte order mark / zero-width no-break space"),
]


def classify_blocked_char(ch: str) -> str | None:
    code = ord(ch)
    for start, end, label in BLOCKED_RANGES:
        if start <= code <= end:
            return label
    return None


def should_scan(path: Path) -> bool:
    relative_parts = path.relative_to(ROOT).parts
    if any(part in EXCLUDED_DIRS for part in relative_parts):
        return False
    return path.name in EXPLICIT_FILES or path.suffix in TEXT_SUFFIXES


def scan_text(text: str, relative_path: str) -> list[str]:
    findings: list[str] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        for col_no, ch in enumerate(line, start=1):
            label = classify_blocked_char(ch)
            if label is not None:
                findings.append(
                    f"{relative_path}:{line_no}:{col_no}: blocked invisible/control character "
                    f"U+{ord(ch):04X} ({label})"
                )
    return findings


def iter_candidate_files() -> list[Path]:
    return sorted(path for path in ROOT.rglob("*") if path.is_file() and should_scan(path))


def main() -> int:
    findings: list[str] = []
    for path in iter_candidate_files():
        relative_path = str(path.relative_to(ROOT))
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        findings.extend(scan_text(text, relative_path))

    if findings:
        print("Security text scan failed. Remove or justify invisible/control characters.", file=sys.stderr)
        for finding in findings:
            print(finding, file=sys.stderr)
        return 1

    print("Security text scan passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
