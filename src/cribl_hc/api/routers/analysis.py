"""
Analysis execution API endpoints.

Provides endpoints for running health check analyses with background task execution
and real-time status updates via WebSocket.
"""

import asyncio
import json
import uuid
from datetime import datetime
from enum import Enum

from fastapi import (
    APIRouter,
    BackgroundTasks,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.responses import Response
from pydantic import BaseModel, Field

from cribl_hc.analyzers import get_global_registry
from cribl_hc.cli.commands.config import load_credentials
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.core.branding_manager import get_branding_config
from cribl_hc.core.orchestrator import AnalyzerOrchestrator
from cribl_hc.core.report_generator import (
    HTMLReportGenerator,
    JSONReportGenerator,
    MarkdownReportGenerator,
)
from cribl_hc.utils.logger import get_logger

router = APIRouter()
log = get_logger(__name__)


# Custom JSON encoder for datetime and enum objects
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()
        if isinstance(o, Enum):
            return o.value
        return super().default(o)


# In-memory storage for analysis results (will be replaced with database in v2)
analysis_results: dict[str, dict] = {}
active_websockets: dict[str, list[WebSocket]] = {}


class AnalysisStatus(str, Enum):
    """Analysis execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AnalysisRequest(BaseModel):
    """Request model for starting an analysis."""

    deployment_name: str = Field(..., description="Name of the configured deployment")
    analyzers: list[str] | None = Field(
        None, description="List of analyzers to run. If not specified, all analyzers run."
    )

    class Config:
        json_schema_extra = {
            "example": {"deployment_name": "prod", "analyzers": ["health", "config", "resource"]}
        }


class AnalysisResponse(BaseModel):
    """Response model for analysis metadata."""

    analysis_id: str
    deployment_name: str
    status: AnalysisStatus
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    analyzers: list[str]
    progress_percent: int = 0
    current_step: str | None = None
    api_calls_used: int = 0


class AnalysisResultResponse(BaseModel):
    """Response model for analysis results."""

    analysis_id: str
    deployment_name: str
    status: AnalysisStatus
    health_score: float | None = None
    findings_count: int = 0
    findings: list[dict] = []
    recommendations_count: int = 0
    completed_at: datetime | None = None
    duration_seconds: float | None = None


async def run_analysis_task(
    analysis_id: str, deployment_name: str, analyzers_to_run: list[str] | None
):
    """
    Background task to run the analysis.
    """
    try:
        # Update status to running
        analysis_results[analysis_id]["status"] = AnalysisStatus.RUNNING
        analysis_results[analysis_id]["started_at"] = datetime.utcnow()

        log.info("analysis_started", analysis_id=analysis_id, deployment=deployment_name)

        # Load credentials
        credentials = load_credentials()
        if deployment_name not in credentials:
            raise ValueError(f"Deployment '{deployment_name}' not found")

        cred = credentials[deployment_name]

        # Create API client (OAuth handled in credentials loading if implemented)
        client = CriblAPIClient(
            base_url=cred["url"],
            auth_token=cred.get("token", ""),
        )

        # Create orchestrator and run analysis
        async with client:
            orchestrator = AnalyzerOrchestrator(client=client)

            # Run analysis with specified analyzers (or None for all)
            results = await orchestrator.run_analysis(objectives=analyzers_to_run)

            # Create analysis run from results
            analysis_run = orchestrator.create_analysis_run(results, deployment_name)

        # Store results
        analysis_results[analysis_id].update(
            {
                "status": AnalysisStatus.COMPLETED,
                "completed_at": datetime.utcnow(),
                "health_score": analysis_run.health_score.overall_score
                if analysis_run.health_score
                else None,
                "findings": [f.model_dump() for f in analysis_run.findings],
                "recommendations": [r.model_dump() for r in analysis_run.recommendations]
                if analysis_run.recommendations
                else [],
                "duration_seconds": analysis_run.duration_seconds,
                "api_calls_used": client.get_api_calls_used(),
                "analysis_run": analysis_run,
                "results": results,
            }
        )

        # Notify WebSocket clients
        await notify_websocket_clients(
            analysis_id,
            {
                "type": "complete",
                "analysis_id": analysis_id,
                "health_score": analysis_run.health_score.overall_score
                if analysis_run.health_score
                else None,
            },
        )

        log.info(
            "analysis_completed",
            analysis_id=analysis_id,
            findings_count=len(analysis_run.findings),
        )

    except Exception as e:
        log.error("analysis_failed", analysis_id=analysis_id, error=str(e))
        analysis_results[analysis_id].update(
            {
                "status": AnalysisStatus.FAILED,
                "completed_at": datetime.utcnow(),
                "error": str(e),
            }
        )

        # Notify WebSocket clients of failure
        await notify_websocket_clients(
            analysis_id,
            {
                "type": "error",
                "analysis_id": analysis_id,
                "error": str(e),
            },
        )


async def notify_websocket_clients(analysis_id: str, message: dict):
    """
    Send message to all WebSocket clients watching this analysis.
    """
    if analysis_id in active_websockets:
        # Create a copy of the list to avoid modification during iteration
        clients = active_websockets[analysis_id].copy()

        for websocket in clients:
            try:
                await websocket.send_json(message)
            except Exception as e:
                log.warning("websocket_send_failed", analysis_id=analysis_id, error=str(e))
                # Remove failed websocket
                try:
                    active_websockets[analysis_id].remove(websocket)
                except ValueError:
                    pass


@router.post("", response_model=AnalysisResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_analysis(request: AnalysisRequest, background_tasks: BackgroundTasks):
    """
    Start a new health check analysis.
    """
    try:
        # Generate unique analysis ID
        analysis_id = str(uuid.uuid4())

        # Get analyzer names
        if request.analyzers:
            analyzer_names = request.analyzers
        else:
            registry = get_global_registry()
            analyzer_names = registry.list_objectives()

        # Store initial analysis metadata
        analysis_results[analysis_id] = {
            "analysis_id": analysis_id,
            "deployment_name": request.deployment_name,
            "status": AnalysisStatus.PENDING,
            "created_at": datetime.utcnow(),
            "started_at": None,
            "completed_at": None,
            "analyzers": analyzer_names,
            "progress_percent": 0,
            "current_step": None,
            "api_calls_used": 0,
            "findings": [],
            "recommendations": [],
        }

        # Start background task
        background_tasks.add_task(
            run_analysis_task, analysis_id, request.deployment_name, request.analyzers
        )

        log.info("analysis_queued", analysis_id=analysis_id, deployment=request.deployment_name)

        return AnalysisResponse(
            analysis_id=analysis_id,
            deployment_name=request.deployment_name,
            status=AnalysisStatus.PENDING,
            created_at=analysis_results[analysis_id]["created_at"],
            analyzers=analyzer_names,
        )

    except Exception as e:
        log.error("start_analysis_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start analysis: {str(e)}",
        )


@router.get("", response_model=list[AnalysisResponse])
async def list_analyses():
    """
    List all analyses.
    """
    responses = []

    for analysis_id, data in analysis_results.items():
        responses.append(
            AnalysisResponse(
                analysis_id=analysis_id,
                deployment_name=data["deployment_name"],
                status=data["status"],
                created_at=data["created_at"],
                started_at=data.get("started_at"),
                completed_at=data.get("completed_at"),
                analyzers=data["analyzers"],
                progress_percent=data.get("progress_percent", 0),
                current_step=data.get("current_step"),
                api_calls_used=data.get("api_calls_used", 0),
            )
        )

    # Sort by created_at descending (newest first)
    responses.sort(key=lambda x: x.created_at, reverse=True)

    return responses


@router.get("/{analysis_id}", response_model=AnalysisResponse)
async def get_analysis(analysis_id: str):
    """
    Get analysis status and metadata.
    """
    if analysis_id not in analysis_results:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Analysis '{analysis_id}' not found"
        )

    data = analysis_results[analysis_id]

    return AnalysisResponse(
        analysis_id=analysis_id,
        deployment_name=data["deployment_name"],
        status=data["status"],
        created_at=data["created_at"],
        started_at=data.get("started_at"),
        completed_at=data.get("completed_at"),
        analyzers=data["analyzers"],
        progress_percent=data.get("progress_percent", 0),
        current_step=data.get("current_step"),
        api_calls_used=data.get("api_calls_used", 0),
    )


@router.get("/{analysis_id}/results", response_model=AnalysisResultResponse)
async def get_analysis_results(analysis_id: str):
    """
    Get full analysis results.
    """
    if analysis_id not in analysis_results:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Analysis '{analysis_id}' not found"
        )

    data = analysis_results[analysis_id]

    if data["status"] not in [AnalysisStatus.COMPLETED, AnalysisStatus.FAILED]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Analysis is still {data['status']}. Results not available yet.",
        )

    return AnalysisResultResponse(
        analysis_id=analysis_id,
        deployment_name=data["deployment_name"],
        status=data["status"],
        health_score=data.get("health_score"),
        findings_count=len(data.get("findings", [])),
        findings=data.get("findings", []),
        recommendations_count=len(data.get("recommendations", [])),
        completed_at=data.get("completed_at"),
        duration_seconds=data.get("duration_seconds"),
    )


@router.delete("/{analysis_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_analysis(analysis_id: str):
    """
    Delete an analysis and its results.
    """
    if analysis_id not in analysis_results:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Analysis '{analysis_id}' not found"
        )

    data = analysis_results[analysis_id]

    if data["status"] == AnalysisStatus.RUNNING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Cannot delete running analysis"
        )

    del analysis_results[analysis_id]

    # Clean up websocket connections
    if analysis_id in active_websockets:
        del active_websockets[analysis_id]

    log.info("analysis_deleted", analysis_id=analysis_id)

    return None


@router.get("/{analysis_id}/export/{format}")
async def export_analysis(analysis_id: str, format: str):
    """
    Export analysis results in various formats with branding.
    """
    if analysis_id not in analysis_results:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Analysis '{analysis_id}' not found"
        )

    data = analysis_results[analysis_id]

    if data["status"] not in [AnalysisStatus.COMPLETED, AnalysisStatus.FAILED]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Analysis is still {data['status']}. Cannot export incomplete analysis.",
        )

    # Get branding configuration
    branding = get_branding_config()

    # Get the AnalysisRun object
    analysis_run = data.get("analysis_run")
    results = data.get("results")

    if not analysis_run:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Analysis run data not found in memory.",
        )

    if format == "json":
        generator = JSONReportGenerator()
        content = json.dumps(generator.generate(analysis_run), indent=2, cls=CustomJSONEncoder)
        media_type = "application/json"

    elif format == "html":
        generator = HTMLReportGenerator(branding=branding)
        content = generator.generate(analysis_run, results or {})
        media_type = "text/html"

    elif format == "md":
        generator = MarkdownReportGenerator(branding=branding)
        content = generator.generate(analysis_run, results or {})
        media_type = "text/markdown"

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported format '{format}'. Use json, html, or md.",
        )

    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="health-check-{analysis_id}.{format}"',
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET",
            "Access-Control-Allow-Headers": "*",
        },
    )


@router.websocket("/ws/{analysis_id}")
async def websocket_analysis_updates(websocket: WebSocket, analysis_id: str):
    """
    WebSocket endpoint for real-time analysis updates.
    """
    await websocket.accept()

    # Register websocket
    if analysis_id not in active_websockets:
        active_websockets[analysis_id] = []
    active_websockets[analysis_id].append(websocket)

    log.info("websocket_connected", analysis_id=analysis_id)

    try:
        # Send initial status
        if analysis_id in analysis_results:
            await websocket.send_json(
                {
                    "type": "status",
                    "analysis_id": analysis_id,
                    "status": analysis_results[analysis_id]["status"],
                }
            )

        # Keep connection alive and wait for messages (if any)
        while True:
            # Just wait for messages (we send from background task)
            try:
                # We don't really expect client messages, but need to keep the loop
                await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                await websocket.send_json({"type": "pong"})
            except TimeoutError:
                # Send keepalive
                await websocket.send_json({"type": "keepalive"})

    except WebSocketDisconnect:
        log.info("websocket_disconnected", analysis_id=analysis_id)
    except Exception as e:
        log.error("websocket_error", analysis_id=analysis_id, error=str(e))
    finally:
        # Unregister websocket
        if analysis_id in active_websockets:
            try:
                active_websockets[analysis_id].remove(websocket)
            except ValueError:
                pass
