from docwarden.config import DensityConfig
from docwarden.density import run


def test_run_scans_tracked_markdown_and_reports_relative_paths(make_repo):
    root = make_repo(
        {
            "docs/a.md": "**Almost entirely bold text right here** but not quite.\n",
            "docs/clean.md": "Perfectly fine short text.\n",
            "notes.txt": "**also bold but not markdown, should be ignored**\n",
        }
    )
    config = DensityConfig(bold_ratio_threshold=0.25)

    findings = run(["docs"], root, config)

    paths = {f.path for f in findings}
    assert paths == {"docs/a.md"}


def test_run_finds_nothing_when_all_clean(make_repo):
    root = make_repo({"docs/a.md": "Nothing wrong here at all.\n"})
    config = DensityConfig()

    assert run(["docs"], root, config) == []
