from docwarden.config import DensityConfig
from docwarden.density.rules import check_em_dash_density, check_line_words, check_sentence_words
from docwarden.markdown import parse


def test_line_words_no_finding_under_threshold():
    doc = parse("a few short words here\n")
    config = DensityConfig(line_words_threshold=60)

    assert check_line_words("a.md", doc, config) == []


def test_line_words_finding_over_threshold():
    doc = parse((" ".join(["word"] * 70)) + "\n")
    config = DensityConfig(line_words_threshold=60)

    findings = check_line_words("a.md", doc, config)

    assert len(findings) == 1
    assert findings[0].rule == "density/line-words"
    assert findings[0].line == 1


def test_line_words_skips_lines_inside_a_fence():
    long_line = " ".join(["word"] * 70)
    text = f"```\n{long_line}\n```\n"
    doc = parse(text)
    config = DensityConfig(line_words_threshold=60)

    assert check_line_words("a.md", doc, config) == []


def test_line_words_catches_oversized_table_cell_as_one_physical_line():
    long_cell = " ".join(["word"] * 70)
    text = f"| a | b |\n|---|---|\n| {long_cell} | short |\n"
    doc = parse(text)
    config = DensityConfig(line_words_threshold=60)

    findings = check_line_words("a.md", doc, config)

    assert len(findings) == 1


def test_sentence_words_no_finding_under_threshold():
    doc = parse("A short sentence.\n")
    config = DensityConfig(sentence_words_threshold=35)

    assert check_sentence_words("a.md", doc, config) == []


def test_sentence_words_finding_over_threshold():
    words = " ".join(["word"] * 40)
    doc = parse(f"{words}.\n")
    config = DensityConfig(sentence_words_threshold=35)

    findings = check_sentence_words("a.md", doc, config)

    assert len(findings) == 1
    assert findings[0].rule == "density/sentence-words"


def test_sentence_words_only_flags_the_long_sentence_not_the_short_one():
    short = "Short one."
    long_ = " ".join(["word"] * 40) + "."
    doc = parse(f"{short} {long_}\n")
    config = DensityConfig(sentence_words_threshold=35)

    findings = check_sentence_words("a.md", doc, config)

    assert len(findings) == 1
    assert "word" in findings[0].snippet


def test_em_dash_density_fires_at_exactly_the_threshold():
    # threshold is inclusive (>=), unlike the other density checks
    doc = parse("Zdanie — z dwoma (nawiasami) — i myślnikiem.\n")
    config = DensityConfig(em_dash_density_threshold=3)

    findings = check_em_dash_density("a.md", doc, config)

    assert len(findings) == 1
    assert findings[0].rule == "density/em-dash-density"


def test_em_dash_density_no_finding_below_threshold():
    doc = parse("Zdanie — z jednym myślnikiem.\n")
    config = DensityConfig(em_dash_density_threshold=3)

    assert check_em_dash_density("a.md", doc, config) == []
