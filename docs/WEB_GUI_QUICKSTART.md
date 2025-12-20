# Web GUI Quick Start Guide

**Status**: Phase 1 (API) Complete, Phase 2 (Frontend) Ready for Development
**Last Updated**: 2025-12-19

---

## Current Status

### ✅ Phase 1: API Backend - COMPLETE

The FastAPI backend is fully functional and tested:

- **22 API routes** across 4 routers
- **WebSocket support** for real-time updates
- **Credential management** (CRUD + connection testing)
- **Analysis execution** (background tasks)
- **Interactive API docs** at `/api/docs`

### ⏳ Phase 2: React Frontend - Ready to Build

All architecture and integration code is prepared. Waiting for Node.js installation.

---

## Quick Start Options

### Option 1: Test API Backend Only (Available Now)

**Prerequisites**: Python 3.11+, pip

```bash
# 1. Install dependencies
pip install -e .

# 2. Start API server
python run_api.py

# 3. Open browser to API docs
open http://localhost:8080/api/docs

# 4. Test endpoints
curl http://localhost:8080/api/v1/version
curl http://localhost:8080/api/v1/analyzers
curl http://localhost:8080/api/v1/credentials
```

**API Documentation**: http://localhost:8080/api/docs

### Option 2: Docker (Web API)

**Prerequisites**: Docker

```bash
# 1. Build image
docker-compose build

# 2. Start web API
docker-compose up -d

# 3. View logs
docker-compose logs -f

# 4. Access API docs
open http://localhost:8080/api/docs

# 5. Stop
docker-compose down
```

### Option 3: Full Stack Development (Requires Node.js)

**Prerequisites**: Python 3.11+, Node.js 18+, npm

```bash
# Backend (Terminal 1)
pip install -e .
python run_api.py

# Frontend (Terminal 2) - AFTER Node.js installed
cd frontend
npm install
npm run dev

# Access
# - Frontend: http://localhost:5173
# - API Docs: http://localhost:8080/api/docs
```

---

## Testing the API Backend

### 1. Health Check

```bash
curl http://localhost:8080/health
```

Response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "service": "cribl-health-check"
}
```

### 2. List Analyzers

```bash
curl http://localhost:8080/api/v1/analyzers | jq
```

Response:
```json
{
  "analyzers": [
    {
      "name": "health",
      "description": "Overall health assessment, worker monitoring, and critical issue identification",
      "api_calls": 3,
      "permissions": ["read:workers", "read:system", "read:metrics"],
      "categories": ["health"]
    },
    {
      "name": "config",
      "description": "Analyzer for config objective",
      "api_calls": 5,
      "permissions": ["read:pipelines", "read:routes", "read:inputs", "read:outputs"],
      "categories": ["config"]
    },
    {
      "name": "resource",
      "description": "Analyzer for resource objective",
      "api_calls": 3,
      "permissions": ["read:workers", "read:metrics", "read:system"],
      "categories": ["resource"]
    }
  ],
  "total_count": 3,
  "total_api_calls": 11
}
```

### 3. Create Credential (Bearer Token)

```bash
curl -X POST http://localhost:8080/api/v1/credentials \
  -H "Content-Type: application/json" \
  -d '{
    "name": "prod",
    "url": "https://main-myorg.cribl.cloud",
    "auth_type": "bearer",
    "token": "your_bearer_token_here"
  }' | jq
```

### 4. Create Credential (OAuth)

```bash
curl -X POST http://localhost:8080/api/v1/credentials \
  -H "Content-Type: application/json" \
  -d '{
    "name": "prod-oauth",
    "url": "https://main-myorg.cribl.cloud",
    "auth_type": "oauth",
    "client_id": "your_client_id",
    "client_secret": "your_client_secret"
  }' | jq
```

### 5. Test Connection

```bash
curl -X POST http://localhost:8080/api/v1/credentials/prod/test | jq
```

Response:
```json
{
  "success": true,
  "message": "Connected successfully",
  "cribl_version": "4.6.0",
  "response_time_ms": 125.5,
  "error": null
}
```

### 6. Start Analysis

```bash
curl -X POST http://localhost:8080/api/v1/analysis \
  -H "Content-Type: application/json" \
  -d '{
    "deployment_name": "prod",
    "analyzers": ["health"]
  }' | jq
```

Response:
```json
{
  "analysis_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "deployment_name": "prod",
  "status": "pending",
  "created_at": "2025-12-19T19:30:00Z",
  "analyzers": ["health"],
  "progress_percent": 0
}
```

### 7. Get Analysis Results

```bash
# Wait a few seconds, then:
ANALYSIS_ID="a1b2c3d4-e5f6-7890-abcd-ef1234567890"
curl http://localhost:8080/api/v1/analysis/$ANALYSIS_ID/results | jq
```

Response:
```json
{
  "analysis_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "deployment_name": "prod",
  "status": "completed",
  "health_score": 87.5,
  "findings_count": 12,
  "findings": [
    {
      "id": "health-overall-critical",
      "category": "health",
      "severity": "critical",
      "title": "System Health: Critical",
      "description": "Worker health check failed",
      "affected_components": ["worker-3"],
      "remediation_steps": ["Review worker logs", "Check resource usage"],
      "estimated_impact": "High availability risk",
      "confidence_level": "high"
    }
  ],
  "duration_seconds": 83.2
}
```

### 8. WebSocket Live Updates (JavaScript)

```javascript
const ws = new WebSocket('ws://localhost:8080/api/v1/analysis/ws/ANALYSIS_ID')

