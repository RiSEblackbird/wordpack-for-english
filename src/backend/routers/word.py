from fastapi import APIRouter

from ..flows.word_pack import WordPackFlow
from ..providers import ChromaClientFactory
from ..models.word import WordPackRequest, WordPack, WordLookupResponse

router = APIRouter(tags=["word"])


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
    # Chroma を利用可能なら接続
    chroma_client = ChromaClientFactory().create_client()
    flow = WordPackFlow(chroma_client=chroma_client)
    return flow.run(
        req.lemma,
        pronunciation_enabled=req.pronunciation_enabled,
        regenerate_scope=req.regenerate_scope,
    )


@router.get(
    "",
    response_model=WordLookupResponse,
    summary="単語の簡易参照（プレースホルダ）",
    response_description="語義や例文の最小情報を返します",
)
async def get_word() -> WordLookupResponse:
    """Retrieve information about a word (placeholder).

    単語の簡易参照エンドポイント（プレースホルダ）。
    実装後は辞書検索やキャッシュからの取得を想定。
    """
    return WordLookupResponse(definition=None, examples=[])
