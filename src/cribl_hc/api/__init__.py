"""
FastAPI web application for Cribl Health Check.

This module provides a REST API and WebSocket interface for the health check tool,
enabling web-based interaction with all core functionality.
"""

from cribl_hc.api.app import app

__all__ = ["app"]
