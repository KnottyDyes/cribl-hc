"""
System-level API endpoints.

Provides version info, health checks, and system metadata.
"""

from fastapi import APIRouter

from cribl_hc import __version__

router = APIRouter()


@router.get("/version")
async def get_version():
    """
    Get API version information.

    Returns version, build info, and supported features.
    """
    return {
        "version": __version__,
        "api_version": "v1",
        "features": {
            "oauth_auth": True,
            "bearer_auth": True,
            "websocket_updates": True,
            "real_time_analysis": True,
        }
    }
