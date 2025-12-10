# Technology Research & Decisions: Cribl Health Check Core

**Feature**: 001-health-check-core
**Date**: 2025-12-10
**Status**: Complete

## Overview

This document captures all technology and architectural decisions made for the Cribl Health Check Core tool. All decisions are aligned with the project constitution principles and functional requirements from [spec.md](./spec.md).

## Decision Summary

| Decision | Choice | Rationale | Constitution Alignment |
|----------|--------|-----------|----------------------|
| Language | Python 3.11+ | Rich ecosystem, Cribl admin familiarity, async support | All principles |
| HTTP Client | httpx | Async support, performance, < 100 API call budget | VII (Performance) |
| CLI Framework | typer + rich | Modern, type-safe, beautiful output | II (Actionability) |
| Data Validation | pydantic | Strong typing, JSON serialization, clear errors | VI (Graceful Degradation) |
| Testing | pytest + pytest-asyncio + respx | TDD support, async, HTTP mocking, coverage | IX (TDD) |
| Storage | JSON files (optional) | Stateless default, air-gapped support | IV, V (Minimal Data, Stateless) |
| Credentials | cryptography (Fernet) | Strong encryption, cross-platform | X (Security) |
| Rate Limiting | Custom with backoff | Cribl-specific, exponential backoff | VII (Performance) |
| Reporting | Multi-format (JSON/YAML/MD/HTML) | Programmatic + human-readable | II, III (Actionability, API-First) |
| Logging | structlog (JSON) | Structured audit trail, performance | I (Read-Only audit) |

## Detailed Technology Decisions

### 1. Programming Language: Python 3.11+

**Decision**: Use Python 3.11 or newer as the implementation language

**Rationale**:
1. **Ecosystem Fit**: Excellent HTTP/API client libraries (httpx with native async/await)
2. **CLI Tooling**: Rich ecosystem for CLI development (typer, rich, click)
3. **Data Validation**: Strong libraries like Pydantic for complex data modeling
4. **Target Audience**: Cribl administrators commonly use Python for automation and scripting
5. **Cross-Platform**: Native support for Linux, macOS, and Windows without modification
6. **Distribution**: Easy packaging via PyPI, pip install, and standalone executables (PyInstaller/PyOxidizer)
7. **Modern Features**: Python 3.11+ provides performance improvements and better async support

**Alternatives Considered**:
- **Go**:
  - Pros: Better performance, single binary distribution, strong concurrency
  - Cons: Weaker data validation libraries, less familiar to Cribl admin community, longer development time for complex data analysis
  - Rejected: Python ecosystem better matches user workflows

- **TypeScript/Node.js**:
  - Pros: Good async support, familiar to web developers, npm packaging
  - Cons: Weaker data validation, less common in enterprise ops tooling, heavier runtime
  - Rejected: Python more aligned with target user base

- **Rust**:
  - Pros: Best performance and safety guarantees, no runtime, single binary
  - Cons: Steep learning curve, longer development time, harder to find contributors
  - Rejected: Development velocity and maintainability prioritized over raw performance

**Constitution Alignment**:
- Supports all 12 principles
- Particularly strong for TDD (Principle IX) with pytest ecosystem
- Excellent library support for API-first design (Principle III)

### 2. HTTP Client: httpx

**Decision**: Use httpx for all Cribl API interactions

**Rationale**:
1. **Async Support**: Native async/await with `AsyncClient` for parallel API calls
2. **Performance**: Connection pooling and keepalive reduce overhead critical for < 100 API call budget (Principle VII)
3. **Familiar API**: requests-compatible interface familiar to Python developers
4. **Error Handling**: Excellent error handling and retry mechanisms
5. **HTTP/2**: Support for HTTP/2 multiplexing (future optimization)
6. **Well-Maintained**: Active development, strong community support

**Alternatives Considered**:
- **requests**:
  - Pros: Most popular, very stable, well-documented
  - Cons: Synchronous only, would require threading/multiprocessing for parallelism
  - Rejected: Performance requirements demand async for parallel API calls

- **aiohttp**:
  - Pros: Mature async library, performant
  - Cons: More complex API, less familiar to developers used to requests
  - Rejected: httpx provides better developer experience with requests-like API

