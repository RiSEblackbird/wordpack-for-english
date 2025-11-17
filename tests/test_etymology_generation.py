"""語源情報の生成ロジックを検証するユニットテスト。"""

import sys
from pathlib import Path

backend_root = Path(__file__).resolve().parents[1] / "apps" / "backend"
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from backend.flows.word_pack import RegenerateScope, WordPackFlow
from backend.models.common import ConfidenceLevel
from backend.models.word import Pronunciation


def test_synthesize_fills_etymology_when_missing(monkeypatch):
    """LLM 出力に語源が無い場合でもフォールバックが入ることを確認する。"""

    flow = WordPackFlow(llm=None)

    # 発音生成が外部辞書に依存しないようにシンプルなダミーへ差し替え。
    monkeypatch.setattr(
        flow,
        "_generate_pronunciation",
        lambda lemma: Pronunciation(
            ipa_GA=None,
            ipa_RP=None,
            syllables=None,
            stress_index=None,
            linking_notes=[],
        ),
        raising=False,
    )

    flow._last_llm_data = {  # type: ignore[attr-defined]
        "senses": [{"id": "s1", "gloss_ja": "意味", "patterns": []}],
        # etymology キーをあえて欠落させ、フォールバックが働くことを検証
        "collocations": {
            "general": {"verb_object": [], "adj_noun": [], "prep_noun": []},
            "academic": {"verb_object": [], "adj_noun": [], "prep_noun": []},
        },
        "examples": {"Dev": [], "CS": [], "LLM": [], "Business": [], "Common": []},
        "study_card": "カード",
    }

    pack = flow._synthesize(  # type: ignore[attr-defined]
        "originless",
        pronunciation_enabled=False,
        regenerate_scope=RegenerateScope.all,
        citations=[],
    )

    assert isinstance(pack.etymology.note, str) and pack.etymology.note.strip()
    assert pack.etymology.confidence in {
        ConfidenceLevel.low,
        ConfidenceLevel.medium,
        ConfidenceLevel.high,
    }

