# ABOUTME: Vercel serverless adapter for FastAPI application
from fastapi import FastAPI
from mangum import Mangum
import os
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the FastAPI app from index.py
from index import app

# Create Vercel handler using Mangum
handler = Mangum(app)