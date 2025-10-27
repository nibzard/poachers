# ABOUTME: FastAPI application for team poaching game using Turso SQL
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import os
import sys

# Add parent directory to path to import turso_game_state
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from turso_game_state import TursoGameManager

# Pydantic models for request/response
class JoinRequest(BaseModel):
    name: str

class TeamCreateRequest(BaseModel):
    action: str
    team_name: str
    creator_name: str

class TeamJoinRequest(BaseModel):
    action: str
    team_name: str
    player_name: str

class PoachRequest(BaseModel):
    target_player_name: str
    poacher_team_name: str

# Initialize FastAPI app
app = FastAPI(
    title="Team Poaching Game API",
    description="A multiplayer game where players can create teams of 2 and poach members from other teams",
    version="1.0.0"
)

# Initialize game manager
game_manager = TursoGameManager(
    db_url=os.getenv("TURSO_DATABASE_URL"),
    auth_token=os.getenv("TURSO_AUTH_TOKEN")
)

# Root endpoint
@app.get("/")
async def root():
    return {
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

# Get game status
@app.get("/status")
async def get_status():
    response = await game_manager.get_status()
    return {
        "game_stats": {
            "total_players": response["total_players"],
            "total_teams": response["total_teams"],
            "free_agents_count": response["free_agents_count"]
        },
        "players": response["players"],
        "teams": response["teams"],
        "free_agents": response["free_agents"]
    }

# Join game
@app.post("/join")
async def join_game(request: JoinRequest):
    result = await game_manager.join_game(request.name)
    if result["success"]:
        return {
            "message": result["message"],
            "player": result["player"]
        }
    else:
        raise HTTPException(status_code=400, detail=result["message"])

# Team operations
@app.post("/team")
async def team_operations(request: Dict[str, Any]):
    action = request.get("action")

    if action == "create":
        team_name = request.get("team_name")
        creator_name = request.get("creator_name")

        if not team_name or not creator_name:
            raise HTTPException(status_code=400, detail="team_name and creator_name are required for create action")

        result = await game_manager.create_team(team_name, creator_name)
        if result["success"]:
            team = result["team"].copy()
            team["is_full"] = len(team["member_ids"]) >= 2
            team["member_count"] = len(team["member_ids"])
            return {
                "message": result["message"],
                "team": team
            }
        else:
            raise HTTPException(status_code=400, detail=result["message"])

    elif action == "join":
        team_name = request.get("team_name")
        player_name = request.get("player_name")

        if not team_name or not player_name:
            raise HTTPException(status_code=400, detail="team_name and player_name are required for join action")

        result = await game_manager.join_team(team_name, player_name)
        if result["success"]:
            team = result["team"].copy()
            team["is_full"] = len(team["member_ids"]) >= 2
            team["member_count"] = len(team["member_ids"])
            return {
                "message": result["message"],
                "team": team
            }
        else:
            raise HTTPException(status_code=400, detail=result["message"])

    else:
        raise HTTPException(status_code=400, detail="Action must be either 'create' or 'join'")

# Poach player
@app.post("/poach")
async def poach_player(request: PoachRequest):
    result = await game_manager.poach_player(request.target_player_name, request.poacher_team_name)
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

        return response_data
    else:
        raise HTTPException(status_code=400, detail=result["message"])

# Health check for Vercel
@app.get("/health")
async def health_check():
    return {"status": "healthy"}