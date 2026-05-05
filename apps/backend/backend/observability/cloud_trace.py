from __future__ import annotations

import string


def parse_cloud_trace_header(
    raw_header: str | None,
    *,
    gcp_project_id: str | None = None,
) -> dict[str, object]:
    """Parse `X-Cloud-Trace-Context` into Cloud Logging trace fields."""

    if gcp_project_id is None:
        from ..config import settings

        project_id = settings.gcp_project_id
    else:
        project_id = gcp_project_id
    if not raw_header or not project_id:
        return {}

    trace_span_part, _, option_part = raw_header.partition(";")
    trace_id, separator, span_part = trace_span_part.partition("/")
    if not separator or not trace_id:
        return {}

    trace_id = trace_id.strip()
    if len(trace_id) != 32 or any(ch not in string.hexdigits for ch in trace_id):
        return {}

    span_id: str | None = None
    cleaned_span = span_part.strip()
    if cleaned_span:
        try:
            span_int = int(cleaned_span, 10)
            if 0 <= span_int < 2**64:
                span_id = str(span_int)
        except ValueError:
            span_id = None

    trace_sampled = False
    if option_part:
        for opt in option_part.split(";"):
            key, _, value = opt.partition("=")
            if key.strip() == "o":
                trace_sampled = value.strip() == "1"

    trace_context: dict[str, object] = {
        "trace": f"projects/{project_id}/traces/{trace_id}",
        "trace_sampled": trace_sampled,
    }
    if span_id is not None:
        trace_context["spanId"] = span_id
    return trace_context
