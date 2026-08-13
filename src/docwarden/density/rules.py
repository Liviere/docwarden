from pathlib import Path

from docwarden.config import DensityConfig
from docwarden.density.sentences import split_sentences
from docwarden.findings import Finding, fingerprint_content
from docwarden.markdown import MarkdownDocument, fence_line_set, iter_inline_tokens


def _front_matter(lines: list[str]) -> dict[str, str] | None:
    """Narrow line-based extraction of a `---\\nkey: value\\n---` header — not a
    YAML library, since the format used by SKILL.md is this constrained.
    """
    if not lines or lines[0].strip() != "---":
        return None
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return None
    fields: dict[str, str] = {}
    for line in lines[1:end]:
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip().strip('"').strip("'")
    return fields


def _bold_ratio(children) -> float:
    """Fraction of visible text characters that sit inside strong_open/close
    spans. Walks real tokens rather than a `\\*\\*...\\*\\*` regex so adjacent
    or delimiter-ambiguous bold spans (already resolved by the parser) are
    handled correctly.
    """
    total = 0
    bold = 0
    depth = 0
    for child in children:
        if child.type == "strong_open":
            depth += 1
            continue
        if child.type == "strong_close":
            depth -= 1
            continue
        text = child.content
        if not text:
            continue
        total += len(text)
        if depth > 0:
            bold += len(text)
    return bold / total if total else 0.0


def check_bold_ratio(rel_path: str, doc: MarkdownDocument, config: DensityConfig) -> list[Finding]:
    findings = []
    for token in iter_inline_tokens(doc.tokens):
        if not token.children:
            continue
        ratio = _bold_ratio(token.children)
        if ratio <= config.bold_ratio_threshold:
            continue
        line = (token.map[0] + 1) if token.map else 1
        end_line = token.map[1] if token.map else line
        findings.append(
            Finding(
                path=rel_path,
                line=line,
                end_line=end_line,
                rule="density/bold-ratio",
                message=f"{ratio:.0%} pogrubienia (próg {config.bold_ratio_threshold:.0%})",
                snippet=token.content[:200],
                fingerprint=fingerprint_content(token.content),
            )
        )
    return findings


def check_list_item_span(rel_path: str, doc: MarkdownDocument, config: DensityConfig) -> list[Finding]:
    findings = []
    for token in doc.tokens:
        if token.type != "list_item_open" or not token.map:
            continue
        start, end = token.map
        span = end - start
        if span <= config.list_item_span_threshold:
            continue
        snippet = "\n".join(doc.lines[start:end])
        findings.append(
            Finding(
                path=rel_path,
                line=start + 1,
                end_line=end,
                rule="density/list-item-span",
                message=f"{span} linii bez przerwy (próg {config.list_item_span_threshold})",
                snippet=snippet[:200],
                fingerprint=fingerprint_content(snippet),
            )
        )
    return findings


def check_line_words(rel_path: str, doc: MarkdownDocument, config: DensityConfig) -> list[Finding]:
    """Per raw physical line — deliberately not token-based, so it works
    without knowing anything about tables: a table row is always one
    physical line, so this alone catches oversized cells.
    """
    fenced = fence_line_set(doc.tokens)
    findings = []
    for i, line in enumerate(doc.lines):
        if i in fenced:
            continue
        words = line.split()
        if len(words) <= config.line_words_threshold:
            continue
        findings.append(
            Finding(
                path=rel_path,
                line=i + 1,
                end_line=i + 1,
                rule="density/line-words",
                message=f"{len(words)} słów w jednej linii (próg {config.line_words_threshold})",
                snippet=line[:200],
                fingerprint=fingerprint_content(line),
            )
        )
    return findings


def check_sentence_words(rel_path: str, doc: MarkdownDocument, config: DensityConfig) -> list[Finding]:
    findings = []
    for token in iter_inline_tokens(doc.tokens):
        line = (token.map[0] + 1) if token.map else 1
        end_line = token.map[1] if token.map else line
        for sentence in split_sentences(token.content):
            words = sentence.split()
            if len(words) <= config.sentence_words_threshold:
                continue
            findings.append(
                Finding(
                    path=rel_path,
                    line=line,
                    end_line=end_line,
                    rule="density/sentence-words",
                    message=f"{len(words)} słów w zdaniu (próg {config.sentence_words_threshold})",
                    snippet=sentence[:200],
                    fingerprint=fingerprint_content(sentence),
                )
            )
    return findings


def check_em_dash_density(rel_path: str, doc: MarkdownDocument, config: DensityConfig) -> list[Finding]:
    findings = []
    for token in iter_inline_tokens(doc.tokens):
        line = (token.map[0] + 1) if token.map else 1
        end_line = token.map[1] if token.map else line
        for sentence in split_sentences(token.content):
            count = sentence.count("—") + sentence.count("(")
            if count < config.em_dash_density_threshold:
                continue
            findings.append(
                Finding(
                    path=rel_path,
                    line=line,
                    end_line=end_line,
                    rule="density/em-dash-density",
                    message=(
                        f"{count} myślników/nawiasów w zdaniu "
                        f"(próg {config.em_dash_density_threshold})"
                    ),
                    snippet=sentence[:200],
                    fingerprint=fingerprint_content(sentence),
                )
            )
    return findings


def check_file_length(rel_path: str, doc: MarkdownDocument, config: DensityConfig) -> list[Finding]:
    basename = Path(rel_path).name
    threshold = config.file_length.thresholds.get(basename, config.file_length.default_threshold)
    count = len(doc.lines)
    if count <= threshold:
        return []
    return [
        Finding(
            path=rel_path,
            line=1,
            end_line=count,
            rule="density/file-length",
            message=f"{count} linii (próg {threshold})",
            snippet="",
            fingerprint="file",
        )
    ]


def check_front_matter_description(
    rel_path: str, doc: MarkdownDocument, config: DensityConfig
) -> list[Finding]:
    if not config.front_matter_description_enabled:
        return []
    if Path(rel_path).name != "SKILL.md":
        return []
    fm = _front_matter(doc.lines)
    if fm is None or "description" not in fm:
        return []
    desc = fm["description"]
    if len(desc) <= config.front_matter_description_threshold:
        return []
    return [
        Finding(
            path=rel_path,
            line=1,
            end_line=1,
            rule="density/front-matter-description",
            message=f"{len(desc)} znaków w opisie (próg {config.front_matter_description_threshold})",
            snippet=desc[:200],
            fingerprint="file",
        )
    ]
