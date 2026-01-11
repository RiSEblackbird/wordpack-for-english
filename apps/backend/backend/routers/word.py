import json
from datetime import datetime
"""Word エンドポイント。backend.providers パッケージ経由で LLM を取得する。"""

from functools import partial
from typing import Any, Callable, Mapping, Optional

import anyio  # オフロード用
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from ..config import settings
from ..flows.word_pack import WordPackFlow
from ..id_factory import generate_word_pack_id
from ..auth import get_current_user, resolve_guest_session_cookie
from ..providers import get_llm_provider
from ..logging import logger
from ..models.word import (
    DEFAULT_ETYMOLOGY_PLACEHOLDER,
    WordPack,
    ExampleCategory,
    ExampleListItem,
    ExampleListResponse,
    ExamplesBulkDeleteRequest,
    ExamplesBulkDeleteResponse,
    ExampleTranscriptionTypingRequest,
    ExampleTranscriptionTypingResponse,
    WordPackCreateRequest,
    WordPackListItem,
    WordPackListResponse,
    WordPackRegenerateRequest,
    WordPackRequest,
    StudyProgressRequest,
    WordPackStudyProgressResponse,
    ExampleStudyProgressResponse,
    _validate_lemma,
)
from ..store import store
from ..sense_title import choose_sense_title
import asyncio
from uuid import uuid4
from typing import Literal

router = APIRouter(tags=["word"])


# --- Regenerate async job registry (in-memory) ---
class RegenerateJob(BaseModel):
    job_id: str
    word_pack_id: str
    status: Literal["pending", "running", "succeeded", "failed"]
    result: WordPack | None = None
    error: str | None = None


_regenerate_jobs: dict[str, RegenerateJob] = {}
_regenerate_lock = asyncio.Lock()


class WordLookupExample(BaseModel):
    """WordPack 内の例文をレスポンス用に整形するモデル。"""

    en: str
    ja: str
    grammar_ja: str | None = None
    category: ExampleCategory


class WordLookupResponse(BaseModel):
    """`GET /api/word` の返却スキーマ。"""

    lemma: str
    sense_title: str | None
    definition: str | None
    word_pack_id: str | None = None
    examples: list[WordLookupExample] = Field(default_factory=list)
    llm_model: str | None = None
    llm_params: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


def _get_override_value(source: object, key: str) -> Any:
    """Pydantic モデル/辞書の双方から値を取り出す内部ユーティリティ。"""

    if hasattr(source, key):
        return getattr(source, key)
    if isinstance(source, Mapping):
        return source.get(key)
    return None


def build_llm_info(overrides: object) -> dict[str, Any]:
    """LLM の使用モデル名と主要パラメータを抽出する。

    backend.providers の階層化後も API 利用者に返す情報形式を変えないため、
    ここで辞書化してメタ情報を統一している。
    """

    # なぜ: LLM オプションを追加するたびに各エンドポイントへ重複修正が波及するのを防ぐため、
    #       build_llm_info でメタ情報の組み立てを一元化している。将来オプションが増えたら
    #       ここを調整すればよい。
    model = _get_override_value(overrides, "model") or settings.llm_model
    params: str | None = None
    try:
        parts: list[str] = []
        temperature = _get_override_value(overrides, "temperature")
        if temperature is not None:
            parts.append(f"temperature={float(temperature):.2f}")
        reasoning = _get_override_value(overrides, "reasoning") or {}
        if isinstance(reasoning, Mapping):
            effort = reasoning.get("effort")
            if effort:
                parts.append(f"reasoning.effort={effort}")
        text_opts = _get_override_value(overrides, "text") or {}
        if isinstance(text_opts, Mapping):
            verbosity = text_opts.get("verbosity")
            if verbosity:
                parts.append(f"text.verbosity={verbosity}")
        params = ";".join(parts) if parts else None
    except Exception:
        params = None
    return {"model": model, "params": params}


