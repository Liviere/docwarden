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
