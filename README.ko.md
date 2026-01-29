# Smart Test Runner

[![Claude Code Skill](https://img.shields.io/badge/Claude%20Code-Skill-blue)](https://claude.ai/code)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> Claude Code를 위한 지능형 테스트 실행 스킬 - 하이브리드 워크플로우 전략

[English](README.md)

## 문제점

기존 테스트 실행 방식은 수정 후 매번 전체 테스트를 재실행하여 시간을 낭비합니다:

```
100개 테스트 (5분) → 2개 실패
→ #30 수정 → 전체 100개 재실행 (5분) → 1개 실패
→ #70 수정 → 전체 100개 재실행 (5분) → 통과

총 소요: 15분 이상
```

## 해결책

Smart Test Runner는 **하이브리드 워크플로우**를 사용합니다:

1. **Phase 1 (빠른 수정)**: `--bail`로 실행, 첫 실패 시 중단, 수정 후 실패 지점부터 재개
2. **Phase 2 (회귀 검증)**: 전체 테스트 1회 실행으로 회귀 버그 감지

```
Phase 1:
100개 테스트 (--bail) → #30 실패 (1.5분에 중단)
→ 수정 → #30만 재실행 (3초) → 통과
→ #31-100 실행 (3.5분) → #70 실패
→ 수정 → #70만 재실행 (3초) → 통과
→ #71-100 실행 (1.5분) → 전체 통과

Phase 2:
100개 전체 테스트 (5분) → 통과

총 소요: ~12분 (20% 단축)
```

## 효율성

| 시나리오 | 기존 방식 | 하이브리드 | 절감률 |
|----------|-----------|------------|--------|
| 100개 중 2개 실패 | 15분 | 12분 | **20%** |
| 100개 중 5개 실패 | 30분 | 18분 | **40%** |
| 100개 중 10개 실패 | 55분 | 25분 | **55%** |

실패가 많을수록 시간 절감 효과가 커집니다.

## 주요 기능

- **하이브리드 워크플로우**: 빠른 수정 + 회귀 검증
- **Bail 모드**: 첫 실패 시 중단 (`--bail`, `-x`, `-failfast`)
- **이어서 실행**: 실패 지점부터 계속, 처음부터 재시작 X
- **다중 프레임워크**: Jest, Vitest, Pytest, Go, Playwright, Cypress
- **자동 감지**: 테스트 도메인 및 명령어 자동 감지
- **실패 분류**: 어설션, 타입 에러, 타임아웃, 목 이슈 등

## 설치

```bash
# 리포지토리 클론
git clone https://github.com/greeun/smart-test-runner.git

# Claude Code 스킬 디렉토리에 심볼릭 링크 생성
ln -s $(pwd)/smart-test-runner ~/.claude/skills/smart-test-runner

# 확인
ls ~/.claude/skills/smart-test-runner/scripts/
```

## 사용법

### Claude Code에서 트리거

```
"테스트 돌려줘"
"테스트 실행하고 에러 수정해줘"
"run tests"
"fix test failures"
```

### 수동 스크립트 사용

```bash
# 1. 테스트 도메인 감지
bash ~/.claude/skills/smart-test-runner/scripts/detect_test_config.sh .

# 2. 테스트 목록 수집 (이어서 실행용)
python ~/.claude/skills/smart-test-runner/scripts/list_tests.py -f jest --pretty

# 3. 테스트 출력 파싱
npx jest --bail 2>&1 | python ~/.claude/skills/smart-test-runner/scripts/parse_test_output.py -p

# 4. 실패 후 나머지 테스트 명령어 생성
python ~/.claude/skills/smart-test-runner/scripts/list_tests.py -f jest -r 15
```

## 스크립트

| 스크립트 | 용도 |
|----------|------|
| `detect_test_config.sh` | 프레임워크, 도메인 감지, bail 명령어 생성 |
| `list_tests.py` | 테스트 목록, 이어서 실행 명령어 생성 |
| `parse_test_output.py` | 테스트 출력을 통합 JSON 형식으로 파싱 |

## 워크플로우 다이어그램

```
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 1: 빠른 수정 (bail 모드)                                   │
├─────────────────────────────────────────────────────────────────┤
│  1. --bail로 실행 (첫 실패 시 중단)                              │
│  2. 실패? ──No──→ Phase 1 완료                                  │
│     │                                                           │
│     Yes                                                         │
│     ↓                                                           │
│  3. 실패 파싱 → 분석 → 수정                                      │
│  4. 실패한 테스트만 재실행                                       │
│  5. 통과? ──No──→ 3번으로                                       │
│     │                                                           │
│     Yes                                                         │
│     ↓                                                           │
│  6. 나머지 테스트 실행 (이어서, 처음부터 X)                       │
│  7. 추가 실패? ──Yes──→ 3번으로                                  │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│ PHASE 2: 회귀 검증                                              │
├─────────────────────────────────────────────────────────────────┤
│  8. 전체 테스트 실행 (bail 없이)                                 │
│  9. 새 실패? ──Yes──→ Phase 1로 (회귀 버그)                      │
│     │                                                           │
│     No → 완료!                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## 지원 프레임워크

| 프레임워크 | 일반 명령어 | Bail 명령어 |
|------------|-------------|-------------|
| Jest | `npx jest` | `npx jest --bail` |
| Vitest | `npx vitest run` | `npx vitest run --bail` |
| Pytest | `pytest` | `pytest -x` |
| Go | `go test ./...` | `go test -failfast ./...` |
| Playwright | `npx playwright test` | `npx playwright test --max-failures=1` |

## 테스트 도메인

우선순위 순으로 자동 감지:

1. **unit** - 단위 테스트 (가장 빠름)
2. **integration** - 통합 테스트
3. **api** - API 테스트
4. **oapi** - OpenAPI 계약 테스트
5. **security** - 보안 테스트
6. **api-e2e** - API E2E 테스트
7. **browser-e2e** - 브라우저 E2E 테스트
8. **performance** - 성능 테스트 (가장 느림)

## 요구사항

- Claude Code CLI
- Python 3.6+
- Bash 4.0+

## 라이선스

MIT License

## 기여

이슈와 PR 환영합니다!

## 관련 링크

- [Claude Code](https://claude.ai/code)
- [블로그 포스트](https://freestory.net/tech/ai/smart-test-runner-v2-하이브리드-워크플로우로-테스트-시간-40-단축/)
