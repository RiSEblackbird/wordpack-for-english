from fastapi import APIRouter, HTTPException

from ..flows.word_pack import WordPackFlow
from ..providers import ChromaClientFactory, get_llm_provider
from ..config import settings
from ..models.word import WordPackRequest, WordPack

router = APIRouter(tags=["word"])


@router.get("/")
async def lookup_word() -> dict[str, object]:
    """暫定の語義参照（プレースホルダ）。

    strict_mode の場合は未実装として 501 を返す。テスト互換のため非 strict では固定応答。
    """
    from ..config import settings
    if settings.strict_mode:
        raise HTTPException(status_code=501, detail="Not Implemented: /api/word in strict mode")
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
    まとめた学習パックを生成して返す。ダミーは生成せず、取得できない
    情報は空値で返す（RAG 有効かつ strict のときは引用不足で失敗）。
    """
    # RAG が有効なときのみ Chroma を接続（初期化失敗は後段で 424 にマップ）
    try:
        chroma_client = ChromaClientFactory().create_client() if settings.rag_enabled else None
    except RuntimeError as exc:
        msg = str(exc)
        if (
            settings.rag_enabled
            and settings.strict_mode
            and (
                "chromadb module is required" in msg.lower()
                or "failed to initialize chroma client" in msg.lower()
            )
        ):
            raise HTTPException(
                status_code=424,
                detail={
                    "message": "RAG dependency not ready or no citations (strict mode)",
                    "hint": "Chroma にインデックスを投入してください: python -m backend.indexing --persist .chroma",
                },
            ) from exc
        # それ以外は再送出
        raise
    llm = get_llm_provider()
    flow = WordPackFlow(chroma_client=chroma_client, llm=llm)
    try:
        return flow.run(
            req.lemma,
            pronunciation_enabled=req.pronunciation_enabled,
            regenerate_scope=req.regenerate_scope,
        )
    except RuntimeError as exc:
        msg = str(exc)
        # RAG が有効かつ strict で引用ゼロなど、依存不足に起因するエラーは 424 に変換
        if (
            settings.rag_enabled
            and settings.strict_mode
            and (
                "no citations" in msg.lower()
                or "chromadb module is required" in msg.lower()
                or "failed to initialize chroma client" in msg.lower()
            )
        ):
            raise HTTPException(
                status_code=424,
                detail={
                    "message": "RAG dependency not ready or no citations (strict mode)",
                    "hint": "Chroma にインデックスを投入してください: python -m backend.indexing --persist .chroma",
                },
            ) from exc
        # それ以外は既定のハンドリングへ委譲
        raise


