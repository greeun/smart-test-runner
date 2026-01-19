---
name: smart-test-runner
description: |
  Intelligent test execution with failure-first retry strategy.
  Runs domain tests (unit, integration, api, api-e2e, browser-e2e, security, performance, oapi),
  analyzes failures, fixes issues, re-runs failed tests only, then runs full domain suite on success.
  Use when running tests, fixing test failures, debugging test errors, or "run tests and fix".
---

# Smart Test Runner

Efficient test execution strategy: fix failures first, then verify full suite.

## Workflow

```
1. Detect test domains
   ↓
2. Run domain tests
   ↓
3. Failures? ──No──→ Next domain (or Done)
   │
   Yes
   ↓
4. Analyze failure cause
   ↓
5. Fix code/test
   ↓
6. Re-run ONLY failed tests
   ↓
7. Pass? ──No──→ Back to step 4
   │
   Yes
   ↓
8. Run full domain suite
   ↓
9. Pass? ──No──→ Back to step 4
   │
   Yes
   ↓
10. Next domain (or Done)
```

## Step 1: Detect Test Domains

Auto-detect available test domains from project configuration:

| Domain | Detection Pattern |
|--------|-------------------|
| unit | `test/unit/`, `__tests__/`, `*_test.py`, `*.spec.ts` |
| integration | `test/integration/`, `integration/` |
| api | `test/api/`, `api.test.*` |
| api-e2e | `test/api-e2e/`, `e2e/api/` |
| browser-e2e | `test/e2e/`, `cypress/`, `playwright/` |
| security | `test/security/`, `security.test.*` |
| performance | `test/performance/`, `perf/`, `k6/` |
| oapi | `openapi.yaml`, `swagger.*`, contract tests |

Check config files:
- `package.json` scripts
- `pytest.ini`, `pyproject.toml`
- `Makefile` targets
- `.github/workflows/*.yml`

## Step 2: Run Tests by Domain

Execute tests in recommended order (fast → slow):

1. **unit** - Fastest, run first
2. **integration** - Dependencies between modules
3. **api** - API endpoint tests
4. **oapi** - OpenAPI contract validation
5. **security** - Security scans
6. **api-e2e** - End-to-end API flows
7. **browser-e2e** - Browser automation (slowest)
8. **performance** - Load/stress tests (optional, heavy)

### Common Test Commands

```bash
# JavaScript/TypeScript
npm test                    # default
npm run test:unit           # unit only
npx jest --testPathPattern=unit
npx vitest run unit/

# Python
pytest tests/unit/
pytest -m unit
python -m pytest tests/

# Go
go test ./...
go test -run TestUnit

# Playwright (browser e2e)
npx playwright test

# Cypress
npx cypress run
```

## Step 3: Identify Failed Tests

Parse test output to extract:
- Failed test file path
- Failed test name/description
- Error message and stack trace
- Line number of failure

Example parsing:
```
FAIL src/utils/parser.test.ts
  ✕ should parse JSON correctly (15ms)
    → Extract: file=src/utils/parser.test.ts, test="should parse JSON correctly"
```

## Step 4: Analyze Failure Cause

For each failed test:

1. **Read the test file** - Understand what the test expects
2. **Read the source file** - Find the implementation being tested
3. **Analyze the error** - Categorize the failure type:

| Failure Type | Indicators | Common Fix |
|--------------|------------|------------|
| Assertion mismatch | `expected X, got Y` | Fix logic or update expectation |
| Type error | `TypeError`, `undefined` | Fix types, null checks |
| Timeout | `Timeout exceeded` | Increase timeout or fix async |
| Mock issue | `mock not called` | Fix mock setup or implementation |
| Environment | `ENOENT`, `connection refused` | Fix env setup or skip in CI |

## Step 5: Fix Code or Test

Apply targeted fixes based on analysis:

- **Implementation bug** → Fix the source code
- **Outdated test** → Update test expectations
- **Missing mock** → Add proper mock/stub
- **Flaky test** → Add retry or fix race condition

**Important**: Make minimal changes. Don't refactor unrelated code.

## Step 6: Re-run Failed Tests Only

Run only the specific failed tests:

```bash
# Jest
npx jest --testNamePattern="should parse JSON correctly"
npx jest path/to/failed.test.ts

# Vitest
npx vitest run -t "should parse JSON correctly"

# Pytest
pytest path/to/test_file.py::test_function_name
pytest -k "test_parse_json"

# Go
go test -run TestParseJSON ./pkg/parser/
```

**Repeat steps 4-6 until the specific test passes.**

## Step 7: Run Full Domain Suite

Once failed tests pass individually, run the complete domain:

```bash
# Run all unit tests
npm run test:unit
pytest tests/unit/
go test ./tests/unit/...
```

If new failures appear:
- These are likely **regression bugs** from your fix
- Go back to Step 4 for new failures

## Step 8: Proceed to Next Domain

After a domain passes completely:
1. Mark domain as complete
2. Move to next domain in priority order
3. Repeat from Step 2

## Output Format

Report progress using this structure:

```markdown
## Test Execution Report

### Domain: unit
- Total: 45 tests
- Passed: 43
- Failed: 2
- Status: FIXING

#### Failed Tests
1. `src/utils/parser.test.ts` - "should parse JSON correctly"
   - Error: Expected { a: 1 }, got { a: "1" }
   - Cause: Type coercion issue in parseJSON()
   - Fix: Added parseInt() conversion
   - Re-run: PASSED

2. `src/api/client.test.ts` - "should retry on failure"
   - Error: Timeout after 5000ms
   - Cause: Missing mock for fetch
   - Fix: Added fetch mock
   - Re-run: PASSED

#### Full Suite Re-run: PASSED (45/45)

### Domain: integration
- Status: RUNNING...
```

## Tips

- **Don't skip domains** - Run all detected domains even if one fails
- **Fix root causes** - Don't just make tests pass; fix underlying issues
- **Minimal changes** - Avoid unrelated refactoring during test fixes
- **Document flaky tests** - Note tests that fail intermittently
- **Check CI parity** - Ensure local and CI environments match
