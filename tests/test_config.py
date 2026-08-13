import pytest

from docwarden.config import (
    Config,
    apply_density_overrides,
    apply_drift_overrides,
    discover_config_path,
    load_config,
)
from docwarden.errors import ConfigError


def test_discover_config_path_prefers_explicit(tmp_path):
    explicit = tmp_path / "custom.toml"
    explicit.write_text("", encoding="utf-8")

    assert discover_config_path(explicit) == explicit


def test_discover_config_path_falls_back_to_cwd_pyproject(tmp_path, monkeypatch):
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    found = discover_config_path(None)

    assert found == tmp_path / "pyproject.toml"


def test_discover_config_path_none_when_nothing_found(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    assert discover_config_path(None) is None


def test_load_config_returns_defaults_for_pyproject_without_docwarden_table(tmp_path):
    path = tmp_path / "pyproject.toml"
    path.write_text("[tool.other]\nx = 1\n", encoding="utf-8")

    config = load_config(path)

    assert config == Config()


def test_load_config_reads_density_section(tmp_path):
    path = tmp_path / "pyproject.toml"
    path.write_text(
        "[tool.docwarden.density]\n"
        "bold_ratio_threshold = 0.5\n"
        "front_matter_description_enabled = true\n",
        encoding="utf-8",
    )

    config = load_config(path)

    assert config.density.bold_ratio_threshold == 0.5
    assert config.density.front_matter_description_enabled is True
    assert config.density.list_item_span_threshold == 15  # untouched default


def test_load_config_reads_nested_file_length_section(tmp_path):
    path = tmp_path / "pyproject.toml"
    path.write_text(
        "[tool.docwarden.density.file_length]\n"
        'thresholds = { "SKILL.md" = 450, "CLAUDE.md" = 300 }\n',
        encoding="utf-8",
    )

    config = load_config(path)

    assert config.density.file_length.thresholds == {"SKILL.md": 450, "CLAUDE.md": 300}
    assert config.density.file_length.default_threshold == 400  # untouched default


def test_load_config_reads_drift_section(tmp_path):
    path = tmp_path / "pyproject.toml"
    path.write_text(
        '[tool.docwarden.drift]\nsettings_glob = "services/*/app/config.py"\n',
        encoding="utf-8",
    )

    config = load_config(path)

    assert config.drift.settings_glob == "services/*/app/config.py"
    assert config.drift.settings_base_classes == ["BaseSettings"]  # untouched default


def test_load_config_raises_config_error_on_malformed_toml(tmp_path):
    path = tmp_path / "pyproject.toml"
    path.write_text("this is not [valid toml\n", encoding="utf-8")

    with pytest.raises(ConfigError):
        load_config(path)


def test_load_config_raises_config_error_when_path_missing(tmp_path):
    with pytest.raises(ConfigError):
        load_config(tmp_path / "missing.toml")


def test_apply_density_overrides_skips_none_and_applies_explicit():
    base = Config().density

    result = apply_density_overrides(base, bold_ratio_threshold=None, line_words_threshold=99)

    assert result.bold_ratio_threshold == base.bold_ratio_threshold
    assert result.line_words_threshold == 99


def test_apply_drift_overrides_skips_none_and_applies_explicit():
    base = Config().drift

    result = apply_drift_overrides(base, settings_glob=None, settings_base_classes=["BaseModel"])

    assert result.settings_glob == base.settings_glob
    assert result.settings_base_classes == ["BaseModel"]
