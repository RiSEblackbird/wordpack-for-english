"""Flow 基盤ユーティリティ。backend.providers の新構成と連携する。"""

from typing import Any

# 共通: LangGraph の StateGraph をインポート（テスト用スタブにも対応）
try:
    from langgraph.graph import StateGraph  # type: ignore
except Exception:
    try:
        import langgraph  # type: ignore

        StateGraph = langgraph.graph.StateGraph  # type: ignore[attr-defined]
    except Exception as exc:  # pragma: no cover - library required
        raise ImportError(
            "Flows require the 'langgraph' package (expected langgraph.graph.StateGraph)."
        ) from exc


def create_state_graph() -> Any:
    """LangGraph の API 差異に耐える `StateGraph` 生成ヘルパ。

    - 旧API: 引数なし `StateGraph()`
    - 新API: `StateGraph(state_schema: TypedDict)` などを要求
    """
    # まずは引数なしで試す（テストのスタブでも動く）
    try:
        return StateGraph()  # type: ignore[call-arg]
    except TypeError:
        pass

    # 最小の TypedDict を定義して渡す（positional/keyword の両方に対応）
    try:
        from typing import TypedDict, Any as TypingAny

        class _MinimalState(TypedDict):
            dummy: TypingAny

        try:
            return StateGraph(_MinimalState)  # type: ignore[arg-type]
        except TypeError:
            return StateGraph(state_schema=_MinimalState)  # type: ignore[arg-type]
    except Exception:
        # ここまで来たら素の例外を投げてデバッグ可能にする
        return StateGraph()  # 再スローさせる


__all__ = ["create_state_graph", "StateGraph"]
