from fastapi import APIRouter

from ..flows.word_pack import WordPackFlow
from ..providers import ChromaClientFactory, get_llm_provider
from ..config import settings
from ..models.word import WordPackRequest, WordPack

router = APIRouter(tags=["word"])


@router.get("/")
async def lookup_word() -> dict[str, object]:
    """暫定の語義参照（プレースホルダ）。

    tests/test_api.py の互換用: {"definition": None, "examples": []}
    """
    return {"definition": None, "examples": []}


@router.post(
    "/pack",
    response_model=WordPack,
    response_model_exclude_none=True,
    summary="WordPack を生成",
    response_description="生成された WordPack を返します",
)
async def generate_word_pack(req: WordPackRequest) -> WordPack:
    """Generate a new word pack using LangGraph flow.

    指定した語について、発音・語義・共起・対比・例文・語源などを
    まとめた学習パックを生成して返す（MVP はダミー）。
    """
    # RAG が有効なときのみ Chroma を接続
    chroma_client = ChromaClientFactory().create_client() if settings.rag_enabled else None
    llm = get_llm_provider()
    flow = WordPackFlow(chroma_client=chroma_client, llm=llm)
    return flow.run(
        req.lemma,
        pronunciation_enabled=req.pronunciation_enabled,
        regenerate_scope=req.regenerate_scope,
    )


