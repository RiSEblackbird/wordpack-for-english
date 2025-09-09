from fastapi import APIRouter, HTTPException, Query
import json
import uuid
from datetime import datetime

from ..flows.word_pack import WordPackFlow
from ..providers import ChromaClientFactory, get_llm_provider
from ..config import settings
from ..models.word import (
    WordPackRequest, 
    WordPack, 
    WordPackListResponse, 
    WordPackListItem,
    WordPackRegenerateRequest
)
from ..srs import store

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
    生成されたWordPackは自動的にデータベースに保存される。
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
        word_pack = flow.run(
            req.lemma,
            pronunciation_enabled=req.pronunciation_enabled,
            regenerate_scope=req.regenerate_scope,
        )
        
        # WordPackをデータベースに保存
        word_pack_id = f"wp:{req.lemma}:{uuid.uuid4().hex[:8]}"
        word_pack_data = word_pack.model_dump_json()
        store.save_word_pack(word_pack_id, req.lemma, word_pack_data)
        
        return word_pack
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


@router.get(
    "/packs",
    response_model=WordPackListResponse,
    summary="保存済みWordPack一覧を取得",
    response_description="保存済みWordPackの一覧を返します",
)
async def list_word_packs(
    limit: int = Query(default=50, ge=1, le=100, description="取得件数上限"),
    offset: int = Query(default=0, ge=0, description="オフセット"),
) -> WordPackListResponse:
    """保存済みWordPackの一覧を取得する。"""
    items_data = store.list_word_packs(limit=limit, offset=offset)
    items = [
        WordPackListItem(
            id=item[0],
            lemma=item[1],
            created_at=item[2],
            updated_at=item[3],
        )
        for item in items_data
    ]
    
    # 総件数を取得（簡易実装：実際のプロダクションでは別途カウントクエリが必要）
    total_items = store.list_word_packs(limit=10000, offset=0)
    total = len(total_items)
    
    return WordPackListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/packs/{word_pack_id}",
    response_model=WordPack,
    response_model_exclude_none=True,
    summary="保存済みWordPackを取得",
    response_description="指定されたIDのWordPackを返します",
)
async def get_word_pack(word_pack_id: str) -> WordPack:
    """保存済みWordPackをIDで取得する。"""
    result = store.get_word_pack(word_pack_id)
    if result is None:
        raise HTTPException(status_code=404, detail="WordPack not found")
    
    lemma, data, created_at, updated_at = result
    try:
        word_pack_dict = json.loads(data)
        return WordPack.model_validate(word_pack_dict)
    except (json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(status_code=500, detail=f"Invalid WordPack data: {exc}")


@router.post(
    "/packs/{word_pack_id}/regenerate",
    response_model=WordPack,
    response_model_exclude_none=True,
    summary="WordPackを再生成",
    response_description="既存のWordPackを再生成して返します",
)
async def regenerate_word_pack(
    word_pack_id: str, 
    req: WordPackRegenerateRequest
) -> WordPack:
    """既存のWordPackを再生成する。"""
    # 既存のWordPackを取得してlemmaを取得
    result = store.get_word_pack(word_pack_id)
    if result is None:
        raise HTTPException(status_code=404, detail="WordPack not found")
    
    lemma, _, _, _ = result
    
    # RAG が有効なときのみ Chroma を接続
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
        raise
    
    llm = get_llm_provider()
    flow = WordPackFlow(chroma_client=chroma_client, llm=llm)
    try:
        word_pack = flow.run(
            lemma,
            pronunciation_enabled=req.pronunciation_enabled,
            regenerate_scope=req.regenerate_scope,
        )
        
        # 再生成されたWordPackをデータベースに保存（既存のIDで上書き）
        word_pack_data = word_pack.model_dump_json()
        store.save_word_pack(word_pack_id, lemma, word_pack_data)
        
        return word_pack
    except RuntimeError as exc:
        msg = str(exc)
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
        raise


@router.delete(
    "/packs/{word_pack_id}",
    summary="WordPackを削除",
    response_description="指定されたIDのWordPackを削除します",
)
async def delete_word_pack(word_pack_id: str) -> dict[str, str]:
    """保存済みWordPackを削除する。"""
    success = store.delete_word_pack(word_pack_id)
    if not success:
        raise HTTPException(status_code=404, detail="WordPack not found")
    
    return {"message": "WordPack deleted successfully"}