def _resolve_http_exception(
    mapping: Mapping[str, Callable[..., HTTPException]] | None,
    key: str,
    **kwargs: Any,
) -> HTTPException | None:
    """カスタム HTTPException を生成する。失敗時は None を返す。"""

    if not mapping:
        return None
    handler = mapping.get(key)
    if handler is None:
        return None
    try:
        return handler(**kwargs)
    except HTTPException as exc:
        return exc
    except Exception as exc:  # 生成処理自体が失敗してもログだけ残し既定処理へ委譲
        logger.warning(
            "wordpack_error_mapping_failed",
            key=key,
            error=str(exc),
        )
        return None


def _extract_definition_from_senses(data: Mapping[str, Any]) -> str | None:
    """語義配列から定義/グロスを優先順に抽出する。"""

    senses = data.get("senses") or []
    for sense in senses if isinstance(senses, list) else []:
        if not isinstance(sense, Mapping):
            continue
        definition = str(sense.get("definition_ja") or "").strip()
        if definition:
            return definition
        gloss = str(sense.get("gloss_ja") or "").strip()
        if gloss:
            return gloss
    return None


def _collect_examples_for_lookup(data: Mapping[str, Any]) -> list[WordLookupExample]:
    """WordPack の例文をカテゴリ付きで平坦化する。"""

    examples: list[WordLookupExample] = []
    raw_examples = data.get("examples") or {}
    if not isinstance(raw_examples, Mapping):
        return examples

    for category, items in raw_examples.items():
        if not isinstance(items, list):
            continue
        try:
            cat_enum = ExampleCategory(category)
        except ValueError:
            continue
        for item in items:
            if not isinstance(item, Mapping):
                continue
            examples.append(
                WordLookupExample(
                    en=str(item.get("en") or ""),
                    ja=str(item.get("ja") or ""),
                    grammar_ja=(item.get("grammar_ja") or None),
                    category=cat_enum,
                )
            )
    return examples


async def _require_authenticated_user(request: Request) -> dict[str, str]:
    """ゲストを拒否するための認証依存関数（テスト時は無効化設定に合わせる）。"""

    # なぜ: DISABLE_SESSION_AUTH が有効な検証環境でも生成系 API を動かせるようにしつつ、
    #       本番では get_current_user でゲスト拒否とセッション検証を強制する。
    if settings.disable_session_auth:
        return {"mode": "test"}
    return await get_current_user(request)


def _handle_flow_runtime_error(
    exc: RuntimeError,
    *,
    lemma: str,
    http_error_mapping: Mapping[str, Callable[..., HTTPException]] | None,
) -> None:
    """Flow 実行失敗を HTTPException にマップする。"""

    msg = str(exc)
    low = msg.lower()
    if "failed to parse llm json" in low and settings.strict_mode:
        custom_exc = _resolve_http_exception(http_error_mapping, "llm_json_parse", lemma=lemma)
        if custom_exc:
            raise custom_exc from exc
        raise HTTPException(
            status_code=502,
            detail={
                "message": "LLM output JSON parse failed (strict mode)",
                "reason_code": "LLM_JSON_PARSE",
                "diagnostics": {"lemma": lemma},
                "hint": "モデル/プロンプトの安定化、text.verbosity を lower に、または strict_mode を無効化して挙動を確認してください。ログの wordpack_llm_json_parse_failed を参照。",
            },
        ) from exc

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
        if (
            "reason_code=AUTH" in msg
            or "invalid api key" in low
            or "unauthorized" in low
        ):
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

    reason_code = getattr(exc, "reason_code", None)
    diagnostics = getattr(exc, "diagnostics", None)
    if reason_code == "EMPTY_CONTENT":
        custom_exc = _resolve_http_exception(
            http_error_mapping,
            "empty_content",
            lemma=lemma,
            diagnostics=diagnostics or {},
        )
        if custom_exc:
            raise custom_exc from exc
        raise HTTPException(
            status_code=502,
            detail={
                "message": "WordPack generation returned empty content (no senses/examples)",
                "reason_code": reason_code,
                "diagnostics": diagnostics or {},
                "hint": "LLM_TIMEOUT_MS/LLM_MAX_TOKENS/モデル安定タグを調整してください。ログの wordpack_llm_* を確認。",
            },
        ) from exc


