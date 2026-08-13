from docwarden.config import DriftConfig
from docwarden.drift import run


def test_run_respects_excludes_for_doc_scoping(make_repo, monkeypatch):
    root = make_repo(
        {
            "src/a.py": "def compute_total():\n    pass\n",
            "docs/a.md": "Wywołuje `compute_missing()`.\n",
            "vendor/a.md": "Wywołuje `compute_missing()`.\n",
        }
    )
    monkeypatch.chdir(root)
    config = DriftConfig(code_extensions=[".py"])

    findings = run(["."], root, config, excludes=["vendor/*"])

    assert {f.path for f in findings} == {"docs/a.md"}