**Constitution Alignment**:
- **Principle VII (Performance Efficiency)**: Async enables parallel calls to meet < 100 API call budget
- **Principle VI (Graceful Degradation)**: Excellent error handling for partial failures

### 3. CLI Framework: typer + rich

**Decision**: Use typer for CLI framework and rich for terminal output formatting

**Rationale**:
1. **typer**:
   - Modern CLI framework with automatic help generation
   - Type hints for parameter validation
   - Subcommand support for `cribl-hc analyze`, `cribl-hc report`, etc.
   - Auto-completion support (Bash, Zsh, Fish)

2. **rich**:
   - Beautiful terminal output with tables, progress bars, syntax highlighting
   - Aligns with Actionability First principle (clear, visual recommendations)
   - Makes findings easy to scan and understand
   - Supports markdown rendering in terminal

**Alternatives Considered**:
- **click**:
  - Pros: Very popular, mature, well-documented
  - Cons: Less type-safe than typer, more verbose
  - Rejected: typer provides modern Python experience with better type safety

- **argparse (stdlib)**:
  - Pros: No external dependency, standard library
  - Cons: Verbose, requires more boilerplate, manual help formatting
  - Rejected: Developer productivity and user experience matter more than avoiding dependencies

**Constitution Alignment**:
- **Principle II (Actionability First)**: rich output makes recommendations clear and scannable
- **Principle III (API-First)**: typer CLI wraps library functions cleanly

### 4. Data Validation: pydantic

**Decision**: Use Pydantic for all data modeling and validation

**Rationale**:
1. **Type Safety**: Strong runtime validation with Python type hints
2. **Automatic Serialization**: JSON serialization/deserialization out of the box
3. **Clear Errors**: Validation errors include clear messages for troubleshooting (Graceful Degradation)
4. **Wide Adoption**: Standard in FastAPI, used by many API projects
5. **Entity Modeling**: Perfect fit for our 9 key entities (Deployment, HealthScore, Finding, etc.)

**Alternatives Considered**:
- **marshmallow**:
  - Pros: More flexible for complex transformations
  - Cons: More verbose schema definitions, less type-safe
  - Rejected: Pydantic's simplicity and type safety win for our use case

- **dataclasses + manual validation**:
  - Pros: Stdlib, less boilerplate
  - Cons: Manual validation logic error-prone, no automatic JSON handling
  - Rejected: Safety and productivity matter more than avoiding dependencies

**Constitution Alignment**:
- **Principle VI (Graceful Degradation)**: Clear validation errors help with debugging
- **Principle XII (Transparent Methodology)**: Type hints make data contracts explicit

### 5. Testing Framework: pytest + pytest-asyncio + respx

**Decision**: Use pytest ecosystem for all testing

**Rationale**:
1. **pytest**: Python standard for testing with excellent fixture support and assertions
2. **pytest-asyncio**: Handles async test cases needed for httpx client testing
3. **respx**: Mock HTTP requests for integration tests without hitting real Cribl API
4. **pytest-cov**: Coverage reporting to enforce 80%+ target (Principle IX)
5. **pytest-xdist**: Parallel test execution for faster CI/CD

**Alternatives Considered**:
- **unittest (stdlib)**:
  - Pros: No dependencies, standard library
  - Cons: More verbose, weaker fixtures, less expressive assertions
  - Rejected: pytest productivity win justifies dependency

- **responses** (HTTP mocking):
  - Pros: Popular, well-documented
  - Cons: Weaker async support compared to respx
  - Rejected: respx better for async httpx mocking

**Constitution Alignment**:
- **Principle IX (TDD)**: Comprehensive test support enforces TDD workflow and 80%+ coverage
- **Principle IX**: Integration tests for ALL Cribl API interactions as required

### 6. Storage: Optional Local JSON Files

**Decision**: No mandatory persistence; optional JSON file storage for historical trending

**Rationale**:
1. **Stateless by Default**: Aligns with Constitution Principle V (Stateless Analysis)
2. **Simple**: JSON files are human-readable and debuggable
3. **No Dependencies**: No database installation or management required
4. **Air-Gapped Support**: Works in environments without external connectivity (Principle IV)
5. **Optional**: Historical trending is optional per FR-004, FR-021
6. **Configurable Retention**: User controls data retention policies

