# docwarden

Configurable linting for Markdown documentation: prose density (overlong sentences, unbroken lists,
oversized table cells, overuse of bold) and drift (docs referencing code symbols, paths, environment
variables, or config defaults that no longer match reality).

## Install (as a dev dependency)

```toml
[tool.poetry.dependencies]
docwarden = { git = "https://github.com/Liviere/docwarden", tag = "v0.3.0" }
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

### What the rules deliberately stay silent about

Each exception below buys precision with recall, because a rule nobody trusts is a rule nobody acts
on. All three were measured against a 17-file corpus before being added.

- **A stemless token is not a path.** `` `.ocr.txt` `` names a class of artifacts, not a file, so it
  is never resolved. Costs: a dotfile cited without its directory (`` `.eslintrc.json` ``).
- **A trailing segment sequence of a known variable is not dead.** Prose spells `LAWSUIT_PHOTOS_MAX_EDGE`
  out once and writes `` `MAX_EDGE` `` afterwards. The `_` boundary is required, so `MAXEDGE` still
  reports. Costs: a genuinely dead short name while any longer name ends the same way.
- **A default stated inside a keyed table row must be about that row's key.** A description cell
  citing a sibling flag ("same class of change as `X`") otherwise hands `X` the row's default.
  Unattributable claims are dropped rather than reattached — reattaching was measured to remove
  2 false claims and invent 5. `default ON` / `OFF` is consumed and dropped too: left unmatched, the
  search window scans past it and reports the next numeral it finds.

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
