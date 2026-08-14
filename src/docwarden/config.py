import tomllib
from dataclasses import dataclass, field, fields, replace
from pathlib import Path

from docwarden.errors import ConfigError

# Files that can DEFINE an environment variable without any Python seeing it:
# compose, dotenv templates, shell, Dockerfiles, and n8n workflow JSON.
DEFAULT_ENV_GLOBS = (
    "*.yml",
    "*.yaml",
    "*.env",
    "*.env.example",
    "*.sh",
    "*Dockerfile*",
    "*.json",
)

# Rules that inform rather than block. `drift/dead-symbol` is advisory by
# default because its oracle cannot close: prose legitimately cites symbols
# from code we depend on but never declare, and no index will hold them.
_DEFAULT_ADVISORY = ("drift/dead-symbol",)


@dataclass(frozen=True)
class FileLengthConfig:
    default_threshold: int = 400
    thresholds: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class DensityConfig:
    bold_ratio_threshold: float = 0.25
    list_item_span_threshold: int = 15
    line_words_threshold: int = 60
    sentence_words_threshold: int = 35
    em_dash_density_threshold: int = 3
    front_matter_description_threshold: int = 500
    front_matter_description_enabled: bool = False
    file_length: FileLengthConfig = field(default_factory=FileLengthConfig)


@dataclass(frozen=True)
class DriftConfig:
    code_extensions: list[str] = field(
        default_factory=lambda: [".py", ".ts", ".tsx", ".js", ".mjs"]
    )
    doc_extensions: list[str] = field(default_factory=lambda: [".md"])
    settings_glob: str = ""
    settings_base_classes: list[str] = field(default_factory=lambda: ["BaseSettings"])
    env_globs: list[str] = field(default_factory=lambda: list(DEFAULT_ENV_GLOBS))


@dataclass(frozen=True)
class Config:
    density: DensityConfig = field(default_factory=DensityConfig)
    drift: DriftConfig = field(default_factory=DriftConfig)
    baseline_path: str = ""
    exclude: list[str] = field(default_factory=list)
    advisory: list[str] = field(default_factory=lambda: list(_DEFAULT_ADVISORY))


def discover_config_path(explicit: Path | None) -> Path | None:
    """Explicit --config wins; otherwise ./pyproject.toml relative to CWD if it
    exists. Deliberately NOT an upward directory search (unlike ruff/black/
    mypy) — a repo with multiple pyproject.toml files (as kancelaria-pjp has)
    makes silent upward discovery pick the wrong one depending on invocation
    directory.
    """
    if explicit is not None:
        return explicit
    cwd_pyproject = Path.cwd() / "pyproject.toml"
    return cwd_pyproject if cwd_pyproject.exists() else None


def load_config(path: Path) -> Config:
    if not path.exists():
        raise ConfigError(f"config file not found: {path}")
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"malformed TOML in {path}: {exc}") from exc

    table = data.get("tool", {}).get("docwarden", {})
    density_table = dict(table.get("density", {}))
    file_length_table = density_table.pop("file_length", {})
    drift_table = table.get("drift", {})

    return Config(
        density=DensityConfig(
            file_length=FileLengthConfig(**file_length_table),
            **density_table,
        ),
        drift=DriftConfig(**drift_table),
        baseline_path=table.get("baseline_path", ""),
        exclude=table.get("exclude", []),
        advisory=list(table.get("advisory", _DEFAULT_ADVISORY)),
    )


def _apply(base, overrides: dict):
    valid = {f.name for f in fields(base)}
    changes = {k: v for k, v in overrides.items() if v is not None and k in valid}
    return replace(base, **changes)


def apply_density_overrides(base: DensityConfig, **overrides) -> DensityConfig:
    return _apply(base, overrides)


def apply_drift_overrides(base: DriftConfig, **overrides) -> DriftConfig:
    return _apply(base, overrides)
