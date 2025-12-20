"""
Analyzer metadata API endpoints.

Provides information about available analyzers, their capabilities,
and API call estimates.
"""

from typing import List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from cribl_hc.analyzers import get_global_registry

router = APIRouter()


class AnalyzerInfo(BaseModel):
    """Information about an analyzer."""
    name: str
    description: str
    api_calls: int
    permissions: List[str]
    categories: List[str]


class AnalyzersListResponse(BaseModel):
    """Response for list analyzers endpoint."""
    analyzers: List[AnalyzerInfo]
    total_count: int
    total_api_calls: int


@router.get("", response_model=AnalyzersListResponse)
async def list_analyzers():
    """
    List all available analyzers.

    Returns metadata for each analyzer including:
    - Name and description
    - Estimated API calls
    - Required permissions
    - Analysis categories
    """
    registry = get_global_registry()
    analyzer_classes = registry.list_analyzers()

    analyzers_info = []
    total_api_calls = 0

    for analyzer_class in analyzer_classes:
        # Create temporary instance to get metadata
        analyzer = analyzer_class()

        info = AnalyzerInfo(
            name=analyzer.objective_name,
            description=analyzer.get_description(),
            api_calls=analyzer.get_estimated_api_calls(),
            permissions=analyzer.get_required_permissions(),
            categories=[analyzer.objective_name],  # Could be enhanced
        )
        analyzers_info.append(info)
        total_api_calls += analyzer.get_estimated_api_calls()

    return AnalyzersListResponse(
        analyzers=analyzers_info,
        total_count=len(analyzers_info),
        total_api_calls=total_api_calls
    )


@router.get("/{analyzer_name}", response_model=AnalyzerInfo)
async def get_analyzer(analyzer_name: str):
    """
    Get details about a specific analyzer.

    Args:
        analyzer_name: Name of the analyzer (e.g., "health", "config")

    Returns:
        Detailed information about the analyzer
    """
    registry = get_global_registry()
    analyzer = registry.get_analyzer(analyzer_name)

    if not analyzer:
        raise HTTPException(
            status_code=404,
            detail=f"Analyzer '{analyzer_name}' not found"
        )

    return AnalyzerInfo(
        name=analyzer.objective_name,
        description=analyzer.get_description(),
        api_calls=analyzer.get_estimated_api_calls(),
        permissions=analyzer.get_required_permissions(),
        categories=[analyzer.objective_name],
    )
