# Tasks: Cribl Health Check Core

**Input**: Design documents from `/specs/001-health-check-core/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: MANDATORY per Constitution Principle IX (Test-Driven Development). All tests MUST be written BEFORE implementation (Red-Green-Refactor cycle).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root
- Paths shown below follow plan.md structure: `src/cribl_hc/`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Create Python package structure with src/cribl_hc/ directory
- [X] T002 Initialize pyproject.toml with Python 3.11+ and dependencies (httpx, pydantic, typer, rich, structlog)
- [X] T003 [P] Create .gitignore for Python project (__pycache__, *.pyc, .pytest_cache, dist/, build/)
- [X] T004 [P] Configure pytest in pyproject.toml with pytest-asyncio and pytest-cov plugins
- [X] T005 [P] Create tests/ directory structure (unit/, integration/, contract/, conftest.py)
- [X] T006 [P] Create src/cribl_hc/__init__.py with package metadata
- [X] T007 [P] Create README.md with installation and quick start instructions
- [X] T008 [P] Create requirements.txt and requirements-dev.txt for development dependencies

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T009 Create Pydantic models directory in src/cribl_hc/models/__init__.py
- [ ] T010 [P] Create Deployment model in src/cribl_hc/models/deployment.py with validation (id, url, auth_token, environment_type)
- [ ] T011 [P] Create HealthScore model in src/cribl_hc/models/health.py with ComponentScore nested model
- [ ] T012 [P] Create Finding model in src/cribl_hc/models/finding.py with severity enum and remediation fields
- [ ] T013 [P] Create Recommendation model in src/cribl_hc/models/recommendation.py with ImpactEstimate nested model
- [ ] T014 [P] Create WorkerNode model in src/cribl_hc/models/worker.py with ResourceUtilization nested model
- [ ] T015 [P] Create ConfigurationElement model in src/cribl_hc/models/config.py with type enum and validation
- [ ] T016 [P] Create AnalysisRun model in src/cribl_hc/models/analysis.py aggregating all result entities
- [ ] T017 [P] Create Historical Trend model in src/cribl_hc/models/trend.py with DataPoint nested model
- [ ] T018 [P] Create BestPracticeRule model in src/cribl_hc/models/rule.py with validation logic field
- [ ] T019 Write unit tests for all Pydantic models in tests/unit/test_models/ ensuring validation works
- [ ] T020 Create utils directory in src/cribl_hc/utils/__init__.py
- [ ] T021 Implement structured logger in src/cribl_hc/utils/logger.py using structlog with JSON output for audit trail
- [ ] T022 Implement rate limiter in src/cribl_hc/utils/rate_limiter.py with exponential backoff (supports <100 API calls)
- [ ] T023 Implement credential encryption in src/cribl_hc/utils/crypto.py using cryptography Fernet
- [ ] T024 Implement Cribl version detection in src/cribl_hc/utils/version.py supporting N through N-2
- [ ] T025 [P] Write unit tests for logger in tests/unit/test_utils/test_logger.py
- [ ] T026 [P] Write unit tests for rate limiter in tests/unit/test_utils/test_rate_limiter.py
- [ ] T027 [P] Write unit tests for crypto in tests/unit/test_utils/test_crypto.py
- [ ] T028 [P] Write unit tests for version detection in tests/unit/test_utils/test_version.py
- [ ] T029 Create core directory in src/cribl_hc/core/__init__.py
- [ ] T030 Implement Cribl API client in src/cribl_hc/core/api_client.py with httpx AsyncClient, rate limiting, and error handling
- [ ] T031 Write integration tests for API client in tests/integration/test_api_client.py using respx to mock Cribl API
- [ ] T032 Write contract tests for Cribl API responses in tests/contract/test_cribl_api.py validating schema compliance
- [ ] T033 Create base analyzer interface in src/cribl_hc/analyzers/base.py defining analyze() method and objective name
- [ ] T034 Create analyzer directory structure src/cribl_hc/analyzers/__init__.py with registry pattern
- [ ] T035 Write unit tests for base analyzer in tests/unit/test_analyzers/test_base.py

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Quick Health Assessment (Priority: P1) 🎯 MVP

**Goal**: Generate overall health score (0-100) with worker health monitoring and critical issue identification

**Independent Test**: Run analysis against a Cribl Stream deployment, receive health score and prioritized findings within 5 minutes

### Tests for User Story 1 (TDD - Write FIRST, ensure they FAIL)

- [ ] T036 [P] [US1] Write contract test for /api/v1/system/status endpoint in tests/contract/test_cribl_api.py
- [ ] T037 [P] [US1] Write contract test for /api/v1/master/workers endpoint in tests/contract/test_cribl_api.py
- [ ] T038 [P] [US1] Write contract test for /api/v1/metrics endpoint in tests/contract/test_cribl_api.py
- [ ] T039 [P] [US1] Write integration test for health analysis workflow in tests/integration/test_health_analysis.py
- [ ] T040 [US1] Write end-to-end test in tests/integration/test_end_to_end.py for P1 MVP (mock Cribl API, verify health score calculation)

### Implementation for User Story 1

- [ ] T041 [P] [US1] Implement HealthAnalyzer in src/cribl_hc/analyzers/health.py fetching worker metrics and calculating health score
- [ ] T042 [US1] Implement health_scorer in src/cribl_hc/core/health_scorer.py with component scoring logic (workers, connectivity)
- [ ] T043 [US1] Implement worker health evaluation logic in health_scorer (CPU >90%, memory >90%, disk >90% = unhealthy)
- [ ] T044 [US1] Implement critical issue identification in health_scorer (flag critical/high severity findings)
- [ ] T045 [US1] Add remediation step generation for worker health issues with links to docs.cribl.io
- [ ] T046 [P] [US1] Write unit tests for HealthAnalyzer in tests/unit/test_analyzers/test_health.py
- [ ] T047 [P] [US1] Write unit tests for health_scorer in tests/unit/test_core/test_health_scorer.py
- [ ] T048 [US1] Implement analyzer orchestrator in src/cribl_hc/core/analyzer.py coordinating health analyzer execution
- [ ] T049 [US1] Add API call tracking to analyzer orchestrator (must stay under 100 calls)
- [ ] T050 [US1] Add partial result handling to analyzer for graceful degradation (Constitution Principle VI)
- [ ] T051 [P] [US1] Write unit tests for analyzer orchestrator in tests/unit/test_core/test_analyzer.py
- [ ] T052 [US1] Create CLI main entry point in src/cribl_hc/cli/main.py with typer app initialization
- [ ] T053 [US1] Implement analyze command in src/cribl_hc/cli/commands/analyze.py calling analyzer orchestrator
- [ ] T054 [US1] Implement rich terminal output in src/cribl_hc/cli/output.py formatting health score and findings
- [ ] T055 [US1] Implement config command in src/cribl_hc/cli/commands/config.py for credential management
- [ ] T056 [US1] Add credential storage using encrypted JSON files in ~/.cribl-hc/credentials.enc
- [ ] T057 [P] [US1] Write unit tests for CLI commands in tests/unit/test_cli/
- [ ] T058 [US1] Implement report generator in src/cribl_hc/core/report_generator.py with JSON formatter
- [ ] T059 [US1] Implement Markdown formatter in report_generator for human-readable output
- [ ] T060 [P] [US1] Write unit tests for report generator in tests/unit/test_core/test_report_generator.py
- [ ] T061 [US1] Add audit logging to all API calls using structured logger (Constitution Principle I)
- [ ] T062 [US1] Validate P1 meets performance targets: <5 min analysis, <100 API calls (SC-005, SC-008)

**Checkpoint**: At this point, User Story 1 (MVP) should be fully functional and independently testable

---

## Phase 4: User Story 2 - Configuration Validation & Best Practices (Priority: P2)

**Goal**: Detect configuration errors (syntax, logic, orphans, conflicts) and validate best practices compliance

**Independent Test**: Run configuration analysis against deployment with known issues, verify all detected with remediation guidance

### Tests for User Story 2 (TDD - Write FIRST, ensure they FAIL)

- [ ] T063 [P] [US2] Write contract test for /api/v1/m/{group}/pipelines endpoint in tests/contract/test_cribl_api.py
- [ ] T064 [P] [US2] Write contract test for /api/v1/m/{group}/routes endpoint in tests/contract/test_cribl_api.py
- [ ] T065 [P] [US2] Write contract test for /api/v1/m/{group}/outputs endpoint in tests/contract/test_cribl_api.py
- [ ] T066 [P] [US2] Write integration test for config audit workflow in tests/integration/test_config_audit.py
- [ ] T067 [US2] Write integration test for best practices validation in tests/integration/test_best_practices.py

### Implementation for User Story 2

- [ ] T068 [P] [US2] Implement ConfigAuditAnalyzer in src/cribl_hc/analyzers/config_audit.py fetching pipeline/route/destination configs
- [ ] T069 [US2] Implement syntax validation logic in config_audit analyzer (JSON schema validation for pipeline functions)
- [ ] T070 [US2] Implement logic error detection (pipelines dropping all data, routes never matching)
- [ ] T071 [US2] Implement orphaned config detection (pipelines/routes not referenced)
- [ ] T072 [US2] Implement conflicting route rule detection (overlapping filters, order-dependent outcomes)
- [ ] T073 [US2] Implement deprecated function detection with migration recommendations
- [ ] T074 [P] [US2] Write unit tests for ConfigAuditAnalyzer in tests/unit/test_analyzers/test_config_audit.py
- [ ] T075 [US2] Implement BestPracticesAnalyzer in src/cribl_hc/analyzers/best_practices.py
- [ ] T076 [US2] Create best practice rules loader in src/cribl_hc/rules/loader.py reading YAML rules
- [ ] T077 [US2] Create initial Cribl best practice rules in src/cribl_hc/rules/cribl_rules.yaml (10-15 rules)
- [ ] T078 [US2] Implement best practice validation engine applying rules to configurations
- [ ] T079 [US2] Implement compliance score calculation aggregating rule violations
- [ ] T080 [US2] Add documentation links to findings (docs.cribl.io URLs for each violation)
- [ ] T081 [P] [US2] Write unit tests for BestPracticesAnalyzer in tests/unit/test_analyzers/test_best_practices.py
- [ ] T082 [P] [US2] Write unit tests for rules loader in tests/unit/test_rules/test_loader.py
- [ ] T083 [US2] Integrate config audit and best practices analyzers into analyzer orchestrator
- [ ] T084 [US2] Add config objective support to CLI analyze command (--objectives config)
- [ ] T085 [US2] Validate US2 independently: configuration analysis works standalone without US1

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Sizing & Performance Optimization (Priority: P3)

**Goal**: Assess worker sizing (over/under-provisioned), recommend scaling strategies, identify performance bottlenecks

**Independent Test**: Analyze deployment with known sizing issues, verify recommendations with cost/performance impact estimates

### Tests for User Story 3 (TDD - Write FIRST, ensure they FAIL)

- [ ] T086 [P] [US3] Write integration test for sizing analysis in tests/integration/test_sizing.py
- [ ] T087 [P] [US3] Write integration test for performance analysis in tests/integration/test_performance.py

### Implementation for User Story 3

- [ ] T088 [P] [US3] Implement SizingAnalyzer in src/cribl_hc/analyzers/sizing.py analyzing worker resource utilization
- [ ] T089 [US3] Implement over-provisioning detection (CPU <30%, memory <40% consistently)
- [ ] T090 [US3] Implement under-provisioning detection (CPU >80%, memory >75% sustained)
- [ ] T091 [US3] Implement optimal worker count calculator based on throughput and resource usage
- [ ] T092 [US3] Implement horizontal vs vertical scaling recommendations
- [ ] T093 [US3] Add cost implications to scaling recommendations (when pricing data available)
- [ ] T094 [P] [US3] Write unit tests for SizingAnalyzer in tests/unit/test_analyzers/test_sizing.py
- [ ] T095 [P] [US3] Implement PerformanceAnalyzer in src/cribl_hc/analyzers/performance.py
- [ ] T096 [US3] Implement inefficient function detection (expensive regex, lookups without optimization)
- [ ] T097 [US3] Implement function ordering recommendations (filters first, expensive ops last)
- [ ] T098 [US3] Implement duplicate processing logic detection across pipelines
- [ ] T099 [P] [US3] Write unit tests for PerformanceAnalyzer in tests/unit/test_analyzers/test_performance.py
- [ ] T100 [P] [US3] Implement StorageAnalyzer in src/cribl_hc/analyzers/storage.py calculating consumption by destination
- [ ] T101 [US3] Implement data reduction opportunity identification (sampling, filtering, aggregation candidates)
- [ ] T102 [US3] Implement ROI calculation for storage optimizations (GB saved, dollars saved, effort estimate)
- [ ] T103 [US3] Add before/after projections to storage recommendations
- [ ] T104 [P] [US3] Write unit tests for StorageAnalyzer in tests/unit/test_analyzers/test_storage.py
- [ ] T105 [US3] Integrate sizing, performance, and storage analyzers into orchestrator
- [ ] T106 [US3] Add sizing and performance objectives to CLI (--objectives sizing,performance,storage)
- [ ] T107 [US3] Validate US3 independently: optimization analysis works without US1/US2

**Checkpoint**: User Stories 1, 2, AND 3 should all work independently

---

## Phase 6: User Story 4 - Security & Compliance Validation (Priority: P4)

**Goal**: Validate TLS/mTLS configs, detect exposed secrets, check authentication, assess audit logging, validate RBAC

**Independent Test**: Run security analysis against deployment with known security gaps, verify all detected with remediation

### Tests for User Story 4 (TDD - Write FIRST, ensure they FAIL)

- [ ] T108 [P] [US4] Write integration test for security analysis in tests/integration/test_security.py

### Implementation for User Story 4

- [ ] T109 [P] [US4] Implement SecurityAnalyzer in src/cribl_hc/analyzers/security.py
- [ ] T110 [US4] Implement TLS/mTLS configuration validation (check encryption strength, certificate validity)
- [ ] T111 [US4] Implement secret scanning in configurations (detect exposed credentials, API keys)
- [ ] T112 [US4] Implement authentication mechanism validation for destinations and inputs
- [ ] T113 [US4] Implement audit logging coverage assessment
- [ ] T114 [US4] Implement RBAC validation (check role definitions, assignments)
- [ ] T115 [US4] Calculate security posture score aggregating findings
- [ ] T116 [P] [US4] Write unit tests for SecurityAnalyzer in tests/unit/test_analyzers/test_security.py
- [ ] T117 [US4] Integrate security analyzer into orchestrator
- [ ] T118 [US4] Add security objective to CLI (--objectives security)
- [ ] T119 [US4] Validate US4 independently: security analysis works standalone

**Checkpoint**: User Stories 1-4 should all work independently

---

## Phase 7: User Story 5 - Cost & License Management (Priority: P5)

**Goal**: Track license consumption, predict exhaustion, calculate TCO, forecast costs

**Independent Test**: Analyze license consumption, verify exhaustion predictions and cost breakdowns

### Tests for User Story 5 (TDD - Write FIRST, ensure they FAIL)

- [ ] T120 [P] [US5] Write contract test for /api/v1/license endpoint in tests/contract/test_cribl_api.py
- [ ] T121 [P] [US5] Write integration test for cost analysis in tests/integration/test_cost.py

### Implementation for User Story 5

- [ ] T122 [P] [US5] Implement CostAnalyzer in src/cribl_hc/analyzers/cost.py
- [ ] T123 [US5] Implement license consumption tracking vs allocation
- [ ] T124 [US5] Implement license exhaustion prediction using linear regression on historical trends
- [ ] T125 [US5] Implement TCO calculation per destination (when pricing data configured)
- [ ] T126 [US5] Implement cost comparison across destinations
- [ ] T127 [US5] Implement future cost forecasting based on growth trends
- [ ] T128 [P] [US5] Write unit tests for CostAnalyzer in tests/unit/test_analyzers/test_cost.py
- [ ] T129 [US5] Integrate cost analyzer into orchestrator
- [ ] T130 [US5] Add cost objective to CLI (--objectives cost)
- [ ] T131 [US5] Validate US5 independently: cost analysis works standalone

**Checkpoint**: User Stories 1-5 should all work independently

---

## Phase 8: User Story 6 - Fleet & Multi-Tenancy Management (Priority: P6)

**Goal**: Analyze multiple deployments in single report, compare metrics across environments, identify fleet-wide patterns

**Independent Test**: Run fleet analysis against dev/staging/prod, verify aggregation and comparison

### Tests for User Story 6 (TDD - Write FIRST, ensure they FAIL)

- [ ] T132 [P] [US6] Write integration test for fleet analysis in tests/integration/test_fleet.py

### Implementation for User Story 6

- [ ] T133 [P] [US6] Implement FleetAnalyzer in src/cribl_hc/analyzers/fleet.py
- [ ] T134 [US6] Implement multi-deployment orchestration (parallel analysis of multiple deployments)
- [ ] T135 [US6] Implement cross-environment comparison logic (dev vs staging vs prod metrics)
- [ ] T136 [US6] Implement fleet-wide pattern detection (common issues, configuration patterns)
- [ ] T137 [US6] Implement aggregated reporting for fleet analysis
- [ ] T138 [P] [US6] Write unit tests for FleetAnalyzer in tests/unit/test_analyzers/test_fleet.py
- [ ] T139 [US6] Add fleet command to CLI in src/cribl_hc/cli/commands/fleet.py
- [ ] T140 [US6] Implement fleet report generation with side-by-side comparisons
- [ ] T141 [US6] Validate US6 independently: fleet analysis works with multiple deployments configured

**Checkpoint**: User Stories 1-6 should all work independently

---

## Phase 9: User Story 7 - Predictive Analytics & Proactive Recommendations (Priority: P7)

**Goal**: Predict capacity exhaustion, forecast license consumption, detect anomalies, provide proactive recommendations

**Independent Test**: Analyze deployment with historical data, verify predictions and anomaly detection

### Tests for User Story 7 (TDD - Write FIRST, ensure they FAIL)

- [ ] T142 [P] [US7] Write integration test for predictive analysis in tests/integration/test_predictive.py

### Implementation for User Story 7

- [ ] T143 [P] [US7] Implement PredictiveAnalyzer in src/cribl_hc/analyzers/predictive.py
- [ ] T144 [US7] Implement optional historical data storage in src/cribl_hc/storage/json_store.py
- [ ] T145 [US7] Implement storage interface in src/cribl_hc/storage/base.py
- [ ] T146 [US7] Implement worker capacity exhaustion prediction using time series analysis
- [ ] T147 [US7] Implement license consumption forecasting
- [ ] T148 [US7] Implement destination backpressure prediction from throughput trends
- [ ] T149 [US7] Implement anomaly detection using statistical methods (z-score, moving average)
- [ ] T150 [US7] Implement proactive scaling recommendations with lead time estimates
- [ ] T151 [P] [US7] Write unit tests for PredictiveAnalyzer in tests/unit/test_analyzers/test_predictive.py
- [ ] T152 [P] [US7] Write unit tests for storage implementations in tests/unit/test_storage/
- [ ] T153 [US7] Integrate predictive analyzer into orchestrator
- [ ] T154 [US7] Add predictive objective to CLI (--objectives predictive)
- [ ] T155 [US7] Add history command to CLI for viewing trends
- [ ] T156 [US7] Validate US7 independently: predictive analysis works with historical data

**Checkpoint**: All user stories should now be independently functional

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T157 [P] Implement HTML report formatter in report_generator
- [ ] T158 [P] Implement YAML report formatter in report_generator
- [ ] T159 [P] Add report command to CLI for generating reports post-analysis
- [ ] T160 [P] Write unit tests for all report formatters in tests/unit/test_core/test_report_generator.py
- [ ] T161 [P] Implement DisasterRecoveryAnalyzer in src/cribl_hc/analyzers/disaster_recovery.py (Objective 8)
- [ ] T162 [P] Implement DataQualityAnalyzer in src/cribl_hc/analyzers/data_quality.py (Objective 10)
- [ ] T163 [P] Implement ChangeImpactAnalyzer in src/cribl_hc/analyzers/change_impact.py (Objective 11)
- [ ] T164 [P] Implement BenchmarkingAnalyzer in src/cribl_hc/analyzers/benchmarking.py (Objective 12)
- [ ] T165 [P] Implement DocumentationAnalyzer in src/cribl_hc/analyzers/documentation.py (Objective 13)
- [ ] T166 [P] Write unit tests for Objectives 8, 10-13 analyzers in tests/unit/test_analyzers/
- [ ] T167 [P] Add quickstart validation tests in tests/integration/test_quickstart.py (verify 5-minute first run goal)
- [ ] T168 [P] Implement validate command in CLI for testing credentials and connectivity
- [ ] T169 Code cleanup and refactoring for consistency
- [ ] T170 [P] Add comprehensive docstrings to all public APIs
- [ ] T171 [P] Generate API documentation using Sphinx or mkdocs
- [ ] T172 Performance optimization: ensure <5 min analysis, <100 API calls (run benchmarks)
- [ ] T173 Security hardening: run bandit security scanner, fix any issues
- [ ] T174 Dependency vulnerability scan: run pip-audit and safety, update dependencies
- [ ] T175 Final validation against constitution: verify all 12 principles still pass
- [ ] T176 Validate 80%+ code coverage target achieved (pytest-cov report)
- [ ] T177 Create package distribution: build wheel and sdist for PyPI
- [ ] T178 Test installation from built package (pip install ./dist/cribl_health_check-*.whl)
- [ ] T179 Run end-to-end integration test suite against all user stories
- [ ] T180 Performance validation: confirm <5 min, <100 API calls, <30 sec report generation

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-9)**: All depend on Foundational phase completion
  - User stories CAN proceed in parallel (if staffed) after Foundational completes
  - Or sequentially in priority order (P1 → P2 → P3 → P4 → P5 → P6 → P7)
- **Polish (Phase 10)**: Depends on desired user stories being complete (at minimum, US1 for MVP)

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Independent of US1
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Independent of US1/US2
- **User Story 4 (P4)**: Can start after Foundational (Phase 2) - Independent of US1/US2/US3
- **User Story 5 (P5)**: Can start after Foundational (Phase 2) - Independent of prior stories
- **User Story 6 (P6)**: Can start after Foundational (Phase 2) - Uses US1 analyzer but independently testable
- **User Story 7 (P7)**: Can start after Foundational (Phase 2) - Requires historical storage but independently testable

### Within Each User Story

- **TDD Requirement**: Tests MUST be written FIRST and FAIL before implementation
- Models (from Foundational phase) → Analyzers → Integration with Orchestrator → CLI Commands
- Contract tests → Integration tests → Unit tests → Implementation
- Each story should complete and be independently testable before moving to next

### Parallel Opportunities

**Phase 1 (Setup)**: All tasks marked [P] can run in parallel
- T003, T004, T005, T006, T007, T008 can all run simultaneously

**Phase 2 (Foundational)**: Many tasks marked [P] can run in parallel within sub-phases
- All Pydantic models (T010-T018) can be created in parallel
- All utility implementations (T025-T028 tests) can run in parallel after their code is written
- Model unit tests (T019) depends on models being created but all can run in parallel

**Phase 3 (US1)**: Contract tests (T036, T037, T038) can run in parallel, many implementation tasks marked [P]
- Health analyzer, health scorer unit tests can run in parallel
- CLI and report generator can be developed in parallel

**Phase 4-9 (US2-US7)**: Each user story is independently parallelizable
- If you have 7 developers, each can take one user story after Foundational completes
- Within each story, tests can run in parallel, implementation tasks marked [P] can run in parallel

**Phase 10 (Polish)**: Most tasks marked [P] can run in parallel
- Report formatters (T157, T158) can run in parallel
- Remaining objective analyzers (T161-T165) can run in parallel
- Documentation and security tasks can run in parallel

---

## Parallel Example: User Story 1

```bash
# After Foundational phase completes, launch all US1 contract tests together:
Task T036: "Write contract test for /api/v1/system/status"
Task T037: "Write contract test for /api/v1/master/workers"
Task T038: "Write contract test for /api/v1/metrics"

