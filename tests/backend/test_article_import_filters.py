from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "backend"))

from backend.flows.article_import import ArticleImportFlow


def test_post_filter_excludes_basic_vocabulary():
    flow = ArticleImportFlow()
    result = flow._post_filter_lemmas(["hello", "mitigate", "supply chain"])

    assert "hello" not in result
    assert "mitigate" in result
    assert "supply chain" in result


def test_post_filter_retains_general_advanced_terms():
    flow = ArticleImportFlow()
    result = flow._post_filter_lemmas(["strategic", "analysis", "thanks"])

    assert "strategic" in result
    assert "analysis" in result
    assert "thanks" not in result
