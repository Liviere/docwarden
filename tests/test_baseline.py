from docwarden.baseline import diff, entry_key, load, write
from docwarden.findings import Finding


def _finding(**overrides):
    base = dict(
        path="CLAUDE.md",
        line=10,
        end_line=10,
        rule="density/bold-ratio",
        message="msg",
        snippet="snip",
        fingerprint="abc123def456",
    )
    base.update(overrides)
    return Finding(**base)


def test_entry_key_joins_path_rule_fingerprint():
    key = entry_key(_finding(path="a.md", rule="density/bold-ratio", fingerprint="abc123def456"))

    assert key == "a.md::density/bold-ratio::abc123def456"


def test_load_missing_file_returns_empty_set(tmp_path):
    assert load(tmp_path / "does-not-exist") == set()


def test_write_then_load_roundtrips(tmp_path):
    path = tmp_path / "baseline.txt"
    entries = {"a.md::density/bold-ratio::abc123def456", "b.md::drift/dead-symbol::foo"}

    write(path, entries)
    loaded = load(path)

    assert loaded == entries


def test_load_skips_comment_and_blank_lines(tmp_path):
    path = tmp_path / "baseline.txt"
    path.write_text("# a comment\n\na.md::rule::fp\n   \n", encoding="utf-8")

    assert load(path) == {"a.md::rule::fp"}


def test_diff_reports_new_and_stale_entries():
    current = {"a.md::rule::1", "b.md::rule::2"}
    baseline = {"a.md::rule::1", "c.md::rule::3"}

    new, stale = diff(current, baseline)

    assert new == {"b.md::rule::2"}
    assert stale == {"c.md::rule::3"}