ws.onopen = () => console.log('Connected')

ws.onmessage = (event) => {
  const message = JSON.parse(event.data)

  switch (message.type) {
    case 'progress':
      console.log(`Progress: ${message.percent}% - ${message.step}`)
      break
    case 'finding':
      console.log('New finding:', message.finding)
      break
    case 'complete':
      console.log('Complete! Health score:', message.health_score)
      break
    case 'error':
      console.error('Error:', message.error)
      break
  }
}
```

---

## Next Steps: Building the Frontend

### Prerequisites

1. **Install Node.js 18+ and npm**

```bash
# On macOS with Homebrew
brew install node

# Verify installation
node --version  # Should be v18 or higher
npm --version   # Should be v9 or higher
```

### Frontend Setup (Once Node.js is installed)

```bash
# 1. Create React app with Vite
npm create vite@latest frontend -- --template react-ts
cd frontend

# 2. Install dependencies
npm install

# Core dependencies
npm install react-router-dom @tanstack/react-query axios

# UI dependencies
npm install @headlessui/react @heroicons/react tailwindcss@latest postcss autoprefixer
npx tailwindcss init -p

# Development dependencies
npm install -D @types/node

# 3. Copy API integration templates
# See docs/API_INTEGRATION_TEMPLATE.md for ready-to-use TypeScript code

# 4. Start development server
npm run dev
```

### Development Workflow

```bash
# Terminal 1: Backend API
cd /path/to/cribl-hc
python run_api.py

# Terminal 2: Frontend Dev Server
cd /path/to/cribl-hc/frontend
npm run dev

# Access:
# - Frontend: http://localhost:5173
# - API: http://localhost:8080
# - API Docs: http://localhost:8080/api/docs
```

---

## Docker Usage

### Build and Run

```bash
# Build image
docker-compose build

# Start in background
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

### CLI Commands via Docker

```bash
# Add credential
docker-compose run --rm cribl-hc cribl-hc config add prod

# Run analysis
docker-compose run --rm cribl-hc cribl-hc analyze prod

# Interactive shell
docker-compose run --rm cribl-hc bash
```

### Data Persistence

Credentials are stored in a Docker volume:

```bash
# Inspect volume
docker volume inspect cribl-hc_cribl-hc-credentials

# Backup credentials
docker run --rm -v cribl-hc_cribl-hc-credentials:/data \
  -v $(pwd):/backup alpine tar czf /backup/credentials-backup.tar.gz -C /data .

# Restore credentials
docker run --rm -v cribl-hc_cribl-hc-credentials:/data \
  -v $(pwd):/backup alpine tar xzf /backup/credentials-backup.tar.gz -C /data
```

---

## API Endpoints Reference

### System

- `GET /health` - Health check
- `GET /api/v1/version` - API version and features

### Credentials

- `GET /api/v1/credentials` - List all credentials
- `POST /api/v1/credentials` - Create credential
- `GET /api/v1/credentials/{name}` - Get credential
- `PUT /api/v1/credentials/{name}` - Update credential
- `DELETE /api/v1/credentials/{name}` - Delete credential
- `POST /api/v1/credentials/{name}/test` - Test connection

### Analyzers

- `GET /api/v1/analyzers` - List all analyzers
- `GET /api/v1/analyzers/{name}` - Get analyzer details

### Analysis

- `POST /api/v1/analysis` - Start analysis
- `GET /api/v1/analysis` - List all analyses
- `GET /api/v1/analysis/{id}` - Get analysis status
- `GET /api/v1/analysis/{id}/results` - Get results
- `DELETE /api/v1/analysis/{id}` - Delete analysis
- `WS /api/v1/analysis/ws/{id}` - WebSocket live updates

---

## Troubleshooting

### API Server Won't Start

```bash
# Check if port 8080 is in use
lsof -i :8080

# Kill process using port
kill -9 <PID>

# Or use a different port
uvicorn cribl_hc.api.app:app --port 8081
```

### CORS Errors

The API is configured to allow requests from:
- `http://localhost:3000` (React default)
- `http://localhost:5173` (Vite default)

If using a different port, update `src/cribl_hc/api/app.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:YOUR_PORT",  # Add your port
    ],
)
```

### Import Errors

```bash
# Reinstall dependencies
pip install -e .

# Or install FastAPI dependencies explicitly
pip install 'fastapi>=0.109.0' 'uvicorn[standard]>=0.27.0' 'websockets>=12.0'
```

### Docker Build Fails

```bash
# Clean build
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

---

## Documentation

- **API Documentation**: [API_PHASE1_COMPLETE.md](../API_PHASE1_COMPLETE.md)
- **Frontend Architecture**: [FRONTEND_ARCHITECTURE.md](./FRONTEND_ARCHITECTURE.md)
- **API Integration Templates**: [API_INTEGRATION_TEMPLATE.md](./API_INTEGRATION_TEMPLATE.md)
- **Docker Guide**: [DOCKER_GUIDE.md](./DOCKER_GUIDE.md)
- **Interactive API Docs**: http://localhost:8080/api/docs

---

## Support

- **Issues**: https://github.com/anthropics/cribl-hc/issues
- **API Spec**: http://localhost:8080/api/openapi.json
- **Swagger UI**: http://localhost:8080/api/docs
- **ReDoc**: http://localhost:8080/api/redoc

---

**Phase 1 Status**: ✅ Complete and Tested
**Phase 2 Status**: ⏳ Ready to build (requires Node.js)

Install Node.js to continue with React frontend development!
