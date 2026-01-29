#!/usr/bin/env python3
"""
Smart Test Runner - Test Output Parser
Parses test output from various frameworks into unified JSON format.

Usage:
    cat test_output.txt | python parse_test_output.py
    python parse_test_output.py < test_output.txt
    python parse_test_output.py --framework jest < test_output.txt
"""

import sys
import re
import json
import argparse
from dataclasses import dataclass, asdict
from typing import Optional
from enum import Enum


class Framework(Enum):
    JEST = "jest"
    VITEST = "vitest"
    PYTEST = "pytest"
    GO = "go"
    PLAYWRIGHT = "playwright"
    CYPRESS = "cypress"
    UNKNOWN = "unknown"


class FailureType(Enum):
    ASSERTION = "assertion"
    TYPE_ERROR = "type_error"
    TIMEOUT = "timeout"
    MOCK_ISSUE = "mock_issue"
    ENVIRONMENT = "environment"
    SYNTAX = "syntax"
    UNKNOWN = "unknown"


@dataclass
class FailedTest:
    file: str
    test_name: str
    error_message: str
    line_number: Optional[int] = None
    failure_type: str = "unknown"
    stack_trace: Optional[str] = None
    rerun_command: Optional[str] = None


@dataclass
class TestResult:
    framework: str
    total: int
    passed: int
    failed: int
    skipped: int
    duration_ms: Optional[int]
    failures: list


def detect_framework(output: str) -> Framework:
    """Auto-detect test framework from output."""
    patterns = {
        Framework.JEST: [r"PASS|FAIL.*\.test\.", r"Jest", r"expect\("],
        Framework.VITEST: [r"vitest", r"✓|×.*\d+ms", r"RERUN"],
        Framework.PYTEST: [r"pytest", r"PASSED|FAILED|ERROR", r"===.*==="],
        Framework.GO: [r"--- FAIL:|--- PASS:", r"go test", r"FAIL\s+\S+\s+\d+\.\d+s"],
        Framework.PLAYWRIGHT: [r"playwright", r"\d+ passed.*\d+ failed", r"browserType"],
        Framework.CYPRESS: [r"cypress", r"Running:.*\.cy\.", r"✓|✕"],
    }

    for framework, pats in patterns.items():
        matches = sum(1 for p in pats if re.search(p, output, re.IGNORECASE))
        if matches >= 2:
            return framework

    return Framework.UNKNOWN


def classify_failure(error_message: str) -> FailureType:
    """Classify failure type from error message."""
    error_lower = error_message.lower()

    if any(kw in error_lower for kw in ["expected", "to equal", "to be", "assertion", "assert"]):
        return FailureType.ASSERTION
    elif any(kw in error_lower for kw in ["typeerror", "undefined is not", "null is not", "cannot read"]):
        return FailureType.TYPE_ERROR
    elif any(kw in error_lower for kw in ["timeout", "exceeded", "timed out"]):
        return FailureType.TIMEOUT
    elif any(kw in error_lower for kw in ["mock", "spy", "stub", "not called"]):
        return FailureType.MOCK_ISSUE
    elif any(kw in error_lower for kw in ["enoent", "connection refused", "econnrefused", "env"]):
        return FailureType.ENVIRONMENT
    elif any(kw in error_lower for kw in ["syntaxerror", "unexpected token"]):
        return FailureType.SYNTAX

    return FailureType.UNKNOWN


