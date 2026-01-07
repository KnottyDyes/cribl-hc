# AGENTS.md - Agentic Coding Guidelines

This document provides guidelines for AI coding agents working in the Cribl Health Check repository.

## Project Overview

**Cribl Health Check** is a comprehensive health checking tool for Cribl Stream deployments.
- **Backend**: Python 3.11+ with FastAPI, Pydantic v2, httpx
- **Frontend**: React 19 + TypeScript 5.9 + Vite + Tailwind CSS 4
- **Desktop**: Tauri (Rust) wrapper

## Quick Commands

### Backend (Python)

```bash
# Run all tests
pytest

# Run single test file
pytest tests/unit/test_models/test_deployment.py

# Run single test function
pytest tests/unit/test_models/test_deployment.py::TestDeployment::test_valid_deployment_creation

# Run tests by marker
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
pytest -m contract      # Contract tests only
pytest -m "not slow"    # Skip slow tests

# Linting
ruff check src/ tests/

# Auto-fix lint issues
ruff check src/ tests/ --fix

# Formatting
black src/ tests/

# Type checking
mypy src/ --ignore-missing-imports

# Install dev dependencies
pip install -e ".[dev]"

# Run API server
python run_api.py
```

### Frontend (TypeScript/React)

```bash
# Install dependencies
cd frontend && npm ci

# Development server
npm run dev

# Lint
npm run lint

# Type check only
npx tsc --noEmit

# Build
npm run build
```

### Docker

```bash
docker-compose up -d      # Start services
docker-compose down       # Stop services
```

## Code Style Guidelines

### Python

**Line Length**: 100 characters (configured in pyproject.toml)

**Imports** (ordered by ruff, rule I):
```python
# Standard library
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

# Third-party
from pydantic import BaseModel, Field
import httpx

# Local
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.models.finding import Finding
```

**Type Hints**: Required everywhere (mypy strict mode). Use modern syntax:
```python
# Good
def process(items: list[str]) -> dict[str, int]: ...
value: str | None = None

# Avoid in new code
def process(items: List[str]) -> Dict[str, int]: ...
value: Optional[str] = None
```

**Docstrings**: Required for all modules, classes, and public functions:
```python
"""
Module docstring explaining purpose.

Example:
    >>> from module import function
    >>> function()
"""

class MyClass:
    """
    Class description.

    Attributes:
        name: Description of attribute

    Example:
        >>> obj = MyClass()
    """
```

**Pydantic Models**: Use v2 syntax:
```python
from pydantic import BaseModel, Field, field_validator

class MyModel(BaseModel):
    id: str = Field(..., description="Unique identifier")
    name: str = Field(..., min_length=1, max_length=255)

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        if not v.islower():
            raise ValueError("ID must be lowercase")
        return v
```

**Async Code**: Use async/await pattern consistently:
```python
async def analyze(self, client: CriblAPIClient) -> AnalyzerResult:
    result = self.create_result()
    data = await client.get_workers()
    # Process data...
    return result
```

**Logging**: Use structured logging via `get_logger`:
```python
from cribl_hc.utils.logger import get_logger
log = get_logger(__name__)

log.info("operation_started", deployment_id=deployment.id)
log.error("operation_failed", error=str(e), traceback=True)
```

### TypeScript/React

**Imports**: Named exports, grouped logically:
```typescript
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { ErrorBoundary } from './components/common'
import { Layout } from './components/layout/Layout'
import type { AxiosError } from 'axios'
```

**Component Structure**: Functional components with hooks:
```typescript
function MyComponent() {
  return (
    <div className="...">
      {/* content */}
    </div>
  )
}

export default MyComponent
```

**Barrel Exports**: Use index.ts for component folders:
```typescript
// components/common/index.ts
export { Button } from './Button'
export { Card } from './Card'
export type { ButtonProps } from './Button'
```

**Error Handling**:
```typescript
try {
  const data = await apiClient.get('/endpoint')
} catch (error: AxiosError) {
  console.error('API Error:', error.response?.status, error.response?.data)
}
```

## Testing Guidelines

### Python Tests

**Structure**: Mirror source structure in `tests/`:
```
tests/
├── unit/           # Fast, isolated tests
│   └── test_models/
├── integration/    # Tests with external dependencies (mocked)
└── contract/       # API contract validation
```

**Test Class Pattern**:
```python
class TestDeployment:
    """Test Deployment model validation and behavior."""

    def test_valid_deployment_creation(self):
        """Test creating a valid deployment."""
        deployment = Deployment(...)
        assert deployment.id == "expected"

    def test_invalid_deployment_id(self):
        """Test that invalid ID is rejected."""
        with pytest.raises(ValidationError):
            Deployment(id="INVALID", ...)
```

**Fixtures**: Define in `conftest.py`:
```python
@pytest.fixture
def sample_deployment():
    from cribl_hc.models.deployment import Deployment
    return Deployment(
        id="test-deployment",
        name="Test Deployment",
        ...
    )
```

**Async Tests**: Use pytest-asyncio (auto mode configured):
```python
async def test_async_operation():
    result = await some_async_function()
    assert result is not None
```

## Architecture Patterns

### Analyzers

