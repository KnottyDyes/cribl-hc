#!/usr/bin/env python3
"""
Development server for Cribl Health Check API.

Quick start script to run the FastAPI application locally for development.
"""

import sys
import argparse
import uvicorn
import socket

def find_free_port():
    """Find a free port on the system."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run Cribl Health Check API server')
    parser.add_argument('--port', type=int, default=8080, help='Port to run on (0 for auto-assign)')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--reload', action='store_true', help='Enable auto-reload')
    args = parser.parse_args()

    # Auto-assign port if 0
    port = args.port
    if port == 0:
        port = find_free_port()

    # Print port for Tauri to capture (must be first output line)
    print(f"PORT:{port}", flush=True)
    sys.stdout.flush()

    uvicorn.run(
        "cribl_hc.api.app:app",
        host=args.host,
        port=port,
        reload=args.reload,
        log_level="info",
    )
