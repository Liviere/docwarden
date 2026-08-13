from docwarden.drift.settings_index import build_settings_index, extract_default_value
import ast


def _value_node(expr: str):
    return ast.parse(expr, mode="eval").body


def test_extract_default_value_reads_int_literal():
    is_literal, value = extract_default_value(_value_node("2"))

    assert is_literal is True
    assert value == 2


def test_extract_default_value_reads_negative_int_literal():
    is_literal, value = extract_default_value(_value_node("-1"))

    assert is_literal is True
    assert value == -1


def test_extract_default_value_reads_string_and_bool():
    assert extract_default_value(_value_node('"paddle"')) == (True, "paddle")
    assert extract_default_value(_value_node("True")) == (True, True)


def test_extract_default_value_none_for_missing_value():
    is_literal, value = extract_default_value(None)

    assert is_literal is False


def test_extract_default_value_none_for_computed_expression():
    is_literal, _ = extract_default_value(_value_node("Field(default_factory=list)"))

    assert is_literal is False


def test_build_settings_index_finds_annassign_defaults(make_repo):
    root = make_repo(
        {
            "services/agent/app/config.py": (
                "class Settings(BaseSettings):\n"
                "    folder_tree_max_depth: int = 2\n"
                "    archive_signatures_min_docs: int = 2\n"
            ),
        }
    )

    index = build_settings_index(root, "services/*/app/config.py", ["BaseSettings"])

    assert index["FOLDER_TREE_MAX_DEPTH"][0].default == 2
    assert index["FOLDER_TREE_MAX_DEPTH"][0].is_literal is True
    assert index["FOLDER_TREE_MAX_DEPTH"][0].service == "services/agent/app/config.py"


def test_build_settings_index_only_matches_direct_base_classes(make_repo):
    root = make_repo(
        {
            "services/agent/app/config.py": (
                "class Settings(BaseSettings):\n    x: int = 1\n"
                "class RequestBody(BaseModel):\n    y: int = 2\n"
            ),
        }
    )

    index = build_settings_index(root, "services/*/app/config.py", ["BaseSettings"])

    assert "X" in index
    assert "Y" not in index  # BaseModel not in base_class_names, correctly excluded


def test_build_settings_index_collects_list_per_name_across_services(make_repo):
    root = make_repo(
        {
            "services/agent/app/config.py": "class Settings(BaseSettings):\n    log_level: str = 'INFO'\n",
            "services/ocr/app/config.py": "class Settings(BaseSettings):\n    log_level: str = 'DEBUG'\n",
        }
    )

    index = build_settings_index(root, "services/*/app/config.py", ["BaseSettings"])

    assert len(index["LOG_LEVEL"]) == 2
    services = {fi.service for fi in index["LOG_LEVEL"]}
    assert services == {"services/agent/app/config.py", "services/ocr/app/config.py"}


def test_build_settings_index_empty_glob_returns_empty_index(make_repo):
    root = make_repo({"services/agent/app/config.py": "class Settings(BaseSettings):\n    x: int = 1\n"})

    assert build_settings_index(root, "", ["BaseSettings"]) == {}
