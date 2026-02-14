"""Minimal formatter for backend Python files.

The formatter performs deterministic whitespace normalization to keep
early-stage source files consistent without external dependencies.
"""

from __future__ import annotations

from pathlib import Path


def iter_python_files() -> list[Path]:
    roots = [Path("src"), Path("tests"), Path("tools")]
    files: list[Path] = []
    for root in roots:
        if root.exists():
            files.extend(sorted(root.rglob("*.py")))
    return files


def normalize(content: str) -> str:
    normalized_lines = [line.rstrip() for line in content.splitlines()]
    return "\n".join(normalized_lines).rstrip() + "\n"


def main() -> int:
    changed = 0
    for py_file in iter_python_files():
        original = py_file.read_text(encoding="utf-8")
        updated = normalize(original)
        if updated != original:
            py_file.write_text(updated, encoding="utf-8")
            changed += 1
    print(f"[format] normalized_files={changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
