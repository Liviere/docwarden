import re
from fnmatch import fnmatch
from pathlib import Path

from docwarden import vcs

# An environment variable is DECLARED as an assignment (`NAME=value`,
# `NAME: value`, `ENV NAME=value`, or a compose list entry `- NAME=value`) and
# REFERENCED as `$NAME` / `${NAME}` in shell-ish files or as `$env.NAME` inside
# n8n expression strings. Uppercase and at least three characters, so ordinary
# YAML keys and two-letter noise stay out.
_ASSIGNMENT = re.compile(r"^\s*(?:-\s*)?(?:ENV\s+)?([A-Z][A-Z0-9_]{2,})\s*[:=]", re.MULTILINE)
_SHELL_REFERENCE = re.compile(r"\$\{?([A-Z][A-Z0-9_]{2,})")
_N8N_REFERENCE = re.compile(r"\$env\.([A-Z][A-Z0-9_]{2,})")

_PATTERNS = (_ASSIGNMENT, _SHELL_REFERENCE, _N8N_REFERENCE)


def build_env_index(repo_root: Path, globs: list[str]) -> set[str]:
    """Every environment-variable name the repository knows, from the surfaces
    a ``Settings`` class cannot see.

    Docs name variables that never reach ``config.py``: they configure n8n,
    Twenty or Traefik and live only in compose files, ``.env.example`` or n8n
    workflow JSON. Without this index every such mention reads as dead — 65 of
    them in the calibration corpus.

    Deliberately permissive within the globs (a referenced-but-never-defined
    name still counts as "the repo knows it"): the point is to stop false
    accusations, and a variable nobody defines is a config problem, not a
    documentation problem.
    """
    if not globs:
        return set()

    names: set[str] = set()
    for path in vcs.tracked_files(repo_root, paths=None):
        rel = path.relative_to(repo_root).as_posix()
        if not any(fnmatch(rel, pattern) for pattern in globs):
            continue
        try:
            source = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for pattern in _PATTERNS:
            names.update(pattern.findall(source))
    return names