async def run_wordpack_flow(
    *,
    lemma: str,
    req_opts: object,
    scope: Any,
    http_error_mapping: Mapping[str, Callable[..., HTTPException]] | None = None,
) -> tuple[WordPack, dict[str, Any]]:
    """WordPackFlow を構築して実行し、生成結果と LLM メタを返す。

    backend.providers の LLM パッケージ化に伴い、ここで `get_llm_provider` を
    呼び出してから Flow へ依存性注入する設計にそろえている。
    """

    # なぜ: Flow 実行・例外分類・LLM メタ設定を単一関数にまとめておくことで、
    #       将来の流用時に1箇所の修正で全エンドポイントへ反映できるようにする。
    llm = get_llm_provider(
        model_override=_get_override_value(req_opts, "model"),
        temperature_override=_get_override_value(req_opts, "temperature"),
        reasoning_override=_get_override_value(req_opts, "reasoning"),
        text_override=_get_override_value(req_opts, "text"),
    )
    llm_info = build_llm_info(req_opts)
    flow = WordPackFlow(chroma_client=None, llm=llm, llm_info=llm_info)
    try:
        word_pack = await anyio.to_thread.run_sync(
            partial(
                flow.run,
                lemma,
                pronunciation_enabled=_get_override_value(req_opts, "pronunciation_enabled")
                if _get_override_value(req_opts, "pronunciation_enabled") is not None
                else True,
                regenerate_scope=scope,
            )
        )
    except RuntimeError as exc:
        _handle_flow_runtime_error(
            exc,
            lemma=lemma,
            http_error_mapping=http_error_mapping,
        )
        raise

    try:
        setattr(word_pack, "llm_model", llm_info.get("model"))
        setattr(word_pack, "llm_params", llm_info.get("params"))
    except Exception:
        pass
    return word_pack, llm_info

def _build_lookup_response(
    *,
    lemma: str,
    sense_title: str | None,
    word_pack_id: str | None,
    word_pack_data: Mapping[str, Any],
    created_at: str | None,
    updated_at: str | None,
) -> WordLookupResponse:
    """語義と例文をレスポンススキーマへ整形する共通ユーティリティ。"""

    definition = _extract_definition_from_senses(word_pack_data)
    examples = _collect_examples_for_lookup(word_pack_data)
    return WordLookupResponse(
        lemma=lemma,
        sense_title=str(sense_title or word_pack_data.get("sense_title") or "") or None,
        definition=definition,
        word_pack_id=word_pack_id,
        examples=examples,
        llm_model=word_pack_data.get("llm_model"),
        llm_params=word_pack_data.get("llm_params"),
        created_at=created_at,
        updated_at=updated_at,
    )


@router.get("/", response_model=WordLookupResponse, response_model_exclude_none=True)
async def lookup_word(
    request: Request, lemma: str = Query(..., description="見出し語")
) -> WordLookupResponse:
    """WordPack を lemma で取得し、定義と例文を返す。"""

    normalized_lemma = str(lemma or "").strip()
    if not normalized_lemma:
        raise HTTPException(status_code=400, detail="lemma is required")
    try:
        _validate_lemma(normalized_lemma)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"invalid lemma: {exc}") from exc

    # 1) 既存データをストアから検索
    stored = store.find_word_pack_by_lemma_ci(normalized_lemma)
    if stored:
        word_pack_id, stored_lemma, stored_sense_title = stored
        packed = store.get_word_pack(word_pack_id)
        if packed is None:
            raise HTTPException(status_code=404, detail="word pack not found")

        lemma_from_store, data_json, created_at, updated_at = packed
        try:
            data_dict = json.loads(data_json) if data_json else {}
        except json.JSONDecodeError:
            data_dict = {}
        return _build_lookup_response(
            lemma=lemma_from_store,
            sense_title=stored_sense_title,
            word_pack_id=word_pack_id,
            word_pack_data=data_dict,
            created_at=created_at,
            updated_at=updated_at,
        )

    # なぜ: GET /api/word は閲覧専用に寄せ、生成は POST 系 API に集約する。
    # 認証済みユーザー（user または user_id が存在する）はゲスト Cookie が残存していても
    # ゲスト扱いせず、未登録語に対して 404 を返す（生成は POST API で実施）。
    has_authenticated_user = bool(
        getattr(request.state, "user", None) or getattr(request.state, "user_id", None)
    )

    if has_authenticated_user:
        # 認証済みユーザーは未登録語に対して 404 を返す
        raise HTTPException(status_code=404, detail="WordPack not found")

    # 認証済みユーザーが存在しない場合、ゲストモードをチェック
    is_guest = bool(getattr(request.state, "guest", False))

    # なぜ: セッション認証が無効化された環境（disable_session_auth=True）でも、
    #       ゲスト Cookie が存在する場合は読み取り専用として扱い、未登録語の生成を抑止する。
    #       resolve_guest_session_cookie は副作用として request.state.guest = True を
    #       設定するため、認証済みユーザーの判定後にのみ呼び出す。
    if not is_guest and resolve_guest_session_cookie(request):
        is_guest = True

    if is_guest:
        raise HTTPException(
            status_code=403, detail="Guest mode cannot generate WordPack"
        )

    raise HTTPException(status_code=404, detail="WordPack not found")


