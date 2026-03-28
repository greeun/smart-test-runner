#!/bin/bash
# Smart Test Runner - Test Configuration Detector
# Analyzes project structure to detect test domains and commands
# Now with bail (fail-fast) command support for hybrid workflow

set -e

PROJECT_DIR="${1:-.}"
cd "$PROJECT_DIR"

# Output JSON structure (bash 3 compatible - no associative arrays)
# Instead of declare -A, use indirect variables: COMMANDS_unit, COMMANDS_BAIL_unit, etc.
DETECTED_DOMAINS=()

# Helper: Check if file exists
has_file() {
    [[ -f "$1" ]]
}

# Helper: Check if directory exists
has_dir() {
    [[ -d "$1" ]]
}

# Helper: Check if command exists in package.json scripts
has_npm_script() {
    if has_file "package.json"; then
        grep -q "\"$1\":" package.json 2>/dev/null
    else
        return 1
    fi
}

# Detect JavaScript/TypeScript test framework
detect_js_framework() {
    local framework=""

    if has_file "package.json"; then
        if grep -q '"vitest"' package.json 2>/dev/null; then
            framework="vitest"
        elif grep -q '"jest"' package.json 2>/dev/null; then
            framework="jest"
        elif grep -q '"mocha"' package.json 2>/dev/null; then
            framework="mocha"
        fi
    fi

    echo "$framework"
}

# Detect Python test framework
detect_python_framework() {
    local framework=""

    if has_file "pytest.ini" || has_file "pyproject.toml" || has_file "setup.cfg"; then
        if grep -q "pytest" pyproject.toml 2>/dev/null || has_file "pytest.ini"; then
            framework="pytest"
        fi
    elif has_file "requirements.txt" || has_file "requirements-dev.txt"; then
        if grep -q "pytest" requirements*.txt 2>/dev/null; then
            framework="pytest"
        fi
    fi

    # Check for unittest
    if [[ -z "$framework" ]] && find . -name "test_*.py" -o -name "*_test.py" 2>/dev/null | head -1 | grep -q .; then
        framework="unittest"
    fi

    echo "$framework"
}

# Detect Go tests
detect_go_framework() {
    if has_file "go.mod"; then
        echo "go"
    fi
}

# Add bail option to command based on framework
add_bail_option() {
    local cmd="$1"
    local framework="$2"

    case "$framework" in
        jest|vitest)
            # Check if it's npm run script or direct npx
            if [[ "$cmd" == npm\ run* ]]; then
                echo "$cmd -- --bail"
            else
                echo "$cmd --bail"
            fi
            ;;
        pytest)
            if [[ "$cmd" == npm\ run* ]]; then
                echo "$cmd -- -x"
            else
                echo "$cmd -x"
            fi
            ;;
        go)
            # Insert -failfast after "go test"
            echo "${cmd/go test/go test -failfast}"
            ;;
        playwright)
            if [[ "$cmd" == npm\ run* ]]; then
                echo "$cmd -- --max-failures=1"
            else
                echo "$cmd --max-failures=1"
            fi
            ;;
        cypress)
            # Cypress doesn't have native bail, use spec isolation
            echo "$cmd"
            ;;
        *)
            echo "$cmd"
            ;;
    esac
}

