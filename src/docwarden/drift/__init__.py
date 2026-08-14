from pathlib import Path

from docwarden import vcs
from docwarden.config import DriftConfig
from docwarden.drift.codebase_index import build_codebase_index
from docwarden.drift.env_index import build_env_index
from docwarden.drift.rules import check_dead_paths, check_dead_symbols, check_stale_defaults
from docwarden.drift.settings_index import build_settings_index
from docwarden.findings import Finding
from docwarden.markdown import parse


def run(
    paths: list[str],
    repo_root: Path,
    config: DriftConfig,
    excludes: list[str] | None = None,
) -> list[Finding]:
    codebase_index = build_codebase_index(repo_root, set(config.code_extensions))
    settings_index = build_settings_index(repo_root, config.settings_glob, config.settings_base_classes)
    env_index = build_env_index(repo_root, config.env_globs)

    findings: list[Finding] = []
    for path in vcs.tracked_files(
        repo_root, paths=paths, suffixes=set(config.doc_extensions), excludes=excludes
    ):
        rel_path = path.relative_to(repo_root).as_posix()
        doc = parse(path.read_text(encoding="utf-8"))
        findings.extend(
            check_dead_symbols(rel_path, doc, codebase_index, settings_index, env_index)
        )
        findings.extend(check_dead_paths(rel_path, repo_root, doc, codebase_index))
        findings.extend(check_stale_defaults(rel_path, doc, settings_index))
    return findings
