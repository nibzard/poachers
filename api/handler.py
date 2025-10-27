# ABOUTME: Vercel serverless handler for FastAPI application
from http.server import BaseHTTPRequestHandler
import json
import asyncio

# Import FastAPI app
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.handle_request('GET')

    def do_POST(self):
        self.handle_request('POST')

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def handle_request(self, method):
        try:
            # Create a test client for FastAPI
            from fastapi.testclient import TestClient
            client = TestClient(app)

            # Read request body for POST requests
            content_length = int(self.headers.get('Content-Length', 0))
            body = None
            if content_length > 0:
                body = self.rfile.read(content_length)

            # Make request to FastAPI app
            if method == 'GET':
                response = client.get(self.path)
            elif method == 'POST':
                headers = dict(self.headers)
                if body:
                    response = client.post(self.path, content=body, headers=headers)
                else:
                    response = client.post(self.path)

            # Send response
            self.send_response(response.status_code)

            # Copy headers from FastAPI response
            for key, value in response.headers.items():
                if key.lower() not in ['content-length', 'transfer-encoding']:
                    self.send_header(key, value)

            # Add CORS headers
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')

            self.end_headers()

            # Send response body
            self.wfile.write(response.content)

        except Exception as e:
            # Handle errors
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()

            error_response = {
                "error": str(e),
                "message": "Internal server error"
            }
            self.wfile.write(json.dumps(error_response).encode())