# Detect test domains
detect_domains() {
    local js_fw=$(detect_js_framework)
    local py_fw=$(detect_python_framework)
    local go_fw=$(detect_go_framework)

    # Helper: set command for domain (bash 3 compatible)
    set_cmd() { eval "COMMANDS_$1=\"$2\""; }
    set_bail() { eval "COMMANDS_BAIL_$1=\"$2\""; }

    # Unit tests
    if has_dir "test/unit" || has_dir "tests/unit" || has_dir "__tests__" || \
       has_dir "src/__tests__" || find . -name "*.spec.ts" -o -name "*.test.ts" 2>/dev/null | head -1 | grep -q .; then
        DETECTED_DOMAINS+=("unit")
        if [[ -n "$js_fw" ]]; then
            if has_npm_script "test:unit"; then
                set_cmd unit "npm run test:unit"
                set_bail unit "$(add_bail_option "npm run test:unit" "$js_fw")"
            elif [[ "$js_fw" == "vitest" ]]; then
                set_cmd unit "npx vitest run"
                set_bail unit "npx vitest run --bail"
            elif [[ "$js_fw" == "jest" ]]; then
                set_cmd unit "npx jest"
                set_bail unit "npx jest --bail"
            fi
        elif [[ -n "$py_fw" ]]; then
            if has_dir "tests/unit"; then
                set_cmd unit "pytest tests/unit/"
                set_bail unit "pytest tests/unit/ -x"
            else
                set_cmd unit "pytest -m unit"
                set_bail unit "pytest -m unit -x"
            fi
        elif [[ -n "$go_fw" ]]; then
            set_cmd unit "go test ./..."
            set_bail unit "go test -failfast ./..."
        fi
    fi

    # Integration tests
    if has_dir "test/integration" || has_dir "tests/integration" || has_dir "integration"; then
        DETECTED_DOMAINS+=("integration")
        if [[ -n "$js_fw" ]]; then
            if has_npm_script "test:integration"; then
                set_cmd integration "npm run test:integration"
                set_bail integration "$(add_bail_option "npm run test:integration" "$js_fw")"
            else
                set_cmd integration "npx $js_fw --testPathPattern=integration"
                set_bail integration "npx $js_fw --testPathPattern=integration --bail"
            fi
        elif [[ -n "$py_fw" ]]; then
            set_cmd integration "pytest tests/integration/"
            set_bail integration "pytest tests/integration/ -x"
        elif [[ -n "$go_fw" ]]; then
            set_cmd integration "go test -tags=integration ./..."
            set_bail integration "go test -failfast -tags=integration ./..."
        fi
    fi

    # API tests
    if has_dir "test/api" || has_dir "tests/api" || find . -name "api.test.*" -o -name "*.api.test.*" 2>/dev/null | head -1 | grep -q .; then
        DETECTED_DOMAINS+=("api")
        if has_npm_script "test:api"; then
            set_cmd api "npm run test:api"
            set_bail api "$(add_bail_option "npm run test:api" "$js_fw")"
        elif [[ -n "$js_fw" ]]; then
            set_cmd api "npx $js_fw --testPathPattern=api"
            set_bail api "npx $js_fw --testPathPattern=api --bail"
        elif [[ -n "$py_fw" ]]; then
            set_cmd api "pytest tests/api/"
            set_bail api "pytest tests/api/ -x"
        fi
    fi

    # E2E tests (browser)
    if has_dir "cypress" || has_dir "e2e" || has_dir "test/e2e" || has_file "playwright.config.ts" || has_file "playwright.config.js"; then
        DETECTED_DOMAINS+=("browser-e2e")
        if has_file "playwright.config.ts" || has_file "playwright.config.js"; then
            set_cmd browser_e2e "npx playwright test"
            set_bail browser_e2e "npx playwright test --max-failures=1"
        elif has_dir "cypress"; then
            set_cmd browser_e2e "npx cypress run"
            set_bail browser_e2e "npx cypress run"
        elif has_npm_script "test:e2e"; then
            set_cmd browser_e2e "npm run test:e2e"
            set_bail browser_e2e "$(add_bail_option "npm run test:e2e" "playwright")"
        fi
    fi

    # API E2E tests
    if has_dir "test/api-e2e" || has_dir "tests/api-e2e" || has_dir "e2e/api"; then
        DETECTED_DOMAINS+=("api-e2e")
        if has_npm_script "test:api-e2e"; then
            set_cmd api_e2e "npm run test:api-e2e"
            set_bail api_e2e "$(add_bail_option "npm run test:api-e2e" "$js_fw")"
        elif [[ -n "$py_fw" ]]; then
            set_cmd api_e2e "pytest tests/api-e2e/"
            set_bail api_e2e "pytest tests/api-e2e/ -x"
        fi
    fi

    # Security tests
    if has_dir "test/security" || has_dir "tests/security"; then
        DETECTED_DOMAINS+=("security")
        if has_npm_script "test:security"; then
            set_cmd security "npm run test:security"
            set_bail security "$(add_bail_option "npm run test:security" "$js_fw")"
        elif [[ -n "$py_fw" ]]; then
            set_cmd security "pytest tests/security/"
            set_bail security "pytest tests/security/ -x"
        fi
    fi

    # Performance tests
    if has_dir "test/performance" || has_dir "tests/performance" || has_dir "k6" || has_file "k6.js"; then
        DETECTED_DOMAINS+=("performance")
        if has_file "k6.js" || has_dir "k6"; then
            set_cmd performance "k6 run k6.js"
            set_bail performance "k6 run k6.js"
        elif has_npm_script "test:perf"; then
            set_cmd performance "npm run test:perf"
            set_bail performance "npm run test:perf"
        fi
    fi

    # OpenAPI contract tests
    if has_file "openapi.yaml" || has_file "openapi.json" || has_file "swagger.yaml" || has_file "swagger.json"; then
        DETECTED_DOMAINS+=("oapi")
        if has_npm_script "test:oapi"; then
            set_cmd oapi "npm run test:oapi"
            set_bail oapi "$(add_bail_option "npm run test:oapi" "$js_fw")"
        elif has_npm_script "test:contract"; then
            set_cmd oapi "npm run test:contract"
            set_bail oapi "$(add_bail_option "npm run test:contract" "$js_fw")"
        fi
    fi
}

# Helper: get command for domain (bash 3 compatible indirect variable)
get_cmd() {
    local key="COMMANDS_${1//-/_}"
    echo "${!key:-not detected}"
}
get_bail() {
    local key="COMMANDS_BAIL_${1//-/_}"
    local fallback_key="COMMANDS_${1//-/_}"
    local val="${!key}"
    if [[ -z "$val" ]]; then
        val="${!fallback_key:-not detected}"
    fi
    echo "$val"
}

# Output JSON
output_json() {
    echo "{"
    echo "  \"project_dir\": \"$(pwd)\","

    # Frameworks
    echo "  \"frameworks\": {"
    echo "    \"javascript\": \"$(detect_js_framework)\","
    echo "    \"python\": \"$(detect_python_framework)\","
    echo "    \"go\": \"$(detect_go_framework)\""
    echo "  },"

    # Domains
    echo "  \"domains\": ["
    local first=true
    for domain in "${DETECTED_DOMAINS[@]}"; do
        if [[ "$first" == "true" ]]; then
            first=false
        else
            echo ","
        fi
        echo -n "    {"
        echo -n "\"name\": \"$domain\", "
        echo -n "\"command\": \"$(get_cmd "$domain")\", "
        echo -n "\"bail_command\": \"$(get_bail "$domain")\", "
        echo -n "\"priority\": $(get_priority "$domain")"
        echo -n "}"
    done
    echo ""
    echo "  ],"

    # Summary
    echo "  \"total_domains\": ${#DETECTED_DOMAINS[@]}"
    echo "}"
}

# Get domain priority (lower = run first)
get_priority() {
    case "$1" in
        unit) echo 1 ;;
        integration) echo 2 ;;
        api) echo 3 ;;
        oapi) echo 4 ;;
        security) echo 5 ;;
        api-e2e) echo 6 ;;
        browser-e2e) echo 7 ;;
        performance) echo 8 ;;
        *) echo 9 ;;
    esac
}

# Main
detect_domains
output_json
