"""Minimal linter checks for backend Python files.

Checks:
1. Python syntax via compilation.
2. No tab-indented lines.
3. No trailing whitespace.
"""

from __future__ import annotations

import py_compile
import sys
from pathlib import Path


def iter_python_files() -> list[Path]:
    roots = [Path("src"), Path("tests"), Path("tools")]
    files: list[Path] = []
    for root in roots:
        if root.exists():
            files.extend(sorted(root.rglob("*.py")))
    return files


def lint_file(path: Path) -> list[str]:
    issues: list[str] = []
    try:
        py_compile.compile(str(path), doraise=True)
    except py_compile.PyCompileError as exc:
        issues.append(f"{path}: syntax error: {exc.msg}")

    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if "\t" in line:
            issues.append(f"{path}:{index}: tab character is not allowed")
        if line.rstrip() != line:
            issues.append(f"{path}:{index}: trailing whitespace")
    return issues


def main() -> int:
    issues: list[str] = []
    for py_file in iter_python_files():
        issues.extend(lint_file(py_file))

    if issues:
        for issue in issues:
            print(issue)
        print(f"[lint] failed_checks={len(issues)}")
        return 1

    print("[lint] all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
