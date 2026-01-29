---
name: smart-test-runner
description: |
  Intelligent test execution with failure-first retry strategy.
  Runs domain tests (unit, integration, api, api-e2e, browser-e2e, security, performance, oapi),
  analyzes failures, fixes issues, re-runs failed tests only, then runs full domain suite on success.
  Use when: "run tests", "테스트 돌려줘", "fix test failures", "테스트 에러 수정", "run tests and fix".
---

# Smart Test Runner

Efficient test execution with **hybrid workflow**: fast fixing + regression verification.

## Trigger Keywords

| 한글 | English |
|------|---------|
| 테스트 돌려줘 | run tests |
| 테스트 실행하고 에러 수정해줘 | run tests and fix |
| 테스트 실패 원인 분석해줘 | fix test failures |
| unit 테스트만 실행해줘 | run unit tests |
| 테스트 디버깅해줘 | debug test errors |

## Installation

```bash
# Symlink to Claude Code skills directory
ln -s /path/to/smart-test-runner ~/.claude/skills/smart-test-runner

# Verify installation
ls ~/.claude/skills/smart-test-runner/scripts/
# Should show: detect_test_config.sh, list_tests.py, parse_test_output.py
```

## Skill Structure

```
smart-test-runner/
├── SKILL.md                           # This guide
└── scripts/
    ├── detect_test_config.sh          # Detect test domains & commands
    ├── list_tests.py                  # List tests for resume capability
    └── parse_test_output.py           # Parse test output to JSON
```

---

## Hybrid Workflow Overview

```
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 1: Fast Fix (bail mode)                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Create TodoWrite for tracking                               │
│  2. Detect test domains (script)                                │
│  3. Collect test list (script)                                  │
│  4. Run with --bail (stop on first failure)                     │
│     ↓                                                           │
│  5. Failure? ──No──→ Phase 1 done for domain                    │
│     │                                                           │
│     Yes (stop immediately)                                      │
│     ↓                                                           │
│  6. Parse failure (script) → Analyze → Fix                      │
│     ↓                                                           │
│  7. Re-run ONLY failed test                                     │
│     ↓                                                           │
│  8. Pass? ──No──→ Back to step 6                                │
│     │                                                           │
│     Yes                                                         │
│     ↓                                                           │
│  9. Run REMAINING tests (continue, not restart)                 │
│     ↓                                                           │
│ 10. More failures? ──Yes──→ Back to step 6                      │
│     │                                                           │
│     No → Phase 1 complete                                       │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│ PHASE 2: Regression Check                                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ 11. Run FULL test suite (no bail)                               │
│     ↓                                                           │
│ 12. New failures? ──Yes──→ Back to Phase 1 step 6               │
│     │              (regression bug detected)                    │
│     No                                                          │
│     ↓                                                           │
│ 13. Domain complete → Next domain or Done                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Script Reference

### 1. detect_test_config.sh

Detects test frameworks, domains, and generates both normal and bail commands.

**Usage:**
```bash
bash ~/.claude/skills/smart-test-runner/scripts/detect_test_config.sh [project_dir]
```

**Arguments:**
| Argument | Default | Description |
|----------|---------|-------------|
| project_dir | `.` | Path to project root |

**Output:**
```json
{
  "project_dir": "/path/to/project",
  "frameworks": {
    "javascript": "jest",
    "python": "",
    "go": ""
  },
  "domains": [
    {
      "name": "unit",
      "command": "npx jest",
      "bail_command": "npx jest --bail",
      "priority": 1
    },
    {
      "name": "integration",
      "command": "npx jest --testPathPattern=integration",
      "bail_command": "npx jest --testPathPattern=integration --bail",
      "priority": 2
    }
  ],
  "total_domains": 2
}
```

**Key Fields:**
- `command`: Use for Phase 2 (full run)
- `bail_command`: Use for Phase 1 (stop on first failure)
- `priority`: Lower = run first (unit before e2e)

---

### 2. list_tests.py

Collects test list before execution. Enables "resume from" capability.

**Usage:**
```bash
python ~/.claude/skills/smart-test-runner/scripts/list_tests.py [options]
```

**Options:**
| Option | Short | Required | Description |
|--------|-------|----------|-------------|
| --framework | -f | Yes | jest, vitest, pytest, go, playwright |
| --path | -p | No | Path to tests (default: .) |
| --pretty | | No | Pretty print JSON |
| --remaining-from | -r | No | Get remaining tests from index N |

**Examples:**

```bash
# List all tests
python ~/.claude/skills/smart-test-runner/scripts/list_tests.py -f jest --pretty

