"""
Vercel Serverless Function entry point for FastAPI backend.
Imports the FastAPI app instance from app.main.
Note: For persistent WebSocket (/ws/live) connections and ML/OpenCV caching,
deploying to a persistent container/PaaS (Render, Railway, Fly.io, HF Spaces)
is recommended over serverless execution.
"""

from app.main import app

# Export app for Vercel
__all__ = ["app"]
