from __future__ import annotations


def study_progress_increments(kind: str) -> tuple[int, int]:
    if kind == "checked":
        return 1, 0
    return 0, 1
