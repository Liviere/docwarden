import ast
import re
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from docwarden import vcs

_TS_BLOCK_COMMENT = re.compile(r"/\*[\s\S]*?\*/")
_TS_LINE_COMMENT = re.compile(r"//[^\n]*")
_TS_STRING = re.compile(r"'(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\"|`(?:\\.|[^`\\])*`")
_TS_DECL = re.compile(r"\b(?:function|class|interface|type|enum|const|let|var)\s+([A-Za-z_$][\w$]*)")
_TS_MEMBER = re.compile(r"^[ \t]*(?:readonly\s+)?([A-Za-z_$][\w$]*)\s*[?!]?\s*:", re.MULTILINE)
_TS_METHOD = re.compile(r"^[ \t]*(?:async\s+)?([A-Za-z_$][\w$]*)\s*\([^)]*\)\s*\{", re.MULTILINE)
_TS_IMPORT_BRACE = re.compile(r"\bimport\s*(?:type\s+)?\{([^}]*)\}")
_TS_IMPORT_DEFAULT = re.compile(r"\bimport\s+([A-Za-z_$][\w$]*)\s*(?:,|from\b)")
_TS_IDENT = re.compile(r"[A-Za-z_$][\w$]*")

_IDENT_SHAPE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def python_declared_names(source: str) -> set[str]:
    """Names DECLARED in a Python module — functions/classes/params/vars/
    Pydantic AnnAssign fields/constants/comprehension & with/except targets/
    import aliases. Ported from kancelaria-pjp's scripts/lint_identifiers.py
    (duplicated, not imported — this package is standalone). ast.parse
    inherently skips comments and docstrings.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return set()

    names: set[str] = set()

    def add_args(node: ast.arguments) -> None:
        for arg in [*node.posonlyargs, *node.args, *node.kwonlyargs]:
            names.add(arg.arg)
        for extra in (node.vararg, node.kwarg):
            if extra is not None:
                names.add(extra.arg)

    def add_target(node: ast.AST) -> None:
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, (ast.Tuple, ast.List)):
            for element in node.elts:
                add_target(element)

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            names.add(node.name)
            add_args(node.args)
        elif isinstance(node, ast.Lambda):
            add_args(node.args)
        elif isinstance(node, ast.ClassDef):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                add_target(target)
        elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
            add_target(node.target)
        elif isinstance(node, (ast.For, ast.AsyncFor)):
            add_target(node.target)
        elif isinstance(node, ast.comprehension):
            add_target(node.target)
        elif isinstance(node, ast.withitem):
            if node.optional_vars is not None:
                add_target(node.optional_vars)
        elif isinstance(node, ast.ExceptHandler):
            if node.name:
                names.add(node.name)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                if alias.asname:
                    names.add(alias.asname)
                # An imported name is a name this module USES and prose
                # legitimately cites (`AliasChoices`, `APIRoute`) — without it
                # every third-party symbol we don't define reads as dead. Both
                # ends of a dotted import count: `import os.path` binds `os`,
                # while `from x.y import Z` is cited as `Z`.
                names.add(alias.name.split(".")[0])
                names.add(alias.name.rsplit(".", 1)[-1])

    return names


def python_string_literal_constants(source: str) -> set[str]:
    """Identifier-shaped string CONSTANTS (not declared names) — e.g. a dict
    key or an API field name referenced only as a literal, like Twenty CRM's
    `folderKlienta`, which never appears as a declared Python identifier.
    lint_identifiers.py deliberately never looks at string literals; this is
    new, to avoid false "dead symbol" positives on that class of reference.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return set()

    pool: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            value = node.value
            if len(value) <= 60 and _IDENT_SHAPE.match(value):
                pool.add(value)
    return pool


def ts_declared_names(source: str) -> set[str]:
    """Heuristic for TS/JS — no parser, so deliberately incomplete (function
    parameters are skipped). Ported from lint_identifiers.py.
    """
    stripped = _TS_BLOCK_COMMENT.sub(" ", source)
    stripped = _TS_LINE_COMMENT.sub(" ", stripped)
    stripped = _TS_STRING.sub('""', stripped)

    names: set[str] = set()
    for pattern in (_TS_DECL, _TS_MEMBER, _TS_METHOD, _TS_IMPORT_DEFAULT):
        names.update(pattern.findall(stripped))
    for group in _TS_IMPORT_BRACE.findall(stripped):
        # `{ A, B as C }` — both ends kept, same reasoning as the Python side.
        names.update(_TS_IDENT.findall(group))
    names.discard("as")
    return names


@dataclass
class CodebaseIndex:
    names: set[str] = field(default_factory=set)
    string_pool: set[str] = field(default_factory=set)
    basenames: dict[str, list[str]] = field(default_factory=dict)
    all_paths: set[str] = field(default_factory=set)
    all_dirs: set[str] = field(default_factory=set)


def build_codebase_index(repo_root: Path, code_extensions: set[str]) -> CodebaseIndex:
    """Always whole-repo (paths=None is never threaded through) — a doc-scan
    scoped to one edited file must not make symbols elsewhere look dead.
    """
    index = CodebaseIndex()

    for path in vcs.tracked_files(repo_root, paths=None):
        rel = path.relative_to(repo_root).as_posix()
        index.all_paths.add(rel)
        index.basenames.setdefault(path.name, []).append(rel)
        # Directories are never tracked by git themselves, but docs link to
        # them constantly ("workflowy leżą w n8n/workflows/inbox/"), so derive
        # them from the file paths.
        index.all_dirs.update(
            parent.as_posix() for parent in PurePosixPath(rel).parents if parent.name
        )

    for path in vcs.tracked_files(repo_root, paths=None, suffixes=code_extensions):
        try:
            source = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if path.suffix == ".py":
            index.names |= python_declared_names(source)
            index.string_pool |= python_string_literal_constants(source)
        else:
            index.names |= ts_declared_names(source)

    return index
