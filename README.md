# docwarden

Configurable linting for Markdown documentation: prose density (overlong sentences, unbroken lists,
oversized table cells, overuse of bold) and drift (docs referencing code symbols, paths, environment
variables, or config defaults that no longer match reality).

## Install (as a dev dependency)

```toml
[tool.poetry.dependencies]
docwarden = { git = "https://github.com/Liviere/docwarden", tag = "v0.2.0" }
```

## Usage

```bash
docwarden density --paths README.md docs/           # prose-density checks
docwarden drift   --paths README.md docs/           # docs-vs-code drift checks
docwarden density --seed  --paths ...               # accept current findings as baseline
docwarden density --stats --paths ...               # triage view
docwarden drift   --advisory --paths ...            # also show non-gating findings
```

Both subcommands require `--paths` explicitly — there is no built-in default scope. Configure via
`[tool.docwarden]` in your project's `pyproject.toml`; see each subcommand's `--help` for the full
list of overridable keys.

**Scope `--paths` to cover the whole baseline.** The baseline is a flat set of accepted findings and
does not record what was scanned, so a narrower `--paths` makes every entry outside it look stale —
and `--prune` would then delete them.

Exit codes: `0` clean, `1` new findings or a stale baseline entry, `2` usage/environment error.

## Drift rules

| Rule | Oracle | Gates by default |
| --- | --- | --- |
| `drift/dead-path` | tracked files and directories; markdown links resolved against the doc's own directory | yes |
| `drift/stale-default` | literal defaults of `BaseSettings` fields (`settings_glob`) | yes |
| `drift/dead-env` | `Settings` fields ∪ environment surfaces ∪ declared code names | yes |
| `drift/dead-symbol` | declared code names ∪ imported names ∪ identifier-shaped string literals | **no — advisory** |

`SCREAMING_SNAKE` candidates go to `dead-env`, everything else to `dead-symbol`. The split exists
because the oracles differ in kind: an environment variable has a closed set of possible definition
sites, whereas prose legitimately cites third-party symbols the project depends on but never
declares — and no index will ever contain those. Reporting both at the same severity buries the
verifiable rule under the unverifiable one.

The environment oracle reads assignments (`NAME=`, `NAME:`, `ENV NAME=`, compose list entries),
shell references (`$NAME`, `${NAME}`) and n8n expression references (`$env.NAME`) from every file
matching `env_globs` — by default `*.yml`, `*.yaml`, `*.env`, `*.env.example`, `*.sh`, `*Dockerfile*`
and `*.json`.

## Advisory rules

A rule listed in `advisory` still runs, but it never enters the baseline, never appears as new or
stale, and never changes the exit code. It is printed only under `--advisory` or `--stats`.

```toml
[tool.docwarden]
advisory = ["drift/dead-symbol"]   # the default; set to [] to gate on everything
```
