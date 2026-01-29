#!/usr/bin/env python3
"""
Smart Test Runner - Test List Collector
Collects test list before execution for "resume from" capability.

Usage:
    python list_tests.py --framework jest [--path .]
    python list_tests.py --framework pytest [--path tests/]
    python list_tests.py --framework go [--path ./...]
"""

import subprocess
import json
import re
import sys
import argparse
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class TestItem:
    id: str  # Unique identifier for re-running
    name: str  # Display name
    file: str  # File path
    line: Optional[int] = None  # Line number if available
    suite: Optional[str] = None  # Test suite/describe block


@dataclass
class TestList:
    framework: str
    total: int
    tests: list
    run_single_command: str  # Template: replace {test_id}
    run_from_command: str  # Template: run from specific test onwards
    bail_command: str  # Command with --bail/-x option


def list_jest_tests(path: str = ".") -> TestList:
    """List Jest/Vitest tests using --listTests."""
    # Try vitest first, then jest
    for runner in ["vitest", "jest"]:
        try:
            cmd = f"npx {runner} --listTests --json"
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, cwd=path, timeout=60
            )
            if result.returncode == 0:
                # Parse JSON output
                try:
                    data = json.loads(result.stdout)
                    test_files = data if isinstance(data, list) else data.get("testResults", [])
                except json.JSONDecodeError:
                    # Fallback: parse line by line
                    test_files = [l.strip() for l in result.stdout.split("\n") if l.strip().endswith((".test.ts", ".test.js", ".spec.ts", ".spec.js"))]

                tests = []
                for i, f in enumerate(test_files):
                    file_path = f if isinstance(f, str) else f.get("name", f"test_{i}")
                    tests.append(TestItem(
                        id=file_path,
                        name=Path(file_path).stem,
                        file=file_path
                    ))

                return TestList(
                    framework=runner,
                    total=len(tests),
                    tests=[asdict(t) for t in tests],
                    run_single_command=f"npx {runner} {{test_id}}",
                    run_from_command=f"npx {runner} --testPathPattern='{{test_id}}'",
                    bail_command=f"npx {runner} --bail"
                )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            continue

    # Fallback: find test files manually
    tests = []
    for pattern in ["**/*.test.ts", "**/*.test.js", "**/*.spec.ts", "**/*.spec.js"]:
        for f in Path(path).glob(pattern):
            if "node_modules" not in str(f):
                tests.append(TestItem(
                    id=str(f),
                    name=f.stem,
                    file=str(f)
                ))

    return TestList(
        framework="jest",
        total=len(tests),
        tests=[asdict(t) for t in tests],
        run_single_command="npx jest {test_id}",
        run_from_command="npx jest --testPathPattern='{test_id}'",
        bail_command="npx jest --bail"
    )