# Get remaining tests after index 15
python ~/.claude/skills/smart-test-runner/scripts/list_tests.py -f jest -r 15
```

**Output (basic):**
```json
{
  "framework": "jest",
  "total": 50,
  "tests": [
    {"id": "src/utils/parser.test.ts", "name": "parser", "file": "src/utils/parser.test.ts"},
    {"id": "src/api/client.test.ts", "name": "client", "file": "src/api/client.test.ts"}
  ],
  "run_single_command": "npx jest {test_id}",
  "run_from_command": "npx jest --testPathPattern='{test_id}'",
  "bail_command": "npx jest --bail"
}
```

**Output (with --remaining-from 15):**
```json
{
  "framework": "jest",
  "total": 50,
  "tests": [...],
  "remaining": {
    "remaining_count": 35,
    "remaining_tests": [...],
    "run_remaining_command": "npx jest src/api/client.test.ts src/db/query.test.ts ..."
  }
}
```

---

### 3. parse_test_output.py

Parses test output from various frameworks into unified JSON format.

**Usage:**
```bash
<test_command> 2>&1 | python ~/.claude/skills/smart-test-runner/scripts/parse_test_output.py [options]
```

**Options:**
| Option | Short | Description |
|--------|-------|-------------|
| --framework | -f | Force framework (auto-detected if omitted) |
| --pretty | -p | Pretty print JSON |

**Supported Frameworks:**
- Jest / Vitest
- Pytest
- Go test
- Playwright
- Cypress

**Examples:**

```bash
# Auto-detect framework
npx jest --bail 2>&1 | python ~/.claude/skills/smart-test-runner/scripts/parse_test_output.py -p

# Force pytest
pytest -x 2>&1 | python ~/.claude/skills/smart-test-runner/scripts/parse_test_output.py -f pytest -p
```

**Output:**
```json
{
  "framework": "jest",
  "total": 45,
  "passed": 43,
  "failed": 2,
  "skipped": 0,
  "duration_ms": 5230,
  "failures": [
    {
      "file": "src/utils/parser.test.ts",
      "test_name": "should parse JSON correctly",
      "error_message": "Expected { a: 1 }, got { a: \"1\" }",
      "line_number": 15,
      "failure_type": "assertion",
      "rerun_command": "npx jest --testNamePattern=\"should parse JSON correctly\""
    }
  ]
}
```

**Failure Types:**
| Type | Indicators | Fix Strategy |
|------|------------|--------------|
| assertion | expected, to equal, assert | Fix logic or update expectation |
| type_error | TypeError, undefined, null | Add null checks, fix types |
| timeout | timeout, exceeded, timed out | Fix async handling, increase timeout |
| mock_issue | mock, spy, stub, not called | Fix mock setup |
| environment | ENOENT, connection refused | Fix env setup |
| syntax | SyntaxError, unexpected token | Fix syntax |

---

## Step-by-Step Execution Guide

### Step 1: Initialize Progress Tracking

```
Use TodoWrite to create:
- [ ] Detect test domains
- [ ] [P1] unit - fast fix
- [ ] [P2] unit - regression check
- [ ] [P1] integration - fast fix
- [ ] [P2] integration - regression check
```

### Step 2: Detect Test Domains

```bash
bash ~/.claude/skills/smart-test-runner/scripts/detect_test_config.sh .
```

Store the output. Use `bail_command` for Phase 1, `command` for Phase 2.

### Step 3: Collect Test List

```bash
python ~/.claude/skills/smart-test-runner/scripts/list_tests.py -f jest --pretty
```

Note the test count and indices for resume capability.

### Step 4: Phase 1 - Run with Bail

```bash
# Use bail_command from step 2
npx jest --bail
```

If all pass → Skip to Step 9.
If failure → Continue to Step 5.

### Step 5: Parse Failure

```bash
npx jest --bail 2>&1 | python ~/.claude/skills/smart-test-runner/scripts/parse_test_output.py -p
```

### Step 6: Analyze and Fix

1. Read the failed test file
2. Read the source file being tested
3. Identify failure type from parser output
4. Apply minimal targeted fix

### Step 7: Re-run Failed Test Only

Use `rerun_command` from parser output:

```bash
npx jest --testNamePattern="should parse JSON correctly"
# or
npx jest src/utils/parser.test.ts
```

If fail → Back to Step 6.
If pass → Continue.

### Step 8: Run Remaining Tests

```bash
# Get remaining tests command
python ~/.claude/skills/smart-test-runner/scripts/list_tests.py -f jest -r 15

