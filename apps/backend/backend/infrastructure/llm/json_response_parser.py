from __future__ import annotations

import json
import re
from typing import Any


def strip_code_fences(text: str, *, prefer_json_object: bool = True) -> str:
    cleaned = str(text or "").strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"```\s*$", "", cleaned)
    if prefer_json_object:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            return cleaned[start : end + 1].strip()
    return cleaned.strip()


def sanitize_json_control_chars(text: str) -> str:
    if not text:
        return text
    out_chars: list[str] = []
    in_string = False
    escaped = False
    for ch in text:
        if in_string:
            if escaped:
                out_chars.append(ch)
                escaped = False
                continue
            if ch == "\\":
                out_chars.append(ch)
                escaped = True
                continue
            if ch == '"':
                out_chars.append(ch)
                in_string = False
                continue
            code = ord(ch)
            if 0 <= code <= 0x1F:
                out_chars.append(f"\\u{code:04x}")
            else:
                out_chars.append(ch)
        else:
            out_chars.append(ch)
            if ch == '"' and not escaped:
                in_string = True
                escaped = False
    return "".join(out_chars)


def parse_json_response(raw: str, *, prefer_json_object: bool = True) -> Any:
    cleaned = strip_code_fences(raw, prefer_json_object=prefer_json_object)
    return json.loads(sanitize_json_control_chars(cleaned))
