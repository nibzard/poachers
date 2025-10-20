# ABOUTME: Cloudflare KV storage game state management for team poaching game
from models import Player, Team
from typing import Dict, Any, List, Optional
import json
import uuid
from datetime import datetime


class KVGameManager:
    """Game management using Cloudflare KV storage"""

    def __init__(self, kv_namespace):
        self.kv = kv_namespace
        self.prefix = {
            "players": "player:",
            "teams": "team:",
            "free_agents": "free_agents:",
            "stats": "stats:"
        }

    async def get_next_id(self) -> str:
        """Generate a new UUID for players/teams"""
        return str(uuid.uuid4())

    async def join_game(self, player_name: str) -> Dict[str, Any]:
        """Add a new player to the game"""
        try:
            # Check if player already exists
            existing_player = await self.kv.get(f"{self.prefix['players']}{player_name}")
            if existing_player:
                return {
                    "success": False,
                    "message": f"Player '{player_name}' already exists"
                }

            player_id = await self.get_next_id()
            player = Player(
                id=player_id,
                name=player_name,
                team_id=None,
                joined_at=datetime.utcnow()
            )

            # Store player
            await self.kv.put(
                f"{self.prefix['players']}{player_name}",
                json.dumps({
                    "id": player.id,
                    "name": player.name,
                    "team_id": player.team_id,
                    "joined_at": player.joined_at.isoformat()
                })
            )

            # Add to free agents
            await self._add_to_free_agents(player_name)

            # Update stats
            await self._increment_stat("total_players")

            return {
                "success": True,
                "player": player,
                "message": f"Player '{player_name}' joined the game"
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to join game: {str(e)}"
            }

    async def create_team(self, team_name: str, creator_name: str) -> Dict[str, Any]:
        """Create a new team with the creator as first member"""
        try:
            # Check if team already exists
            existing_team = await self.kv.get(f"{self.prefix['teams']}{team_name}")
            if existing_team:
                return {
                    "success": False,
                    "message": f"Team '{team_name}' already exists"
                }

            # Get creator
            player_data = await self.kv.get(f"{self.prefix['players']}{creator_name}")
            if not player_data:
                return {
                    "success": False,
                    "message": "You must join the game before creating a team"
                }

            player = json.loads(player_data)
            if player.get("team_id"):
                return {
                    "success": False,
                    "message": "You must leave your current team before creating a new one"
                }

            # Create team
            team_id = await self.get_next_id()
            team = Team(
                id=team_id,
                name=team_name,
                member_ids=[player["id"]],
                created_at=datetime.utcnow()
            )

            # Store team
            await self.kv.put(
                f"{self.prefix['teams']}{team_name}",
                json.dumps({
                    "id": team.id,
                    "name": team.name,
                    "member_ids": team.member_ids,
                    "created_at": team.created_at.isoformat()
                })
            )

            # Update player with team
            player["team_id"] = team_id
            await self.kv.put(
                f"{self.prefix['players']}{creator_name}",
                json.dumps(player)
            )

            # Remove from free agents
            await self._remove_from_free_agents(creator_name)

            # Update stats
            await self._increment_stat("total_teams")

            return {
                "success": True,
                "team": team,
                "message": f"Team '{team_name}' created by '{creator_name}'"
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to create team: {str(e)}"
            }

    async def join_team(self, team_name: str, player_name: str) -> Dict[str, Any]:
        """Join an existing team"""
        try:
            # Get player
            player_data = await self.kv.get(f"{self.prefix['players']}{player_name}")
            if not player_data:
                return {
                    "success": False,
                    "message": "You must join the game before joining a team"
                }

            player = json.loads(player_data)
            if player.get("team_id"):
                return {
                    "success": False,
                    "message": "You must leave your current team before joining another one"
                }

            # Get team
            team_data = await self.kv.get(f"{self.prefix['teams']}{team_name}")
            if not team_data:
                return {
                    "success": False,
                    "message": f"Team '{team_name}' not found"
                }

            team = json.loads(team_data)
            if len(team["member_ids"]) >= 2:
                return {
                    "success": False,
                    "message": f"Team '{team_name}' is already full"
                }

            # Update team members
            team["member_ids"].append(player["id"])
            await self.kv.put(
                f"{self.prefix['teams']}{team_name}",
                json.dumps(team)
            )

            # Update player with team
            player["team_id"] = team["id"]
            await self.kv.put(
                f"{self.prefix['players']}{player_name}",
                json.dumps(player)
            )

            # Remove from free agents
            await self._remove_from_free_agents(player_name)

            return {
                "success": True,
                "team": team,
                "message": f"Player '{player_name}' joined team '{team_name}'"
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to join team: {str(e)}"
            }

    async def poach_player(self, target_player_name: str, poacher_team_name: str) -> Dict[str, Any]:
        """Poach a player from another team"""
        try:
            # Get target player
            target_data = await self.kv.get(f"{self.prefix['players']}{target_player_name}")
            if not target_data:
                return {
                    "success": False,
                    "message": f"Player '{target_player_name}' not found"
                }

            target_player = json.loads(target_data)
            if not target_player.get("team_id"):
                return {
                    "success": False,
                    "message": "Cannot poach a free agent"
                }

            # Get poacher team
            poacher_data = await self.kv.get(f"{self.prefix['teams']}{poacher_team_name}")
            if not poacher_data:
                return {
                    "success": False,
                    "message": f"Team '{poacher_team_name}' not found"
                }

            poacher_team = json.loads(poacher_data)
            if len(poacher_team["member_ids"]) >= 2:
                return {
                    "success": False,
                    "message": "Cannot poach when your team is full"
                }

            # Don't poach from own team
            if target_player["team_id"] == poacher_team["id"]:
                return {
                    "success": False,
                    "message": "Target player is already on your team"
                }

            # Get old team
            old_team_name = await self._get_team_name_by_id(target_player["team_id"])
            old_team_data = await self.kv.get(f"{self.prefix['teams']}{old_team_name}")
            old_team = json.loads(old_team_data)

            # Update old team (remove player)
            old_team["member_ids"].remove(target_player["id"])
            if old_team["member_ids"]:
                await self.kv.put(
                    f"{self.prefix['teams']}{old_team_name}",
                    json.dumps(old_team)
                )
            else:
                # Delete empty team
                await self.kv.delete(f"{self.prefix['teams']}{old_team_name}")
                await self._decrement_stat("total_teams")
                old_team = None

            # Update new team (add player)
            poacher_team["member_ids"].append(target_player["id"])
            await self.kv.put(
                f"{self.prefix['teams']}{poacher_team_name}",
                json.dumps(poacher_team)
            )

            # Update player's team
            target_player["team_id"] = poacher_team["id"]
            await self.kv.put(
                f"{self.prefix['players']}{target_player_name}",
                json.dumps(target_player)
            )

            return {
                "success": True,
                "message": f"Player '{target_player_name}' poached to team '{poacher_team_name}'",
                "old_team": old_team,
                "new_team": poacher_team
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to poach player: {str(e)}"
            }

    async def get_status(self) -> Dict[str, Any]:
        """Get current game status"""
        try:
            # Get all players
            players = []
            player_list = await self.kv.list({"prefix": self.prefix["players"]})
            for key in player_list.keys:
                player_data = await self.kv.get(key.name)
                if player_data:
                    players.append(json.loads(player_data))

            # Get all teams
            teams = []
            team_list = await self.kv.list({"prefix": self.prefix["teams"]})
            for key in team_list.keys:
                team_data = await self.kv.get(key.name)
                if team_data:
                    team_dict = json.loads(team_data)
                    team_dict["is_full"] = len(team_dict["member_ids"]) >= 2
                    team_dict["member_count"] = len(team_dict["member_ids"])
                    teams.append(team_dict)

            # Get free agents
            free_agents_data = await self.kv.get(self.prefix["free_agents"])
            free_agents = json.loads(free_agents_data) if free_agents_data else []

            # Get stats
            stats_data = await self.kv.get(self.prefix["stats"])
            stats = json.loads(stats_data) if stats_data else {
                "total_players": 0,
                "total_teams": 0
            }

            # Get free agent player objects
            free_agents = []
            for player_name in free_agents:
                player_data = await self.kv.get(f"{self.prefix['players']}{player_name}")
                if player_data:
                    free_agents.append(json.loads(player_data))

            return {
                "players": players,
                "teams": teams,
                "free_agents": free_agents,
                "total_players": stats.get("total_players", 0),
                "total_teams": stats.get("total_teams", 0),
                "free_agents_count": len(free_agents)
            }

        except Exception as e:
            return {
                "players": [],
                "teams": [],
                "free_agents": [],
                "total_players": 0,
                "total_teams": 0,
                "free_agents_count": 0,
                "error": str(e)
            }

    async def _add_to_free_agents(self, player_name: str):
        """Add player to free agents list"""
        free_agents_data = await self.kv.get(self.prefix["free_agents"])
        free_agents = json.loads(free_agents_data) if free_agents_data else []
        free_agents.append(player_name)
        await self.kv.put(self.prefix["free_agents"], json.dumps(free_agents))

    async def _remove_from_free_agents(self, player_name: str):
        """Remove player from free agents list"""
        free_agents_data = await self.kv.get(self.prefix["free_agents"])
        free_agents = json.loads(free_agents_data) if free_agents_data else []
        if player_name in free_agents:
            free_agents.remove(player_name)
        await self.kv.put(self.prefix["free_agents"], json.dumps(free_agents))

    async def _increment_stat(self, stat_name: str):
        """Increment a game statistic"""
        stats_data = await self.kv.get(self.prefix["stats"])
        stats = json.loads(stats_data) if stats_data else {}
        stats[stat_name] = stats.get(stat_name, 0) + 1
        await self.kv.put(self.prefix["stats"], json.dumps(stats))

    async def _decrement_stat(self, stat_name: str):
        """Decrement a game statistic"""
        stats_data = await self.kv.get(self.prefix["stats"])
        stats = json.loads(stats_data) if stats_data else {}
        stats[stat_name] = max(0, stats.get(stat_name, 0) - 1)
        await self.kv.put(self.prefix["stats"], json.dumps(stats))

    async def _get_team_name_by_id(self, team_id: str) -> Optional[str]:
        """Get team name by team ID"""
        team_list = await self.kv.list({"prefix": self.prefix["teams"]})
        for key in team_list.keys:
            team_data = await self.kv.get(key.name)
            if team_data:
                team = json.loads(team_data)
                if team["id"] == team_id:
                    return team["name"]
        return None