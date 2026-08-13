import subprocess
from fnmatch import fnmatch
from pathlib import Path

from docwarden.errors import NotAGitRepositoryError


def repo_root(start: Path | None = None) -> Path:
    """Locate the git work tree root containing ``start`` (default: cwd).

    Fails loud rather than falling back to a raw filesystem walk: the whole
    baseline model and drift's "whole codebase" ground truth are meaningless
    outside a git repo, and this gets .gitignore exclusion for free.
    """
    cwd = start or Path.cwd()
    result = subprocess.run(
        ["git", "-C", str(cwd), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise NotAGitRepositoryError(f"{cwd} is not inside a git work tree")
    return Path(result.stdout.strip()).resolve()


def tracked_files(
    root: Path,
    paths: list[str] | None = None,
    suffixes: set[str] | None = None,
    excludes: list[str] | None = None,
) -> list[Path]:
    """List git-tracked files under ``root``, optionally scoped/filtered.

    One function reused for every scoping need in the package: doc-scoping
    (paths=--paths, suffixes={.md}), drift's codebase index (paths=None,
    suffixes=code extensions), and drift's path index (paths=None,
    suffixes=None). ``paths=None`` always means "whole repo", never "nothing".
    """
    args = ["git", "-C", str(root), "ls-files", "-z"]
    if paths:
        args.extend(paths)
    result = subprocess.run(args, check=True, capture_output=True, text=True)

    found: list[Path] = []
    for rel in result.stdout.split("\0"):
        if not rel:
            continue
        if excludes and any(fnmatch(rel, pattern) for pattern in excludes):
            continue
        path = root / rel
        if suffixes is not None and path.suffix not in suffixes:
            continue
        found.append(path)
    return found
