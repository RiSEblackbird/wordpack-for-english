from __future__ import annotations

import threading
from functools import lru_cache
from typing import Any, Callable

try:
    # g2p_en は ARPABET を返す
    from g2p_en import G2p  # type: ignore
except Exception:  # pragma: no cover - optional during tests
    G2p = None  # type: ignore

try:
    import cmudict  # type: ignore
except Exception:  # pragma: no cover - optional during tests
    cmudict = None  # type: ignore

from .models.word import Pronunciation


_ARPABET_TO_IPA = {
    # Vowels
    "AA": "ɑ",
    "AE": "æ",
    "AH": "ʌ",
    "AO": "ɔ",
    "AW": "aʊ",
    "AY": "aɪ",
    "EH": "ɛ",
    "ER": "ɝ",
    "EY": "eɪ",
    "IH": "ɪ",
    "IY": "i",
    "OW": "oʊ",
    "OY": "ɔɪ",
    "UH": "ʊ",
    "UW": "u",
    # Consonants
    "B": "b",
    "CH": "tʃ",
    "D": "d",
    "DH": "ð",
    "F": "f",
    "G": "ɡ",
    "HH": "h",
    "JH": "dʒ",
    "K": "k",
    "L": "l",
    "M": "m",
    "N": "n",
    "NG": "ŋ",
    "P": "p",
    "R": "ɹ",
    "S": "s",
    "SH": "ʃ",
    "T": "t",
    "TH": "θ",
    "V": "v",
    "W": "w",
    "Y": "j",
    "Z": "z",
    "ZH": "ʒ",
}

_VOWELS = {
    "AA",
    "AE",
    "AH",
    "AO",
    "AW",
    "AY",
    "EH",
    "ER",
    "EY",
    "IH",
    "IY",
    "OW",
    "OY",
    "UH",
    "UW",
}


# 例外辞書（運用で拡張予定）。キーは小文字の見出し語、値は ARPABET 配列。
_EXCEPTION_DICT: dict[str, list[str]] = {
    # 最小サンプル。必要に応じて追加・更新する。
    "the": ["DH", "AH0"],
    "of": ["AH1", "V"],
    "data": ["D", "EY1", "T", "AH0"],
    "converge": ["K", "AH0", "N", "V", "ER1", "JH"],
}

# cmudict の辞書インスタンスは高コストのためキャッシュ
_CMU_CACHE: dict[str, list[list[str]]] | None = None


def _get_cmu_dict() -> dict[str, list[list[str]]] | None:
    global _CMU_CACHE
    if cmudict is None:
        return None
    if _CMU_CACHE is None:
        try:
            _CMU_CACHE = cmudict.dict()  # type: ignore[attr-defined]
        except Exception:  # pragma: no cover
            _CMU_CACHE = None
    return _CMU_CACHE


def _call_with_timeout(func: Callable[[], Any], timeout_ms: int) -> Any | None:
    """Run func with a timeout in ms. Return None on timeout or exception."""
    result: dict[str, Any] = {"value": None}
    exc: dict[str, BaseException | None] = {"err": None}

    def target() -> None:
        try:
            result["value"] = func()
        except BaseException as e:  # pragma: no cover
            exc["err"] = e

    thread = threading.Thread(target=target, daemon=True)
    thread.start()
    thread.join(timeout=timeout_ms / 1000.0)
    if thread.is_alive() or exc["err"] is not None:
        return None
    return result["value"]


_PRONUN_TIMEOUT_MS = 800  # g2p_en の安全タイムアウト（ミリ秒）


def _strip_stress(phone: str) -> tuple[str, int | None]:
    """Return base ARPABET phone and stress (0/1/2) if present."""
    if not phone:
        return phone, None
    if phone[-1].isdigit():
        return phone[:-1], int(phone[-1])
    return phone, None


