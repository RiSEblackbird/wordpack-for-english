from typing import Any, Dict, List

from . import create_state_graph

# ChromaDB import removed - RAG functionality disabled

from ..models.text import (
    TextAssistResponse,
    AssistedSentence,
    SyntaxInfo,
    TermInfo,
)
from ..models.common import Citation, ConfidenceLevel
from ..logging import logger
from ..config import settings
# RAG imports removed - functionality disabled


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
        """文を解析し、構文情報・用語注・パラフレーズを付与。OpenAI LLM を使用。"""
        # OpenAI LLM を使用して文の解析とパラフレーズを生成
        terms = []
        paraphrase = sentence
        syntax_info = SyntaxInfo(subject=None, predicate=None, mods=[])
        
        try:
            if self.llm is not None and hasattr(self.llm, "complete"):
                # 文の解析とパラフレーズを同時に生成
                prompt = f"""Analyze this English sentence and provide:
1. A simple paraphrase (10-18 words)
2. Key vocabulary words with Japanese meanings
3. Basic syntax structure

Sentence: {sentence}

Respond in JSON format:
{{
  "paraphrase": "simple paraphrase here",
  "vocabulary": [{{"word": "word1", "meaning": "Japanese meaning"}}],
  "syntax": {{"subject": "subject", "predicate": "predicate"}}
}}"""
                
                out = self.llm.complete(prompt)  # type: ignore[attr-defined]
                if isinstance(out, str) and out.strip():
                    import json
                    try:
                        data = json.loads(out.strip())
                        paraphrase = data.get("paraphrase", sentence)
                        
                        # 語彙情報を抽出
                        vocab_list = data.get("vocabulary", [])
                        for item in vocab_list[:3]:  # 最大3語まで
                            if isinstance(item, dict) and "word" in item:
                                terms.append(TermInfo(
                                    lemma=item["word"],
                                    gloss_ja=item.get("meaning"),
                                    ipa=None
                                ))
                        
                        # 構文情報を抽出
                        syntax_data = data.get("syntax", {})
                        if isinstance(syntax_data, dict):
                            syntax_info = SyntaxInfo(
                                subject=syntax_data.get("subject"),
                                predicate=syntax_data.get("predicate"),
                                mods=[]
                            )
                    except json.JSONDecodeError:
                        # JSON解析に失敗した場合は元の文をそのまま使用
                        paraphrase = out.strip()
        except Exception:
            if settings.strict_mode:
                raise
            # フォールバック: 最小限の用語抽出
            words = sentence.split()
            if words:
                terms = [TermInfo(lemma=words[0], gloss_ja=None, ipa=None)]

        return AssistedSentence(
            raw=sentence,
            syntax=syntax_info,
            terms=terms,
            paraphrase=paraphrase,
        )

    def run(self, paragraph: str) -> TextAssistResponse:
        """段落を入力として文ごとの支援情報を返す。OpenAI LLM を使用。"""
        sentences = [self._analyze(s) for s in self._segment(paragraph)]
        citations: List[Citation] = []
        
        # RAGは無効化されているため、LLMベースの解析のみを使用
        # 確度ヒューリスティクス: LLM パラフレーズ成功で high / 失敗で medium
        used_llm = any(s.paraphrase and s.paraphrase != s.raw for s in sentences)
        has_terms = any(s.terms for s in sentences)
        
        if used_llm and has_terms:
            confidence = ConfidenceLevel.high
        elif used_llm or has_terms:
            confidence = ConfidenceLevel.medium
        else:
            confidence = ConfidenceLevel.low
            
        summary = sentences[0].paraphrase if sentences else None
        return TextAssistResponse(sentences=sentences, summary=summary, citations=citations, confidence=confidence)
