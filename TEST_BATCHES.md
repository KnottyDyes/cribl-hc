# Test Implementation Batches

**Status**: 19/180 tasks completed (10.6%)
**Focus**: Implementing comprehensive test suite following TDD principles

**Note**: Core functionality (Web GUI, TUI, CLI) is already working. We're backfilling tests to meet spec requirements.

---

## Batch 1: Foundational Tests - Utils & Core Infrastructure (Est. 30-45 min)

**Goal**: Test utility modules and core infrastructure

**Prerequisites**: All utils and core modules already implemented

### Tasks (11 tasks)

- [ ] T019 - Write unit tests for all Pydantic models in `tests/unit/test_models/` ensuring validation works
- [ ] T025 - [P] Write unit tests for logger in `tests/unit/test_utils/test_logger.py`
- [ ] T026 - [P] Write unit tests for rate limiter in `tests/unit/test_utils/test_rate_limiter.py`
- [ ] T027 - [P] Write unit tests for crypto in `tests/unit/test_utils/test_crypto.py`
- [ ] T028 - [P] Write unit tests for version detection in `tests/unit/test_utils/test_version.py`
- [ ] T031 - Write integration tests for API client in `tests/integration/test_api_client.py` using respx to mock Cribl API
- [ ] T032 - Write contract tests for Cribl API responses in `tests/contract/test_cribl_api.py` validating schema compliance
- [ ] T035 - Write unit tests for base analyzer in `tests/unit/test_analyzers/test_base.py`

**Parallel Opportunities**: T025-T028 can all run in parallel (different files, no dependencies)

**Success Criteria**:
- All utility functions have 80%+ coverage
- Pydantic models validate correctly (test valid + invalid inputs)
- API client handles errors gracefully
- Contract tests validate actual Cribl API response schemas

**Files to Create**:
- `tests/unit/test_models/*.py`
- `tests/unit/test_utils/*.py`
- `tests/integration/test_api_client.py`
- `tests/contract/test_cribl_api.py`
- `tests/unit/test_analyzers/test_base.py`

---

## Batch 2: User Story 1 Tests - Health Assessment (Est. 45-60 min)

**Goal**: Complete test coverage for health assessment (already implemented)

**Prerequisites**: Batch 1 complete, HealthAnalyzer already implemented

### Tasks (22 tasks)

**Contract Tests** (can run in parallel):
- [ ] T036 - [P] [US1] Write contract test for `/api/v1/system/status` endpoint
- [ ] T037 - [P] [US1] Write contract test for `/api/v1/master/workers` endpoint
- [ ] T038 - [P] [US1] Write contract test for `/api/v1/metrics` endpoint

**Integration Tests**:
- [ ] T039 - [P] [US1] Write integration test for health analysis workflow in `tests/integration/test_health_analysis.py`
- [ ] T040 - [US1] Write end-to-end test in `tests/integration/test_end_to_end.py` for P1 MVP (mock Cribl API, verify health score calculation)

**Unit Tests** (can run in parallel):
- [ ] T046 - [P] [US1] Write unit tests for HealthAnalyzer in `tests/unit/test_analyzers/test_health.py`
- [ ] T047 - [P] [US1] Write unit tests for health_scorer in `tests/unit/test_core/test_health_scorer.py`
- [ ] T051 - [P] [US1] Write unit tests for analyzer orchestrator in `tests/unit/test_core/test_analyzer.py`
- [ ] T057 - [P] [US1] Write unit tests for CLI commands in `tests/unit/test_cli/`
- [ ] T060 - [P] [US1] Write unit tests for report generator in `tests/unit/test_core/test_report_generator.py`

**Success Criteria**:
- Health analyzer achieves 80%+ coverage
- Contract tests validate actual Cribl API responses
- End-to-end test completes full workflow (<5 min, <100 API calls)
- CLI commands tested with mocked dependencies

**Files to Create**:
- `tests/contract/test_cribl_api.py` (extend with US1 endpoints)
- `tests/integration/test_health_analysis.py`
- `tests/integration/test_end_to_end.py`
- `tests/unit/test_analyzers/test_health.py`
- `tests/unit/test_core/test_health_scorer.py`
- `tests/unit/test_core/test_analyzer.py`
- `tests/unit/test_cli/*.py`
- `tests/unit/test_core/test_report_generator.py`

---

## Batch 3: User Story 2 Tests - Configuration Validation (Est. 45-60 min)

**Goal**: Test configuration auditing and best practices validation (already implemented)

**Prerequisites**: Batch 1 complete, ConfigAuditAnalyzer and BestPracticesAnalyzer implemented

### Tasks (18 tasks)

**Contract Tests** (can run in parallel):
- [ ] T063 - [P] [US2] Write contract test for `/api/v1/m/{group}/pipelines` endpoint
- [ ] T064 - [P] [US2] Write contract test for `/api/v1/m/{group}/routes` endpoint
- [ ] T065 - [P] [US2] Write contract test for `/api/v1/m/{group}/outputs` endpoint

