# ABOUTME: Vercel serverless function entry point for team poaching game
from http.server import BaseHTTPRequestHandler
import json
import uuid
from datetime import datetime
from urllib.parse import urlparse, parse_qs
import os

# Simple in-memory storage (for demo - in production you'd use a database)
class SimpleGameManager:
    def __init__(self):
        self.players = {}
        self.teams = {}
        self.free_agents = []
        self.stats = {"total_players": 0, "total_teams": 0}

    def join_game(self, player_name):
        if player_name in self.players:
            return {"success": False, "message": f"Player '{player_name}' already exists"}

        player_id = str(uuid.uuid4())
        player = {
            "id": player_id,
            "name": player_name,
            "team_id": None,
            "joined_at": datetime.utcnow().isoformat()
        }

        self.players[player_name] = player
        self.free_agents.append(player_name)
        self.stats["total_players"] += 1

        return {
            "success": True,
            "player": player,
            "message": f"Player '{player_name}' joined the game"
        }

    def create_team(self, team_name, creator_name):
        if team_name in self.teams:
            return {"success": False, "message": f"Team '{team_name}' already exists"}

        if creator_name not in self.players:
            return {"success": False, "message": "You must join the game before creating a team"}

        creator = self.players[creator_name]
        if creator["team_id"]:
            return {"success": False, "message": "You must leave your current team before creating a new one"}

        team_id = str(uuid.uuid4())
        team = {
            "id": team_id,
            "name": team_name,
            "member_ids": [creator["id"]],
            "created_at": datetime.utcnow().isoformat()
        }

        self.teams[team_name] = team
        creator["team_id"] = team_id

        if creator_name in self.free_agents:
            self.free_agents.remove(creator_name)

        self.stats["total_teams"] += 1

        return {
            "success": True,
            "team": team,
            "message": f"Team '{team_name}' created by '{creator_name}'"
        }

    def join_team(self, team_name, player_name):
        if player_name not in self.players:
            return {"success": False, "message": "You must join the game before joining a team"}

        if team_name not in self.teams:
            return {"success": False, "message": f"Team '{team_name}' not found"}

        player = self.players[player_name]
        if player["team_id"]:
            return {"success": False, "message": "You must leave your current team before joining another one"}

        team = self.teams[team_name]
        if len(team["member_ids"]) >= 2:
            return {"success": False, "message": f"Team '{team_name}' is already full"}

        team["member_ids"].append(player["id"])
        player["team_id"] = team["id"]

        if player_name in self.free_agents:
            self.free_agents.remove(player_name)

        return {
            "success": True,
            "team": team,
            "message": f"Player '{player_name}' joined team '{team_name}'"
        }

    def poach_player(self, target_player_name, poacher_team_name):
        if target_player_name not in self.players:
            return {"success": False, "message": f"Player '{target_player_name}' not found"}

        if poacher_team_name not in self.teams:
            return {"success": False, "message": f"Team '{poacher_team_name}' not found"}

        target_player = self.players[target_player_name]
        if not target_player["team_id"]:
            return {"success": False, "message": "Cannot poach a free agent"}

        poacher_team = self.teams[poacher_team_name]
        if len(poacher_team["member_ids"]) >= 2:
            return {"success": False, "message": "Cannot poach when your team is full"}

        if target_player["team_id"] == poacher_team["id"]:
            return {"success": False, "message": "Target player is already on your team"}

        # Find old team
        old_team_name = None
        old_team = None
        for name, team in self.teams.items():
            if team["id"] == target_player["team_id"]:
                old_team_name = name
                old_team = team.copy()
                break

        # Update old team
        if old_team_name and old_team:
            old_team["member_ids"].remove(target_player["id"])
            if old_team["member_ids"]:
                self.teams[old_team_name] = old_team
            else:
                del self.teams[old_team_name]
                self.stats["total_teams"] -= 1
                old_team = None

        # Update new team
        poacher_team["member_ids"].append(target_player["id"])
        target_player["team_id"] = poacher_team["id"]

        return {
            "success": True,
            "message": f"Player '{target_player_name}' poached to team '{poacher_team_name}'",
            "old_team": old_team,
            "new_team": poacher_team
        }

    def get_status(self):
        free_agents = []
        for player_name in self.free_agents:
            if player_name in self.players:
                free_agents.append(self.players[player_name])

        teams_list = []
        for team in self.teams.values():
            team_copy = team.copy()
            team_copy["is_full"] = len(team["member_ids"]) >= 2
            team_copy["member_count"] = len(team["member_ids"])
            teams_list.append(team_copy)

        return {
            "players": list(self.players.values()),
            "teams": teams_list,
            "free_agents": free_agents,
            "total_players": self.stats["total_players"],
            "total_teams": self.stats["total_teams"],
            "free_agents_count": len(free_agents)
        }

# Global game manager instance
game_manager = SimpleGameManager()

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
            response = game_manager.get_status()
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
                result = game_manager.join_game(data['name'])
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
                    result = game_manager.create_team(data['team_name'], data['creator_name'])
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
                    result = game_manager.join_team(data['team_name'], data['player_name'])
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
                result = game_manager.poach_player(data['target_player_name'], data['poacher_team_name'])
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