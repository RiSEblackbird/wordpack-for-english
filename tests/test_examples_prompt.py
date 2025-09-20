import os
import sys
from pathlib import Path

import pytest


# Ensure backend package is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "backend"))
os.environ.setdefault("STRICT_MODE", "false")

from backend.flows.word_pack import WordPackFlow  # noqa: E402
from backend.models.word import ExampleCategory  # noqa: E402


@pytest.mark.parametrize(
    "category, present, absent",
    [
        (
            ExampleCategory.Dev,
            ["- Dev: ソフトウェア開発の文脈。"],
            ["- CS:", "- LLM:", "- Business:", "- Common:", "ビジネス英語ではなく"],
        ),
        (
            ExampleCategory.CS,
            ["- CS: 計算機科学の学術文脈。"],
            ["- Dev:", "- LLM:", "- Business:", "- Common:", "ビジネス英語ではなく"],
        ),
        (
            ExampleCategory.LLM,
            ["- LLM: 機械学習/LLM 文脈。"],
            ["- Dev:", "- CS:", "- Business:", "- Common:", "ビジネス英語ではなく"],
        ),
        (
            ExampleCategory.Business,
            ["- Business: ビジネス文脈"],
            ["- Dev:", "- CS:", "- LLM:", "- Common:", "ビジネス英語ではなく"],
        ),
        (
            ExampleCategory.Common,
            ["- Common: とても様々な日常会話", "ビジネス英語ではなく"],
            ["- Dev:", "- CS:", "- LLM:", "- Business:"],
        ),
    ],
)
def test_examples_prompt_is_category_specific(category, present, absent):
    flow = WordPackFlow(llm=None)
    prompt = flow._build_examples_prompt("converge", category, 2)

    # Common parts are always included
    assert "あなたは辞書編集者である。" in prompt
    assert "\"examples\"" in prompt
    assert "上書き指示: 例文数は必ず 2 件とする。" in prompt

    # Category-specific presence/absence
    for token in present:
        assert token in prompt, f"expected to include: {token}"
    for token in absent:
        assert token not in prompt, f"expected to exclude: {token}"