**Integration Tests**:
- [ ] T066 - [P] [US2] Write integration test for config audit workflow in `tests/integration/test_config_audit.py`
- [ ] T067 - [US2] Write integration test for best practices validation in `tests/integration/test_best_practices.py`

**Unit Tests** (can run in parallel):
- [ ] T074 - [P] [US2] Write unit tests for ConfigAuditAnalyzer in `tests/unit/test_analyzers/test_config_audit.py`
- [ ] T081 - [P] [US2] Write unit tests for BestPracticesAnalyzer in `tests/unit/test_analyzers/test_best_practices.py`
- [ ] T082 - [P] [US2] Write unit tests for rules loader in `tests/unit/test_rules/test_loader.py`

**Success Criteria**:
- Config audit analyzer achieves 80%+ coverage
- Test syntax validation, logic error detection, orphaned configs
- Best practices rules validate correctly
- Rules loader handles YAML parsing errors gracefully

**Files to Create**:
- `tests/contract/test_cribl_api.py` (extend with US2 endpoints)
- `tests/integration/test_config_audit.py`
- `tests/integration/test_best_practices.py`
- `tests/unit/test_analyzers/test_config_audit.py`
- `tests/unit/test_analyzers/test_best_practices.py`
- `tests/unit/test_rules/test_loader.py`

---

## Batch 4: User Story 3 Tests - Sizing & Performance (Est. 60 min)

**Goal**: Test sizing, performance, and storage analyzers (already implemented)

**Prerequisites**: Batch 1 complete, SizingAnalyzer, PerformanceAnalyzer, StorageAnalyzer implemented

### Tasks (20 tasks)

**Integration Tests**:
- [ ] T086 - [P] [US3] Write integration test for sizing analysis in `tests/integration/test_sizing.py`
- [ ] T087 - [P] [US3] Write integration test for performance analysis in `tests/integration/test_performance.py`

**Unit Tests** (can run in parallel):
- [ ] T094 - [P] [US3] Write unit tests for SizingAnalyzer in `tests/unit/test_analyzers/test_sizing.py`
- [ ] T099 - [P] [US3] Write unit tests for PerformanceAnalyzer in `tests/unit/test_analyzers/test_performance.py`
- [ ] T104 - [P] [US3] Write unit tests for StorageAnalyzer in `tests/unit/test_analyzers/test_storage.py`

**Success Criteria**:
- Test over-provisioning detection (CPU <30%, memory <40%)
- Test under-provisioning detection (CPU >80%, memory >75%)
- Test inefficient function detection
- Test storage optimization recommendations with ROI calculations

**Files to Create**:
- `tests/integration/test_sizing.py`
- `tests/integration/test_performance.py`
- `tests/unit/test_analyzers/test_sizing.py`
- `tests/unit/test_analyzers/test_performance.py`
- `tests/unit/test_analyzers/test_storage.py`

---

## Batch 5: User Story 4-5 Tests - Security & Cost (Est. 45 min)

**Goal**: Test security and cost analyzers (already implemented)

**Prerequisites**: Batch 1 complete, SecurityAnalyzer and CostAnalyzer implemented

### Tasks (13 tasks)

**Contract Tests**:
- [ ] T120 - [P] [US5] Write contract test for `/api/v1/license` endpoint

**Integration Tests**:
- [ ] T108 - [P] [US4] Write integration test for security analysis in `tests/integration/test_security.py`
- [ ] T121 - [P] [US5] Write integration test for cost analysis in `tests/integration/test_cost.py`

**Unit Tests** (can run in parallel):
- [ ] T116 - [P] [US4] Write unit tests for SecurityAnalyzer in `tests/unit/test_analyzers/test_security.py`
- [ ] T128 - [P] [US5] Write unit tests for CostAnalyzer in `tests/unit/test_analyzers/test_cost.py`

**Success Criteria**:
- Test TLS/mTLS validation
- Test secret scanning in configurations
- Test license consumption tracking
- Test cost forecasting algorithms

**Files to Create**:
- `tests/contract/test_cribl_api.py` (extend with license endpoint)
- `tests/integration/test_security.py`
- `tests/integration/test_cost.py`
- `tests/unit/test_analyzers/test_security.py`
- `tests/unit/test_analyzers/test_cost.py`

---

## Batch 6: User Story 6-7 Tests - Fleet & Predictive (Est. 45 min)

**Goal**: Test fleet management and predictive analytics (if implemented)

**Prerequisites**: Batch 1 complete, FleetAnalyzer and PredictiveAnalyzer implemented (if available)

### Tasks (15 tasks)

**Integration Tests**:
- [ ] T132 - [P] [US6] Write integration test for fleet analysis in `tests/integration/test_fleet.py`
- [ ] T142 - [P] [US7] Write integration test for predictive analysis in `tests/integration/test_predictive.py`