@router.post(
    "/packs",
    response_model=dict,
    summary="空のWordPackを作成して保存",
    response_description="作成されたWordPackのIDを返します",
)
async def create_empty_word_pack(
    req: WordPackCreateRequest,
    _user: dict[str, str] = Depends(_require_authenticated_user),
) -> dict:
    """空のWordPackを作成・保存する（sense_title は短い日本語をLLMで生成）。

    - スキーマに適合する空のWordPack JSONを構築して保存
    - sense_title は日本語の短い見出しを優先（LLM）。失敗時のフォールバックは choose_sense_title。
    - 保存ID（wp:{32桁uuid}。旧形式のIDもそのまま利用可能）を返す
    """
    lemma = req.lemma.strip()
    if not lemma:
        raise HTTPException(status_code=400, detail="lemma is required")

    # 短い日本語の語義タイトルを LLM で生成（説明なし・1行・最大12文字程度）
    generated_title: str | None = None
    try:
        llm = get_llm_provider()
        prompt = (
            "次の英語の見出し語に対して、日本語の短い語義タイトルを1つだけ返してください。\n"
            "条件: 最大12文字、名詞句ベース、日本語のみ、説明文や引用符や記号は不要。\n"
            "見出し語: "
            f"{lemma}\n"
            "出力:"
        )
        try:
            out: str = llm.complete(prompt)  # type: ignore[attr-defined]
        except Exception as exc:  # LLM 呼出し失敗
            if settings.strict_mode:
                raise HTTPException(
                    status_code=502,
                    detail={
                        "message": "LLM failed to generate sense_title (strict mode)",
                        "reason_code": "LLM_FAILURE",
                        "diagnostics": {"lemma": lemma, "error": str(exc)[:200]},
                    },
                ) from exc
            out = ""
        cand = (out or "").strip().splitlines()[0] if isinstance(out, str) else ""
        # 余分な引用符や記号を簡易除去
        cand = cand.strip().strip('"').strip("'")
        if cand:
            generated_title = cand[:20]
    except HTTPException:
        # strict のみ再送出。それ以外はフォールバック
        raise
    except Exception:
        # 非 strict: 静かにフォールバック
        generated_title = None

    # スキーマ準拠の空WordPackを構築
    empty_word_pack = WordPack(
        lemma=lemma,
        sense_title=(
            generated_title or choose_sense_title(None, [], lemma=lemma, limit=20)
        ),
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
        etymology={"note": DEFAULT_ETYMOLOGY_PLACEHOLDER, "confidence": "low"},
        study_card="",
        citations=[],
        confidence="low",
    )

    word_pack_id = generate_word_pack_id()
    store.save_word_pack(word_pack_id, lemma, empty_word_pack.model_dump_json())

    return {"id": word_pack_id}