def parse_jest(output: str) -> TestResult:
    """Parse Jest/Vitest output."""
    failures = []

    # Find failed test blocks
    fail_pattern = r"FAIL\s+(\S+)\n(.*?)(?=\n(?:PASS|FAIL|Test Suites:)|\Z)"
    for match in re.finditer(fail_pattern, output, re.DOTALL):
        file_path = match.group(1)
        block = match.group(2)

        # Extract individual test failures
        test_pattern = r"[×✕]\s+(.+?)\s+\((\d+)\s*ms\)\n(.*?)(?=\n\s*[×✕●]|\Z)"
        for test_match in re.finditer(test_pattern, block, re.DOTALL):
            test_name = test_match.group(1).strip()
            error_block = test_match.group(3).strip()

            # Extract error message
            error_lines = error_block.split("\n")
            error_message = error_lines[0] if error_lines else "Unknown error"

            # Extract line number
            line_match = re.search(r":(\d+):\d+", error_block)
            line_number = int(line_match.group(1)) if line_match else None

            failure = FailedTest(
                file=file_path,
                test_name=test_name,
                error_message=error_message,
                line_number=line_number,
                failure_type=classify_failure(error_message).value,
                rerun_command=f'npx jest --testNamePattern="{test_name}"'
            )
            failures.append(failure)

    # Parse summary
    summary_match = re.search(
        r"Tests:\s+(\d+)\s+failed.*?(\d+)\s+passed.*?(\d+)\s+total",
        output, re.IGNORECASE
    )
    if summary_match:
        failed = int(summary_match.group(1))
        passed = int(summary_match.group(2))
        total = int(summary_match.group(3))
    else:
        # Alternative pattern
        total_match = re.search(r"(\d+)\s+(?:tests?|specs?)", output, re.IGNORECASE)
        total = int(total_match.group(1)) if total_match else len(failures)
        failed = len(failures)
        passed = total - failed

    # Duration
    duration_match = re.search(r"Time:\s+([\d.]+)\s*s", output)
    duration_ms = int(float(duration_match.group(1)) * 1000) if duration_match else None

    return TestResult(
        framework="jest",
        total=total,
        passed=passed,
        failed=failed,
        skipped=0,
        duration_ms=duration_ms,
        failures=[asdict(f) for f in failures]
    )


def parse_pytest(output: str) -> TestResult:
    """Parse Pytest output."""
    failures = []

    # Find FAILED tests
    fail_pattern = r"FAILED\s+(\S+)::(\S+)"
    for match in re.finditer(fail_pattern, output):
        file_path = match.group(1)
        test_name = match.group(2)

        # Try to find error message
        error_pattern = rf"{re.escape(test_name)}.*?\n(.*?)(?=\n(?:FAILED|PASSED|=====)|\Z)"
        error_match = re.search(error_pattern, output, re.DOTALL)
        error_message = error_match.group(1).strip()[:200] if error_match else "Unknown error"

        failure = FailedTest(
            file=file_path,
            test_name=test_name,
            error_message=error_message,
            failure_type=classify_failure(error_message).value,
            rerun_command=f"pytest {file_path}::{test_name}"
        )
        failures.append(failure)

    # Parse summary line: "1 failed, 5 passed, 2 skipped"
    summary_match = re.search(
        r"(\d+)\s+failed.*?(\d+)\s+passed",
        output, re.IGNORECASE
    )
    if summary_match:
        failed = int(summary_match.group(1))
        passed = int(summary_match.group(2))
    else:
        failed = len(failures)
        passed_match = re.search(r"(\d+)\s+passed", output)
        passed = int(passed_match.group(1)) if passed_match else 0

    skipped_match = re.search(r"(\d+)\s+skipped", output)
    skipped = int(skipped_match.group(1)) if skipped_match else 0

    total = passed + failed + skipped

    # Duration
    duration_match = re.search(r"in\s+([\d.]+)s", output)
    duration_ms = int(float(duration_match.group(1)) * 1000) if duration_match else None

    return TestResult(
        framework="pytest",
        total=total,
        passed=passed,
        failed=failed,
        skipped=skipped,
        duration_ms=duration_ms,
        failures=[asdict(f) for f in failures]
    )


