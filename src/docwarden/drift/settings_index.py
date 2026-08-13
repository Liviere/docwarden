import ast
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path

from docwarden import vcs


@dataclass(frozen=True)
class FieldInfo:
    field_name: str
    default: object
    is_literal: bool
    service: str


def extract_default_value(node: ast.expr | None) -> tuple[bool, object]:
    """(is_literal, value). Deliberately not a general expression evaluator:
    Field(default_factory=...) and other computed RHS get (False, None) —
    silently unverified, never wrongly flagged. Safe failure direction.
    """
    if node is None:
        return False, None
    if isinstance(node, ast.Constant):
        return True, node.value
    if (
        isinstance(node, ast.UnaryOp)
        and isinstance(node.op, ast.USub)
        and isinstance(node.operand, ast.Constant)
    ):
        return True, -node.operand.value
    return False, None


def _base_names(class_def: ast.ClassDef) -> set[str]:
    names = set()
    for base in class_def.bases:
        if isinstance(base, ast.Name):
            names.add(base.id)
        elif isinstance(base, ast.Attribute):
            names.add(base.attr)
    return names


def build_settings_index(
    repo_root: Path, glob_pattern: str, base_class_names: list[str]
) -> dict[str, list[FieldInfo]]:
    if not glob_pattern:
        return {}

    base_class_set = set(base_class_names)
    index: dict[str, list[FieldInfo]] = {}

    for path in vcs.tracked_files(repo_root, paths=None):
        rel = path.relative_to(repo_root).as_posix()
        if not fnmatch(rel, glob_pattern):
            continue
        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except (UnicodeDecodeError, OSError, SyntaxError):
            continue

        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            if not (_base_names(node) & base_class_set):
                continue
            for stmt in node.body:
                if not isinstance(stmt, ast.AnnAssign) or not isinstance(stmt.target, ast.Name):
                    continue
                field_name = stmt.target.id
                is_literal, value = extract_default_value(stmt.value)
                info = FieldInfo(
                    field_name=field_name, default=value, is_literal=is_literal, service=rel
                )
                index.setdefault(field_name.upper(), []).append(info)

    return index