@router.post(
    "/pack",
    response_model=WordPack,
    response_model_exclude_none=True,
    summary="WordPack を生成",
    response_description="生成された WordPack を返します",
)
async def generate_word_pack(
    req: WordPackRequest,
    _user: dict[str, str] = Depends(_require_authenticated_user),
) -> WordPack:
    """Generate a new word pack using LangGraph flow.

    指定した語について、発音・語義・共起・対比・例文・語源などを
    まとめた学習パックを生成して返す。ダミーは生成せず、取得できない
    情報は空値で返す。
    生成されたWordPackは自動的にデータベースに保存される。
    """
    try:
        logger.info(
            "wordpack_generate_request",
            lemma=req.lemma,
            pronunciation_enabled=req.pronunciation_enabled,
            regenerate_scope=str(req.regenerate_scope),
        )
        word_pack, _ = await run_wordpack_flow(
            lemma=req.lemma,
            req_opts=req,
            scope=req.regenerate_scope,
            http_error_mapping={
                "llm_json_parse": lambda *, lemma, **__: HTTPException(
                    status_code=502,
                    detail={
                        "message": "LLM output JSON parse failed (strict mode)",
                        "reason_code": "LLM_JSON_PARSE",
                        "diagnostics": {"lemma": lemma},
                        "hint": "モデル/プロンプトの安定化、text.verbosity を lower に、または strict_mode を無効化して挙動を確認してください。ログの wordpack_llm_json_parse_failed を参照。",
                    },
                ),
                "empty_content": lambda *, lemma, diagnostics, **__: HTTPException(
                    status_code=502,
                    detail={
                        "message": "WordPack generation returned empty content (no senses/examples)",
                        "reason_code": "EMPTY_CONTENT",
                        "diagnostics": diagnostics or {},
                        "hint": "LLM_TIMEOUT_MS/LLM_MAX_TOKENS/モデル安定タグを調整してください。ログの wordpack_llm_* を確認。",
                    },
                ),
            },
        )

        # WordPackをデータベースに保存
        word_pack_id = generate_word_pack_id()
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
    except RuntimeError:
        # run_wordpack_flow 内で HTTPException へ変換済み。それ以外は上位へ委譲。
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
    for (
        wp_id,
        lemma,
        sense_title,
        created_at,
        updated_at,
        is_empty,
        examples_count,
        checked_only,
        learned,
    ) in items_with_flags:
        items.append(
            WordPackListItem(
                id=wp_id,
                lemma=lemma,
                sense_title=sense_title,
                created_at=created_at,
                updated_at=updated_at,
                is_empty=bool(is_empty),
                examples_count=examples_count,
                checked_only_count=checked_only,
                learned_count=learned,
            )
        )

    total = store.count_word_packs()

    return WordPackListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/packs/{word_pack_id}/study-progress",
    response_model=WordPackStudyProgressResponse,
    summary="WordPackの学習進捗を記録",
)
async def update_word_pack_study_progress(
    word_pack_id: str,
    req: StudyProgressRequest,
) -> WordPackStudyProgressResponse:
    """WordPack単位の確認/学習済みカウントを更新する。"""

    # kind に応じて加算対象を明示的に切り替える。
    # - checked: 確認のみ。checked_only_count を +1、learned_count は変化なし。
    # - learned: 学習完了。learned_count のみ +1。checked_only_count は「確認止まり」の回数を維持する。
    if req.kind == "checked":
        checked_increment = 1
        learned_increment = 0
    else:  # req.kind == "learned" のみ通過（Pydantic Literal で保証）
        checked_increment = 0
        learned_increment = 1
    result = store.update_word_pack_study_progress(
        word_pack_id, checked_increment, learned_increment
    )
    if result is None:
        raise HTTPException(status_code=404, detail="WordPack not found")
    checked_only_count, learned_count = result
    return WordPackStudyProgressResponse(
        checked_only_count=checked_only_count,
        learned_count=learned_count,
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
    req: WordPackRegenerateRequest,
    _user: dict[str, str] = Depends(_require_authenticated_user),
) -> WordPack:
    """既存のWordPackを再生成する。"""
    # 既存のWordPackを取得してlemmaを取得
    result = store.get_word_pack(word_pack_id)
    if result is None:
        raise HTTPException(status_code=404, detail="WordPack not found")

    lemma, _, _, _ = result

    try:
        word_pack, _ = await run_wordpack_flow(
            lemma=lemma,
            req_opts=req,
            scope=req.regenerate_scope,
            http_error_mapping={
                "llm_json_parse": lambda *, lemma, **__: HTTPException(
                    status_code=502,
                    detail={
                        "message": "LLM output JSON parse failed (strict mode)",
                        "reason_code": "LLM_JSON_PARSE",
                        "diagnostics": {"lemma": lemma},
                        "hint": "モデル/プロンプトの安定化、text.verbosity を lower に、または strict_mode を無効化して挙動を確認してください。ログの wordpack_llm_json_parse_failed を参照。",
                    },
                ),
                "empty_content": lambda *, lemma, diagnostics, **__: HTTPException(
                    status_code=502,
                    detail={
                        "message": "WordPack regeneration returned empty content (no senses/examples)",
                        "reason_code": "EMPTY_CONTENT",
                        "diagnostics": diagnostics or {},
                        "hint": "LLM_TIMEOUT_MS/LLM_MAX_TOKENS/モデル安定タグを調整してください。ログの wordpack_llm_* を確認。",
                    },
                ),
            },
        )

        # 再生成されたWordPackをデータベースに保存（既存のIDで上書き）
        word_pack_data = word_pack.model_dump_json()
        store.save_word_pack(word_pack_id, lemma, word_pack_data)

        return word_pack
    except RuntimeError:
        # run_wordpack_flow 内で HTTPException へ変換済み。それ以外は既定処理へ委譲。
        raise


