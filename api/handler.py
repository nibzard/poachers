# ABOUTME: Vercel serverless handler for FastAPI application using Mangum
import sys
import os
import traceback

# Add parent directory to path to import main module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from main import app
    from mangum import Mangum
    
    # Create the Mangum handler
    handler = Mangum(app, lifespan="off")
except Exception as e:
    # If initialization fails, create a fallback handler
    def handler(event, context):
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'text/plain'},
            'body': f'Initialization Error: {str(e)}\n\nTraceback:\n{traceback.format_exc()}'
        }