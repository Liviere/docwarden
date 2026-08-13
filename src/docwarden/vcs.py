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

    ``paths`` entries are resolved against the process's cwd (normal shell
    semantics — the same way a bare ``git ls-files <path>`` would from
    wherever the caller happens to be standing), then re-expressed as
    absolute paths before being handed to ``git -C root``. Passing them
    through unresolved would be wrong whenever cwd != root: ``-C`` makes
    git evaluate relative pathspecs against ``root`` instead, so e.g.
    ``../CLAUDE.md`` typed from a subdirectory of the repo would resolve
    against the wrong base and often land outside the repo entirely.
    """
    args = ["git", "-C", str(root), "ls-files", "-z"]
    if paths:
        args.extend(str(Path(p).resolve()) for p in paths)
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