# --- Async regenerate endpoints ---
async def _run_regenerate_job(
    job_id: str, word_pack_id: str, req: WordPackRegenerateRequest
) -> None:
    """Background coroutine to regenerate WordPack and update job registry."""

    async with _regenerate_lock:
        job = _regenerate_jobs.get(job_id)
        if not job:
            return
        job.status = "running"
        _regenerate_jobs[job_id] = job
    try:
        result = store.get_word_pack(word_pack_id)
        if result is None:
            raise HTTPException(status_code=404, detail="WordPack not found")
        lemma, _, _, _ = result
        word_pack, _ = await run_wordpack_flow(
            lemma=lemma,
            req_opts=req,
            scope=req.regenerate_scope,
            http_error_mapping={
                "llm_json_parse": lambda *, lemma, **__: HTTPException(
                    status_code=502,
                    detail={
                        "message": "LLM output JSON parse failed (strict mode)",
                        "reason_code": "LLM_JSON_PARSE",
                        "diagnostics": {"lemma": lemma},
                        "hint": "モデル/プロンプトの安定化、text.verbosity を lower に、または strict_mode を無効化して挙動を確認してください。ログの wordpack_llm_json_parse_failed を参照。",
                    },
                ),
                "empty_content": lambda *, lemma, diagnostics, **__: HTTPException(
                    status_code=502,
                    detail={
                        "message": "WordPack regeneration returned empty content (no senses/examples)",
                        "reason_code": "EMPTY_CONTENT",
                        "diagnostics": diagnostics or {},
                        "hint": "LLM_TIMEOUT_MS/LLM_MAX_TOKENS/モデル安定タグを調整してください。ログの wordpack_llm_* を確認。",
                    },
                ),
            },
        )
        word_pack_data = word_pack.model_dump_json()
        store.save_word_pack(word_pack_id, lemma, word_pack_data)
        job_result = word_pack
        async with _regenerate_lock:
            job = _regenerate_jobs.get(job_id)
            if job:
                job.status = "succeeded"
                job.result = job_result
                _regenerate_jobs[job_id] = job
        logger.info(
            "wordpack_regenerate_async_succeeded",
            word_pack_id=word_pack_id,
            lemma=lemma,
            job_id=job_id,
        )
    except Exception as exc:
        err_msg = str(exc)
        async with _regenerate_lock:
            job = _regenerate_jobs.get(job_id)
            if job:
                job.status = "failed"
                job.error = err_msg[:500]
                _regenerate_jobs[job_id] = job
        logger.error(
            "wordpack_regenerate_async_failed",
            word_pack_id=word_pack_id,
            job_id=job_id,
            error_type=exc.__class__.__name__,
            error_message=err_msg[:200],
        )


