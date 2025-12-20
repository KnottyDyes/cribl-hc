#!/usr/bin/env python3
"""
Development server for Cribl Health Check API.

Quick start script to run the FastAPI application locally for development.
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "cribl_hc.api.app:app",
        host="0.0.0.0",
        port=8080,
        reload=True,  # Auto-reload on code changes
        log_level="info",
    )
