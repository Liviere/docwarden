import argparse
import sys
from pathlib import Path

from docwarden import density, drift, vcs
from docwarden.baseline import diff as baseline_diff
from docwarden.baseline import entry_key
from docwarden.baseline import load as load_baseline
from docwarden.baseline import write as write_baseline
from docwarden.config import (
    Config,
    apply_density_overrides,
    apply_drift_overrides,
    discover_config_path,
    load_config,
)
from docwarden.errors import DocwardenError
from docwarden.findings import format_json, format_stats, format_text


def _add_common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--paths", nargs="+", required=True, help="pliki/katalogi do skanowania")
    parser.add_argument("--seed", action="store_true", help="zasiej baseline obecnym stanem")
    parser.add_argument("--prune", action="store_true", help="usuń nieaktualne wpisy baseline")
    parser.add_argument("--stats", action="store_true", help="pokaż rozkład znalezisk po plikach")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    parser.add_argument("--baseline", default=None, help="ścieżka do pliku baseline")
    parser.add_argument("--config", type=Path, default=None, help="jawna ścieżka do pyproject.toml")
    parser.add_argument("--exclude", action="append", default=None, help="wzorzec fnmatch do wykluczenia")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="docwarden")
    subparsers = parser.add_subparsers(dest="command", required=True)

    density_parser = subparsers.add_parser("density", help="metryki gęstości prozy")
    _add_common_arguments(density_parser)
    density_parser.add_argument("--bold-ratio-threshold", type=float, default=None)
    density_parser.add_argument("--list-item-span-threshold", type=int, default=None)
    density_parser.add_argument("--line-words-threshold", type=int, default=None)
    density_parser.add_argument("--sentence-words-threshold", type=int, default=None)
    density_parser.add_argument("--em-dash-density-threshold", type=int, default=None)
    density_parser.add_argument("--front-matter-description-threshold", type=int, default=None)
    density_parser.add_argument(
        "--front-matter-description",
        dest="front_matter_description_enabled",
        action=argparse.BooleanOptionalAction,
        default=None,
    )

    drift_parser = subparsers.add_parser("drift", help="rozjazd dokumentacja↔kod")
    _add_common_arguments(drift_parser)
    drift_parser.add_argument("--settings-glob", default=None)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    try:
        config_path = discover_config_path(args.config)
        config = load_config(config_path) if config_path else Config()
        repo_root = vcs.repo_root()
    except DocwardenError as exc:
        print(f"błąd: {exc}", file=sys.stderr)
        return 2

    excludes = args.exclude if args.exclude else (config.exclude or None)

    if args.command == "density":
        rule_config = apply_density_overrides(
            config.density,
            bold_ratio_threshold=args.bold_ratio_threshold,
            list_item_span_threshold=args.list_item_span_threshold,
            line_words_threshold=args.line_words_threshold,
            sentence_words_threshold=args.sentence_words_threshold,
            em_dash_density_threshold=args.em_dash_density_threshold,
            front_matter_description_threshold=args.front_matter_description_threshold,
            front_matter_description_enabled=args.front_matter_description_enabled,
        )
        findings = density.run(args.paths, repo_root, rule_config, excludes=excludes)
        default_baseline_name = ".docwarden-baseline-density"
    else:
        rule_config = apply_drift_overrides(config.drift, settings_glob=args.settings_glob)
        findings = drift.run(args.paths, repo_root, rule_config, excludes=excludes)
        default_baseline_name = ".docwarden-baseline-drift"

    baseline_path = Path(args.baseline) if args.baseline else (repo_root / default_baseline_name)
    current = {entry_key(f) for f in findings}

    if args.seed:
        write_baseline(baseline_path, current)
        print(f"Zasiano {baseline_path}: {len(current)} wpisów.")
        return 0

    if args.stats:
        print(format_stats(findings))
        return 0

    baseline = load_baseline(baseline_path)

    if args.prune:
        stale = baseline - current
        write_baseline(baseline_path, baseline & current)
        print(f"Usunięto {len(stale)} nieaktualnych wpisów; zostaje {len(baseline & current)}.")
        return 0

    new_keys, stale_keys = baseline_diff(current, baseline)
    new_findings = [f for f in findings if entry_key(f) in new_keys]

    if args.format == "json":
        if new_findings:
            print(format_json(new_findings))
    else:
        if new_findings:
            print(format_text(new_findings))
        if stale_keys:
            print(f"\nNIEAKTUALNE wpisy baseline ({len(stale_keys)}) — usuń przez --prune:")
            for entry in sorted(stale_keys):
                print(f"  {entry}")

    return 1 if (new_keys or stale_keys) else 0
