from docwarden.config import DriftConfig
from docwarden.drift import run


def test_run_finds_dead_symbol_across_scoped_docs(make_repo, monkeypatch):
    root = make_repo(
        {
            "src/a.py": "def compute_total():\n    pass\n",
            "docs/guide.md": "Wywołuje `compute_missing()`.\n",
            "docs/other.md": "Wywołuje `compute_total()`.\n",
        }
    )
    monkeypatch.chdir(root)
    config = DriftConfig(code_extensions=[".py"])

    findings = run(["docs"], root, config)

    assert {f.path for f in findings} == {"docs/guide.md"}


def test_run_ground_truth_stays_whole_repo_even_when_paths_scoped(make_repo, monkeypatch):
    # symbol declared OUTSIDE the scanned --paths scope must still resolve
    root = make_repo(
        {
            "src/outside_scope.py": "def compute_total():\n    pass\n",
            "docs/guide.md": "Wywołuje `compute_total()`.\n",
        }
    )
    monkeypatch.chdir(root)
    config = DriftConfig(code_extensions=[".py"])

    findings = run(["docs"], root, config)

    assert findings == []