# After tests written and failing, launch parallel implementation:
Task T041: "Implement HealthAnalyzer in src/cribl_hc/analyzers/health.py"
Task T046: "Write unit tests for HealthAnalyzer"
Task T047: "Write unit tests for health_scorer"

# CLI and report generation can also proceed in parallel:
Task T052: "Create CLI main entry point"
Task T058: "Implement report generator"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T008)
2. Complete Phase 2: Foundational (T009-T035) - CRITICAL BLOCKER
3. Complete Phase 3: User Story 1 (T036-T062)
4. **STOP and VALIDATE**: Test User Story 1 independently
   - Run `cribl-hc analyze --deployment test --objectives health`
   - Verify health score generation, findings output, <5 min, <100 API calls
   - Verify tests pass with 80%+ coverage for US1 code
5. Deploy/demo MVP if ready

**MVP Deliverable**: Working health check tool that:
- Connects to Cribl API (read-only)
- Calculates health score (0-100)
- Identifies critical issues
- Generates reports (JSON, Markdown)
- Completes in <5 minutes
- Uses <100 API calls

### Incremental Delivery (Recommended)

1. Complete Setup + Foundational → Foundation ready (T001-T035)
2. **Sprint 1**: Add User Story 1 (T036-T062) → Test independently → Deploy/Demo (MVP!)
3. **Sprint 2**: Add User Story 2 (T063-T085) → Test independently → Deploy/Demo (MVP + Config Validation)
4. **Sprint 3**: Add User Story 3 (T086-T107) → Test independently → Deploy/Demo (+ Optimization)
5. **Sprint 4**: Add User Stories 4-5 (T108-T131) → Test independently → Deploy/Demo (+ Security + Cost)
6. **Sprint 5**: Add User Stories 6-7 (T132-T156) → Test independently → Deploy/Demo (+ Fleet + Predictive)
7. **Sprint 6**: Polish (T157-T180) → Full feature set complete

