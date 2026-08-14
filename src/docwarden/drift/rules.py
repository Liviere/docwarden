from pathlib import Path

from docwarden.drift.candidates import (
    extract_link_candidates,
    extract_settings_claims,
    extract_symbol_candidates,
)
from docwarden.drift.codebase_index import CodebaseIndex
from docwarden.drift.settings_index import FieldInfo
from docwarden.findings import Finding
from docwarden.markdown import MarkdownDocument


def _is_shorthand_for_a_known_name(candidate: str, known: set[str]) -> bool:
    """True when the candidate is a trailing SEGMENT SEQUENCE of a name we do
    know — `MAX_EDGE` inside `LAWSUIT_PHOTOS_MAX_EDGE`. Prose spells a variable
    out once and shortens it afterwards, which is a reference, not a second
    variable. The `_` boundary is what makes this safe: without it every name
    ending in a common word would switch the rule off (`MAXEDGE` must still
    report). Costs us a genuinely dead short name whenever some longer name
    ends the same way — the same precision-for-recall trade as import indexing.
    """
    tail = "_" + candidate
    return any(name.endswith(tail) for name in known)


def check_dead_symbols(
    rel_path: str,
    doc: MarkdownDocument,
    codebase_index: CodebaseIndex,
    settings_index: dict[str, list[FieldInfo]],
    env_index: set[str] | None = None,
) -> list[Finding]:
    """Two rules from one sweep, split by candidate SHAPE — because the two
    shapes have oracles of very different quality.

    An env-shaped name (``SCREAMING_SNAKE``) can be resolved exactly: it is
    either a ``Settings`` field, or it appears on one of the environment
    surfaces, or it is a constant in the code. Nothing else can define it, so
    a miss means it genuinely exists nowhere — reported as ``drift/dead-env``.

    A code-shaped name has no such closure: docs legitimately cite third-party
    symbols the project never imports (LangChain classes, Twenty enums, n8n
    node types), and no index will ever contain them. That verdict stays
    ``drift/dead-symbol`` and is meant to be run advisory (see ``Config.advisory``).
    """
    known_env = env_index or set()
    known_full_names = (
        known_env
        | set(settings_index)
        | {name for name in codebase_index.names if name.isupper()}
    )
    findings = []
    for candidate in extract_symbol_candidates(doc):
        if candidate.kind == "path":
            continue  # handled by check_dead_paths
        in_code = (
            candidate.text in codebase_index.names
            or candidate.text in codebase_index.string_pool
        )
        if candidate.kind == "screaming_snake":
            if candidate.text in settings_index or candidate.text in known_env or in_code:
                continue
            if _is_shorthand_for_a_known_name(candidate.text, known_full_names):
                continue
            findings.append(
                Finding(
                    path=rel_path,
                    line=candidate.line,
                    end_line=candidate.line,
                    rule="drift/dead-env",
                    message=(
                        f"`{candidate.text}` nie istnieje — ani w Settings, ani w środowisku, "
                        f"ani w kodzie"
                    ),
                    snippet=candidate.text,
                    fingerprint=candidate.text,
                )
            )
            continue
        if in_code:
            continue
        findings.append(
            Finding(
                path=rel_path,
                line=candidate.line,
                end_line=candidate.line,
                rule="drift/dead-symbol",
                message=f"symbol `{candidate.text}` nie istnieje w kodzie",
                snippet=candidate.text,
                fingerprint=candidate.text,
            )
        )
    return findings


def _bare_path_exists(text: str, index: CodebaseIndex) -> bool:
    if "/" not in text:
        return text in index.basenames
    return any(
        p == text or p.endswith("/" + text) for p in (*index.all_paths, *index.all_dirs)
    )


def check_dead_paths(
    rel_path: str, repo_root: Path, doc: MarkdownDocument, codebase_index: CodebaseIndex
) -> list[Finding]:
    findings = []

    for candidate in extract_symbol_candidates(doc):
        if candidate.kind != "path":
            continue
        if _bare_path_exists(candidate.text, codebase_index):
            continue
        findings.append(
            Finding(
                path=rel_path,
                line=candidate.line,
                end_line=candidate.line,
                rule="drift/dead-path",
                message=f"ścieżka `{candidate.text}` nie istnieje",
                snippet=candidate.text,
                fingerprint=candidate.text,
            )
        )

    doc_dir = (repo_root / rel_path).parent
    for candidate in extract_link_candidates(doc):
        try:
            target_rel = (doc_dir / candidate.text).resolve().relative_to(repo_root.resolve())
        except ValueError:
            continue  # points outside the repo entirely — not our concern
        target = target_rel.as_posix()
        if target in codebase_index.all_paths or target in codebase_index.all_dirs:
            continue  # docs link to directories as often as to files
        findings.append(
            Finding(
                path=rel_path,
                line=candidate.line,
                end_line=candidate.line,
                rule="drift/dead-path",
                message=f"link `{candidate.text}` nie istnieje",
                snippet=candidate.text,
                fingerprint=candidate.text,
            )
        )
    return findings


def _values_match(claimed: str, actual: object) -> bool:
    claimed = claimed.strip()
    if claimed.lower() == "true":
        return actual is True
    if claimed.lower() == "false":
        return actual is False
    if claimed.startswith('"') and claimed.endswith('"'):
        return actual == claimed[1:-1]
    if isinstance(actual, bool):
        return False
    try:
        return isinstance(actual, (int, float)) and float(actual) == float(claimed.replace(",", "."))
    except ValueError:
        return False


def check_stale_defaults(
    rel_path: str, doc: MarkdownDocument, settings_index: dict[str, list[FieldInfo]]
) -> list[Finding]:
    findings = []
    for claim in extract_settings_claims(doc):
        infos = settings_index.get(claim.key)
        if infos is None:
            continue  # unresolvable key — already surfaced via drift/dead-symbol
        literal_infos = [i for i in infos if i.is_literal]
        if not literal_infos:
            continue  # nothing literal to compare — safe silent direction
        if any(_values_match(claim.claimed_value, i.default) for i in literal_infos):
            continue
        actual = ", ".join(repr(i.default) for i in literal_infos)
        findings.append(
            Finding(
                path=rel_path,
                line=claim.line,
                end_line=claim.line,
                rule="drift/stale-default",
                message=(
                    f"zadeklarowano {claim.claimed_value}, faktycznie {actual} "
                    f"(`{claim.key}`)"
                ),
                snippet=f"{claim.key}={claim.claimed_value}",
                fingerprint=f"{claim.key}={claim.claimed_value}",
            )
        )
    return findings