def list_pytest_tests(path: str = ".") -> TestList:
    """List pytest tests using --collect-only."""
    try:
        cmd = f"pytest --collect-only -q {path}"
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=120
        )

        tests = []
        # Parse output: "tests/test_foo.py::test_bar"
        for line in result.stdout.split("\n"):
            line = line.strip()
            if "::" in line and not line.startswith("<"):
                parts = line.split("::")
                file_path = parts[0]
                test_name = parts[-1] if len(parts) > 1 else "unknown"

                tests.append(TestItem(
                    id=line,  # Full path like tests/test_foo.py::test_bar
                    name=test_name,
                    file=file_path,
                    suite="::".join(parts[1:-1]) if len(parts) > 2 else None
                ))

        return TestList(
            framework="pytest",
            total=len(tests),
            tests=[asdict(t) for t in tests],
            run_single_command="pytest {test_id}",
            run_from_command="pytest {test_id}",  # pytest doesn't have native "from" support
            bail_command="pytest -x"
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return TestList(
            framework="pytest",
            total=0,
            tests=[],
            run_single_command="pytest {test_id}",
            run_from_command="pytest {test_id}",
            bail_command="pytest -x"
        )


def list_go_tests(path: str = "./...") -> TestList:
    """List Go tests using go test -list."""
    try:
        cmd = f"go test -list '.*' {path}"
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=60
        )

        tests = []
        current_pkg = ""

        for line in result.stdout.split("\n"):
            line = line.strip()

            # Package line: "ok  github.com/user/pkg  0.001s"
            if line.startswith("ok") or line.startswith("?"):
                continue

            # Test name line
            if line.startswith("Test") or line.startswith("Benchmark"):
                tests.append(TestItem(
                    id=line,
                    name=line,
                    file=current_pkg or path
                ))

        return TestList(
            framework="go",
            total=len(tests),
            tests=[asdict(t) for t in tests],
            run_single_command="go test -run {test_id} " + path,
            run_from_command="go test -run '{test_id}.*' " + path,
            bail_command="go test -failfast " + path
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return TestList(
            framework="go",
            total=0,
            tests=[],
            run_single_command=f"go test -run {{test_id}} {path}",
            run_from_command=f"go test -run '{{test_id}}.*' {path}",
            bail_command=f"go test -failfast {path}"
        )


def list_playwright_tests(path: str = ".") -> TestList:
    """List Playwright tests using --list."""
    try:
        cmd = "npx playwright test --list"
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, cwd=path, timeout=60
        )

        tests = []
        # Parse: "  ✓  tests/example.spec.ts:3:5 › basic test"
        pattern = r"[✓◯]\s+(\S+):(\d+):\d+\s+›\s+(.+)"

        for line in result.stdout.split("\n"):
            match = re.search(pattern, line)
            if match:
                file_path = match.group(1)
                line_num = int(match.group(2))
                test_name = match.group(3).strip()

                tests.append(TestItem(
                    id=f"{file_path}:{line_num}",
                    name=test_name,
                    file=file_path,
                    line=line_num
                ))

        return TestList(
            framework="playwright",
            total=len(tests),
            tests=[asdict(t) for t in tests],
            run_single_command="npx playwright test {test_id}",
            run_from_command="npx playwright test {test_id}",
            bail_command="npx playwright test --max-failures=1"
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return TestList(
            framework="playwright",
            total=0,
            tests=[],
            run_single_command="npx playwright test {test_id}",
            run_from_command="npx playwright test {test_id}",
            bail_command="npx playwright test --max-failures=1"
        )


def generate_remaining_tests(test_list: TestList, failed_index: int) -> dict:
    """Generate command to run remaining tests after a failure."""
    remaining = test_list.tests[failed_index + 1:]

    if not remaining:
        return {
            "remaining_count": 0,
            "remaining_tests": [],
            "run_remaining_command": None
        }

    # Framework-specific remaining test commands
    framework = test_list.framework
    test_ids = [t["id"] for t in remaining]

    if framework in ["jest", "vitest"]:
        # Jest can run multiple files
        cmd = f"npx {framework} " + " ".join(test_ids)
    elif framework == "pytest":
        # Pytest can run multiple test IDs
        cmd = "pytest " + " ".join(test_ids)
    elif framework == "go":
        # Go needs regex pattern
        pattern = "|".join(test_ids)
        cmd = f"go test -run '{pattern}' ./..."
    elif framework == "playwright":
        # Playwright can run multiple files
        cmd = "npx playwright test " + " ".join(test_ids)
    else:
        cmd = None

    return {
        "remaining_count": len(remaining),
        "remaining_tests": remaining,
        "run_remaining_command": cmd
    }


def main():
    parser = argparse.ArgumentParser(description="List tests for resume capability")
    parser.add_argument("--framework", "-f", required=True,
                        choices=["jest", "vitest", "pytest", "go", "playwright"],
                        help="Test framework")
    parser.add_argument("--path", "-p", default=".",
                        help="Path to tests (default: current directory)")
    parser.add_argument("--pretty", action="store_true",
                        help="Pretty print JSON")
    parser.add_argument("--remaining-from", "-r", type=int,
                        help="Generate remaining tests command from index N")
    args = parser.parse_args()

    # List tests based on framework
    listers = {
        "jest": list_jest_tests,
        "vitest": list_jest_tests,
        "pytest": list_pytest_tests,
        "go": list_go_tests,
        "playwright": list_playwright_tests
    }

    lister = listers.get(args.framework)
    if not lister:
        print(json.dumps({"error": f"Unknown framework: {args.framework}"}))
        sys.exit(1)

    test_list = lister(args.path)
    result = asdict(test_list)

    # Add remaining tests info if requested
    if args.remaining_from is not None:
        result["remaining"] = generate_remaining_tests(test_list, args.remaining_from)

    indent = 2 if args.pretty else None
    print(json.dumps(result, indent=indent))


if __name__ == "__main__":
    main()
