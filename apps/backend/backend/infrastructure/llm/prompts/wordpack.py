from __future__ import annotations


def build_wordpack_prompt(lemma: str) -> str:
    return (
        "あなたは辞書編集者である。必ず JSON オブジェクト1件のみを返し、説明文は書かないこと。\n"
        "対象語: "
        f"{lemma}\n\n"
        "スキーマ（キーと型は完全一致させること）:\n"
        "{\n"
        '  "senses": [ { "id": "s1", "gloss_ja": "...", "definition_ja": "...", "nuances_ja": "...", "patterns": ["..."], "synonyms": ["..."], "antonyms": ["..."], "register": "...", "notes_ja": "...", "term_overview_ja": "...", "term_core_ja": "..." } ],\n'
        '  "sense_title": "10文字前後で語義全体の見出しになる短い日本語タイトル",\n'
        '  "collocations": {\n'
        '    "general": { "verb_object": ["..."], "adj_noun": ["..."], "prep_noun": ["..."] },\n'
        '    "academic": { "verb_object": ["..."], "adj_noun": ["..."], "prep_noun": ["..."] }\n'
        "  },\n"
        '  "contrast": [ { "with": "...", "diff_ja": "..." } ],\n'
        '  "etymology": { "note": "...", "confidence": "low|medium|high" },\n'
        '  "study_card": "1文の要点(日本語)",\n'
        '  "pronunciation": { "ipa_RP": "/.../" }\n'
        "}\n"
        "注意事項:\n"
        "- gloss_ja / definition_ja / nuances_ja / notes_ja は日本語。\n"
        "- もし対象語が名詞（一般名詞/固有名詞）や専門用語である場合、\n"
        "  term_overview_ja（3〜5文の概要）と term_core_ja（3〜5文の本質）を必ず日本語で記述する。\n"
        "  名詞以外（動詞/形容詞など）の場合、これら2つのキーは省略してよい。\n"
    )
