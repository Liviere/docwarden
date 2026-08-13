import json

from docwarden.findings import Finding, fingerprint_content, format_json, format_stats, format_text


def _finding(**overrides):
    base = dict(
        path="CLAUDE.md",
        line=10,
        end_line=10,
        rule="density/bold-ratio",
        message="42% pogrubienia (próg 25%)",
        snippet="**a lot** of **bold** text",
        fingerprint="abc123",
    )
    base.update(overrides)
    return Finding(**base)


def test_fingerprint_content_is_deterministic():
    assert fingerprint_content("some text") == fingerprint_content("some text")


def test_fingerprint_content_normalizes_whitespace():
    assert fingerprint_content("some   text\n") == fingerprint_content("some text")


def test_fingerprint_content_differs_for_different_text():
    assert fingerprint_content("some text") != fingerprint_content("other text")


def test_fingerprint_content_is_twelve_hex_chars():
    fp = fingerprint_content("anything")

    assert len(fp) == 12
    int(fp, 16)  # raises if not hex


def test_format_text_produces_grep_friendly_line():
    findings = [_finding(path="a.md", line=7, rule="density/line-words", message="too long")]

    text = format_text(findings)

    assert text == "a.md:7:density/line-words: too long"


def test_format_json_produces_ndjson_with_seven_fields():
    findings = [_finding(), _finding(line=20)]

    lines = format_json(findings).splitlines()

    assert len(lines) == 2
    obj = json.loads(lines[0])
    assert set(obj.keys()) == {"path", "line", "end_line", "rule", "message", "snippet", "fingerprint"}


def test_format_stats_counts_findings_per_file_sorted_descending():
    findings = [
        _finding(path="a.md"),
        _finding(path="a.md"),
        _finding(path="b.md"),
    ]

    stats = format_stats(findings)

    lines = stats.splitlines()
    assert "3" in lines[0]
    a_idx = next(i for i, line in enumerate(lines) if "a.md" in line)
    b_idx = next(i for i, line in enumerate(lines) if "b.md" in line)
    assert a_idx < b_idx
