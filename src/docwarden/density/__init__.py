from pathlib import Path

from docwarden import vcs
from docwarden.config import DensityConfig
from docwarden.density import rules
from docwarden.findings import Finding
from docwarden.markdown import parse

_CHECKS = (
    rules.check_bold_ratio,
    rules.check_list_item_span,
    rules.check_line_words,
    rules.check_sentence_words,
    rules.check_em_dash_density,
    rules.check_front_matter_description,
    rules.check_file_length,
)


def run(
    paths: list[str],
    repo_root: Path,
    config: DensityConfig,
    excludes: list[str] | None = None,
) -> list[Finding]:
    findings: list[Finding] = []
    for path in vcs.tracked_files(repo_root, paths=paths, suffixes={".md"}, excludes=excludes):
        rel_path = path.relative_to(repo_root).as_posix()
        text = path.read_text(encoding="utf-8")
        doc = parse(text)
        for check in _CHECKS:
            findings.extend(check(rel_path, doc, config))
    return findings
