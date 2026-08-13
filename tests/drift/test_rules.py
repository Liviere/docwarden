from docwarden.drift.codebase_index import build_codebase_index
from docwarden.drift.rules import check_dead_paths, check_dead_symbols, check_stale_defaults
from docwarden.drift.settings_index import build_settings_index
from docwarden.markdown import parse


def test_dead_symbol_fires_for_removed_python_name(make_repo):
    root = make_repo({"src/a.py": "def compute_total():\n    pass\n"})
    index = build_codebase_index(root, code_extensions={".py"})
    doc = parse("Wywołuje `compute_missing()`.\n")

    findings = check_dead_symbols("docs.md", doc, index, settings_index={})

    assert len(findings) == 1
    assert findings[0].rule == "drift/dead-symbol"


def test_dead_symbol_silent_for_existing_python_name(make_repo):
    root = make_repo({"src/a.py": "def compute_total():\n    pass\n"})
    index = build_codebase_index(root, code_extensions={".py"})
    doc = parse("Wywołuje `compute_total()`... a raczej `compute_total`.\n")

    assert check_dead_symbols("docs.md", doc, index, settings_index={}) == []


def test_dead_symbol_resolves_via_string_literal_pool_not_declared_names(make_repo):
    # folderKlienta: never a declared Python identifier, only a string literal —
    # must NOT be flagged dead (this is the calibration case from the design).
    root = make_repo({"src/a.py": 'x = get(record, "folderKlienta")\n'})
    index = build_codebase_index(root, code_extensions={".py"})
    doc = parse("Pole `folderKlienta` w CRM.\n")

    assert check_dead_symbols("docs.md", doc, index, settings_index={}) == []


def test_dead_symbol_screaming_snake_checks_settings_index_before_codebase_names(make_repo):
    # The doc form is UPPERCASE (env-var style); the Python field is lowercase
    # — without checking settings_index first, this would be a false dead-symbol.
    root = make_repo(
        {"services/agent/app/config.py": "class Settings(BaseSettings):\n    folder_tree_max_depth: int = 2\n"}
    )
    codebase_index = build_codebase_index(root, code_extensions={".py"})
    settings_index = build_settings_index(root, "services/*/app/config.py", ["BaseSettings"])
    doc = parse("Próg `FOLDER_TREE_MAX_DEPTH` (2).\n")

    assert check_dead_symbols("docs.md", doc, codebase_index, settings_index) == []


def test_dead_path_fires_for_missing_bare_filename(make_repo):
    root = make_repo({"src/real.py": "x = 1\n"})
    index = build_codebase_index(root, code_extensions={".py"})
    doc = parse("Patrz `missing_file.py`.\n")

    findings = check_dead_paths("docs.md", root, doc, index)

    assert len(findings) == 1
    assert findings[0].rule == "drift/dead-path"


def test_dead_path_silent_for_existing_bare_filename(make_repo):
    root = make_repo({"src/real.py": "x = 1\n"})
    index = build_codebase_index(root, code_extensions={".py"})
    doc = parse("Patrz `real.py`.\n")

    assert check_dead_paths("docs.md", root, doc, index) == []


def test_dead_path_link_resolved_relative_to_the_doc_own_directory(make_repo):
    root = make_repo({"docs/guide.md": "x", "docs/architecture.md": "y"})
    index = build_codebase_index(root, code_extensions={".py"})
    doc = parse("See [arch](architecture.md).\n")

    assert check_dead_paths("docs/guide.md", root, doc, index) == []


def test_dead_path_link_fires_for_missing_relative_target(make_repo):
    root = make_repo({"docs/guide.md": "x"})
    index = build_codebase_index(root, code_extensions={".py"})
    doc = parse("See [missing](nope.md).\n")

    findings = check_dead_paths("docs/guide.md", root, doc, index)

    assert len(findings) == 1
    assert findings[0].rule == "drift/dead-path"


def test_stale_default_fires_when_claimed_value_differs(make_repo):
    root = make_repo(
        {"services/agent/app/config.py": "class Settings(BaseSettings):\n    archive_signatures_min_docs: int = 3\n"}
    )
    settings_index = build_settings_index(root, "services/*/app/config.py", ["BaseSettings"])
    doc = parse("(`ARCHIVE_SIGNATURES_MIN_DOCS`, default **2**)\n")

    findings = check_stale_defaults("docs.md", doc, settings_index)

    assert len(findings) == 1
    assert findings[0].rule == "drift/stale-default"
    assert "3" in findings[0].message and "2" in findings[0].message


def test_stale_default_silent_when_claimed_value_matches(make_repo):
    root = make_repo(
        {"services/agent/app/config.py": "class Settings(BaseSettings):\n    archive_signatures_min_docs: int = 2\n"}
    )
    settings_index = build_settings_index(root, "services/*/app/config.py", ["BaseSettings"])
    doc = parse("(`ARCHIVE_SIGNATURES_MIN_DOCS`, default **2**)\n")

    assert check_stale_defaults("docs.md", doc, settings_index) == []


def test_stale_default_silent_when_key_unknown_not_double_reported(make_repo):
    root = make_repo({"services/agent/app/config.py": "class Settings(BaseSettings):\n    x: int = 1\n"})
    settings_index = build_settings_index(root, "services/*/app/config.py", ["BaseSettings"])
    doc = parse("`TOTALLY_UNKNOWN_KEY` (5)\n")

    # not this check's job — already covered by check_dead_symbols
    assert check_stale_defaults("docs.md", doc, settings_index) == []