All analyzers inherit from `BaseAnalyzer` and implement:
```python
class MyAnalyzer(BaseAnalyzer):
    @property
    def objective_name(self) -> str:
        return "my_objective"

    @property
    def supported_products(self) -> list[str]:
        return ["stream", "edge"]  # or ["stream", "edge", "lake", "search"]

    async def analyze(self, client: CriblAPIClient) -> AnalyzerResult:
        result = self.create_result()
        # ... analysis logic ...
        result.add_finding(self.create_finding(...))
        return result
```

### Models

Use Pydantic BaseModel with Field descriptors:
- Required fields: `Field(..., description="...")`
- Optional fields: `Field(None, description="...")`
- Validation: `@field_validator` decorators

## Conventions

### Naming

**Python**:
- Classes: `PascalCase` (e.g., `HealthAnalyzer`)
- Functions/variables: `snake_case` (e.g., `get_workers`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `MAX_RETRIES`)
- Private: prefix with `_` (e.g., `_internal_method`)

**TypeScript**:
- Components: `PascalCase` (e.g., `HomePage`)
- Functions/variables: `camelCase` (e.g., `getBackendUrl`)
- Types/Interfaces: `PascalCase` (e.g., `ApiResponse`)

### Error Handling

**Python**: Catch specific exceptions, log with context:
```python
try:
    result = await client.get_workers()
except httpx.HTTPError as e:
    log.error("api_request_failed", error=str(e), endpoint="/workers")
    result = AnalyzerResult(objective=self.objective_name, success=False, error=str(e))
```

**Never suppress errors silently** - always log or propagate.

### Constitution Principles

This project follows 12 core principles (see `.specify/memory/constitution.md`):
1. Read-Only by Default - Never modify Cribl configurations
2. Actionability First - Clear remediation steps for findings
3. API-First Design - Core library with thin CLI wrapper
4. Performance Efficiency - <5 min analysis, <100 API calls

## CI/CD

GitHub Actions workflow (`.github/workflows/ci.yml`):
- Backend: ruff check, mypy, pytest
- Frontend: eslint, tsc --noEmit, npm run build
- Docker build test

## File Structure Reference

```
src/cribl_hc/
├── analyzers/     # Health check analyzers (19 total)
├── api/           # FastAPI routes
├── cli/           # Typer CLI commands
├── core/          # API client, orchestrator
├── models/        # Pydantic models
├── rules/         # YAML rule definitions
└── utils/         # Helpers, logging

frontend/src/
├── api/           # API client, hooks
├── components/    # React components
├── hooks/         # Custom React hooks
├── pages/         # Route pages
└── utils/         # Utility functions

tests/
├── unit/          # Unit tests
├── integration/   # Integration tests
└── contract/      # API contract tests
```

## Documentation Sync (MANDATORY for AI Agents)

**When you add or modify features, you MUST update documentation.** This is not optional.

### Trigger Conditions

Update documentation when you:
- Add a new analyzer class
- Add a new CLI command
- Add a new API endpoint
- Change analyzer objectives or supported products
- Modify CLI command signatures or help text
- Change API endpoint paths or methods

### Documentation Locations

| Feature Type | Document to Update |
|--------------|-------------------|
| Analyzers | README.md (analyzer list/count), docs/ANALYZERS.md |
| CLI Commands | README.md (usage examples), docs/CLI_GUIDE.md |
| API Endpoints | docs/API_REFERENCE.md |
| Models | docs/API_REFERENCE.md (schemas section) |
| Architecture changes | docs/ARCHITECTURE.md |

### What to Document

**For new Analyzers:**
```markdown
- Analyzer class name and objective
- Supported products (stream, edge, lake, search)
- What it checks (1-2 sentence description)
- Update analyzer count in README.md
```

**For new CLI Commands:**
```markdown
- Command name and subcommands
- All options/flags with descriptions
- Usage examples
- Update command list in README.md
```

**For new API Endpoints:**
```markdown
- HTTP method and path
- Request/response schemas
- Example requests with curl
- Error responses
```

### Pre-Commit Checklist

Before completing any feature work, verify:

- [ ] All new analyzers mentioned in README.md
- [ ] Analyzer count in README.md matches actual count
- [ ] New CLI commands documented with examples
- [ ] New API endpoints have request/response examples
- [ ] AGENTS.md file structure is current

### Documentation Quality Standards

1. **Be specific**: Include exact command syntax, not just descriptions
2. **Show examples**: Every feature needs at least one usage example
3. **Keep counts accurate**: Analyzer counts, command counts must match code
4. **Update architecture docs**: For structural changes to the codebase

### Quick Audit Commands

Run these to check documentation accuracy:

```bash
# Count analyzers in code vs README
grep -c "Analyzer" src/cribl_hc/analyzers/*.py
grep -o "[0-9]* analyzer" README.md

# List all CLI commands
grep -r "@app.command\|@cli.command" src/cribl_hc/cli/

# List all API endpoints  
grep -r "router.get\|router.post\|@app.get\|@app.post" src/cribl_hc/api/
```

### When in Doubt

If unsure whether documentation needs updating:
1. **Check the diff**: Review what files you changed
2. **User-facing = document**: If users interact with it, document it
3. **Ask**: "Would a new developer need to know about this change?"
