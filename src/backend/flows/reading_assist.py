from typing import Any, Dict, List

from . import create_state_graph

try:
    import chromadb
except Exception:  # pragma: no cover - library optional
    chromadb = Any  # type: ignore

from ..models.text import (
    TextAssistResponse,
    AssistedSentence,
    SyntaxInfo,
    TermInfo,
)
from ..models.common import Citation, ConfidenceLevel
from ..logging import logger
from ..config import settings
from ..providers import chroma_query_with_policy, COL_DOMAIN_TERMS


class ReadingAssistFlow:
    """Minimal reading assistance via LangGraph.

    LangGraph を用いた簡易なリーディング支援フロー。
    MVP では段落を文に単純分割し、ダミーの構文情報と用語注を返す。
    将来的には RAG による用語検出、IPA（発音記号）付与、
    文意のパラフレーズ生成、引用元提示等を追加する想定。
    """

    def __init__(self, chroma_client: Any | None = None, *, llm: Any | None = None) -> None:
        """ChromaDB クライアント等を受け取り、LangGraph を初期化。

        Parameters
        ----------
        chroma_client: Any | None
            用語サーチ/RAG に用いるベクトルDB クライアント（任意）。
        """
        self.chroma = chroma_client
        self.llm = llm
        self.graph = create_state_graph()

    def _segment(self, paragraph: str) -> List[str]:
        """簡易な文分割（., !, ? を区切り）。連続空白・改行を正規化。"""
        import re
        normalized = " ".join(paragraph.replace("\n", " ").split())
        parts = re.split(r"(?<=[.!?])\s+", normalized)
        return [s.strip().rstrip(".?!") for s in parts if s.strip()]

    def _analyze(self, sentence: str) -> AssistedSentence:
        """文を解析し、構文情報・用語注・パラフレーズを付与。LLM があれば簡易言い換え。"""
        # 最小の用語抽出: 先頭語を代表語として抽出
        terms = [TermInfo(lemma=w, gloss_ja=None, ipa=None) for w in sentence.split()[:1]]
        paraphrase = sentence
        # LLM が使えれば、非常に短い指示でパラフレーズを試みる（失敗時は無視）
        try:
            if self.llm is not None and hasattr(self.llm, "complete"):
                prompt = (
                    "Paraphrase the following English sentence in simple words (10-18 words).\n" 
                    f"Sentence: {sentence}"
                )
                out = self.llm.complete(prompt)  # type: ignore[attr-defined]
                if isinstance(out, str) and out.strip():
                    paraphrase = out.strip()
        except Exception:
            if settings.strict_mode:
                raise
            pass

        return AssistedSentence(
            raw=sentence,
            syntax=SyntaxInfo(subject=None, predicate=None, mods=[]),
            terms=terms,
            paraphrase=paraphrase,
        )

    def run(self, paragraph: str) -> TextAssistResponse:
        """段落を入力として文ごとの支援情報を返す。RAG の引用を付与（任意）。"""
        sentences = [self._analyze(s) for s in self._segment(paragraph)]
        citations: List[Citation] = []
        if settings.rag_enabled and self.chroma and getattr(self.chroma, "get_or_create_collection", None):
            # 先頭文の先頭語で軽く近傍を引く（MVP）
            query = sentences[0].terms[0].lemma if sentences and sentences[0].terms else ""
            if query:
                res = chroma_query_with_policy(
                    self.chroma,
                    collection=COL_DOMAIN_TERMS,
                    query_text=query,
                    n_results=3,
                )
                if res:
                    docs = (res.get("documents") or [[]])[0]
                    metas = (res.get("metadatas") or [[]])[0]
                    for d, m in zip(docs, metas):
                        citations.append(Citation(text=d, meta=m))
                elif settings.strict_mode:
                    raise RuntimeError("RAG is enabled but no citations were retrieved (strict mode)")
        # 確度ヒューリスティクス: RAG あり + LLM パラフレーズ成功で high / 片方で medium
        used_llm = any(s.paraphrase and s.paraphrase != s.raw for s in sentences)
        if citations and used_llm:
            confidence = ConfidenceLevel.high
        elif citations or used_llm:
            confidence = ConfidenceLevel.medium
        else:
            confidence = ConfidenceLevel.low
        summary = sentences[0].paraphrase if sentences else None
        return TextAssistResponse(sentences=sentences, summary=summary, citations=citations, confidence=confidence)