def _phones_to_ipa(phones: list[str]) -> tuple[str, int, int | None]:
    """Convert ARPABET phones to IPA string, return (ipa, syllables, primary_stress_index)."""
    ipa_parts: list[str] = []
    syllable_count = 0
    syllable_index = -1
    primary_stress_index: int | None = None

    for phone in phones:
        base, stress = _strip_stress(phone)
        # syllable detection on vowels
        if base in _VOWELS:
            syllable_index += 1
            syllable_count += 1
            if stress == 1 and primary_stress_index is None:
                primary_stress_index = syllable_index
        ipa = _ARPABET_TO_IPA.get(base, base.lower())
        ipa_parts.append(ipa)

    # fallback when no vowel detected
    if syllable_count == 0:
        syllable_count = 1
        primary_stress_index = (
            0 if primary_stress_index is None else primary_stress_index
        )

    return " ".join(ipa_parts), syllable_count, primary_stress_index


@lru_cache(maxsize=4096)
def _g2p_phones(word: str) -> list[str] | None:
    """Get ARPABET phones using exception dict, cmudict, then g2p-en (with timeout)."""
    if not word:
        return None
    lower = word.lower()
    if lower in _EXCEPTION_DICT:
        return list(_EXCEPTION_DICT[lower])

    # Prefer cached cmudict results
    cmu = _get_cmu_dict()
    if cmu is not None:
        try:
            entries = cmu.get(lower.upper()) or cmu.get(lower)
            if entries:
                return list(entries[0])
        except Exception:  # pragma: no cover
            pass

    # Fallback to g2p_en with timeout
    if G2p is not None:
        try:

            def _run() -> list[str] | None:
                g2p = G2p()
                seq = g2p(word)
                phones = [t for t in seq if t and t[0].isalpha()]
                return phones or None

            phones = _call_with_timeout(_run, _PRONUN_TIMEOUT_MS)
            if isinstance(phones, list) and phones:
                return phones
        except Exception:  # pragma: no cover
            pass
    return None


@lru_cache(maxsize=4096)
def generate_pronunciation(lemma: str) -> Pronunciation:
    """Generate Pronunciation with IPA (GA), syllables, stress, and notes.

    Uses cmudict or g2p-en when available. Falls back to heuristic estimation.
    """
    word = lemma.strip()
    if not word:
        return Pronunciation(
            ipa_GA=None,
            ipa_RP=None,
            syllables=None,
            stress_index=None,
            linking_notes=[],
        )

    phones = _g2p_phones(word)
    if phones:
        ipa_core, syllables, stress_index = _phones_to_ipa(phones)
        ipa_GA = f"/{ipa_core.replace(' ', '')}/" if ipa_core else None
        notes: list[str] = []
        if word.lower().endswith("r"):
            notes.append("語末 r の連結に注意（rhotic）")
        return Pronunciation(
            ipa_GA=ipa_GA,
            ipa_RP=None,
            syllables=syllables,
            stress_index=0 if stress_index is None else stress_index,
            linking_notes=notes,
        )

    # Heuristic fallback (very rough)
    import re

    vowel_groups = re.findall(r"[aeiouyAEIOUY]+", word)
    syllables = max(1, len(vowel_groups))
    stress_index = 0

    ipa = word.lower()
    ipa = re.sub(r"ph", "f", ipa)
    ipa = re.sub(r"tion\b", "ʃən", ipa)
    ipa = re.sub(r"sion\b", "ʒən", ipa)
    ipa = re.sub(r"ch", "tʃ", ipa)
    ipa = re.sub(r"sh", "ʃ", ipa)
    ipa = re.sub(r"th", "θ", ipa)
    ipa = re.sub(r"\bcon", "kɒn", ipa)
    ipa_GA = f"/{ipa}/"

    notes = ["語末 r の連結に注意（rhotic）"] if word.lower().endswith("r") else []
    return Pronunciation(
        ipa_GA=ipa_GA,
        ipa_RP=None,
        syllables=syllables,
        stress_index=stress_index,
        linking_notes=notes,
    )
