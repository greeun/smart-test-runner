# Smart Test Runner

Intelligent test execution skill for Claude Code with failure-first retry strategy.

테스트 실패 시 전체 테스트를 반복 실행하는 비효율을 해결하는 Claude Code 스킬입니다.

## Features

- **Failure-First Retry**: 실패한 테스트만 먼저 수정/재실행 후 전체 테스트 검증
- **Multi-Domain Support**: unit, integration, api, e2e, security, performance 등 모든 도메인
- **Auto Detection**: 테스트 프레임워크 및 도메인 자동 감지
- **Smart Analysis**: 실패 원인 자동 분류 및 해결 방향 제시

## Installation

이 스킬은 `~/.claude/skills/smart-test-runner/`에 설치되어 있습니다.

### Manual Installation

```bash
# Clone or copy to skills directory
mkdir -p ~/.claude/skills/smart-test-runner
cp SKILL.md ~/.claude/skills/smart-test-runner/
```

## Usage

### Trigger Keywords

Claude Code에서 다음 키워드로 스킬이 자동 트리거됩니다:

| 한글 | English |
|------|---------|
| "테스트 돌려줘" | "run tests" |
| "테스트 실행하고 에러 수정해줘" | "run tests and fix" |
| "테스트 실패 원인 분석해줘" | "fix test failures" |
| "unit 테스트만 실행해줘" | "run unit tests" |

### Examples

```
# 기본 사용
사용자: 테스트 돌리고 에러 수정해줘

# 특정 도메인만
사용자: integration 테스트만 실행해줘

# 영어로도 가능
User: run tests and fix any failures
```

## Workflow

```
1. Detect test domains
   ↓
2. Run domain tests (fast → slow order)
   ↓
3. Failures? ──No──→ Next domain (or Done)
   │
   Yes
   ↓
4. Analyze failure cause
   ↓
5. Fix code/test
   ↓
6. Re-run ONLY failed tests  ← Key optimization
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

## Supported Test Domains

| Domain | Detection Pattern | Priority |
|--------|-------------------|----------|
| unit | `test/unit/`, `__tests__/`, `*.spec.ts` | 1 (fastest) |
| integration | `test/integration/` | 2 |
| api | `test/api/`, `api.test.*` | 3 |
| oapi | `openapi.yaml`, contract tests | 4 |
| security | `test/security/` | 5 |
| api-e2e | `test/api-e2e/`, `e2e/api/` | 6 |
| browser-e2e | `cypress/`, `playwright/` | 7 |
| performance | `test/performance/`, `k6/` | 8 (slowest) |

## Supported Test Frameworks

### JavaScript/TypeScript

```bash
# Jest
npx jest
npx jest --testNamePattern="test name"
npx jest path/to/file.test.ts

# Vitest
npx vitest run
npx vitest run -t "test name"

# Playwright
npx playwright test

# Cypress
npx cypress run
```

### Python

```bash
# Pytest
pytest
pytest path/to/test_file.py::test_function
pytest -k "test_name"
```

### Go

```bash
go test ./...
go test -run TestName ./pkg/...
```

## Failure Analysis

스킬은 테스트 실패 시 원인을 자동으로 분류합니다:

| Type | Indicators | Common Fix |
|------|------------|------------|
| Assertion mismatch | `expected X, got Y` | Fix logic or update expectation |
| Type error | `TypeError`, `undefined` | Fix types, null checks |
| Timeout | `Timeout exceeded` | Increase timeout or fix async |
| Mock issue | `mock not called` | Fix mock setup |
| Environment | `ENOENT`, `connection refused` | Fix env or skip in CI |

## Output Format

```markdown
## Test Execution Report

### Domain: unit
- Total: 45 tests
- Passed: 43
- Failed: 2
- Status: FIXING

#### Failed Tests
1. `src/utils/parser.test.ts` - "should parse JSON"
   - Error: Expected { a: 1 }, got { a: "1" }
   - Cause: Type coercion issue
   - Fix: Added parseInt()
   - Re-run: PASSED

#### Full Suite Re-run: PASSED (45/45)
```

## Configuration

현재 버전은 별도의 설정 파일 없이 프로젝트 구조를 자동으로 분석합니다.

### Auto-detected Config Files

- `package.json` - npm scripts
- `pytest.ini`, `pyproject.toml` - Python
- `Makefile` - Make targets
- `.github/workflows/*.yml` - CI configuration

## Best Practices

1. **Don't skip domains** - 모든 감지된 도메인 실행
2. **Fix root causes** - 테스트만 통과시키지 말고 근본 원인 해결
3. **Minimal changes** - 수정 시 관련 없는 리팩토링 금지
4. **Document flaky tests** - 간헐적 실패 테스트 기록
5. **Check CI parity** - 로컬과 CI 환경 일치 확인

## Comparison

### Before (Traditional)

```
전체 테스트 (5분) → 2개 실패
  → 수정 → 전체 테스트 (5분) → 1개 실패
  → 수정 → 전체 테스트 (5분) → 통과!

Total: 15분
```

### After (Smart Test Runner)

```
전체 테스트 (5분) → 2개 실패
  → 수정 → 실패 테스트만 (3초) → 통과
  → 수정 → 실패 테스트만 (3초) → 통과
  → 전체 테스트 (5분) → 통과!

Total: 10분 6초
```

## License

MIT License

## Contributing

Issues and PRs welcome at the skill repository.