# Run the remaining command from output
npx jest src/api/client.test.ts src/db/query.test.ts ...
```

If more failures → Back to Step 5.
If all pass → Continue.

### Step 9: Phase 2 - Full Regression Check

```bash
# Use command (not bail_command)
npx jest
```

If new failures → These are regression bugs. Back to Step 5.
If all pass → Domain complete!

### Step 10: Next Domain

Update todos and repeat from Step 4 for next domain.

---

## Bail Options Reference

| Framework | Normal | Bail |
|-----------|--------|------|
| Jest | `npx jest` | `npx jest --bail` |
| Vitest | `npx vitest run` | `npx vitest run --bail` |
| Pytest | `pytest` | `pytest -x` |
| Go | `go test ./...` | `go test -failfast ./...` |
| Playwright | `npx playwright test` | `npx playwright test --max-failures=1` |
| Mocha | `npx mocha` | `npx mocha --bail` |

---

## Test Domain Priority

Execute in this order (fast → slow):

| Priority | Domain | Typical Duration |
|----------|--------|------------------|
| 1 | unit | Seconds |
| 2 | integration | Seconds-Minutes |
| 3 | api | Minutes |
| 4 | oapi | Minutes |
| 5 | security | Minutes |
| 6 | api-e2e | Minutes |
| 7 | browser-e2e | Minutes-Hours |
| 8 | performance | Minutes-Hours |

---

## Output Report Format

```markdown
## Test Execution Report

### Domain: unit

#### Phase 1: Fast Fix
| # | Test | Error | Cause | Fix | Status |
|---|------|-------|-------|-----|--------|
| 30 | parser.test.ts | Expected {a:1} got {a:"1"} | Type coercion | Added parseInt | FIXED |
| 70 | client.test.ts | Timeout 5000ms | Missing mock | Added fetch mock | FIXED |

Remaining after #70: 30 tests → All passed

#### Phase 2: Regression Check
Full suite: 100/100 PASSED

### Domain: integration
Status: PENDING

### Progress
- [x] [P1] unit (fixed 2)
- [x] [P2] unit (100/100)
- [ ] [P1] integration
- [ ] [P2] integration
```

---

## Efficiency Comparison

| Scenario | Traditional | Hybrid | Savings |
|----------|-------------|--------|---------|
| 100 tests, 2 failures | 15 min | 12 min | 20% |
| 100 tests, 5 failures | 30 min | 18 min | 40% |
| 100 tests, 10 failures | 55 min | 25 min | 55% |

More failures = more savings with hybrid approach.

---

## Troubleshooting

### Script not found
```bash
# Verify symlink
ls -la ~/.claude/skills/smart-test-runner/

# Fix symlink
ln -sf /actual/path/to/smart-test-runner ~/.claude/skills/smart-test-runner
```

### No domains detected
- Check if test files exist
- Verify package.json has test scripts
- Check directory structure matches patterns

### Parser returns empty failures
- Ensure stderr is captured: `2>&1`
- Try forcing framework: `-f jest`
- Check test output format matches expected patterns

### Remaining tests command too long
- Run tests by pattern instead
- Split into batches

---

## Tips

- **Always use bail in Phase 1** - Stop early, fix fast
- **Track test indices** - Essential for resume capability
- **Phase 2 is mandatory** - Catches regression bugs
- **Minimal changes only** - Don't refactor during fixes
- **Document flaky tests** - Note intermittent failures
- **Check CI parity** - Local and CI environments should match