**Alternatives Considered**:
- **SQLite**:
  - Pros: More structured queries, ACID guarantees
  - Cons: Adds persistence complexity, violates stateless principle
  - Rejected: Stateless principle takes priority

- **PostgreSQL/MySQL**:
  - Pros: Robust, scalable, strong querying
  - Cons: Massive overkill, requires separate database service, violates stateless and minimal data principles
  - Rejected: Way too complex for optional trending

**Constitution Alignment**:
- **Principle V (Stateless Analysis)**: Each run is independent, no mandatory state
- **Principle IV (Minimal Data Collection)**: No external data transmission, configurable retention
- **Principle IV**: Air-gapped deployment support

### 7. Credential Management: cryptography (Fernet)

**Decision**: Use Python cryptography library with Fernet symmetric encryption for API token storage

**Rationale**:
1. **Strong Encryption**: Fernet provides authenticated encryption (AES-128-CBC + HMAC)
2. **Simple API**: Easy key derivation from master password
3. **Well-Audited**: Standard Python library, security-vetted
4. **Cross-Platform**: Works consistently across Linux, macOS, Windows
5. **Encrypted Files**: Stores encrypted credentials in `~/.cribl-hc/credentials.enc`
6. **Air-Gapped**: No external service dependencies

**Alternatives Considered**:
- **keyring library**:
  - Pros: Uses OS-specific secure storage (macOS Keychain, Windows Credential Manager)
  - Cons: Inconsistent behavior across platforms, harder in air-gapped environments
  - Rejected: Need consistent cross-platform behavior

- **Plaintext config**:
  - Pros: Simple, no encryption overhead
  - Cons: VIOLATES Security by Design principle (X)
  - Rejected: Constitution violation

**Constitution Alignment**:
- **Principle X (Security by Design)**: Encrypted storage mandated, no plaintext credentials
- **Principle IV (Minimal Data Collection)**: Works offline in air-gapped environments

### 8. Rate Limiting: Custom Implementation with Exponential Backoff

**Decision**: Implement custom rate limiter using asyncio primitives with exponential backoff

**Rationale**:
1. **Cribl-Specific**: Cribl rate limits vary by Cloud vs self-hosted deployment
2. **Exponential Backoff**: Prevents thundering herd when hitting limits
3. **Simple**: ~50 lines of code, no external dependency overhead
4. **Flexible**: Configurable limits per deployment type
5. **Performance**: Aligns with Performance Efficiency principle (< 100 API calls)

**Implementation Approach**:
```python
class RateLimiter:
    def __init__(self, calls_per_second: int):
        self.calls_per_second = calls_per_second
        self.semaphore = asyncio.Semaphore(calls_per_second)

    async def acquire(self, retry_count: int = 0):
        async with self.semaphore:
            await asyncio.sleep(1 / self.calls_per_second)
            if retry_count > 0:
                backoff = min(2 ** retry_count, 32)  # Max 32 seconds
                await asyncio.sleep(backoff)
```

**Alternatives Considered**:
- **pyrate-limiter**:
  - Pros: Feature-rich, battle-tested
  - Cons: Heavy dependency, more than we need
  - Rejected: Simple custom implementation sufficient

- **aiolimiter**:
  - Pros: async-native, well-designed
  - Cons: Less flexible for varying limits by deployment type
  - Rejected: Need more control for Cribl-specific behavior

**Constitution Alignment**:
- **Principle VII (Performance Efficiency)**: Critical for staying under 100 API call budget
- **Principle VII**: Respect API rate limits with backoff mandated

### 9. Report Generation: Multi-Format with Pluggable Architecture

**Decision**: Support multiple output formats (JSON, YAML, Markdown, HTML) with pluggable formatter design

**Rationale**:
1. **JSON**: Programmatic consumption, API integration (Principle III)
2. **YAML**: Configuration-style output, human-readable
3. **Markdown**: Documentation, GitHub/GitLab rendering, printable reports
4. **HTML**: Browser viewing with CSS styling, rich formatting
5. **Pluggable**: Easy to add CSV, PDF, or custom formats in future

**Architecture**:
```text
ReportFormatter (base class)
├── JSONFormatter
├── YAMLFormatter
├── MarkdownFormatter
└── HTMLFormatter
```

**Alternatives Considered**:
- **JSON only**:
  - Pros: Simple, universal
  - Cons: Too technical for administrators, violates Actionability principle
  - Rejected: Need human-readable formats

