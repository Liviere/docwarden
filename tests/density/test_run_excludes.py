from docwarden.config import DensityConfig
from docwarden.density import run


def test_run_respects_excludes(make_repo):
    root = make_repo(
        {
            "docs/a.md": "**Almost entirely bold text right here** but not quite.\n",
            "vendor/lib.md": "**Also almost entirely bold text right here** yes.\n",
        }
    )
    config = DensityConfig(bold_ratio_threshold=0.25)

    findings = run(["."], root, config, excludes=["vendor/*"])

    assert {f.path for f in findings} == {"docs/a.md"}