def parse_go(output: str) -> TestResult:
    """Parse Go test output."""
    failures = []

    # Find failed tests
    fail_pattern = r"--- FAIL:\s+(\S+)\s+\(([\d.]+)s\)\n(.*?)(?=\n--- |\nFAIL\s|\nok\s|\Z)"
    for match in re.finditer(fail_pattern, output, re.DOTALL):
        test_name = match.group(1)
        error_block = match.group(3).strip()

        # Extract file and line
        loc_match = re.search(r"(\S+\.go):(\d+)", error_block)
        file_path = loc_match.group(1) if loc_match else "unknown"
        line_number = int(loc_match.group(2)) if loc_match else None

        # Extract error message
        error_lines = [l.strip() for l in error_block.split("\n") if l.strip()]
        error_message = error_lines[0] if error_lines else "Unknown error"

        failure = FailedTest(
            file=file_path,
            test_name=test_name,
            error_message=error_message,
            line_number=line_number,
            failure_type=classify_failure(error_message).value,
            rerun_command=f"go test -run {test_name} ./..."
        )
        failures.append(failure)

    # Parse summary
    pass_count = len(re.findall(r"--- PASS:", output))
    fail_count = len(failures)
    total = pass_count + fail_count

    # Duration
    duration_match = re.search(r"([\d.]+)s\s*$", output, re.MULTILINE)
    duration_ms = int(float(duration_match.group(1)) * 1000) if duration_match else None

    return TestResult(
        framework="go",
        total=total,
        passed=pass_count,
        failed=fail_count,
        skipped=0,
        duration_ms=duration_ms,
        failures=[asdict(f) for f in failures]
    )


def parse_playwright(output: str) -> TestResult:
    """Parse Playwright output."""
    failures = []

    # Find failed tests
    fail_pattern = r"(\d+)\)\s+\[.*?\]\s+›\s+(\S+):(\d+):\d+\s+›\s+(.+?)\n(.*?)(?=\n\d+\)|\n\s+\d+ passed|\Z)"
    for match in re.finditer(fail_pattern, output, re.DOTALL):
        file_path = match.group(2)
        line_number = int(match.group(3))
        test_name = match.group(4).strip()
        error_block = match.group(5).strip()

        # Extract error message
        error_lines = error_block.split("\n")
        error_message = next((l.strip() for l in error_lines if l.strip()), "Unknown error")

        failure = FailedTest(
            file=file_path,
            test_name=test_name,
            error_message=error_message[:200],
            line_number=line_number,
            failure_type=classify_failure(error_message).value,
            rerun_command=f"npx playwright test {file_path}:{line_number}"
        )
        failures.append(failure)

    # Parse summary
    summary_match = re.search(r"(\d+)\s+passed.*?(\d+)\s+failed", output)
    if summary_match:
        passed = int(summary_match.group(1))
        failed = int(summary_match.group(2))
    else:
        failed = len(failures)
        passed_match = re.search(r"(\d+)\s+passed", output)
        passed = int(passed_match.group(1)) if passed_match else 0

    total = passed + failed

    return TestResult(
        framework="playwright",
        total=total,
        passed=passed,
        failed=failed,
        skipped=0,
        duration_ms=None,
        failures=[asdict(f) for f in failures]
    )


def parse_output(output: str, framework: Optional[str] = None) -> TestResult:
    """Parse test output and return structured result."""
    if framework:
        fw = Framework(framework)
    else:
        fw = detect_framework(output)

    parsers = {
        Framework.JEST: parse_jest,
        Framework.VITEST: parse_jest,  # Similar format
        Framework.PYTEST: parse_pytest,
        Framework.GO: parse_go,
        Framework.PLAYWRIGHT: parse_playwright,
        Framework.CYPRESS: parse_jest,  # Similar enough
    }

    parser = parsers.get(fw, parse_jest)  # Default to Jest parser
    result = parser(output)

    if fw != Framework.UNKNOWN:
        result.framework = fw.value

    return result


def main():
    parser = argparse.ArgumentParser(description="Parse test output to JSON")
    parser.add_argument("--framework", "-f", choices=["jest", "vitest", "pytest", "go", "playwright"],
                        help="Force specific framework (auto-detected if not specified)")
    parser.add_argument("--pretty", "-p", action="store_true", help="Pretty print JSON output")
    args = parser.parse_args()

    # Read from stdin
    output = sys.stdin.read()

    if not output.strip():
        print(json.dumps({"error": "No input provided"}))
        sys.exit(1)

    result = parse_output(output, args.framework)

    indent = 2 if args.pretty else None
    print(json.dumps(asdict(result), indent=indent))


if __name__ == "__main__":
    main()
