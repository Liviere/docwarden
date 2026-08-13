import subprocess
from pathlib import Path

import pytest


def _run_git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True)


@pytest.fixture
def make_repo(tmp_path):
    """Factory fixture: writes files under a fresh git repo and commits them.

    Usage: root = make_repo({"CLAUDE.md": "# hi\\n", "src/a.py": "def f(): pass\\n"})
    """

    def _make(files: dict[str, str]) -> Path:
        root = tmp_path / "repo"
        root.mkdir()
        _run_git(root, "init", "-q")
        _run_git(root, "config", "user.email", "test@example.com")
        _run_git(root, "config", "user.name", "Test")
        for rel_path, content in files.items():
            path = root / rel_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        _run_git(root, "add", "-A")
        _run_git(root, "commit", "-q", "-m", "init")
        return root

    return _make
