from typing import Any, List, Dict, Any as AnyType

from . import create_state_graph

from ..models.sentence import SentenceCheckResponse, Issue, Revision, MiniExercise
from ..models.common import Citation, ConfidenceLevel
from ..providers import chroma_query_with_policy, COL_DOMAIN_TERMS
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
        """与えられた文を解析し、フィードバックを返す。

        - LLM があれば軽量プロンプトで issues/revisions/mini exercise を補強
        - LLM が無い/失敗時は安全なダミー
        - RAG があれば citations を付与
        """
        # 安全な初期値（LLM 失敗時のフォールバック）
        issues = [Issue(what="語法", why="対象語の使い分け不正確", fix="共起に合わせて置換")]  # type: ignore[arg-type]
        revisions = [
            Revision(style="natural", text=sentence),
            Revision(style="formal", text=sentence),
        ]
        exercise = MiniExercise(q="Fill the blank: ...", a="...")

        # LLM による簡易補強
        try:
            if self.llm is not None and hasattr(self.llm, "complete"):
                prompt = (
                    "Analyze the sentence and return three parts as JSON keys: "
                    "issues (array of {what, why, fix}), revisions (array of {style, text}), "
                    "and exercise ({q,a}). Keep outputs short and safe.\n"
                    f"Sentence: {sentence}"
                )
                out = self.llm.complete(prompt)  # type: ignore[attr-defined]
                if isinstance(out, str) and out.strip().startswith("{"):
                    import json
                    data = json.loads(out)
                    iss = data.get("issues") or []
                    revs = data.get("revisions") or []
                    ex = data.get("exercise") or None
                    # 型安全に最小限取り込む
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
                    if isinstance(revs, list):
                        tmp2: List[Revision] = []
                        for rv in revs[:2]:
                            if isinstance(rv, dict):
                                st = str(rv.get("style", "")) or "variant"
                                tx = str(rv.get("text", "")) or sentence
                                tmp2.append(Revision(style=st, text=tx))
                        if tmp2:
                            revisions = tmp2
                    if isinstance(ex, dict):
                        q = str(ex.get("q", "Fill the blank: ..."))
                        a = str(ex.get("a", "..."))
                        exercise = MiniExercise(q=q, a=a)
        except Exception:
            if settings.strict_mode:
                raise
            # 例外はフォールバックで吸収（非 strict）
            pass
        # 可能ならRAGの引用を付与
        citations: List[Citation] = []
        if settings.rag_enabled and self.chroma and getattr(self.chroma, "get_or_create_collection", None):
            res = chroma_query_with_policy(
                self.chroma,
                collection=COL_DOMAIN_TERMS,
                query_text=sentence.split()[0] if sentence.split() else "",
                n_results=3,
            )
            if res:
                docs = (res.get("documents") or [[]])[0]
                metas = (res.get("metadatas") or [[]])[0]
                for d, m in zip(docs, metas):
                    citations.append(Citation(text=d, meta=m))
            elif settings.strict_mode:
                # strict: RAGを期待しているのに取得できない
                raise RuntimeError("RAG is enabled but no citations were retrieved (strict mode)")
        # 確度: RAG 引用があれば medium、LLM 補強も効いていれば high に近い扱い
        if citations and revisions and issues:
            confidence = ConfidenceLevel.medium
        else:
            confidence = ConfidenceLevel.low
        return SentenceCheckResponse(issues=issues, revisions=revisions, exercise=exercise, citations=citations, confidence=confidence)
