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


def test_classify_rejects_placeholder_and_glob_tokens():
    # Prose writes patterns, not names: a token carrying a placeholder or a
    # glob describes a FAMILY of files, so resolving it against the index is
    # meaningless. No real identifier or path contains these characters.
    assert classify_candidate("{stem}.ocr.txt") is None
    assert classify_candidate("src/objects/<name>.ts") is None
    assert classify_candidate("*.json") is None
    assert classify_candidate("…_plik.json") is None
    assert classify_candidate("services/agent/app/{main,crm_twenty}.py") is None


def test_classify_rejects_a_bare_extension_chain():
    # Prose names a CLASS of artifacts by its suffix ("the .ocr.txt next to
    # each PDF") — there is no stem, so there is no file to resolve. Compare
    # `x.ocr.txt`, which does name one.
    assert classify_candidate(".ocr.txt") is None
    assert classify_candidate(".result.json") is None
    assert classify_candidate(".ocr.manifest.json") is None
    assert classify_candidate("x.ocr.txt") == "path"
    # A dotted path with a directory still names a real place.
    assert classify_candidate(".claude/settings.local.json") == "path"


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


def test_extract_settings_claims_word_form_does_not_cross_into_a_markdown_link():
    # Real repo prose: an unparseable value ("OFF") followed by an ADR link
    # reference, soft-wrapped. The link's "0007" must not be mistaken for
    # the claimed default just because it's the nearest number after "domyślnie".
    doc = parse(
        "przez `LAWSUIT_PHOTOS_TO_MODEL` (domyślnie OFF,\n"
        "[ADR 0007](docs/adr/0007-foo.md)) — reszta zdania.\n"
    )

    claims = extract_settings_claims(doc)

    assert not any(c.key == "LAWSUIT_PHOTOS_TO_MODEL" for c in claims)


def test_extract_settings_claims_drops_a_default_the_table_row_does_not_own():
    # A reference table documents ONE key per row. When the description cell
    # cites a second key ("same class of change as X"), the value that follows
    # is not attributable — neither to the cited key (it is not its default)
    # nor to the row (proximity says otherwise). Nothing is claimed.
    doc = parse(
        "| Flaga | Opis |\n"
        "| --- | --- |\n"
        "| `CASE_FOLDER_ROUTING` | ta sama klasa zmiany co `FLOW_NAME_BY_FLOW_DATE`. "
        "Default **false** = rollback |\n"
    )

    assert extract_settings_claims(doc) == []


def test_extract_settings_claims_keeps_a_table_row_default_about_its_own_key():
    doc = parse(
        "| Flaga | Opis |\n"
        "| --- | --- |\n"
        "| `FOLDER_TREE_MAX_DEPTH` | głębokość drzewa, `FOLDER_TREE_MAX_DEPTH` default **2** |\n"
    )

    claims = extract_settings_claims(doc)

    assert [(c.key, c.claimed_value) for c in claims] == [("FOLDER_TREE_MAX_DEPTH", "2")]


def test_extract_settings_claims_word_form_stops_at_a_word_valued_default():
    # "default ON" states the default in words. Without consuming it the
    # window scans on and swallows the next numeral it meets — here the "(1)"
    # opening an enumeration — producing a claim of `=1` out of thin air.
    doc = parse(
        "(za flagą `AI_GATEWAY_ATTACHMENTS_ENABLED`, default ON): (1) **front robi de-inline**\n"
    )

    claims = extract_settings_claims(doc)

    assert not any(c.key == "AI_GATEWAY_ATTACHMENTS_ENABLED" for c in claims)


def test_extract_settings_claims_word_form_across_soft_wrapped_source_line():
    # Manually-wrapped prose (this repo's actual SKILL.md style) puts "default"
    # at the end of one source line and the value at the start of the next —
    # still one paragraph/inline token, joined by a soft line break.
    doc = parse("(`aggregate`, `ARCHIVE_SIGNATURES_MIN_DOCS`, default\n**2**): reszta zdania.\n")

    claims = extract_settings_claims(doc)

    keys = {c.key for c in claims}
    assert "ARCHIVE_SIGNATURES_MIN_DOCS" in keys