Each sprint delivers working, testable increment that adds value.

### Parallel Team Strategy

With multiple developers (after Foundational phase completes):

1. **Team completes Setup + Foundational together** (T001-T035)
2. **Once Foundational is done, split into parallel tracks**:
   - Developer A: User Story 1 (T036-T062) - MVP
   - Developer B: User Story 2 (T063-T085) - Config Validation
   - Developer C: User Story 3 (T086-T107) - Optimization
   - Developer D: User Stories 4-5 (T108-T131) - Security + Cost
   - Developer E: User Stories 6-7 (T132-T156) - Fleet + Predictive
3. Stories complete and integrate independently
4. Team collaborates on Polish phase (T157-T180)

---

## Notes

- **TDD Mandatory**: Constitution Principle IX requires tests BEFORE implementation (Red-Green-Refactor)
- **80% Coverage Target**: All modules must achieve 80%+ code coverage
- **Integration Tests**: ALL Cribl API interactions must have integration tests
- **[P] tasks**: Different files, no dependencies - safe to parallelize
- **[Story] label**: Maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests FAIL before implementing (Red phase of TDD)
- Commit after each task or logical group of related tasks
- Stop at any checkpoint to validate story independently
- **Performance Validation**: Continuously verify <5 min, <100 API calls throughout development
- **Constitution Compliance**: Re-check all 12 principles after each major phase

---

## Task Count Summary

- **Phase 1 (Setup)**: 8 tasks
- **Phase 2 (Foundational)**: 27 tasks (BLOCKING)
- **Phase 3 (US1 - MVP)**: 27 tasks
- **Phase 4 (US2)**: 23 tasks
- **Phase 5 (US3)**: 22 tasks
- **Phase 6 (US4)**: 12 tasks
- **Phase 7 (US5)**: 12 tasks
- **Phase 8 (US6)**: 10 tasks
- **Phase 9 (US7)**: 15 tasks
- **Phase 10 (Polish)**: 24 tasks

**Total**: 180 tasks

**Parallel Opportunities**: 87 tasks marked [P] can run in parallel with other tasks
**Independent User Stories**: 7 user stories can be developed independently after Foundational phase
**MVP Scope**: 62 tasks (Setup + Foundational + US1)