**Unit Tests** (can run in parallel):
- [ ] T138 - [P] [US6] Write unit tests for FleetAnalyzer in `tests/unit/test_analyzers/test_fleet.py`
- [ ] T151 - [P] [US7] Write unit tests for PredictiveAnalyzer in `tests/unit/test_analyzers/test_predictive.py`
- [ ] T152 - [P] [US7] Write unit tests for storage implementations in `tests/unit/test_storage/`

**Success Criteria**:
- Test multi-deployment orchestration
- Test cross-environment comparison
- Test capacity exhaustion predictions
- Test anomaly detection algorithms

**Files to Create**:
- `tests/integration/test_fleet.py`
- `tests/integration/test_predictive.py`
- `tests/unit/test_analyzers/test_fleet.py`
- `tests/unit/test_analyzers/test_predictive.py`
- `tests/unit/test_storage/*.py`

---

## Batch 7: Polish Tests - Additional Analyzers & Validation (Est. 45 min)

**Goal**: Test remaining analyzers and perform final validation

**Prerequisites**: Previous batches complete

### Tasks (24 tasks)

**Unit Tests** (can run in parallel):
- [ ] T160 - [P] Write unit tests for all report formatters in `tests/unit/test_core/test_report_generator.py`
- [ ] T166 - [P] Write unit tests for Objectives 8, 10-13 analyzers in `tests/unit/test_analyzers/`
  - DisasterRecoveryAnalyzer
  - DataQualityAnalyzer
  - ChangeImpactAnalyzer
  - BenchmarkingAnalyzer
  - DocumentationAnalyzer

**Integration Tests**:
- [ ] T167 - [P] Add quickstart validation tests in `tests/integration/test_quickstart.py` (verify 5-minute first run goal)
- [ ] T179 - Run end-to-end integration test suite against all user stories

**Validation Tasks**:
- [ ] T172 - Performance optimization: ensure <5 min analysis, <100 API calls (run benchmarks)
- [ ] T173 - Security hardening: run bandit security scanner, fix any issues
- [ ] T174 - Dependency vulnerability scan: run pip-audit and safety, update dependencies
- [ ] T175 - Final validation against constitution: verify all 12 principles still pass
- [ ] T176 - Validate 80%+ code coverage target achieved (pytest-cov report)
- [ ] T180 - Performance validation: confirm <5 min, <100 API calls, <30 sec report generation

**Success Criteria**:
- All report formats tested (JSON, Markdown, HTML, YAML)
- All analyzers achieve 80%+ coverage
- Performance benchmarks met
- Security scan passes
- No dependency vulnerabilities
- Constitution compliance verified

**Files to Create**:
- `tests/unit/test_core/test_report_generator.py` (extend)
- `tests/unit/test_analyzers/test_disaster_recovery.py`
- `tests/unit/test_analyzers/test_data_quality.py`
- `tests/unit/test_analyzers/test_change_impact.py`
- `tests/unit/test_analyzers/test_benchmarking.py`
- `tests/unit/test_analyzers/test_documentation.py`
- `tests/integration/test_quickstart.py`

---

## Batch Execution Strategy

### Recommended Approach: Sequential

Execute batches in order to build test foundation progressively:

1. **Batch 1** → Foundation (utils, core infrastructure)
2. **Batch 2** → US1 tests (health assessment - MVP)
3. **Batch 3** → US2 tests (config validation)
4. **Batch 4** → US3 tests (sizing/performance)
5. **Batch 5** → US4-5 tests (security/cost)
6. **Batch 6** → US6-7 tests (fleet/predictive) - *if implemented*
7. **Batch 7** → Polish and validation

### Alternative Approach: Parallel

If multiple developers available:
- Developer A: Batch 1 (blocking, must complete first)
- After Batch 1:
  - Developer B: Batch 2 (US1 tests)
  - Developer C: Batch 3 (US2 tests)
  - Developer D: Batch 4 (US3 tests)
  - Developer E: Batch 5 (US4-5 tests)
- Developer A: Batch 7 (validation) - after all others complete

---

## Notes

- **TDD Principle**: We're backfilling tests for already-implemented code. Normally tests would be written FIRST.
- **Focus on Coverage**: All batches target 80%+ code coverage as required by constitution
- **Realistic Estimates**: Each batch estimated for 30-60 minutes of focused work
- **Parallel Opportunities**: Tasks marked [P] can run concurrently to save time
- **Graceful Degradation**: If analyzers aren't implemented yet (US6-7), skip those batches
- **Budget-Friendly**: Batches designed to fit within typical usage budgets

---

## Current Status Summary

**Completed** (19 tasks):
- ✅ Phase 1: Setup (T001-T008)
- ✅ Phase 2: Foundational Models (T009-T018)
- ✅ T019: Some model tests exist

**Not Completed** (161 tasks):
- ❌ T020-T180: All remaining tasks

**Core Functionality Status**:
- ✅ Web GUI: Working
- ✅ TUI: Working
- ✅ CLI: Working
- ✅ Analyzers: Implemented (health, config, performance, security)
- ❌ Tests: Mostly missing (need comprehensive test suite)

**Recommendation**: Start with Batch 1 to establish test foundation, then proceed sequentially through user story tests.
