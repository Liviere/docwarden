import re
from dataclasses import dataclass
from pathlib import Path

from docwarden.markdown import MarkdownDocument, iter_inline_tokens

_SCREAMING_SNAKE = re.compile(r"^[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+$")
_SNAKE = re.compile(r"^_*[a-z][a-z0-9_]*$")
_CAMEL = re.compile(r"^[A-Za-z][A-Za-z0-9]*$")
# Whitespace/quotes/`$` are shell-or-prose noise; braces, angle brackets, `*`,
# `,` and `…` mark a PATTERN rather than a name (`{stem}.ocr.txt`,
# `src/objects/<name>.ts`, `*.json`) — resolving a family of files against the
# index is meaningless, so these never reach a rule.
_NOISE = re.compile(r"[\s\"'${}<>*,…]")

_PATH_EXTENSIONS = {
    ".py", ".ts", ".tsx", ".js", ".mjs", ".md", ".json", ".yml", ".yaml",
    ".j2", ".docx", ".txt", ".sh",
}

_DEFAULT_PAREN = re.compile(
    r"`([A-Z][A-Z0-9_]*)`\s*\((-?\d+(?:[.,]\d+)?|true|false|\"[^\"]{0,40}\")\)"
)
_DEFAULT_WORD = re.compile(
    r"`([A-Z][A-Z0-9_]*)`[^`\[]{0,60}?\b(?:default|domy[sś]ln\w*)\b[^`\[]{0,20}?"
    r"(?:\*\*)?(-?\d+(?:[.,]\d+)?|true|false)(?:\*\*)?",
    re.IGNORECASE,
)


def classify_candidate(token: str) -> str | None:
    """Shape-based noise gate, validated against a 2957-span/17-file corpus.
    Buckets: screaming_snake (requires underscore — excludes bare acronyms
    like ADR), path (requires a recognized extension — excludes HTTP routes),
    identifier (snake_case/camelCase — rejects all-caps error codes like
    AADSTS50194, which have no lowercase to signal a real symbol shape).
    """
    token = token.strip()
    if not token or _NOISE.search(token):
        return None
    if _SCREAMING_SNAKE.match(token):
        return "screaming_snake"

    last_segment = token.rsplit("/", 1)[-1]
    if Path(last_segment).suffix in _PATH_EXTENSIONS:
        return "path"
    if "/" in token or "." in token:
        return None  # path-shaped but unrecognized extension — not a file, not a symbol

    if _SNAKE.match(token):
        return "identifier"
    if _CAMEL.match(token) and any(c.islower() for c in token) and any(c.isupper() for c in token):
        return "identifier"
    return None


@dataclass(frozen=True)
class Candidate:
    text: str
    line: int
    kind: str


@dataclass(frozen=True)
class SettingsClaim:
    key: str
    claimed_value: str
    line: int


def _strip_call_parens(text: str) -> str:
    """`` `foo()` `` in prose means "the symbol foo" — a very common doc
    convention. Only the bare empty-call suffix is stripped; `foo(bar)` keeps
    its arguments and is correctly left to fail identifier-shape (it's a
    snippet, not a symbol reference).
    """
    return text[:-2] if text.endswith("()") else text


def extract_symbol_candidates(doc: MarkdownDocument) -> list[Candidate]:
    """Backtick spans (code_inline tokens) — never sees fenced code, since
    markdown-it-py only emits code_inline for backticks inside prose.
    """
    candidates = []
    for inline_token in iter_inline_tokens(doc.tokens):
        if not inline_token.children:
            continue
        line = (inline_token.map[0] + 1) if inline_token.map else 1
        for child in inline_token.children:
            if child.type != "code_inline":
                continue
            text = _strip_call_parens(child.content)
            kind = classify_candidate(text)
            if kind is None:
                continue
            candidates.append(Candidate(text=text, line=line, kind=kind))
    return candidates


def extract_link_candidates(doc: MarkdownDocument) -> list[Candidate]:
    """Markdown links (link_open href) — high precision, no classification
    gate needed: external/mailto links and bare in-page anchors are skipped,
    everything else is a real relative reference to resolve.
    """
    candidates = []
    for inline_token in iter_inline_tokens(doc.tokens):
        if not inline_token.children:
            continue
        line = (inline_token.map[0] + 1) if inline_token.map else 1
        for child in inline_token.children:
            if child.type != "link_open":
                continue
            href = child.attrs.get("href", "")
            if not href or href.startswith(("http://", "https://", "mailto:")):
                continue
            href = href.split("#", 1)[0]
            if not href:
                continue
            candidates.append(Candidate(text=href, line=line, kind="link"))
    return candidates


def extract_settings_claims(doc: MarkdownDocument) -> list[SettingsClaim]:
    """`` `KEY` (value) `` or "`KEY` ... default **value**" claims from raw
    inline content (retains backticks/markup, which the regexes need).
    """
    claims = []
    for inline_token in iter_inline_tokens(doc.tokens):
        line = (inline_token.map[0] + 1) if inline_token.map else 1
        for pattern in (_DEFAULT_PAREN, _DEFAULT_WORD):
            for m in pattern.finditer(inline_token.content):
                claims.append(SettingsClaim(key=m.group(1), claimed_value=m.group(2), line=line))
    return claims
