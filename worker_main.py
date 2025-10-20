# ABOUTME: Cloudflare Workers entry point for team poaching game
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from models import JoinRequest, TeamCreateRequest, TeamJoinRequest, PoachRequest, StatusResponse
from kv_game_state import KVGameManager
from typing import Dict, Any
import json

# Create FastAPI app
app = FastAPI(
    title="Team Poaching Game",
    description="A multiplayer game where players can create teams and poach members",
    version="1.0.0"
)

# Global game manager (will be initialized with KV namespace)
game_manager = None


def init_game_manager(kv_namespace):
    """Initialize the game manager with KV namespace"""
    global game_manager
    game_manager = KVGameManager(kv_namespace)


@app.post("/join")
async def join_game(request: JoinRequest) -> Dict[str, Any]:
    """
    Join the game as a new player

    - **name**: Player name (must be unique)
    """
    if not game_manager:
        raise HTTPException(status_code=500, detail="Game manager not initialized")

    result = await game_manager.join_game(request.name)
    if result["success"]:
        return JSONResponse(
            status_code=201,
            content={
                "message": result["message"],
                "player": {
                    "id": result["player"]["id"],
                    "name": result["player"]["name"],
                    "team_id": result["player"].get("team_id"),
                    "joined_at": result["player"]["joined_at"]
                }
            }
        )
    else:
        raise HTTPException(status_code=400, detail=result["message"])


@app.post("/team")
async def manage_team(request: Dict[str, str]) -> Dict[str, Any]:
    """
    Create a new team or join an existing team

    Two modes:
    - **create**: {"action": "create", "team_name": "TeamName", "creator_name": "PlayerName"}
    - **join**: {"action": "join", "team_name": "TeamName", "player_name": "PlayerName"}
    """
    if not game_manager:
        raise HTTPException(status_code=500, detail="Game manager not initialized")

    action = request.get("action")

    if action == "create":
        team_name = request.get("team_name")
        creator_name = request.get("creator_name")

        if not team_name or not creator_name:
            raise HTTPException(status_code=400, detail="team_name and creator_name are required for create action")

        result = await game_manager.create_team(team_name, creator_name)

    elif action == "join":
        team_name = request.get("team_name")
        player_name = request.get("player_name")

        if not team_name or not player_name:
            raise HTTPException(status_code=400, detail="team_name and player_name are required for join action")

        result = await game_manager.join_team(team_name, player_name)

    else:
        raise HTTPException(status_code=400, detail="Action must be either 'create' or 'join'")

    if result["success"]:
        team_data = {
            "id": result["team"]["id"],
            "name": result["team"]["name"],
            "member_ids": result["team"]["member_ids"],
            "created_at": result["team"]["created_at"],
            "is_full": len(result["team"]["member_ids"]) >= 2,
            "member_count": len(result["team"]["member_ids"])
        }
        return JSONResponse(
            status_code=200,
            content={
                "message": result["message"],
                "team": team_data
            }
        )
    else:
        raise HTTPException(status_code=400, detail=result["message"])


@app.get("/status")
async def get_status() -> Dict[str, Any]:
    """
    Get current game state including all players, teams, and free agents
    """
    if not game_manager:
        raise HTTPException(status_code=500, detail="Game manager not initialized")

    status = await game_manager.get_status()

    return JSONResponse(
        status_code=200,
        content={
            "game_stats": {
                "total_players": status["total_players"],
                "total_teams": status["total_teams"],
                "free_agents_count": status["free_agents_count"]
            },
            "players": status["players"],
            "teams": status["teams"],
            "free_agents": status["free_agents"]
        }
    )


@app.post("/poach")
async def poach_player(request: PoachRequest) -> Dict[str, Any]:
    """
    Poach a player from another team to join your team

    - **target_player_name**: Name of the player to poach
    - **poacher_team_name**: Name of your team (must have space available)
    """
    if not game_manager:
        raise HTTPException(status_code=500, detail="Game manager not initialized")

    result = await game_manager.poach_player(request.target_player_name, request.poacher_team_name)

    if result["success"]:
        response_data = {
            "message": result["message"],
            "new_team": {
                "id": result["new_team"]["id"],
                "name": result["new_team"]["name"],
                "member_ids": result["new_team"]["member_ids"],
                "is_full": len(result["new_team"]["member_ids"]) >= 2
            }
        }

        if result["old_team"]:
            response_data["old_team"] = {
                "id": result["old_team"]["id"],
                "name": result["old_team"]["name"],
                "member_ids": result["old_team"]["member_ids"],
                "is_full": len(result["old_team"]["member_ids"]) >= 2
            }
        else:
            response_data["old_team"] = {
                "message": "Old team was dissolved (no members remaining)"
            }

        return JSONResponse(status_code=200, content=response_data)
    else:
        raise HTTPException(status_code=400, detail=result["message"])


@app.get("/")
async def root():
    """
    Root endpoint with game information
    """
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


# Cloudflare Workers handler
async def handler(request):
    """Cloudflare Workers request handler"""
    # Initialize game manager with KV namespace
    if not game_manager:
        init_game_manager(request.env.GAME_STATE_KV)

    # Convert request to FastAPI format
    method = request.method.lower()
    path = request.url.path

    try:
        if method == "post" and path == "/join":
            data = await request.json()
            join_request = JoinRequest(**data)
            return await join_game(join_request)

        elif method == "post" and path == "/team":
            data = await request.json()
            return await manage_team(data)

        elif method == "get" and path == "/status":
            return await get_status()

        elif method == "post" and path == "/poach":
            data = await request.json()
            poach_request = PoachRequest(**data)
            return await poach_player(poach_request)

        elif method == "get" and path == "/":
            return await root()

        else:
            return JSONResponse(
                status_code=404,
                content={"error": "Endpoint not found"}
            )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Internal server error: {str(e)}"}
        )


# Export for Cloudflare Workers
fetch = handler