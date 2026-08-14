import json

from docwarden.cli import main


def test_paths_flag_is_required(make_repo, monkeypatch, capsys):
    root = make_repo({"a.md": "text\n"})
    monkeypatch.chdir(root)

    try:
        main(["density"])
        assert False, "expected SystemExit"
    except SystemExit as exc:
        assert exc.code != 0


def test_errors_with_exit_two_outside_a_git_repo(tmp_path, monkeypatch, capsys):
    outside = tmp_path / "not-a-repo"
    outside.mkdir()
    monkeypatch.chdir(outside)

    code = main(["density", "--paths", "."])

    assert code == 2


def test_density_seed_then_clean_run_exits_zero(make_repo, monkeypatch, capsys):
    root = make_repo({"a.md": "**way too much bold text here for sure** yes indeed friend.\n"})
    monkeypatch.chdir(root)

    assert main(["density", "--seed", "--paths", "a.md", "--bold-ratio-threshold", "0.1"]) == 0
    assert main(["density", "--paths", "a.md", "--bold-ratio-threshold", "0.1"]) == 0


def test_density_new_violation_after_seed_exits_one(make_repo, monkeypatch, capsys):
    root = make_repo({"a.md": "Clean text with nothing bold at all here.\n"})
    monkeypatch.chdir(root)

    assert main(["density", "--seed", "--paths", "a.md"]) == 0
    capsys.readouterr()  # clear the seed confirmation message

    (root / "a.md").write_text("**Now almost entirely bold text right here** yes.\n", encoding="utf-8")

    code = main(["density", "--paths", "a.md", "--format", "json"])

    assert code == 1
    out = capsys.readouterr().out
    finding = json.loads(out.strip().splitlines()[0])
    assert finding["rule"] == "density/bold-ratio"


def test_density_prune_removes_stale_baseline_entry(make_repo, monkeypatch, capsys):
    root = make_repo({"a.md": "**Almost entirely bold text right here** yes.\n"})
    monkeypatch.chdir(root)
    main(["density", "--seed", "--paths", "a.md"])

    (root / "a.md").write_text("Now perfectly clean text with nothing bold.\n", encoding="utf-8")

    code = main(["density", "--prune", "--paths", "a.md"])

    assert code == 0
    baseline = (root / ".docwarden-baseline-density").read_text(encoding="utf-8")
    assert "density/bold-ratio" not in baseline


def test_density_stats_mode_exits_zero_regardless_of_findings(make_repo, monkeypatch, capsys):
    root = make_repo({"a.md": "**Almost entirely bold text right here** yes.\n"})
    monkeypatch.chdir(root)

    assert main(["density", "--stats", "--paths", "a.md"]) == 0
    assert "a.md" in capsys.readouterr().out


def test_drift_command_reports_dead_env(make_repo, monkeypatch, capsys):
    root = make_repo({"src/a.py": "x = 1\n", "docs.md": "Flaga `ARCHIVE_LONG_GONE`.\n"})
    monkeypatch.chdir(root)

    code = main(["drift", "--paths", "docs.md"])

    assert code == 1
    assert "drift/dead-env" in capsys.readouterr().out


def test_advisory_rule_neither_gates_nor_prints_by_default(make_repo, monkeypatch, capsys):
    # dead-symbol is advisory: the code-symbol oracle cannot see third-party
    # names the docs legitimately cite, so it informs rather than blocks.
    root = make_repo(
        {
            "src/a.py": "def compute_total():\n    pass\n",
            "docs.md": "Wywołuje `compute_missing()`.\n",
        }
    )
    monkeypatch.chdir(root)

    code = main(["drift", "--paths", "docs.md"])

    assert code == 0
    assert "drift/dead-symbol" not in capsys.readouterr().out


def test_advisory_flag_prints_advisory_findings_without_changing_exit_code(
    make_repo, monkeypatch, capsys
):
    root = make_repo(
        {
            "src/a.py": "def compute_total():\n    pass\n",
            "docs.md": "Wywołuje `compute_missing()`.\n",
        }
    )
    monkeypatch.chdir(root)

    code = main(["drift", "--paths", "docs.md", "--advisory"])

    assert code == 0
    assert "drift/dead-symbol" in capsys.readouterr().out


def test_advisory_findings_never_enter_the_baseline(make_repo, monkeypatch, capsys):
    root = make_repo(
        {
            "src/a.py": "def compute_total():\n    pass\n",
            "docs.md": "Wywołuje `compute_missing()`.\n",
        }
    )
    monkeypatch.chdir(root)

    main(["drift", "--seed", "--paths", "docs.md"])

    assert "drift/dead-symbol" not in (root / ".docwarden-baseline-drift").read_text(
        encoding="utf-8"
    )


def test_advisory_list_is_configurable(make_repo, monkeypatch, capsys):
    # Same lever must work the other way round: demote a gating rule.
    root = make_repo(
        {
            "pyproject.toml": '[tool.docwarden]\nadvisory = ["drift/dead-env"]\n',
            "src/a.py": "x = 1\n",
            "docs.md": "Flaga `ARCHIVE_LONG_GONE`.\n",
        }
    )
    monkeypatch.chdir(root)

    assert main(["drift", "--paths", "docs.md"]) == 0


def test_config_file_thresholds_are_applied(make_repo, monkeypatch, capsys):
    root = make_repo(
        {
            "pyproject.toml": "[tool.docwarden.density]\nbold_ratio_threshold = 0.9\n",
            "a.md": "**Almost entirely bold text right here** yes indeed friend.\n",
        }
    )
    monkeypatch.chdir(root)

    # 0.9 threshold from config means this shouldn't fire
    assert main(["density", "--paths", "a.md"]) == 0


def test_cli_flag_overrides_config_file_value(make_repo, monkeypatch, capsys):
    root = make_repo(
        {
            "pyproject.toml": "[tool.docwarden.density]\nbold_ratio_threshold = 0.9\n",
            "a.md": "**Almost entirely bold text right here** yes indeed friend.\n",
        }
    )
    monkeypatch.chdir(root)

    # explicit CLI flag should win over the 0.9 in pyproject.toml
    code = main(["density", "--paths", "a.md", "--bold-ratio-threshold", "0.1"])

    assert code == 1