- **PDF generation** (WeasyPrint, ReportLab):
  - Pros: Professional reports, portable
  - Cons: Heavy dependencies (Cairo, Pango for WeasyPrint), complex
  - Decision: Deferred to Phase 2, HTML + print stylesheet sufficient for now

**Constitution Alignment**:
- **Principle II (Actionability First)**: Multiple formats ensure findings are accessible
- **Principle III (API-First)**: JSON output enables programmatic consumption

### 10. Logging & Audit Trail: structlog with JSON Output

**Decision**: Use structlog for structured logging with JSON formatting

**Rationale**:
1. **Structured**: Key-value logging for easy parsing by log aggregators (Splunk, ELK)
2. **Audit Trail**: Logs all API calls, timestamps, and outcomes (Principle I requirement)
3. **Performance**: Lazy formatting, minimal overhead
4. **Context**: Thread-local context for request tracing
5. **JSON Output**: Machine-readable for automation

**Example Log Entry**:
```json
{
  "timestamp": "2025-12-10T14:32:15.123Z",
  "level": "info",
  "event": "api_call",
  "method": "GET",
  "url": "/api/v1/system/status",
  "duration_ms": 145,
  "status_code": 200,
  "deployment_id": "prod-cribl",
  "correlation_id": "abc-123"
}
```

**Alternatives Considered**:
- **Standard logging library**:
  - Pros: Stdlib, no dependencies
  - Cons: Unstructured text, hard to parse, no JSON support
  - Rejected: Audit trail requires structured logging

- **loguru**:
  - Pros: Beautiful API, colored output
  - Cons: Less structured than structlog, harder to parse programmatically
  - Rejected: structlog better for audit requirements

**Constitution Alignment**:
- **Principle I (Read-Only by Default)**: Complete audit trail of all API access mandated
- **Principle VI (Graceful Degradation)**: Clear context for troubleshooting errors

## Architecture Patterns

### Pattern 1: Pluggable Analyzer Architecture

**Decision**: Each of the 15 objectives implemented as independent analyzer module inheriting from base analyzer interface

**Design**:
```python
class BaseAnalyzer(ABC):
    @abstractmethod
    async def analyze(self, deployment: Deployment, data: Dict) -> List[Finding]:
        pass

    @abstractmethod
    def get_objective_name(self) -> str:
        pass

class HealthAnalyzer(BaseAnalyzer):
    async def analyze(self, deployment, data):
        # Objective 1: Health Assessment
        findings = []
        # ... analysis logic
        return findings
```

**Rationale**:
- **Independence**: Each analyzer can be developed and tested separately
- **Pluggability**: Easy to add new objectives or disable specific analyzers
- **Parallel Execution**: Analyzers can run concurrently to meet performance targets
- **Testability**: Unit tests can mock individual analyzers

**Constitution Alignment**:
- **Principle VIII (Pluggable Architecture)**: Module-based design mandated
- **Principle IX (TDD)**: Independent analyzers easier to test

### Pattern 2: API-First Library Design

**Decision**: Core functionality in `cribl_hc` library package, CLI is thin wrapper

**Design**:
```python
# Library usage (Python)
from cribl_hc import Deployment, analyze_deployment

deployment = Deployment(url="...", token="...")
result = await analyze_deployment(deployment, objectives=["health", "config"])
print(result.health_score)

# CLI usage (wraps library)
$ cribl-hc analyze --deployment prod --objectives health,config
```

**Rationale**:
- **API-First**: All functionality accessible programmatically (Principle III)
- **Integration**: Third-party tools can import and use the library
- **Testing**: Library can be tested independently of CLI
- **Future UI**: Web UI can consume same library

**Constitution Alignment**:
- **Principle III (API-First Design)**: CLI MUST be thin wrapper mandated
- **Principle III**: Enable third-party integrations

### Pattern 3: Fail-Fast Validation, Graceful Runtime Degradation

**Decision**: Use Pydantic for fail-fast input validation, but degrade gracefully for API errors during analysis

**Design**:
```python
# Fail-fast: Invalid inputs rejected immediately
deployment = Deployment(url="not-a-url", token="")  # Raises ValidationError

# Graceful: API errors produce partial results
result = await analyze_deployment(deployment)
if result.partial:
    print(f"Analysis completed with {len(result.errors)} errors")
    print(result.findings)  # Show what we DID learn
```

