from docwarden.drift.codebase_index import (
    build_codebase_index,
    python_declared_names,
    python_string_literal_constants,
    ts_declared_names,
)


def test_python_declared_names_finds_function_class_and_variable():
    source = "def compute_total():\n    pass\n\nclass Widget:\n    pass\n\nMAX_DEPTH = 2\n"

    names = python_declared_names(source)

    assert {"compute_total", "Widget", "MAX_DEPTH"} <= names


def test_python_declared_names_finds_pydantic_annassign_field():
    source = (
        "class Settings(BaseSettings):\n"
        "    folder_tree_max_depth: int = 2\n"
    )

    names = python_declared_names(source)

    assert "folder_tree_max_depth" in names


def test_python_declared_names_finds_function_parameters():
    source = "def f(archive_signatures_min_docs, other=1):\n    pass\n"

    names = python_declared_names(source)

    assert {"archive_signatures_min_docs", "other"} <= names


def test_python_string_literal_constants_finds_identifier_shaped_strings():
    source = 'x = get(record, "folderKlienta")\n'

    pool = python_string_literal_constants(source)

    assert "folderKlienta" in pool


def test_python_string_literal_constants_ignores_prose_strings():
    source = 'msg = "this is a whole sentence with spaces"\n'

    pool = python_string_literal_constants(source)

    assert pool == set()


def test_ts_declared_names_finds_function_class_interface():
    source = (
        "function computeTotal() {}\n"
        "class Widget {}\n"
        "interface Config {}\n"
    )

    names = ts_declared_names(source)

    assert {"computeTotal", "Widget", "Config"} <= names


def test_build_codebase_index_aggregates_across_whole_repo(make_repo):
    root = make_repo(
        {
            "services/agent/app/config.py": (
                "class Settings(BaseSettings):\n    folder_tree_max_depth: int = 2\n"
            ),
            "services/agent/app/helper.py": 'x = get(r, "folderKlienta")\n',
            "src/widget.ts": "export class Widget {}\n",
            "docs/readme.md": "not code\n",
        }
    )

    index = build_codebase_index(root, code_extensions={".py", ".ts"})

    assert "folder_tree_max_depth" in index.names
    assert "Widget" in index.names
    assert "folderKlienta" in index.string_pool
    assert index.basenames["config.py"] == ["services/agent/app/config.py"]
    assert "docs/readme.md" in index.all_paths  # unfiltered path index sees every tracked file
