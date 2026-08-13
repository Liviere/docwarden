import json
from dataclasses import asdict, dataclass
from hashlib import sha1


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    end_line: int
    rule: str
    message: str
    snippet: str
    fingerprint: str


def fingerprint_content(snippet: str) -> str:
    """Stable 12-hex-char id for a piece of prose, keyed on normalized content
    rather than line number — prose shifts under editing, so a baseline
    keyed by line would go stale on every unrelated edit above the flagged
    span. Whitespace-collapsed before hashing so reflow alone doesn't change
    the fingerprint.
    """
    normalized = " ".join(snippet.split())
    return sha1(normalized.encode("utf-8")).hexdigest()[:12]


def format_text(findings: list[Finding]) -> str:
    return "\n".join(f"{f.path}:{f.line}:{f.rule}: {f.message}" for f in findings)


def format_json(findings: list[Finding]) -> str:
    return "\n".join(json.dumps(asdict(f), ensure_ascii=False) for f in findings)


def format_stats(findings: list[Finding]) -> str:
    per_file: dict[str, int] = {}
    for f in findings:
        per_file[f.path] = per_file.get(f.path, 0) + 1

    lines = [f"{len(findings)} znalezisk w {len(per_file)} plikach.", ""]
    for path, count in sorted(per_file.items(), key=lambda kv: -kv[1]):
        lines.append(f"{count:5d}  {path}")
    return "\n".join(lines)
