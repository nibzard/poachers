# ABOUTME: FastAPI application for team poaching game
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from models import JoinRequest, TeamCreateRequest, TeamJoinRequest, PoachRequest, LeaveTeamRequest, StatusResponse
from turso_game_state import TursoGameManager
from typing import Dict, Any
import uvicorn
import os

# Initialize game manager with Turso
GameManager = TursoGameManager()

app = FastAPI(
    title="Team Poaching Game",
    description="A multiplayer game where players can create teams and poach members",
    version="1.0.0"
)


@app.post("/join")
async def join_game(request: JoinRequest) -> Dict[str, Any]:
    """
    Join the game as a new player

    - **player_name**: Player name (must be unique)
    """
    try:
        result = await GameManager.join_game(request.player_name)
        if result["success"]:
            player = result["player"]
            return JSONResponse(
                status_code=201,
                content={
                    "message": result["message"],
                    "player": player if isinstance(player, dict) else {
                        "id": str(player.id),
                        "name": player.name,
                        "team_id": str(player.team_id) if player.team_id else None,
                        "joined_at": player.joined_at.isoformat()
                    }
                }
            )
        else:
            raise HTTPException(status_code=400, detail=result["message"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/team")
async def manage_team(request: Dict[str, str]) -> Dict[str, Any]:
    """
    Create a new team or join an existing team

    Two modes:
    - **create**: {"action": "create", "team_name": "TeamName", "creator_name": "PlayerName"}
    - **join**: {"action": "join", "team_name": "TeamName", "player_name": "PlayerName"}
    """
    try:
        action = request.get("action")

        if action == "create":
            team_name = request.get("team_name")
            creator_name = request.get("creator_name")

            if not team_name or not creator_name:
                raise HTTPException(status_code=400, detail="team_name and creator_name are required for create action")

            result = await GameManager.create_team(team_name, creator_name)

        elif action == "join":
            team_name = request.get("team_name")
            player_name = request.get("player_name")

            if not team_name or not player_name:
                raise HTTPException(status_code=400, detail="team_name and player_name are required for join action")

            result = await GameManager.join_team(team_name, player_name)

        else:
            raise HTTPException(status_code=400, detail="Action must be either 'create' or 'join'")

        if result["success"]:
            team = result["team"]
            # Handle both dict and object responses
            if isinstance(team, dict):
                team_data = team
            else:
                team_data = {
                    "id": str(team.id),
                    "name": team.name,
                    "member_ids": [str(member_id) for member_id in team.member_ids],
                    "created_at": team.created_at.isoformat(),
                    "is_full": team.is_full
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

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/status")
async def get_status() -> Dict[str, Any]:
    """
    Get current game state including all players, teams, and free agents
    """
    try:
        status = await GameManager.get_status()

        players_data = []
        for player in status["players"]:
            if isinstance(player, dict):
                players_data.append(player)
            else:
                players_data.append({
                    "id": str(player.id),
                    "name": player.name,
                    "team_id": str(player.team_id) if player.team_id else None,
                    "joined_at": player.joined_at.isoformat()
                })

        teams_data = []
        for team in status["teams"]:
            if isinstance(team, dict):
                teams_data.append(team)
            else:
                teams_data.append({
                    "id": str(team.id),
                    "name": team.name,
                    "member_ids": [str(member_id) for member_id in team.member_ids],
                    "created_at": team.created_at.isoformat(),
                    "is_full": team.is_full,
                    "member_count": len(team.member_ids)
                })

        free_agents_data = []
        for player in status["free_agents"]:
            if isinstance(player, dict):
                free_agents_data.append(player)
            else:
                free_agents_data.append({
                    "id": str(player.id),
                    "name": player.name,
                    "joined_at": player.joined_at.isoformat()
                })

        return JSONResponse(
            status_code=200,
            content={
                "game_stats": {
                    "total_players": status["total_players"],
                    "total_teams": status["total_teams"],
                    "free_agents_count": status["free_agents_count"]
                },
                "players": players_data,
                "teams": teams_data,
                "free_agents": free_agents_data
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/poach")
async def poach_player(request: PoachRequest) -> Dict[str, Any]:
    """
    Poach a player from another team to join your team

    - **target_player_name**: Name of the player to poach
    - **poacher_team_name**: Name of your team (must have space available)
    """
    try:
        result = await GameManager.poach_player(request.target_player_name, request.poacher_team_name)

        if result["success"]:
            new_team = result["new_team"]
            # Handle both dict and object responses
            if isinstance(new_team, dict):
                new_team_data = new_team
            else:
                new_team_data = {
                    "id": str(new_team.id),
                    "name": new_team.name,
                    "member_ids": [str(member_id) for member_id in new_team.member_ids],
                    "is_full": new_team.is_full
                }
            
            response_data = {
                "message": result["message"],
                "new_team": new_team_data
            }

            if result["old_team"]:
                old_team = result["old_team"]
                if isinstance(old_team, dict):
                    response_data["old_team"] = old_team
                else:
                    response_data["old_team"] = {
                        "id": str(old_team.id),
                        "name": old_team.name,
                        "member_ids": [str(member_id) for member_id in old_team.member_ids],
                        "is_full": old_team.is_full
                    }
            else:
                response_data["old_team"] = {
                    "message": "Old team was dissolved (no members remaining)"
                }

            return JSONResponse(status_code=200, content=response_data)
        else:
            raise HTTPException(status_code=400, detail=result["message"])

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/leave")
async def leave_team(request: LeaveTeamRequest) -> Dict[str, Any]:
    """
    Leave your current team and become a free agent
    
    - **player_name**: Name of the player who wants to leave their team
    """
    try:
        result = await GameManager.leave_team(request.player_name)
        
        if result["success"]:
            player = result["player"]
            return JSONResponse(
                status_code=200,
                content={
                    "message": result["message"],
                    "player": player if isinstance(player, dict) else {
                        "id": str(player.id),
                        "name": player.name,
                        "team_id": str(player.team_id) if player.team_id else None,
                        "joined_at": player.joined_at.isoformat()
                    },
                    "team_dissolved": result.get("team_dissolved", False)
                }
            )
        else:
            raise HTTPException(status_code=400, detail=result["message"])
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


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
            "POST /poach": "Poach a player from another team",
            "POST /leave": "Leave your current team and become a free agent"
        },
        "rules": {
            "teams": "Maximum 2 members per team",
            "poaching": "Can only poach if your team has space available",
            "names": "Player and team names must be unique"
        }
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)