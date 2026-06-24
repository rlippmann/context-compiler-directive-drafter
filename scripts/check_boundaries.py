#!/usr/bin/env python3
"""Fail on obvious authority-layer boundary violations in package-owned code."""

import ast
from dataclasses import dataclass
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent.parent
SCAN_ROOTS = [
    ROOT / "src" / "context_compiler_directive_drafter",
    ROOT / "examples",
]
ALLOWED_SUFFIXES = {".py"}


@dataclass(frozen=True)
class Check:
    pattern: str
    rationale: str


CHECKS = [
    Check(
        pattern="create_engine(",
        rationale="Package source and package-owned examples should not construct compiler authority objects.",
    ),
    Check(
        pattern="engine.step(",
        rationale="The drafter proposes candidate directives; only hosts using context-compiler should drive authoritative engine steps.",
    ),
    Check(
        pattern="engine.state",
        rationale="The drafting layer must not read or edit authoritative engine state directly.",
    ),
    Check(
        pattern=".state =",
        rationale="Direct .state assignment is a simple signal for possible authoritative state mutation across the boundary.",
    ),
    Check(
        pattern="from host_support",
        rationale="Package source and package-owned examples should not import runnable host integration helpers.",
    ),
    Check(
        pattern="import host_support",
        rationale="Package source and package-owned examples should not import runnable host integration helpers.",
    ),
    Check(
        pattern="from context_compiler.host_support",
        rationale="Package source and package-owned examples should not import authority-layer or host orchestration helpers.",
    ),
    Check(
        pattern="import context_compiler.host_support",
        rationale="Package source and package-owned examples should not import authority-layer or host orchestration helpers.",
    ),
]
HOST_INTEGRATION_IMPORTS = {
    "fastapi": "Runnable web-host integrations belong outside package-owned drafting source and examples.",
    "flask": "Runnable web-host integrations belong outside package-owned drafting source and examples.",
    "litellm": "Provider/runtime integrations belong outside package-owned drafting source and examples.",
    "open_webui": "OpenWebUI-style host integrations belong outside package-owned drafting source and examples.",
    "openwebui": "OpenWebUI-style host integrations belong outside package-owned drafting source and examples.",
    "quart": "Runnable web-host integrations belong outside package-owned drafting source and examples.",
    "starlette": "Runnable web-host integrations belong outside package-owned drafting source and examples.",
    "uvicorn": "Runnable web-host integrations belong outside package-owned drafting source and examples.",
}


@dataclass(frozen=True)
class Violation:
    path: Path
    line: int
    snippet: str
    check: Check


def _iter_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix in ALLOWED_SUFFIXES
    )


def _format_violation(path: Path, content: str, index: int, check: Check) -> Violation:
    before = content[:index]
    line = before.count("\n") + 1
    line_start = before.rfind("\n") + 1
    line_end = content.find("\n", index)
    if line_end == -1:
        line_end = len(content)
    snippet = content[line_start:line_end].strip()
    return Violation(path=path, line=line, snippet=snippet, check=check)


def _scan_file(path: Path) -> list[Violation]:
    content = path.read_text(encoding="utf-8")
    violations: list[Violation] = []
    for check in CHECKS:
        index = content.find(check.pattern)
        if index == -1:
            continue
        violations.append(_format_violation(path, content, index, check))
    try:
        tree = ast.parse(content, filename=str(path))
    except SyntaxError:
        return violations
    violations.extend(_scan_imports(path, content, tree))
    return violations


def _scan_imports(path: Path, content: str, tree: ast.AST) -> list[Violation]:
    violations: list[Violation] = []
    for node in ast.walk(tree):
        imported_modules: list[str] = []
        if isinstance(node, ast.Import):
            imported_modules = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_modules = [node.module]
        else:
            continue

        for module_name in imported_modules:
            root_name = module_name.split(".", 1)[0]
            rationale = HOST_INTEGRATION_IMPORTS.get(root_name)
            if rationale is None:
                continue
            line = getattr(node, "lineno", 1)
            snippet = content.splitlines()[line - 1].strip()
            violations.append(
                Violation(
                    path=path,
                    line=line,
                    snippet=snippet,
                    check=Check(
                        pattern=f"import {module_name}",
                        rationale=rationale,
                    ),
                )
            )
    return violations


def main() -> int:
    violations = [
        violation
        for root in SCAN_ROOTS
        for path in _iter_files(root)
        for violation in _scan_file(path)
    ]

    if not violations:
        print("Boundary checks passed for src/context_compiler_directive_drafter/** and examples/**.")
        return 0

    print("Boundary check failed. Found authority-layer boundary violations:", file=sys.stderr)
    for violation in violations:
        relative = violation.path.relative_to(ROOT)
        print(
            f"- {relative}:{violation.line} matched {violation.check.pattern!r}",
            file=sys.stderr,
        )
        print(f"  Rationale: {violation.check.rationale}", file=sys.stderr)
        print(f"  Snippet: {violation.snippet}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
