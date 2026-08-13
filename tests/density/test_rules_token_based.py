from docwarden.config import DensityConfig
from docwarden.density.rules import check_bold_ratio, check_list_item_span
from docwarden.markdown import parse


def test_bold_ratio_no_finding_under_threshold():
    doc = parse("Some **bold** word in a long sentence that is mostly plain text here.\n")
    config = DensityConfig(bold_ratio_threshold=0.25)

    assert check_bold_ratio("a.md", doc, config) == []


def test_bold_ratio_finding_over_threshold():
    doc = parse("**Almost all of this text is bold** but a bit isn't.\n")
    config = DensityConfig(bold_ratio_threshold=0.25)

    findings = check_bold_ratio("a.md", doc, config)

    assert len(findings) == 1
    f = findings[0]
    assert f.rule == "density/bold-ratio"
    assert f.line == 1
    assert f.fingerprint != ""


def test_bold_ratio_handles_adjacent_bold_spans():
    # A naive `\*\*[^*]+\*\*` regex can misparse "**a****b**" — walking real
    # strong_open/strong_close tokens handles it correctly regardless.
    doc = parse("**a****b** rest of sentence that is plain text and long enough.\n")
    config = DensityConfig(bold_ratio_threshold=0.5)

    findings = check_bold_ratio("a.md", doc, config)

    assert findings == []  # "ab" (2 chars) out of the whole sentence is well under 50%


def test_bold_ratio_scoped_per_table_cell_not_whole_table():
    text = "| a | b |\n|---|---|\n| **bold cell** | plain |\n"
    doc = parse(text)
    config = DensityConfig(bold_ratio_threshold=0.5)

    findings = check_bold_ratio("a.md", doc, config)

    assert len(findings) == 1  # only the bold cell fires, not the whole table as one block


def test_list_item_span_no_finding_under_threshold():
    doc = parse("- short item\n- another short one\n")
    config = DensityConfig(list_item_span_threshold=15)

    assert check_list_item_span("a.md", doc, config) == []


def test_list_item_span_finding_over_threshold():
    item_lines = "\n".join(f"  continuation line {i}" for i in range(20))
    text = f"- first line of a long item\n{item_lines}\n"
    doc = parse(text)
    config = DensityConfig(list_item_span_threshold=15)

    findings = check_list_item_span("a.md", doc, config)

    assert len(findings) == 1
    f = findings[0]
    assert f.rule == "density/list-item-span"
    assert f.line == 1
