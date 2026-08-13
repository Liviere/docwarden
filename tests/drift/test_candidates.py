from docwarden.drift.candidates import (
    classify_candidate,
    extract_link_candidates,
    extract_settings_claims,
    extract_symbol_candidates,
)
from docwarden.markdown import parse


def test_classify_screaming_snake_requires_underscore():
    assert classify_candidate("ARCHIVE_SIGNATURES_MIN_DOCS") == "screaming_snake"
    assert classify_candidate("ADR") is None  # bare acronym, no underscore — noise


def test_classify_path_requires_known_extension():
    assert classify_candidate("client_folders.py") == "path"
    assert classify_candidate("services/agent/app/archive_drift.py") == "path"
    assert classify_candidate("/ai/attachments") is None  # HTTP route, not a file


def test_classify_identifier_snake_and_camel():
    assert classify_candidate("_accrue_side_role") == "identifier"
    assert classify_candidate("AliasChoices") == "identifier"
    assert classify_candidate("folderKlienta") == "identifier"


def test_classify_rejects_all_caps_error_codes_and_noise():
    assert classify_candidate("AADSTS50194") is None  # all-caps, no underscore, has digits
    assert classify_candidate("od case corekta.wykonaj") is None  # contains spaces


def test_extract_symbol_candidates_from_code_inline_tokens():
    doc = parse("Patrz `_python_identifiers` oraz `ADR` i `client_folders.py`.\n")

    candidates = extract_symbol_candidates(doc)

    texts = {c.text for c in candidates}
    assert "_python_identifiers" in texts
    assert "client_folders.py" in texts
    assert "ADR" not in texts  # filtered by the classification gate


def test_extract_symbol_candidates_strips_trailing_call_parens():
    doc = parse("Wywołuje `compute_total()`.\n")

    candidates = extract_symbol_candidates(doc)

    assert [c.text for c in candidates] == ["compute_total"]


def test_extract_symbol_candidates_skips_fenced_code():
    doc = parse("```\n`_not_a_real_candidate`\n```\n")

    assert extract_symbol_candidates(doc) == []


def test_extract_link_candidates_resolves_relative_hrefs():
    doc = parse("See [docs](../docs/architecture.md) and [ext](https://example.com).\n")

    candidates = extract_link_candidates(doc)

    texts = {c.text for c in candidates}
    assert texts == {"../docs/architecture.md"}


def test_extract_link_candidates_strips_trailing_anchor():
    doc = parse("See [x](./file.md#section).\n")

    candidates = extract_link_candidates(doc)

    assert candidates[0].text == "./file.md"


def test_extract_settings_claims_paren_form():
    doc = parse("sufit domyślny `FOLDER_TREE_MAX_DEPTH` (2)\n")

    claims = extract_settings_claims(doc)

    assert len(claims) == 1
    assert claims[0].key == "FOLDER_TREE_MAX_DEPTH"
    assert claims[0].claimed_value == "2"


def test_extract_settings_claims_word_form():
    doc = parse("(`aggregate`, `ARCHIVE_SIGNATURES_MIN_DOCS`, default **2**)\n")

    claims = extract_settings_claims(doc)

    keys = {c.key for c in claims}
    assert "ARCHIVE_SIGNATURES_MIN_DOCS" in keys
