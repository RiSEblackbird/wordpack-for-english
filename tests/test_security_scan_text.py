from scripts.security_scan_text import scan_text


def test_detects_bidi_control_character() -> None:
    findings = scan_text("safe = True\u202e", "example.py")
    assert findings
    assert "U+202E" in findings[0]


def test_detects_zero_width_character() -> None:
    findings = scan_text("token = 'abc\u200bdef'", "example.py")
    assert findings
    assert "U+200B" in findings[0]


def test_allows_plain_japanese_text() -> None:
    findings = scan_text("# 日本語コメントは許可する\nprint('hello')", "example.py")
    assert findings == []
