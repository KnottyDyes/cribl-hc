# Test Coverage Report

**Date**: 2025-12-26
**Current Status**: 674 tests, ~18% coverage (target: 80%)

## Executive Summary

The cribl-hc project has a solid foundation of unit tests for foundational components (utils, models, rules) with good coverage (40-87% range). The main coverage gaps are in integration layers (API, CLI, Analyzers) which require integration and contract tests rather than unit tests.

## Coverage by Module

### ✅ GOOD - Utils & Foundation (40-87% coverage)

| Module | Coverage | Tests | Status |
|--------|----------|-------|--------|
| `utils/rate_limiter.py` | 87% | 25 tests | Excellent - comprehensive async/sync testing |
| `utils/logger.py` | 47% | 17 tests | Good - covers main workflows |
| `utils/crypto.py` | 44% | 31 tests | Good - security-focused testing |
| `utils/version.py` | 42% | Included in rules tests | Good |
| `rules/loader.py` | 72% | 27 tests | Good - YAML loading, filtering, evaluation |
| `models/*` | 62-100% | 674 total | Good - Pydantic validation tested |

### ⚠️ NEEDS WORK - API Layer (0-20% coverage)

| Module | Lines | Coverage | Priority |
|--------|-------|----------|----------|
| `api/routers/analysis.py` | 218 | 0% | **HIGH** - Now has integration tests |
| `api/routers/credentials.py` | 154 | 0% | **HIGH** - Now has integration tests |
| `api/routers/analyzers.py` | 34 | 0% | **MEDIUM** - Now has integration tests |
| `api/app.py` | 28 | 0% | **MEDIUM** |
| `core/api_client.py` | 255 | 20% | **HIGH** - Now has integration tests |

**Recently Added**: 4 new integration test files with 1,194 lines of comprehensive API testing

### ⚠️ NEEDS WORK - Core Orchestration (0-25% coverage)

| Module | Lines | Coverage | Priority |
|--------|-------|----------|----------|
| `core/orchestrator.py` | 122 | 0% | **HIGH** |
| `core/report_generator.py` | 85 | 0% | **HIGH** |
| `core/health_scorer.py` | 101 | 25% | **MEDIUM** |

### ⚠️ NEEDS WORK - Analyzers (9-16% coverage)

| Module | Lines | Coverage | Priority |
|--------|-------|----------|----------|
| `analyzers/config.py` | 531 | 9% | **HIGH** |
| `analyzers/health.py` | 226 | 12% | **HIGH** |
| `analyzers/resource.py` | 196 | 16% | **MEDIUM** |

### ❌ NOT TESTED - CLI (0% coverage)

| Module | Lines | Coverage | Notes |
|--------|-------|----------|-------|
| `cli/commands/analyze.py` | 147 | 0% | Command-line interface |
| `cli/commands/config.py` | 120 | 0% | Configuration management |
| `cli/modern_tui.py` | 377 | 0% | Terminal UI |
| `cli/config_tui.py` | 280 | 0% | Configuration TUI |
| `cli/unified_tui.py` | 208 | 0% | Unified TUI |
| `cli/tui.py` | 154 | 0% | Legacy TUI |
| `cli/output.py` | 108 | 0% | Output formatting |

## New Integration Tests Added (Dec 26, 2025)

### API Credentials Tests (`test_api_credentials.py` - 411 lines)
- ✅ Create, list, get, update, delete credentials
- ✅ Connection testing with success/failure scenarios
- ✅ Validation (name, URL, required fields)
- ✅ Security (tokens never exposed in responses)
- ✅ Duplicate handling
- ✅ OAuth client secret protection

### API Analysis Tests (`test_api_analysis.py` - 379 lines)
- ✅ Start analysis with various objectives
- ✅ Status checking and results retrieval
- ✅ Export in multiple formats (JSON, MD, HTML)
- ✅ Validation (empty objectives, duplicates)
- ✅ Concurrency handling
- ✅ Error scenarios (invalid credentials, nonexistent analysis)

### API Analyzers Tests (`test_api_analyzers.py` - 118 lines)
- ✅ List all analyzers
- ✅ Get specific analyzer info
- ✅ Filter by objective
- ✅ Metadata and capabilities
- ✅ Required fields validation

