from typing import Any, Dict, List

# LangGraph は必須
# 正式 import を試し、失敗時は tests スタブ互換のフォールバック。
try:
    from langgraph.graph import StateGraph  # type: ignore
except Exception:
    try:
        import langgraph  # type: ignore
        StateGraph = langgraph.graph.StateGraph  # type: ignore[attr-defined]
    except Exception as exc:  # pragma: no cover - library required
        raise ImportError(
            "WordPackFlow requires the 'langgraph' package (expected langgraph.graph.StateGraph)."
        ) from exc

try:
    import chromadb
except Exception:  # pragma: no cover - library optional
    chromadb = Any  # type: ignore

from ..models.word import (
    WordPack,
    Sense,
    Collocations,
    Etymology,
    Pronunciation,
    Examples,
)


class WordPackFlow:
    """Word pack generation via a minimal LangGraph pipeline.

    単語学習パックを生成する最小構成のフロー。
    MVP ではダミーの RAG ステップを通し、スキーマに沿った固定形の
    `WordPack` を返す。実際の RAG/LLM は `providers` から差し替え予定。
    """

    def __init__(self, chroma_client: Any | None = None) -> None:
        """ベクトルDB クライアントを受け取り、LangGraph を初期化。

        Parameters
        ----------
        chroma_client: Any | None
            語義・共起取得などの検索に利用するクライアント（任意）。
        """
        self.chroma = chroma_client
        self.graph = StateGraph()

    # --- MVP: 簡易発音推定（暫定・不完全） ---
    def _guess_pronunciation(self, lemma: str) -> Pronunciation:
        """非常に大雑把な規則で IPA, 音節数, 強勢位置を推定（暫定）。

        将来的に g2p-en / cmudict を導入するまでのプレースホルダ。
        """
        word = lemma.lower()
        # ごく簡易な母音クラスタによる音節近似
        import re

        vowel_groups = re.findall(r"[aeiouy]+", word)
        syllables = max(1, len(vowel_groups))

        # 強勢はとりあえず最初の音節（暫定）
        stress_index = 0

        # 超簡易 IPA 置換（非常に不完全）
        ipa = word
        ipa = re.sub(r"ph", "f", ipa)
        ipa = re.sub(r"tion\b", "ʃən", ipa)
        ipa = re.sub(r"sion\b", "ʒən", ipa)
        ipa = re.sub(r"ch", "tʃ", ipa)
        ipa = re.sub(r"sh", "ʃ", ipa)
        ipa = re.sub(r"th", "θ", ipa)
        ipa = re.sub(r"\bcon", "kɒn", ipa)
        ipa_GA = f"/{ipa}/"

        linking_notes: list[str] = []
        if word.endswith(("r",)):
            linking_notes.append("語末 r の連結に注意（rhotic）")

        return Pronunciation(
            ipa_GA=ipa_GA,
            syllables=syllables,
            stress_index=stress_index,
            linking_notes=linking_notes,
        )

    def _retrieve(self, lemma: str) -> Dict[str, Any]:
        """語の近傍情報を取得（将来: chroma からベクトル近傍）。"""
        return {"lemma": lemma}

    def _synthesize(self, lemma: str) -> WordPack:
        """取得結果を整形し `WordPack` を構成（将来: LLM で整形）。"""
        pronunciation = self._guess_pronunciation(lemma)
        return WordPack(
            lemma=lemma,
            pronunciation=pronunciation,
            senses=[Sense(id="s1", gloss_ja="意味（暫定）", patterns=[], register=None)],
            collocations=Collocations(),
            contrast=[],
            examples=Examples(A1=[f"{lemma} example."], tech=[]),
            etymology=Etymology(note="TBD", confidence="low"),
            study_card="この語の要点（暫定）。",
        )

    def run(self, lemma: str) -> WordPack:
        """語を入力として `WordPack` を生成して返す（MVP ダミー）。"""
        _ = self._retrieve(lemma)
        return self._synthesize(lemma)