@router.post(
    "/packs/{word_pack_id}/regenerate/async",
    response_model=RegenerateJob,
    status_code=202,
    summary="WordPackを非同期で再生成（ジョブIDを返す）",
)
async def enqueue_regenerate_word_pack(
    word_pack_id: str,
    req: WordPackRegenerateRequest,
    _user: dict[str, str] = Depends(_require_authenticated_user),
) -> RegenerateJob:
    """Enqueue an async regenerate job and return job ID immediately."""

    if store.get_word_pack(word_pack_id) is None:
        raise HTTPException(status_code=404, detail="WordPack not found")
    job_id = uuid4().hex
    job = RegenerateJob(
        job_id=job_id, word_pack_id=word_pack_id, status="pending", result=None
    )
    async with _regenerate_lock:
        _regenerate_jobs[job_id] = job
    asyncio.create_task(_run_regenerate_job(job_id, word_pack_id, req))
    logger.info(
        "wordpack_regenerate_async_enqueued",
        word_pack_id=word_pack_id,
        job_id=job_id,
        regenerate_scope=req.regenerate_scope,
    )
    return job


@router.get(
    "/packs/{word_pack_id}/regenerate/jobs/{job_id}",
    response_model=RegenerateJob,
    summary="非同期再生成ジョブの状態を取得",
)
async def get_regenerate_job_status(
    word_pack_id: str, job_id: str
) -> RegenerateJob:
    """Return current job status and result when available."""

    async with _regenerate_lock:
        job = _regenerate_jobs.get(job_id)
    if job is None or job.word_pack_id != word_pack_id:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


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
    _user: dict[str, str] = Depends(_require_authenticated_user),
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
        model_override=_get_override_value(req, "model"),
        temperature_override=_get_override_value(req, "temperature"),
        reasoning_override=_get_override_value(req, "reasoning"),
        text_override=_get_override_value(req, "text"),
    )

    # 統合フロー（LangGraph駆動）でカテゴリ別の例文を生成して即保存
    # 失敗した場合のみ、後続の従来プロンプト経路にフォールバック
    try:
        llm_info = build_llm_info(req)
        flow = WordPackFlow(chroma_client=None, llm=llm, llm_info=llm_info)
        plan = {category: 2}
        gen = flow.generate_examples_for_categories(lemma, plan)
        items_model = gen.get(category, [])
        items: list[dict[str, object]] = []
        for it in items_model:
            items.append(
                {
                    "en": it.en,
                    "ja": it.ja,
                    "grammar_ja": it.grammar_ja,
                    "llm_model": it.llm_model,
                    "llm_params": it.llm_params,
                }
            )
        if not items:
            raise HTTPException(
                status_code=502, detail="LLM returned no usable examples"
            )
        added = store.append_examples(word_pack_id, category.value, items)
        return {
            "message": "Examples generated and appended",
            "added": added,
            "category": category.value,
            "items": items,
        }
    except RuntimeError as exc:
        _handle_flow_runtime_error(
            exc,
            lemma=lemma,
            http_error_mapping={
                "llm_json_parse": lambda *, lemma, **__: HTTPException(
                    status_code=502,
                    detail={
                        "message": "LLM output JSON parse failed (strict mode)",
                        "reason_code": "LLM_JSON_PARSE",
                        "diagnostics": {"lemma": lemma, "category": category.value},
                        "hint": "モデル/プロンプトの安定化、text.verbosity を lower に、または strict_mode を無効化して挙動を確認してください。ログの wordpack_llm_json_parse_failed を参照。",
                    },
                ),
                "empty_content": lambda *, lemma, diagnostics, **__: HTTPException(
                    status_code=502,
                    detail={
                        "message": "Example generation returned empty content",
                        "reason_code": "EMPTY_CONTENT",
                        "diagnostics": diagnostics or {"lemma": lemma, "category": category.value},
                        "hint": "LLM_TIMEOUT_MS/LLM_MAX_TOKENS/モデル安定タグを調整してください。ログの wordpack_llm_* を確認。",
                    },
                ),
            },
        )
        raise


