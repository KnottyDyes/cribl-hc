# Web GUI Quick Start Guide

The Cribl Health Check Web GUI provides a modern, browser-based interface for managing health checks across your Cribl Stream deployments.

## Features

- **Interactive Dashboard**: Modern web interface for managing health checks
- **Real-time Updates**: Live progress tracking via WebSocket during analysis
- **Credential Management**: Add, edit, test, and delete deployment credentials
- **Visual Results**: Interactive findings table with filtering and sorting
- **Export Options**: Export results as JSON or Markdown
- **REST API**: Full API backend with interactive documentation

## Prerequisites

- Python 3.11+
- Node.js 18+ (for frontend development)
- Docker & Docker Compose (optional, for containerized deployment)

## Quick Start

### Option 1: Using Docker (Recommended)

```bash
# Start both API and frontend
docker-compose up -d

# Access the application
open http://localhost:8080
```

The Docker setup includes:
- FastAPI backend on port 8080
- React frontend (served via FastAPI)
- Automatic rebuilds during development

### Option 2: Manual Setup

#### 1. Start the API Server

```bash
# Install Python dependencies
pip install -r requirements.txt

# Start the FastAPI server
python run_api.py

# API will be available at http://localhost:8080
```

#### 2. Start the Frontend (Development)

```bash
# Install frontend dependencies
cd frontend
npm install

# Start the Vite dev server
npm run dev

# Frontend will be available at http://localhost:5173
```

## Using the Web GUI

### 1. Manage Credentials

**Add a New Credential:**
1. Navigate to the "Credentials" page
2. Click "Add Credential"
3. Fill in the form:
   - **Name**: Unique identifier (e.g., "prod", "dev")
   - **URL**: Cribl deployment URL
     - Cribl Cloud: `https://<workspace>-<org>.cribl.cloud`
     - Self-hosted: `https://cribl.example.com`
   - **Auth Type**: Choose Bearer Token or OAuth
   - **Token/Credentials**: Enter your API token or OAuth credentials
4. Click "Test Connection" to verify
5. Click "Save"

**Test a Credential:**
- Click the "Test" button on any credential card
- Green checkmark = successful connection
- Red X = connection failed (check credentials)

**Edit/Delete:**
- Click "Edit" to modify credentials
- Click "Delete" to remove (with confirmation)

### 2. Run Health Checks

**Start a New Analysis:**
1. Navigate to the "Analysis" page
2. Click "New Analysis"
3. Select:
   - **Credential**: Choose from saved credentials
   - **Analyzers**: Select which analyzers to run
     - Config Analyzer
     - Health Analyzer
     - Performance Analyzer
     - Security Analyzer
4. Click "Start Analysis"

**Monitor Progress:**
- Real-time progress updates via WebSocket
- Status changes: `pending` → `running` → `completed`/`failed`
- Live findings appear as they're discovered

### 3. View Results

**Analysis List:**
- View all analyses with status and health scores
- Click any analysis to view detailed results

**Results Page:**
- **Summary**: Health score, risk level, findings count
- **Filters**: Filter by severity (Critical, High, Medium, Low, Info) or category
- **Sort**: Automatically sorted by severity (Critical → Info)
- **Findings**: Detailed list with descriptions and recommendations
- **Export**: Download results as JSON or Markdown

## API Documentation

The FastAPI backend includes interactive API documentation:

```bash
# Swagger UI (try out endpoints directly)
open http://localhost:8080/api/docs

# ReDoc (alternative documentation)
open http://localhost:8080/api/redoc
```

### API Endpoints

**Credentials:**
- `GET /api/v1/credentials` - List all credentials
- `POST /api/v1/credentials` - Create new credential
- `GET /api/v1/credentials/{name}` - Get credential details
- `PUT /api/v1/credentials/{name}` - Update credential
- `DELETE /api/v1/credentials/{name}` - Delete credential
- `POST /api/v1/credentials/{name}/test` - Test connection

**Analyzers:**
- `GET /api/v1/analyzers` - List available analyzers

**Analysis:**
- `POST /api/v1/analysis` - Start new analysis
- `GET /api/v1/analysis` - List all analyses
- `GET /api/v1/analysis/{id}` - Get analysis results
- `DELETE /api/v1/analysis/{id}` - Delete analysis

**WebSocket:**
- `WS /api/v1/ws/analysis/{id}` - Real-time analysis updates

## Development

### Frontend Development

```bash
cd frontend

# Install dependencies
npm install

# Start dev server with hot reload
npm run dev

# Build for production
npm run build

# Run linter
npm run lint
```

### API Development

```bash
# Install in development mode
pip install -e .

# Run with auto-reload
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8080
```

## Troubleshooting

### Port Already in Use

```bash
# Kill process on port 8080
lsof -ti:8080 | xargs kill -9

# Or change the port
uvicorn src.api.main:app --port 8081
```

### CORS Issues

If you see CORS errors in the browser console:
- Ensure the API is running on port 8080
- Frontend should connect to `http://localhost:8080`
- Check `.env.development` in the frontend directory

### WebSocket Connection Failed

- Verify the API server is running
- Check browser console for WebSocket errors
- Ensure firewall allows WebSocket connections

### Tailwind CSS Not Working

If styles aren't applied:
- Ensure `@tailwindcss/vite` plugin is installed
- Check `tailwind.config.js` exists with proper content paths
- Clear Vite cache: `rm -rf frontend/.vite`
- Restart dev server

## Production Deployment

### Using Docker Compose

```bash
# Build and start
docker-compose up -d --build

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Manual Production Build

```bash
# Build frontend
cd frontend
npm run build

# The build output goes to frontend/dist/
# FastAPI will serve this automatically

# Start production server
cd ..
uvicorn src.api.main:app --host 0.0.0.0 --port 8080
```

## Architecture

```
┌─────────────────────────────────────────────────┐
│                   Browser                       │
│  ┌──────────────┐         ┌─────────────────┐  │
│  │ React UI     │◄────────┤ WebSocket       │  │
│  │ (Port 5173)  │         │ (Real-time)     │  │
│  └──────┬───────┘         └────────▲────────┘  │
│         │ HTTP                      │           │
└─────────┼───────────────────────────┼───────────┘
          │                           │
          ▼                           │
┌─────────────────────────────────────┴───────────┐
│           FastAPI Backend (Port 8080)           │
│  ┌──────────────────────────────────────────┐   │
│  │  REST API Endpoints                      │   │
│  │  - Credentials, Analysis, Analyzers      │   │
│  └──────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────┐   │
│  │  WebSocket Server                        │   │
│  │  - Real-time analysis updates            │   │
│  └──────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────┐   │
│  │  Core Health Check Engine                │   │
│  │  - Config, Health, Perf, Security        │   │
│  └──────────────────────────────────────────┘   │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼
         ┌────────────────────┐
         │  Cribl Stream API  │
         │  (Read-only)       │
         └────────────────────┘
```

## Next Steps

- Explore the [CLI Guide](CLI_GUIDE.md) for command-line usage
- Check the main [README](../README.md) for full feature list
- Review API documentation at http://localhost:8080/api/docs
