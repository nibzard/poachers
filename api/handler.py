# ABOUTME: Vercel serverless handler for FastAPI application using Mangum
import sys
import os

# Add parent directory to path to import main module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from mangum import Mangum

# Create the Mangum handler
handler = Mangum(app, lifespan="off")