@router.get(
    "/examples",
    response_model=ExampleListResponse,
    summary="例文一覧を取得（WordPackを横断）",
)
async def list_examples(
    limit: int = Query(default=50, ge=1, le=200, description="取得件数上限"),
    offset: int = Query(default=0, ge=0, description="オフセット"),
    order_by: str = Query(
        default="created_at", description="created_at|pack_updated_at|lemma|category"
    ),
    order_dir: str = Query(default="desc", description="asc|desc"),
    search: Optional[str] = Query(
        default=None, description="英文に対する検索文字列（部分一致等）"
    ),
    search_mode: str = Query(default="contains", description="prefix|suffix|contains"),
    category: Optional[ExampleCategory] = Query(
        default=None, description="カテゴリで絞り込み"
    ),
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
    for (
        rid,
        wp_id,
        lemma,
        cat,
        en,
        ja,
        grammar_ja,
        created_at,
        pack_updated_at,
        checked_only_count,
        learned_count,
        transcription_typing_count,
    ) in items_raw:
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
                checked_only_count=checked_only_count,
                learned_count=learned_count,
                transcription_typing_count=transcription_typing_count,
            )
        )
    return ExampleListResponse(items=items, total=total, limit=limit, offset=offset)


@router.post(
    "/examples/bulk-delete",
    response_model=ExamplesBulkDeleteResponse,
    summary="例文をID指定で一括削除",
)
async def bulk_delete_examples(
    req: ExamplesBulkDeleteRequest,
) -> ExamplesBulkDeleteResponse:
    """例文IDのリストを受け取り、一括で削除する。"""

    deleted, not_found = store.delete_examples_by_ids(req.ids)
    return ExamplesBulkDeleteResponse(deleted=deleted, not_found=not_found)


@router.post(
    "/examples/{example_id}/study-progress",
    response_model=ExampleStudyProgressResponse,
    summary="例文の学習進捗を記録",
)
async def update_example_study_progress(
    example_id: int,
    req: StudyProgressRequest,
) -> ExampleStudyProgressResponse:
    """例文単位の確認/学習済みカウントを更新する。"""

    # WordPack と同様に、確認操作と学習完了を明確に分離する。
    if req.kind == "checked":
        checked_increment = 1
        learned_increment = 0
    else:
        checked_increment = 0
        learned_increment = 1
    result = store.update_example_study_progress(
        example_id, checked_increment, learned_increment
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Example not found")
    word_pack_id, checked_only_count, learned_count = result
    return ExampleStudyProgressResponse(
        id=example_id,
        word_pack_id=word_pack_id,
        checked_only_count=checked_only_count,
        learned_count=learned_count,
    )


@router.post(
    "/examples/{example_id}/transcription-typing",
    response_model=ExampleTranscriptionTypingResponse,
    summary="例文の文字起こし練習入力を記録",
)
async def update_example_transcription_typing(
    example_id: int, req: ExampleTranscriptionTypingRequest
) -> ExampleTranscriptionTypingResponse:
    """入力長の妥当性を確認しつつ文字起こしカウントを加算する。"""

    try:
        updated = store.update_example_transcription_typing(example_id, req.input_length)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if updated is None:
        raise HTTPException(status_code=404, detail="Example not found")
    return ExampleTranscriptionTypingResponse(transcription_typing_count=updated)


class LemmaLookupResponse(BaseModel):
    found: bool = Field(..., description="lemma がDBに存在するか")
    id: Optional[str] = Field(default=None, description="WordPack ID（存在時）")
    lemma: Optional[str] = Field(
        default=None, description="保存されている lemma（正規化反映後）"
    )
    sense_title: Optional[str] = Field(
        default=None, description="語義タイトル（存在時）"
    )


@router.get(
    "/lemma/{lemma}",
    response_model=LemmaLookupResponse,
    summary="lemma から WordPack を検索（case-insensitive）",
)
async def lookup_by_lemma(lemma: str) -> LemmaLookupResponse:
    """DB内の WordPack を lemma=完全一致（大文字小文字無視）で検索し返す。

    - ヒット時: {found:true, id, lemma, sense_title}
    - 未ヒット: {found:false}
    """
    result = store.find_word_pack_by_lemma_ci(lemma)
    if result is None:
        return LemmaLookupResponse(found=False)
    wp_id, saved_lemma, sense_title = result
    return LemmaLookupResponse(
        found=True, id=wp_id, lemma=saved_lemma, sense_title=sense_title
    )