### Core API Client Tests (`test_api_client.py` - 286 lines)
- ✅ Initialization with bearer token and OAuth
- ✅ Connection testing
- ✅ Retry logic (5xx vs 4xx)
- ✅ Rate limiting integration
- ✅ Auth header injection
- ✅ Error handling (timeouts, connection errors, invalid JSON)
- ✅ API call tracking

## Test Categories

### Unit Tests (674 total)
- **Models**: Pydantic validation, serialization, field constraints
- **Utils**: Logger, rate limiter, crypto, version detection
- **Rules**: YAML loading, filtering, evaluation

### Integration Tests (New - 4 files)
- **API Routers**: Full workflow testing with mocked external dependencies
- **Core Components**: API client with respx mocking
- **Existing**: Health analysis, config analyzer, connection workflow, end-to-end

### Contract Tests (Existing)
- **Cribl API**: Schema validation for external API responses

## Coverage Improvement Strategy

### Phase 1: Integration Tests for API & Core ✅ IN PROGRESS
**Target**: Increase API coverage from 0% → 60%

**Completed**:
- ✅ API routers (credentials, analysis, analyzers) - 1,194 lines of tests
- ✅ Core API client - comprehensive mocking with respx

**Remaining**:
- Orchestrator workflow tests
- Health scorer tests
- Report generator tests

### Phase 2: Analyzer Integration Tests
**Target**: Increase analyzer coverage from 9-16% → 50%

**Needed**:
- Health analyzer with mocked Cribl API responses
- Config analyzer pattern matching tests
- Resource analyzer threshold tests

### Phase 3: Contract Tests
**Target**: Validate all Cribl API endpoint schemas

**Needed**:
- System endpoints (/api/v1/system/*)
- Worker endpoints (/api/v1/master/workers)
- Metrics endpoints (/api/v1/metrics/*)
- Config endpoints

### Phase 4: CLI Tests (Optional)
**Target**: Basic CLI command testing

**Needed**:
- Click command invocation tests
- Output format validation
- TUI interaction tests (if feasible)

## Running Tests

```bash
# All tests
pytest tests/ -v

# Unit tests only
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v

# Contract tests only
pytest tests/contract/ -v

# With coverage report
pytest tests/ --cov=src/cribl_hc --cov-report=html

# Specific module coverage
pytest tests/integration/test_api_credentials.py -v --cov=src/cribl_hc/api/routers/credentials
```

## Dependencies for Testing

Required packages (from `requirements-dev.txt`):
- `pytest` - Test framework
- `pytest-asyncio` - Async test support
- `pytest-cov` - Coverage reporting
- `httpx` - Async HTTP client for API testing
- `respx` - HTTP mocking for httpx
- `pytest-mock` - Mocking utilities

## Next Steps

1. **Immediate** (High Impact):
   - Add orchestrator integration tests (core workflow)
   - Add health scorer unit tests (scoring logic)
   - Run new integration tests to measure coverage improvement

2. **Short Term**:
   - Analyzer integration tests with mocked Cribl API
   - Contract tests for remaining Cribl API endpoints
   - Report generator tests

3. **Long Term**:
   - CLI command tests
   - TUI interaction tests (if beneficial)
   - Performance/load testing

## Coverage Goal Timeline

| Milestone | Target Coverage | Completion Date |
|-----------|----------------|-----------------|
| Foundation (Utils/Models) | 50% | ✅ Completed |
| API Integration Tests | 40% | 🔄 In Progress (Dec 26) |
| Core Components | 50% | Jan 2026 |
| Analyzers | 50% | Jan 2026 |
| Overall Target | 80% | Feb 2026 |

## Notes

- CLI tests (0% coverage) are lowest priority - these are user-facing and harder to test
- Focus is on business logic: API routers, core components, and analyzers
- Good test foundation exists - main gap is integration layer coverage
- New integration tests follow FastAPI testing best practices with httpx AsyncClient
- Mocking strategy uses respx for external HTTP calls to Cribl API

---
Generated: 2025-12-26
