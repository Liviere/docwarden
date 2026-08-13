from pathlib import Path

from docwarden.findings import Finding

_HEADER = (
    "# docwarden baseline — accepted findings, meant to only SHRINK.\n"
    "# One entry per line: path::rule::fingerprint.\n"
    "# A new entry not listed here is reported as a new finding; a listed\n"
    "# entry no longer produced is reported as stale (fix by re-seeding).\n"
    "#\n"
    "# Regenerate: docwarden <density|drift> --seed --paths ...\n"
)


def entry_key(finding: Finding) -> str:
    return f"{finding.path}::{finding.rule}::{finding.fingerprint}"


def load(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }


def write(path: Path, entries: set[str]) -> None:
    path.write_text(_HEADER + "\n".join(sorted(entries)) + "\n", encoding="utf-8")


def diff(current: set[str], baseline: set[str]) -> tuple[set[str], set[str]]:
    """Returns (new, stale): entries in current-not-baseline, and baseline-not-current."""
    return current - baseline, baseline - current