**Rationale**:
- **Clear Contracts**: Pydantic validation catches errors early
- **Graceful Degradation**: Runtime errors produce partial reports (Principle VI)
- **User Value**: Users get value even from incomplete data

**Constitution Alignment**:
- **Principle VI (Graceful Degradation)**: Continue even when metrics unavailable
- **Principle VI**: Partial reports better than failures

## Performance Optimization Strategies

### Strategy 1: Parallel API Calls with Connection Pooling

**Approach**:
- Use httpx `AsyncClient` with connection pool (max 10 concurrent connections)
- Batch independent API calls using `asyncio.gather()`
- Example: Fetch all worker groups in parallel rather than sequentially

**Expected Impact**:
- Reduce analysis time by 60-70% compared to sequential calls
- Stay under 100 API call budget by eliminating redundant calls

### Strategy 2: Lazy Data Loading

**Approach**:
- Only fetch data for enabled objectives
- If user runs only "health" objective, don't fetch pipeline configs
- Conditional API calls based on analyzer requirements

**Expected Impact**:
- Reduce API calls for partial analysis runs by 40-60%
- Enable faster targeted assessments

### Strategy 3: Response Caching within Analysis Run

**Approach**:
- Cache API responses within a single analysis run (not across runs - stateless!)
- If multiple analyzers need worker list, fetch once and share
- Use `functools.lru_cache` for in-memory caching

**Expected Impact**:
- Reduce redundant API calls by 20-30%
- Critical for staying under 100 call budget with 15 objectives

## Security Considerations

### Credential Storage

- Encrypted with Fernet (AES-128-CBC + HMAC)
- Master password never stored, derived from user input
- Credentials stored in `~/.cribl-hc/credentials.enc` with 0600 permissions (Unix)

### Audit Logging

- All API calls logged with timestamps and outcomes
- No sensitive data (passwords, tokens, log content) logged
- Audit logs stored in `~/.cribl-hc/audit.log` with rotation

### Dependency Scanning

- CI/CD runs `pip-audit` and `safety` checks
- Automated PRs for dependency updates (Dependabot/Renovate)
- Principle X mandates vulnerability scanning

## Testing Strategy

### Unit Tests
- Test individual functions and classes in isolation
- Mock all external dependencies (API client, file I/O)
- Target: 80%+ coverage for all modules

### Integration Tests
- Test analyzer logic with mocked HTTP responses
- Use respx to mock Cribl API responses
- Validate end-to-end analysis workflows

### Contract Tests
- Validate Cribl API response schemas match expectations
- Test backward compatibility with Cribl Stream N through N-2
- Alert if API contracts change unexpectedly

### Known-Good Deployment Tests
- Test against sanitized production deployment data
- Validate findings match manual assessment
- Principle IX mandates validation against real deployments

## Open Questions & Future Research

### Question 1: Cribl API Rate Limits

**Status**: Need to confirm actual rate limits for Cloud vs self-hosted

**Next Steps**:
- Review Cribl documentation for published limits
- Test against trial Cloud account to measure limits
- Implement conservative defaults (10 req/sec) until confirmed

### Question 2: Cribl Version Detection

**Status**: Need to determine reliable version detection method

**Next Steps**:
- Check if `/api/v1/system/status` includes version field
- Test version parsing for N through N-2 (e.g., 4.5.x, 4.4.x, 4.3.x)
- Build compatibility matrix

### Question 3: Best Practice Rules Source

**Status**: Need to compile authoritative Cribl best practices

**Next Steps**:
- Review Cribl official documentation
- Consult Cribl community forums and best practices guides
- Interview Cribl SEs or support engineers
- Build initial rule set in `src/cribl_hc/rules/cribl_rules.yaml`

## Conclusion

All technology decisions have been made with explicit alignment to the project constitution. The architecture is straightforward, leveraging proven Python libraries and patterns. No decisions violate constitution principles, and several explicitly enforce them (e.g., httpx for Performance, structlog for Audit Trail, Fernet for Security).

**Next Phase**: Proceed to detailed data modeling and API contract specification.

**Constitution Compliance**: ✅ ALL DECISIONS PASS
