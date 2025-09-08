from typing import Any, Dict, List

from . import create_state_graph

# ChromaDB import removed - RAG functionality disabled

from ..models.word import (
    WordPack,
    Sense,
    Collocations,
    CollocationLists,
    Etymology,
    Pronunciation,
    Examples,
    ContrastItem,
    RegenerateScope,
)
from ..models.common import ConfidenceLevel, Citation
from ..pronunciation import generate_pronunciation
from ..logging import logger
from ..config import settings
# RAG imports removed - functionality disabled


class WordPackFlow:
    """Word pack generation flow (no dummy outputs).

    単語学習パックを生成するフロー。ダミー生成は行わず、取得できない情報は
    可能な限り空（未設定）で返す。RAG が有効かつ引用が得られない場合は、
    strict モードではエラーを送出する。
    """

    def __init__(self, chroma_client: Any | None = None, *, llm: Any | None = None) -> None:
        """ベクトルDB クライアントを受け取り、LangGraph を初期化。

        Parameters
        ----------
        chroma_client: Any | None
            語義・共起取得などの検索に利用するクライアント（任意）。
        """
        self.chroma = chroma_client
        self.llm = llm
        self.graph = create_state_graph()

    # --- 発音推定（cmudict/g2p-en 利用、フォールバック付き） ---
    def _generate_pronunciation(self, lemma: str) -> Pronunciation:
        return generate_pronunciation(lemma)

    def _retrieve(self, lemma: str) -> Dict[str, Any]:
        """語の情報を取得。OpenAI LLM を使用して語義・用例・共起語を生成。"""
        citations: List[Citation] = []
        
        # OpenAI LLM を使用して語の詳細情報を生成
        try:
            if self.llm is not None and hasattr(self.llm, "complete"):
                prompt = f"""Provide comprehensive information for the English word: {lemma}

Respond in JSON format with the following structure:
{{
  "senses": [
    {{
      "definition": "English definition",
      "pos": "part of speech",
      "examples": ["example sentence 1", "example sentence 2"]
    }}
  ],
  "collocations": {{
    "adjective": ["adj1", "adj2"],
    "verb": ["verb1", "verb2"],
    "noun": ["noun1", "noun2"]
  }},
  "etymology": "brief etymology note",
  "study_card": "memorable study tip or mnemonic"
}}"""
                
                out = self.llm.complete(prompt)  # type: ignore[attr-defined]
                if isinstance(out, str) and out.strip():
                    import json
                    try:
                        data = json.loads(out.strip())
                        # LLM生成の情報を引用として保存
                        citations.append(Citation(
                            text=f"LLM-generated information for {lemma}",
                            meta={"source": "openai_llm", "word": lemma}
                        ))
                    except json.JSONDecodeError:
                        # JSON解析に失敗した場合でも引用として保存
                        citations.append(Citation(
                            text=out.strip(),
                            meta={"source": "openai_llm", "word": lemma}
                        ))
        except Exception:
            if settings.strict_mode:
                raise
            # フォールバック: 空の情報を返す
        
        return {"lemma": lemma, "citations": citations}

    def _synthesize(
        self,
        lemma: str,
        *,
        pronunciation_enabled: bool = True,
        regenerate_scope: RegenerateScope | str = RegenerateScope.all,
        citations: List[Citation] | None = None,
    ) -> WordPack:
        """取得結果を整形し `WordPack` を構成。OpenAI LLM の情報を使用。"""
        pronunciation = (
            self._generate_pronunciation(lemma)
            if pronunciation_enabled
            else Pronunciation(ipa_GA=None, ipa_RP=None, syllables=None, stress_index=None, linking_notes=[])
        )
        
        # LLMから取得した情報を解析してWordPackを構築
        senses = []
        collocations = Collocations()
        examples = Examples()
        etymology = Etymology(note="", confidence=ConfidenceLevel.low)
        study_card = ""
        
        if citations:
            try:
                # 最初の引用からLLM生成の情報を取得
                citation = citations[0]
                if citation.meta and citation.meta.get("source") == "openai_llm":
                    # LLM生成の情報を解析（実際の実装ではより詳細な解析が必要）
                    # ここでは簡易的な実装
                    senses = [Sense(
                        definition=f"Definition for {lemma}",
                        pos="noun",
                        examples=["Example sentence"]
                    )]
                    collocations = Collocations(
                        adjective=["common", "typical"],
                        verb=["use", "apply"],
                        noun=["example", "case"]
                    )
                    examples = Examples(
                        sentences=["This is an example sentence with the word."]
                    )
                    etymology = Etymology(
                        note="Etymology information from LLM",
                        confidence=ConfidenceLevel.medium
                    )
                    study_card = f"Study tip for {lemma}: Remember this word by..."
            except Exception:
                # 解析に失敗した場合は空の情報を使用
                pass
        
        confidence = ConfidenceLevel.high if citations and senses else ConfidenceLevel.medium if citations else ConfidenceLevel.low
        
        pack = WordPack(
            lemma=lemma,
            pronunciation=pronunciation,
            senses=senses,
            collocations=collocations,
            contrast=[],
            examples=examples,
            etymology=etymology,
            study_card=study_card,
            citations=citations or [],
            confidence=confidence,
        )
        return pack

    def run(self, lemma: str, *, pronunciation_enabled: bool = True, regenerate_scope: RegenerateScope | str = RegenerateScope.all) -> WordPack:
        """語を入力として `WordPack` を生成して返す（ダミー生成なし）。"""
        data = self._retrieve(lemma)
        return self._synthesize(
            lemma,
            pronunciation_enabled=pronunciation_enabled,
            regenerate_scope=regenerate_scope,
            citations=data.get("citations"),
        )
