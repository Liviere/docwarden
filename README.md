# docwarden

Configurable linting for Markdown documentation: prose density (overlong sentences, unbroken lists,
oversized table cells, overuse of bold) and drift (docs referencing code symbols, paths, or config
defaults that no longer match reality).

## Install (as a dev dependency)

```toml
[tool.poetry.dependencies]
docwarden = { git = "https://github.com/Liviere/docwarden", tag = "v0.1.0" }
```

## Usage

```bash
docwarden density --paths README.md docs/          # prose-density checks
docwarden drift    --paths README.md docs/          # docs-vs-code drift checks
docwarden density --seed --paths ...                # accept current findings as baseline
docwarden density --stats --paths ...                # triage view
```

Both subcommands require `--paths` explicitly — there is no built-in default scope. Configure via
`[tool.docwarden]` in your project's `pyproject.toml`; see each subcommand's `--help` for the full
list of overridable keys.

Exit codes: `0` clean, `1` new findings or a stale baseline entry, `2` usage/environment error.
