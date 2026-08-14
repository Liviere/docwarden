from collections.abc import Iterator
from dataclasses import dataclass

from markdown_it import MarkdownIt
from markdown_it.token import Token

# Explicit about which extensions we want rather than relying on preset
# defaults: the "commonmark" preset is strict CommonMark and does NOT parse
# GFM tables unless "table" is enabled — core markdown-it-py has the rule,
# it's just off by default under this preset.
_MD = MarkdownIt("commonmark", {"html": False}).enable("table")


@dataclass
class MarkdownDocument:
    text: str
    lines: list[str]
    tokens: list[Token]


def parse(text: str) -> MarkdownDocument:
    return MarkdownDocument(text=text, lines=text.splitlines(), tokens=_MD.parse(text))


def fence_line_set(tokens: list[Token]) -> set[int]:
    """0-indexed line numbers covered by fenced code blocks (opening + content + closing).

    For gating line-based checks (e.g. density/line-words) that read raw
    physical lines rather than tokens, so a code example inside a fence isn't
    mistaken for prose.
    """
    lines: set[int] = set()
    for token in tokens:
        if token.type == "fence" and token.map:
            start, end = token.map
            lines.update(range(start, end))
    return lines


def iter_inline_tokens(tokens: list[Token]) -> Iterator[Token]:
    """Yield every 'inline' token in the tree: paragraphs, list-item paragraphs,
    and table cells all bottom out in exactly one inline token each, carrying
    .map (line range), .content (raw markdown source for that span), and
    .children (strong_open/text/code_inline/link_open/... once inline-parsed).

    This is the single content-bearing unit density/drift rules operate on —
    deliberately flat (walks the whole token list, not just top-level), since
    markdown-it-py's parse() returns a flat stream with nesting encoded via
    the `level`/open-close tokens, not a real tree.
    """
    for token in tokens:
        if token.type == "inline":
            yield token


def iter_inline_tokens_with_row_head(tokens: list[Token]) -> Iterator[tuple[Token, str | None]]:
    """Same walk as iter_inline_tokens, but each token is paired with the raw
    content of the FIRST cell of its table row (None outside a table).

    Reference tables document one subject per row and name it in the leading
    cell, so that cell is the only reliable answer to "what is this row about"
    — a rule reading the description alone attributes it to whatever name the
    prose happened to cite last. markdown-it-py emits a flat stream, so row and
    cell boundaries have to be tracked from the open/close tokens.
    """
    row_head: str | None = None
    cell_index = -1
    for token in tokens:
        if token.type == "tr_open":
            row_head, cell_index = None, -1
        elif token.type in ("td_open", "th_open"):
            cell_index += 1
        elif token.type == "tr_close":
            row_head, cell_index = None, -1
        elif token.type == "inline":
            if cell_index == 0:
                row_head = token.content
            yield token, row_head
