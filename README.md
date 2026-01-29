# Smart Test Runner

[![Claude Code Skill](https://img.shields.io/badge/Claude%20Code-Skill-blue)](https://claude.ai/code)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> Intelligent test execution skill for Claude Code with hybrid workflow strategy.

[한국어 문서](README.ko.md)

## Problem

Traditional test execution wastes time by re-running all tests after each fix:

```
100 tests (5min) → 2 failures
→ Fix #30 → Run ALL 100 tests (5min) → 1 failure
→ Fix #70 → Run ALL 100 tests (5min) → Pass

Total: 15+ minutes
```

## Solution

Smart Test Runner uses a **hybrid workflow**:

1. **Phase 1 (Fast Fix)**: Run with `--bail`, stop on first failure, fix, resume from failure point
2. **Phase 2 (Regression Check)**: Run full suite once to catch regression bugs

```
Phase 1:
100 tests (--bail) → #30 fails (1.5min, stopped early)
→ Fix → Re-run #30 only (3sec) → Pass
→ Run #31-100 (3.5min) → #70 fails
→ Fix → Re-run #70 only (3sec) → Pass
→ Run #71-100 (1.5min) → All pass

Phase 2:
100 tests full (5min) → Pass

Total: ~12 minutes (20% faster)
```

## Efficiency

| Scenario | Traditional | Hybrid | Savings |
|----------|-------------|--------|---------|
| 100 tests, 2 failures | 15 min | 12 min | **20%** |
| 100 tests, 5 failures | 30 min | 18 min | **40%** |
| 100 tests, 10 failures | 55 min | 25 min | **55%** |

More failures = more time saved.

## Features

- **Hybrid Workflow**: Fast fix + regression verification
- **Bail Mode**: Stop on first failure (`--bail`, `-x`, `-failfast`)
- **Resume Capability**: Continue from failure point, not restart
- **Multi-Framework**: Jest, Vitest, Pytest, Go, Playwright, Cypress
- **Auto Detection**: Detect test domains and commands automatically
- **Failure Classification**: Assertion, type error, timeout, mock issue, etc.

## Installation

```bash
# Clone repository
git clone https://github.com/greeun/smart-test-runner.git

# Create symlink to Claude Code skills directory
ln -s $(pwd)/smart-test-runner ~/.claude/skills/smart-test-runner

# Verify
ls ~/.claude/skills/smart-test-runner/scripts/
```

## Usage

### Trigger in Claude Code

```
"run tests"
"테스트 돌려줘"
"run tests and fix"
"fix test failures"
```

### Manual Script Usage

```bash
# 1. Detect test domains
bash ~/.claude/skills/smart-test-runner/scripts/detect_test_config.sh .

# 2. List tests for resume capability
python ~/.claude/skills/smart-test-runner/scripts/list_tests.py -f jest --pretty

# 3. Parse test output
npx jest --bail 2>&1 | python ~/.claude/skills/smart-test-runner/scripts/parse_test_output.py -p

# 4. Get remaining tests after failure
python ~/.claude/skills/smart-test-runner/scripts/list_tests.py -f jest -r 15
```

## Scripts

| Script | Purpose |
|--------|---------|
| `detect_test_config.sh` | Detect frameworks, domains, generate bail commands |
| `list_tests.py` | List tests, generate resume-from commands |
| `parse_test_output.py` | Parse test output to unified JSON format |

## Workflow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 1: Fast Fix (bail mode)                                   │
├─────────────────────────────────────────────────────────────────┤
│  1. Run with --bail (stop on first failure)                     │
│  2. Failure? ──No──→ Phase 1 done                               │
│     │                                                           │
│     Yes                                                         │
│     ↓                                                           │
│  3. Parse failure → Analyze → Fix                               │
│  4. Re-run ONLY failed test                                     │
│  5. Pass? ──No──→ Back to step 3                                │
│     │                                                           │
│     Yes                                                         │
│     ↓                                                           │
│  6. Run REMAINING tests (continue, not restart)                 │
│  7. More failures? ──Yes──→ Back to step 3                      │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│ PHASE 2: Regression Check                                       │
├─────────────────────────────────────────────────────────────────┤
│  8. Run FULL test suite (no bail)                               │
│  9. New failures? ──Yes──→ Back to Phase 1 (regression bug)     │
│     │                                                           │
│     No → Done!                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Supported Frameworks

| Framework | Normal | Bail |
|-----------|--------|------|
| Jest | `npx jest` | `npx jest --bail` |
| Vitest | `npx vitest run` | `npx vitest run --bail` |
| Pytest | `pytest` | `pytest -x` |
| Go | `go test ./...` | `go test -failfast ./...` |
| Playwright | `npx playwright test` | `npx playwright test --max-failures=1` |

## Test Domains

Detected automatically in priority order:

1. **unit** - Unit tests (fastest)
2. **integration** - Integration tests
3. **api** - API tests
4. **oapi** - OpenAPI contract tests
5. **security** - Security tests
6. **api-e2e** - API end-to-end tests
7. **browser-e2e** - Browser end-to-end tests
8. **performance** - Performance tests (slowest)

## Requirements

- Claude Code CLI
- Python 3.6+
- Bash 4.0+

## License

MIT License

## Contributing

Issues and PRs welcome!

## Related

- [Claude Code](https://claude.ai/code)
- [Blog Post (Korean)](https://freestory.net/tech/ai/smart-test-runner-v2-하이브리드-워크플로우로-테스트-시간-40-단축/)
