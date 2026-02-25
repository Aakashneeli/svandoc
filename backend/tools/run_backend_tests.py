"""Run backend unittest modules with per-module timeout guards.

This avoids indefinite hangs in environments where a subset of tests can
block inside framework internals (for example, TestClient/anyio paths).
"""

from __future__ import annotations

import argparse
import fnmatch
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ModuleResult:
    module: str
    status: str
    duration_seconds: float
    return_code: int | None = None
    output: str = ""


def _backend_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _discover_modules(tests_dir: Path, pattern: str) -> list[str]:
    modules: list[str] = []
    for path in sorted(tests_dir.rglob(pattern)):
        if not path.is_file():
            continue
        relative = path.relative_to(tests_dir)
        module_name = "tests." + ".".join(relative.with_suffix("").parts)
        modules.append(module_name)
    return modules


def _build_env(existing: dict[str, str], backend_root: Path) -> dict[str, str]:
    env = dict(existing)
    src_path = str((backend_root / "src").resolve())
    current_pythonpath = env.get("PYTHONPATH", "").strip()
    if current_pythonpath:
        env["PYTHONPATH"] = f"{src_path}{os.pathsep}{current_pythonpath}"
    else:
        env["PYTHONPATH"] = src_path
    return env


def _run_module(
    *,
    python_cmd: str,
    module_name: str,
    backend_root: Path,
    env: dict[str, str],
    timeout_seconds: int,
) -> ModuleResult:
    started = time.perf_counter()
    try:
        completed = subprocess.run(
            [python_cmd, "-m", "unittest", module_name, "-v"],
            cwd=str(backend_root),
            env=env,
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
        duration = time.perf_counter() - started
        combined = (completed.stdout or "") + (completed.stderr or "")
        status = "passed" if completed.returncode == 0 else "failed"
        return ModuleResult(
            module=module_name,
            status=status,
            duration_seconds=duration,
            return_code=completed.returncode,
            output=combined,
        )
    except subprocess.TimeoutExpired as exc:
        duration = time.perf_counter() - started
        partial_stdout = exc.stdout or ""
        partial_stderr = exc.stderr or ""
        message = (
            f"[test-runner] module timed out after {timeout_seconds}s: {module_name}\n"
            f"{partial_stdout}{partial_stderr}"
        )
        return ModuleResult(
            module=module_name,
            status="timed_out",
            duration_seconds=duration,
            return_code=None,
            output=message,
        )


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run backend tests with module timeout guards.")
    parser.add_argument(
        "--tests-dir",
        default="tests",
        help="Directory containing unittest modules (default: tests).",
    )
    parser.add_argument(
        "--pattern",
        default="test_*.py",
        help="Filename pattern for unittest modules (default: test_*.py).",
    )
    parser.add_argument(
        "--module-timeout-seconds",
        type=int,
        default=180,
        help="Per-module timeout in seconds (default: 180).",
    )
    parser.add_argument(
        "--python-cmd",
        default=sys.executable,
        help="Python executable path used for module subprocesses.",
    )
    parser.add_argument(
        "--module-filter",
        default="",
        help="Optional fnmatch filter for discovered module names (for targeted runs).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv or sys.argv[1:])
    backend_root = _backend_root()
    tests_dir = (backend_root / args.tests_dir).resolve()
    if not tests_dir.exists():
        print(f"[test-runner] tests directory not found: {tests_dir}")
        return 1
    if args.module_timeout_seconds <= 0:
        print("[test-runner] module timeout must be greater than zero.")
        return 1

    modules = _discover_modules(tests_dir, args.pattern)
    if args.module_filter:
        modules = [name for name in modules if fnmatch.fnmatch(name, args.module_filter)]

    if not modules:
        print("[test-runner] no test modules discovered.")
        return 1

    env = _build_env(os.environ, backend_root)
    print(
        f"[test-runner] discovered_modules={len(modules)} "
        f"timeout_seconds={args.module_timeout_seconds}"
    )

    failed_modules: list[str] = []
    timed_out_modules: list[str] = []

    for module_name in modules:
        print(f"[test-runner] running {module_name}")
        result = _run_module(
            python_cmd=args.python_cmd,
            module_name=module_name,
            backend_root=backend_root,
            env=env,
            timeout_seconds=args.module_timeout_seconds,
        )
        print(
            f"[test-runner] module={result.module} status={result.status} "
            f"duration_seconds={result.duration_seconds:.2f}"
        )
        if result.output:
            print(result.output.rstrip())

        if result.status == "failed":
            failed_modules.append(module_name)
        elif result.status == "timed_out":
            timed_out_modules.append(module_name)

    print(
        f"[test-runner] summary passed={len(modules) - len(failed_modules) - len(timed_out_modules)} "
        f"failed={len(failed_modules)} timed_out={len(timed_out_modules)}"
    )
    if failed_modules:
        print("[test-runner] failed_modules=" + ",".join(failed_modules))
    if timed_out_modules:
        print("[test-runner] timed_out_modules=" + ",".join(timed_out_modules))

    return 0 if not failed_modules and not timed_out_modules else 1


if __name__ == "__main__":
    raise SystemExit(main())
