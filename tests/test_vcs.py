from docwarden.errors import NotAGitRepositoryError
from docwarden.vcs import repo_root, tracked_files


def test_repo_root_finds_toplevel_from_nested_start(make_repo):
    root = make_repo({"a/b/c.md": "hi\n"})

    found = repo_root(start=root / "a" / "b")

    assert found == root.resolve()


def test_repo_root_raises_outside_a_repo(tmp_path):
    outside = tmp_path / "not-a-repo"
    outside.mkdir()

    try:
        repo_root(start=outside)
        assert False, "expected NotAGitRepositoryError"
    except NotAGitRepositoryError:
        pass


def test_tracked_files_lists_everything_by_default(make_repo):
    root = make_repo({"CLAUDE.md": "x", "src/a.py": "x", "README": "x"})

    found = {p.relative_to(root).as_posix() for p in tracked_files(root)}

    assert found == {"CLAUDE.md", "src/a.py", "README"}


def test_tracked_files_filters_by_suffix(make_repo):
    root = make_repo({"CLAUDE.md": "x", "src/a.py": "x", "README": "x"})

    found = {p.relative_to(root).as_posix() for p in tracked_files(root, suffixes={".md"})}

    assert found == {"CLAUDE.md"}


def test_tracked_files_scopes_by_paths(make_repo):
    root = make_repo({"CLAUDE.md": "x", "sub/inner.md": "x", "other/inner.md": "x"})

    found = {p.relative_to(root).as_posix() for p in tracked_files(root, paths=["sub"])}

    assert found == {"sub/inner.md"}


def test_tracked_files_ignores_untracked_files(make_repo):
    root = make_repo({"CLAUDE.md": "x"})
    (root / "untracked.md").write_text("x", encoding="utf-8")

    found = {p.relative_to(root).as_posix() for p in tracked_files(root)}

    assert found == {"CLAUDE.md"}


def test_tracked_files_respects_excludes(make_repo):
    root = make_repo({"CLAUDE.md": "x", "vendor/lib.md": "x"})

    found = {p.relative_to(root).as_posix() for p in tracked_files(root, excludes=["vendor/*"])}

    assert found == {"CLAUDE.md"}
