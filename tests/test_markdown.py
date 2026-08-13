from docwarden.markdown import fence_line_set, iter_inline_tokens, parse


def test_parse_splits_raw_lines():
    doc = parse("first\nsecond\n")

    assert doc.lines == ["first", "second"]


def test_parse_produces_block_tokens():
    doc = parse("# Title\n\nBody text.\n")

    types = [t.type for t in doc.tokens]

    assert "heading_open" in types
    assert "paragraph_open" in types


def test_fence_line_set_covers_whole_fenced_block_only():
    text = (
        "before\n"
        "\n"
        "```\n"
        "code line\n"
        "```\n"
        "\n"
        "after\n"
    )
    doc = parse(text)

    fenced = fence_line_set(doc.tokens)

    # 0-indexed: line 2 = "```", 3 = "code line", 4 = "```"
    assert fenced == {2, 3, 4}


def test_iter_inline_tokens_finds_paragraph_and_nested_list_item():
    text = "Top paragraph.\n\n- list item text\n"
    doc = parse(text)

    contents = [t.content for t in iter_inline_tokens(doc.tokens)]

    assert "Top paragraph." in contents
    assert "list item text" in contents


def test_iter_inline_tokens_finds_table_cells():
    text = "| a | b |\n|---|---|\n| x | y |\n"
    doc = parse(text)

    contents = {t.content for t in iter_inline_tokens(doc.tokens)}

    assert contents == {"a", "b", "x", "y"}
