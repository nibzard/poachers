# ABOUTME: Vercel serverless handler for FastAPI application
import sys
import os

# Add parent directory to path to import main module
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from main import app

# Export the app directly for ASGI
# Vercel will handle the ASGI server automatically
__all__ = ['app']