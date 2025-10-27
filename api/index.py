# ABOUTME: Vercel serverless function entry point for team poaching game using Turso SQL
from http.server import BaseHTTPRequestHandler
import json
import asyncio
import sys
import os
from urllib.parse import urlparse, parse_qs

# Add parent directory to path to import turso_game_state
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from turso_game_state import TursoGameManager

# Global game manager instance
game_manager = TursoGameManager(
    db_url=os.getenv("TURSO_DATABASE_URL"),
    auth_token=os.getenv("TURSO_AUTH_TOKEN")
)

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

        parsed_path = urlparse(self.path)

        if parsed_path.path == '/':
            response = {
                "game": "Team Poaching Game",
                "version": "1.0.0",
                "description": "A multiplayer game where players can create teams of 2 and poach members from other teams",
                "endpoints": {
                    "POST /join": "Join the game as a new player",
                    "POST /team": "Create a new team or join an existing team",
                    "GET /status": "Get current game state",
                    "POST /poach": "Poach a player from another team"
                },
                "rules": {
                    "teams": "Maximum 2 members per team",
                    "poaching": "Can only poach if your team has space available",
                    "names": "Player and team names must be unique"
                }
            }
        elif parsed_path.path == '/status':
            response = asyncio.run(game_manager.get_status())
            response = {
                "game_stats": {
                    "total_players": response["total_players"],
                    "total_teams": response["total_teams"],
                    "free_agents_count": response["free_agents_count"]
                },
                "players": response["players"],
                "teams": response["teams"],
                "free_agents": response["free_agents"]
            }
        else:
            self.send_response(404)
            response = {"error": "Endpoint not found"}

        self.wfile.write(json.dumps(response).encode())

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)

        try:
            data = json.loads(post_data.decode('utf-8'))
        except:
            data = {}

        parsed_path = urlparse(self.path)

        response = None
        status_code = 200

        if parsed_path.path == '/join':
            if 'name' not in data:
                status_code = 400
                response = {"error": "Missing 'name' field"}
            else:
                result = asyncio.run(game_manager.join_game(data['name']))
                if result["success"]:
                    status_code = 201
                    response = {
                        "message": result["message"],
                        "player": result["player"]
                    }
                else:
                    status_code = 400
                    response = {"error": result["message"]}

        elif parsed_path.path == '/team':
            if 'action' not in data:
                status_code = 400
                response = {"error": "Missing 'action' field"}
            elif data['action'] == 'create':
                if 'team_name' not in data or 'creator_name' not in data:
                    status_code = 400
                    response = {"error": "team_name and creator_name are required for create action"}
                else:
                    result = asyncio.run(game_manager.create_team(data['team_name'], data['creator_name']))
                    if result["success"]:
                        team = result["team"].copy()
                        team["is_full"] = len(team["member_ids"]) >= 2
                        team["member_count"] = len(team["member_ids"])
                        response = {
                            "message": result["message"],
                            "team": team
                        }
                    else:
                        status_code = 400
                        response = {"error": result["message"]}

            elif data['action'] == 'join':
                if 'team_name' not in data or 'player_name' not in data:
                    status_code = 400
                    response = {"error": "team_name and player_name are required for join action"}
                else:
                    result = asyncio.run(game_manager.join_team(data['team_name'], data['player_name']))
                    if result["success"]:
                        team = result["team"].copy()
                        team["is_full"] = len(team["member_ids"]) >= 2
                        team["member_count"] = len(team["member_ids"])
                        response = {
                            "message": result["message"],
                            "team": team
                        }
                    else:
                        status_code = 400
                        response = {"error": result["message"]}
            else:
                status_code = 400
                response = {"error": "Action must be either 'create' or 'join'"}

        elif parsed_path.path == '/poach':
            if 'target_player_name' not in data or 'poacher_team_name' not in data:
                status_code = 400
                response = {"error": "target_player_name and poacher_team_name are required"}
            else:
                result = asyncio.run(game_manager.poach_player(data['target_player_name'], data['poacher_team_name']))
                if result["success"]:
                    new_team = result["new_team"].copy()
                    new_team["is_full"] = len(new_team["member_ids"]) >= 2

                    response_data = {
                        "message": result["message"],
                        "new_team": new_team
                    }

                    if result["old_team"]:
                        old_team = result["old_team"].copy()
                        old_team["is_full"] = len(old_team["member_ids"]) >= 2
                        response_data["old_team"] = old_team
                    else:
                        response_data["old_team"] = {
                            "message": "Old team was dissolved (no members remaining)"
                        }

                    response = response_data
                else:
                    status_code = 400
                    response = {"error": result["message"]}

        else:
            status_code = 404
            response = {"error": "Endpoint not found"}

        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

        self.wfile.write(json.dumps(response).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()