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
) -> list[Finding]:
    findings = []
    for candidate in extract_symbol_candidates(doc):
        if candidate.kind == "path":
            continue  # handled by check_dead_paths
        if candidate.kind == "screaming_snake" and candidate.text in settings_index:
            continue  # env-var-style mention of a real Settings field
        if candidate.text in codebase_index.names or candidate.text in codebase_index.string_pool:
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
    return any(p == text or p.endswith("/" + text) for p in index.all_paths)


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
        if target_rel.as_posix() in codebase_index.all_paths:
            continue
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
