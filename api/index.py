# ABOUTME: Vercel serverless handler for FastAPI application using Mangum
import sys
import os

# Add parent directory to path to import main module
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from main import app
from mangum import Mangum

# Create the Mangum handler
handler = Mangum(app, lifespan="off")