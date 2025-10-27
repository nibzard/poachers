# Simple test handler to debug
import sys
import os
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def handler(event, context):
    try:
        from main import app
        from mangum import Mangum
        
        h = Mangum(app, lifespan="off")
        return h(event, context)
    except Exception as e:
        return {
            'statusCode': 500,
            'body': f'Error: {str(e)}\n\nTraceback:\n{traceback.format_exc()}'
        }
