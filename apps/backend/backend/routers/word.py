from fastapi import APIRouter, HTTPException, Query
import json
import uuid
import anyio  # オフロード用
from datetime import datetime
from functools import partial

from ..flows.word_pack import WordPackFlow
from ..providers import get_llm_provider
from ..config import settings
from ..models.word import (
    WordPackRequest,
    WordPackCreateRequest,
    WordPack,
    WordPackListResponse,
    WordPackListItem,
    WordPackRegenerateRequest,
    ExampleCategory,
    ExampleListResponse,
    ExampleListItem,
)
from ..store import store
from ..sense_title import choose_sense_title
from ..logging import logger
from pydantic import BaseModel, Field
from typing import Optional, Any

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
    "/packs",
    response_model=dict,
    summary="空のWordPackを作成して保存",
    response_description="作成されたWordPackのIDを返します",
)
async def create_empty_word_pack(req: WordPackCreateRequest) -> dict:
    """生成を行わず、各情報を空としてWordPackを作成・保存する。

    - 既存の生成フローやLLMには依存しない
    - スキーマに適合する空のWordPack JSONを構築して保存
    - 保存ID（wp:{lemma}:{短縮uuid}）を返す
    """
    lemma = req.lemma.strip()
    if not lemma:
        raise HTTPException(status_code=400, detail="lemma is required")

    # スキーマ準拠の空WordPackを構築
    empty_word_pack = WordPack(
        lemma=lemma,
        sense_title=choose_sense_title(None, [], lemma=lemma, limit=20),
        pronunciation={
            "ipa_GA": None,
            "ipa_RP": None,
            "syllables": None,
            "stress_index": None,
            "linking_notes": [],
        },
        senses=[],
        collocations={
            "general": {"verb_object": [], "adj_noun": [], "prep_noun": []},
            "academic": {"verb_object": [], "adj_noun": [], "prep_noun": []},
        },
        contrast=[],
        examples={"Dev": [], "CS": [], "LLM": [], "Business": [], "Common": []},
        etymology={"note": "-", "confidence": "low"},
        study_card="",
        citations=[],
        confidence="low",
    )

    word_pack_id = f"wp:{lemma}:{uuid.uuid4().hex[:8]}"
    store.save_word_pack(word_pack_id, lemma, empty_word_pack.model_dump_json())

    return {"id": word_pack_id}



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
    情報は空値で返す。
    生成されたWordPackは自動的にデータベースに保存される。
    """
    # 近傍検索クライアントは使用しない
    chroma_client = None
    # リクエストでモデル/パラメータが指定されていればオーバーライド
    llm = get_llm_provider(
        model_override=getattr(req, 'model', None),
        temperature_override=getattr(req, 'temperature', None),
        reasoning_override=getattr(req, 'reasoning', None),
        text_override=getattr(req, 'text', None),
    )
    # 例文の LLM メタ付与用に、モデル名とパラメータ文字列を組み立て
    def _format_llm_params_for_request() -> str | None:
        try:
            parts: list[str] = []
            if getattr(req, 'temperature', None) is not None:
                parts.append(f"temperature={float(req.temperature):.2f}")
            r = getattr(req, 'reasoning', None) or {}
            if isinstance(r, dict) and r.get('effort'):
                parts.append(f"reasoning.effort={r.get('effort')}")
            t = getattr(req, 'text', None) or {}
            if isinstance(t, dict) and t.get('verbosity'):
                parts.append(f"text.verbosity={t.get('verbosity')}")
            return ";".join(parts) if parts else None
        except Exception:
            return None
    llm_info = {
        "model": getattr(req, 'model', None) or settings.llm_model,
        "params": _format_llm_params_for_request(),
    }
    flow = WordPackFlow(chroma_client=chroma_client, llm=llm, llm_info=llm_info)
    try:
        logger.info(
            "wordpack_generate_request",
            lemma=req.lemma,
            pronunciation_enabled=req.pronunciation_enabled,
            regenerate_scope=str(req.regenerate_scope),
        )
        # 同期実装のフローをスレッドプールにオフロードし、イベントループのブロッキングを防ぐ
        # anyio.to_thread.run_sync はキーワード引数を転送しないため partial で包む
        word_pack = await anyio.to_thread.run_sync(
            partial(
                flow.run,
                req.lemma,
                pronunciation_enabled=req.pronunciation_enabled,
                regenerate_scope=req.regenerate_scope,
            )
        )
        
        # 生成に使用した LLM 情報を WordPack に反映（常に最新で上書き）
        try:
            setattr(word_pack, 'llm_model', llm_info.get('model'))
            setattr(word_pack, 'llm_params', llm_info.get('params'))
        except Exception:
            pass
        
        # WordPackをデータベースに保存
        word_pack_id = f"wp:{req.lemma}:{uuid.uuid4().hex[:8]}"
        word_pack_data = word_pack.model_dump_json()
        store.save_word_pack(word_pack_id, req.lemma, word_pack_data)
        
        logger.info(
            "wordpack_generate_response",
            lemma=word_pack.lemma,
            senses_count=len(word_pack.senses),
            examples_total=(
                len(word_pack.examples.Dev)
                + len(word_pack.examples.CS)
                + len(word_pack.examples.LLM)
                + len(word_pack.examples.Business)
                + len(word_pack.examples.Common)
            ),
            has_definition_any=any(bool(s.definition_ja) for s in word_pack.senses),
        )
        return word_pack
    except RuntimeError as exc:
        msg = str(exc)
        # strict モードでの LLM JSON パース失敗を 502 に明示マップ
        low = msg.lower()
        if "failed to parse llm json" in low and settings.strict_mode:
            raise HTTPException(
                status_code=502,
                detail={
                    "message": "LLM output JSON parse failed (strict mode)",
                    "reason_code": "LLM_JSON_PARSE",
                    "diagnostics": {"lemma": req.lemma},
                    "hint": "モデル/プロンプトの安定化、text.verbosity を lower に、または strict_mode を無効化して挙動を確認してください。ログの wordpack_llm_json_parse_failed を参照。",
                },
            ) from exc
        # LLM 系のエラー分類（providers で付与）
        if "reason_code=" in msg:
            if "reason_code=TIMEOUT" in msg:
                raise HTTPException(
                    status_code=504,
                    detail={
                        "message": "LLM request timed out",
                        "reason_code": "TIMEOUT",
                        "hint": "LLM_TIMEOUT_MS を増やす（例: 90000）、HTTP全体のタイムアウトは +5秒。リトライも検討。",
                    },
                ) from exc
            if "reason_code=RATE_LIMIT" in msg:
                raise HTTPException(
                    status_code=429,
                    detail={
                        "message": "LLM provider rate limited",
                        "reason_code": "RATE_LIMIT",
                        "hint": "少し待って再試行。モデル/アカウントのレート制限を確認。リトライ上限を増やす。",
                    },
                ) from exc
            if "reason_code=AUTH" in msg or "invalid api key" in low or "unauthorized" in low:
                raise HTTPException(
                    status_code=401,
                    detail={
                        "message": "LLM provider authentication failed",
                        "reason_code": "AUTH",
                        "hint": "OPENAI_API_KEY を確認（有効/権限/課金）。コンテナ環境変数に反映されているか確認。",
                    },
                ) from exc
            if "reason_code=PARAM_UNSUPPORTED" in msg:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "message": "LLM parameter not supported by model",
                        "reason_code": "PARAM_UNSUPPORTED",
                        "hint": "モデルの仕様変更により 'max_tokens' 非対応の可能性。最新SDK/パラメータを使用してください。",
                    },
                ) from exc
        # Flow での空データ検出（厳格）を詳細に変換
        reason_code = getattr(exc, "reason_code", None)
        diagnostics = getattr(exc, "diagnostics", None)
        if reason_code == "EMPTY_CONTENT":
            raise HTTPException(
                status_code=502,
                detail={
                    "message": "WordPack generation returned empty content (no senses/examples)",
                    "reason_code": reason_code,
                    "diagnostics": diagnostics or {},
                    "hint": "LLM_TIMEOUT_MS/LLM_MAX_TOKENS/モデル安定タグを調整してください。ログの wordpack_llm_* を確認。",
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
    limit: int = Query(default=50, ge=1, le=200, description="取得件数上限"),
    offset: int = Query(default=0, ge=0, description="オフセット"),
) -> WordPackListResponse:
    """保存済みWordPackの一覧を取得する。"""
    items_with_flags = store.list_word_packs_with_flags(limit=limit, offset=offset)
    items: list[WordPackListItem] = []
    for wp_id, lemma, sense_title, created_at, updated_at, is_empty, examples_count in items_with_flags:
        items.append(
            WordPackListItem(
                id=wp_id,
                lemma=lemma,
                sense_title=sense_title,
                created_at=created_at,
                updated_at=updated_at,
                is_empty=bool(is_empty),
                examples_count=examples_count,
            )
        )

    total = store.count_word_packs()

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
    
    # 近傍検索クライアントは使用しない
    chroma_client = None
    
    # リクエストでモデル/パラメータが指定されていればオーバーライド
    llm = get_llm_provider(
        model_override=getattr(req, 'model', None),
        temperature_override=getattr(req, 'temperature', None),
        reasoning_override=getattr(req, 'reasoning', None),
        text_override=getattr(req, 'text', None),
    )
    # 例文の LLM メタ付与用に、モデル名とパラメータ文字列を組み立て
    def _format_llm_params_for_request() -> str | None:
        try:
            parts: list[str] = []
            if getattr(req, 'temperature', None) is not None:
                parts.append(f"temperature={float(req.temperature):.2f}")
            r = getattr(req, 'reasoning', None) or {}
            if isinstance(r, dict) and r.get('effort'):
                parts.append(f"reasoning.effort={r.get('effort')}")
            t = getattr(req, 'text', None) or {}
            if isinstance(t, dict) and t.get('verbosity'):
                parts.append(f"text.verbosity={t.get('verbosity')}")
            return ";".join(parts) if parts else None
        except Exception:
            return None
    llm_info = {
        "model": getattr(req, 'model', None) or settings.llm_model,
        "params": _format_llm_params_for_request(),
    }
    flow = WordPackFlow(chroma_client=chroma_client, llm=llm, llm_info=llm_info)
    try:
        word_pack = await anyio.to_thread.run_sync(
            partial(
                flow.run,
                lemma,
                pronunciation_enabled=req.pronunciation_enabled,
                regenerate_scope=req.regenerate_scope,
            )
        )
        
        # 生成に使用した LLM 情報を反映（常に最新で上書き）
        try:
            setattr(word_pack, 'llm_model', llm_info.get('model'))
            setattr(word_pack, 'llm_params', llm_info.get('params'))
        except Exception:
            pass
        
        # 再生成されたWordPackをデータベースに保存（既存のIDで上書き）
        word_pack_data = word_pack.model_dump_json()
        store.save_word_pack(word_pack_id, lemma, word_pack_data)
        
        return word_pack
    except RuntimeError as exc:
        msg = str(exc)
        # strict モードでの LLM JSON パース失敗を 502 に明示マップ
        low = msg.lower()
        if "failed to parse llm json" in low and settings.strict_mode:
            raise HTTPException(
                status_code=502,
                detail={
                    "message": "LLM output JSON parse failed (strict mode)",
                    "reason_code": "LLM_JSON_PARSE",
                    "diagnostics": {"lemma": lemma},
                    "hint": "モデル/プロンプトの安定化、text.verbosity を lower に、または strict_mode を無効化して挙動を確認してください。ログの wordpack_llm_json_parse_failed を参照。",
                },
            ) from exc
        reason_code = getattr(exc, "reason_code", None)
        diagnostics = getattr(exc, "diagnostics", None)
        if reason_code == "EMPTY_CONTENT":
            raise HTTPException(
                status_code=502,
                detail={
                    "message": "WordPack regeneration returned empty content (no senses/examples)",
                    "reason_code": reason_code,
                    "diagnostics": diagnostics or {},
                    "hint": "LLM_TIMEOUT_MS/LLM_MAX_TOKENS/モデル安定タグを調整してください。ログの wordpack_llm_* を確認。",
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



@router.delete(
    "/packs/{word_pack_id}/examples/{category}/{index}",
    summary="保存済みWordPackから個々の例文を削除",
    response_description="指定カテゴリ内の index の例文を削除します",
)
async def delete_example_from_word_pack(
    word_pack_id: str,
    category: ExampleCategory,
    index: int,
) -> dict[str, object]:
    """保存済みWordPackから個々の例文を削除する（正規化テーブルを直接操作）。

    - `category`: `Dev|CS|LLM|Business|Common`
    - `index`: 0 始まり
    - 成功時は残件数を返す
    """
    # WordPack 存在チェック（直接の存在確認 API が無いので get_word_pack で検証）
    wp = store.get_word_pack(word_pack_id)
    if wp is None:
        raise HTTPException(status_code=404, detail="WordPack not found")

    remaining = store.delete_example(word_pack_id, category.value, index)
    if remaining is None:
        # index 範囲外またはカテゴリ不一致とみなす
        raise HTTPException(status_code=404, detail="Example index out of range")

    return {
        "message": "Example deleted",
        "category": category.value,
        "index": index,
        "remaining": remaining,
    }


class ExamplesGenerateRequest(BaseModel):
    """例文追加生成のための任意パラメータ。"""
    model: Optional[str] = Field(default=None, description="LLMモデル名の上書き")
    temperature: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    reasoning: Optional[dict] = Field(default=None)
    text: Optional[dict] = Field(default=None)


@router.post(
    "/packs/{word_pack_id}/examples/{category}/generate",
    summary="カテゴリ別の例文を2件追加生成して保存",
)
async def generate_examples_for_word_pack(
    word_pack_id: str,
    category: ExampleCategory,
    req: ExamplesGenerateRequest | None = None,
) -> dict[str, Any]:
    """保存済みWordPackに、指定カテゴリの例文を2件追加生成して保存する。

    既存の例文データはプロンプトに含めず、入力トークンを削減する。
    """
    result = store.get_word_pack(word_pack_id)
    if result is None:
        raise HTTPException(status_code=404, detail="WordPack not found")
    lemma, _, _, _ = result

    req = req or ExamplesGenerateRequest()
    llm = get_llm_provider(
        model_override=getattr(req, 'model', None),
        temperature_override=getattr(req, 'temperature', None),
        reasoning_override=getattr(req, 'reasoning', None),
        text_override=getattr(req, 'text', None),
    )

    # 統合フロー（LangGraph駆動）でカテゴリ別の例文を生成して即保存
    # 失敗した場合のみ、後続の従来プロンプト経路にフォールバック
    try:
        def _fmt_llm_params_here() -> str | None:
            try:
                parts: list[str] = []
                if getattr(req, 'temperature', None) is not None:
                    parts.append(f"temperature={float(req.temperature):.2f}")
                r = getattr(req, 'reasoning', None) or {}
                if isinstance(r, dict) and r.get('effort'):
                    parts.append(f"reasoning.effort={r.get('effort')}")
                t = getattr(req, 'text', None) or {}
                if isinstance(t, dict) and t.get('verbosity'):
                    parts.append(f"text.verbosity={t.get('verbosity')}")
                return ";".join(parts) if parts else None
            except Exception:
                return None

        llm_info = {
            "model": getattr(req, 'model', None) or settings.llm_model,
            "params": _fmt_llm_params_here(),
        }
        flow = WordPackFlow(chroma_client=None, llm=llm, llm_info=llm_info)
        plan = {category: 2}
        gen = flow.generate_examples_for_categories(lemma, plan)
        items_model = gen.get(category, [])
        items: list[dict[str, object]] = []
        for it in items_model:
            items.append({
                "en": it.en,
                "ja": it.ja,
                "grammar_ja": it.grammar_ja,
                "llm_model": it.llm_model,
                "llm_params": it.llm_params,
            })
        if not items:
            raise HTTPException(status_code=502, detail="LLM returned no usable examples")
        added = store.append_examples(word_pack_id, category.value, items)
        return {
            "message": "Examples generated and appended",
            "added": added,
            "category": category.value,
            "items": items,
        }
    except HTTPException:
        raise


@router.get(
    "/examples",
    response_model=ExampleListResponse,
    summary="例文一覧を取得（WordPackを横断）",
)
async def list_examples(
    limit: int = Query(default=50, ge=1, le=200, description="取得件数上限"),
    offset: int = Query(default=0, ge=0, description="オフセット"),
    order_by: str = Query(default="created_at", description="created_at|pack_updated_at|lemma|category"),
    order_dir: str = Query(default="desc", description="asc|desc"),
    search: Optional[str] = Query(default=None, description="英文に対する検索文字列（部分一致等）"),
    search_mode: str = Query(default="contains", description="prefix|suffix|contains"),
    category: Optional[ExampleCategory] = Query(default=None, description="カテゴリで絞り込み"),
) -> ExampleListResponse:
    """`word_pack_examples` を元に横断的な例文一覧を返す。"""
    # 取得
    items_raw = store.list_examples(
        limit=limit,
        offset=offset,
        order_by=order_by,
        order_dir=order_dir,
        search=search,
        search_mode=search_mode,
        category=category.value if category is not None else None,
    )
    total = store.count_examples(
        search=search,
        search_mode=search_mode,
        category=category.value if category is not None else None,
    )

    items: list[ExampleListItem] = []
    for (rid, wp_id, lemma, cat, en, ja, grammar_ja, created_at, pack_updated_at) in items_raw:
        items.append(
            ExampleListItem(
                id=rid,
                word_pack_id=wp_id,
                lemma=lemma,
                category=ExampleCategory(cat),
                en=en,
                ja=ja,
                grammar_ja=grammar_ja,
                created_at=created_at,
                word_pack_updated_at=pack_updated_at,
            )
        )
    return ExampleListResponse(items=items, total=total, limit=limit, offset=offset)
