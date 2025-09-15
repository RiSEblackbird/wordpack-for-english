import sys
from pathlib import Path

import pytest


# Ensure `src` is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

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
            ["- Common: 日常会話", "ビジネス英語ではなく"],
            ["- Dev:", "- CS:", "- LLM:", "- Business:"],
        ),
    ],
)
def test_examples_prompt_is_category_specific(category, present, absent):
    flow = WordPackFlow(llm=None)
    prompt = flow._build_examples_prompt("converge", category, 2)

    # Common parts are always included
    assert "You are a lexicographer." in prompt
    assert "\"examples\"" in prompt
    assert "Override: examples must be exactly 2 items." in prompt

    # Category-specific presence/absence
    for token in present:
        assert token in prompt, f"expected to include: {token}"
    for token in absent:
        assert token not in prompt, f"expected to exclude: {token}"


