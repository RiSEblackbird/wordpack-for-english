from typing import Any, List, Dict, Any as AnyType

from . import create_state_graph

from ..models.sentence import SentenceCheckResponse, Issue, Revision, MiniExercise
from ..models.common import Citation, ConfidenceLevel
# RAG imports removed - functionality disabled
from ..config import settings


class FeedbackFlow:
    """Minimal feedback generator.

    文の診断フィードバックを最小構成で生成するフロー。
    MVP では固定の3要素（issues/revisions/exercise）をダミー生成。
    将来的には LLM によるエラー検出・説明・修正案、および
    ミニ演習（穴埋め等）の自動生成に置き換える想定。
    """

    def __init__(self, llm: Any | None = None, *, chroma_client: Any | None = None) -> None:
        """LLM クライアント等を受け取り、LangGraph の状態遷移を初期化。

        Parameters
        ----------
        llm: Any | None
            フィードバック生成に用いる LLM クライアント（任意）。
        """
        self.llm = llm
        self.chroma = chroma_client
        self.graph = create_state_graph()

    def run(self, sentence: str) -> SentenceCheckResponse:
        """与えられた文を解析し、フィードバックを返す。OpenAI LLM を使用。

        - OpenAI LLM で issues/revisions/mini exercise を生成
        - 失敗時は安全なフォールバック
        """
        # 安全な初期値（LLM 失敗時のフォールバック）
        issues = [Issue(what="語法", why="対象語の使い分け不正確", fix="共起に合わせて置換")]  # type: ignore[arg-type]
        revisions = [
            Revision(style="natural", text=sentence),
            Revision(style="formal", text=sentence),
        ]
        exercise = MiniExercise(q="Fill the blank: ...", a="...")
        citations: List[Citation] = []

        # OpenAI LLM による詳細な分析
        try:
            if self.llm is not None and hasattr(self.llm, "complete"):
                prompt = f"""Analyze this English sentence for grammar, style, and provide learning feedback.

Sentence: {sentence}

Respond in JSON format:
{{
  "issues": [
    {{
      "what": "grammar issue type",
      "why": "explanation of the problem",
      "fix": "suggested correction"
    }}
  ],
  "revisions": [
    {{
      "style": "natural",
      "text": "more natural version"
    }},
    {{
      "style": "formal", 
      "text": "formal version"
    }}
  ],
  "exercise": {{
    "q": "fill-in-the-blank question",
    "a": "answer"
  }}
}}"""
                
                out = self.llm.complete(prompt)  # type: ignore[attr-defined]
                if isinstance(out, str) and out.strip().startswith("{"):
                    import json
                    data = json.loads(out)
                    
                    # 問題点の解析
                    iss = data.get("issues") or []
                    if isinstance(iss, list):
                        tmp: List[Issue] = []
                        for it in iss[:3]:
                            if isinstance(it, dict):
                                w = str(it.get("what", ""))
                                y = str(it.get("why", ""))
                                f = str(it.get("fix", ""))
                                if w:
                                    tmp.append(Issue(what=w, why=y, fix=f))
                        if tmp:
                            issues = tmp
                    
                    # 修正案の解析
                    revs = data.get("revisions") or []
                    if isinstance(revs, list):
                        tmp2: List[Revision] = []
                        for rv in revs[:2]:
                            if isinstance(rv, dict):
                                st = str(rv.get("style", "")) or "variant"
                                tx = str(rv.get("text", "")) or sentence
                                tmp2.append(Revision(style=st, text=tx))
                        if tmp2:
                            revisions = tmp2
                    
                    # 演習問題の解析
                    ex = data.get("exercise") or None
                    if isinstance(ex, dict):
                        q = str(ex.get("q", "Fill the blank: ..."))
                        a = str(ex.get("a", "..."))
                        exercise = MiniExercise(q=q, a=a)
                    
                    # LLM生成の情報を引用として保存
                    citations.append(Citation(
                        text=f"LLM-generated feedback for: {sentence}",
                        meta={"source": "openai_llm", "sentence": sentence}
                    ))
        except Exception:
            if settings.strict_mode:
                raise
            # 例外はフォールバックで吸収（非 strict）
            pass
        
        # 確度: LLM 補強が効いていれば high、フォールバックなら medium
        if citations and revisions and issues:
            confidence = ConfidenceLevel.high
        elif revisions and issues:
            confidence = ConfidenceLevel.medium
        else:
            confidence = ConfidenceLevel.low
            
        return SentenceCheckResponse(issues=issues, revisions=revisions, exercise=exercise, citations=citations, confidence=confidence)
