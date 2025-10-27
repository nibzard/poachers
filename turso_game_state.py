# ABOUTME: Simple Turso SQL database game state management for team poaching game
from typing import Dict, Any
import uuid
import os
from datetime import datetime
from libsql_client import create_client_sync


class TursoGameManager:
    """Game management using Turso SQL database"""

    def __init__(self, db_url: str = None, auth_token: str = None):
        if not db_url:
            db_url = os.getenv("TURSO_DATABASE_URL")
        if not auth_token:
            auth_token = os.getenv("TURSO_AUTH_TOKEN")

        self.db_url = db_url
        self.auth_token = auth_token
        self.client = None
        self._initialized = False

    def _get_client(self):
        """Get or create Turso client"""
        if not self.client:
            self.client = create_client_sync(
                url=self.db_url,
                auth_token=self.auth_token
            )
            self._initialize_database()
        return self.client

    def _initialize_database(self):
        """Initialize database schema if not exists"""
        if self._initialized:
            return

        try:
            client = self._get_client()

            # Read and execute schema
            with open('db/schema.sql', 'r') as f:
                schema_sql = f.read()

            # Execute schema statements
            statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]
            for statement in statements:
                if statement:
                    try:
                        client.execute(statement)
                    except Exception as e:
                        # Ignore errors for statements that might already exist
                        if "already exists" not in str(e):
                            raise e

            self._initialized = True

        except Exception as e:
            raise Exception(f"Failed to initialize database: {str(e)}")

    async def get_next_id(self) -> str:
        """Generate a new UUID for players/teams"""
        return str(uuid.uuid4())

    async def join_game(self, player_name: str) -> Dict[str, Any]:
        """Add a new player to the game"""
        try:
            client = self._get_client()

            # Check if player already exists
            existing = client.execute(
                "SELECT id FROM players WHERE name = ?",
                [player_name]
            )
            if len(existing) > 0:
                return {
                    "success": False,
                    "message": f"Player '{player_name}' already exists"
                }

            player_id = await self.get_next_id()
            joined_at = datetime.utcnow().isoformat()

            # Insert player
            client.execute(
                "INSERT INTO players (id, name, team_id, joined_at) VALUES (?, ?, ?, ?)",
                [player_id, player_name, None, joined_at]
            )

            # Update stats
            client.execute(
                "UPDATE game_stats SET stat_value = stat_value + 1 WHERE stat_key = 'total_players'"
            )

            return {
                "success": True,
                "player": {
                    "id": player_id,
                    "name": player_name,
                    "team_id": None,
                    "joined_at": joined_at
                },
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
            client = self._get_client()

            # Check if team already exists
            existing = client.execute(
                "SELECT id FROM teams WHERE name = ?",
                [team_name]
            )
            if len(existing) > 0:
                return {
                    "success": False,
                    "message": f"Team '{team_name}' already exists"
                }

            # Get creator
            creator = client.execute(
                "SELECT id, team_id FROM players WHERE name = ?",
                [creator_name]
            )
            if len(creator) == 0:
                return {
                    "success": False,
                    "message": "You must join the game before creating a team"
                }

            creator_data = creator[0]
            if creator_data[1]:  # team_id is not None
                return {
                    "success": False,
                    "message": "You must leave your current team before creating a new one"
                }

            # Create team
            team_id = await self.get_next_id()
            created_at = datetime.utcnow().isoformat()

            client.execute(
                "INSERT INTO teams (id, name, created_at) VALUES (?, ?, ?)",
                [team_id, team_name, created_at]
            )

            # Update creator's team
            client.execute(
                "UPDATE players SET team_id = ? WHERE id = ?",
                [team_id, creator_data[0]]
            )

            # Add to team members
            client.execute(
                "INSERT INTO team_members (team_id, player_id, joined_at) VALUES (?, ?, ?)",
                [team_id, creator_data[0], created_at]
            )

            # Update stats
            client.execute(
                "UPDATE game_stats SET stat_value = stat_value + 1 WHERE stat_key = 'total_teams'"
            )

            return {
                "success": True,
                "team": {
                    "id": team_id,
                    "name": team_name,
                    "member_ids": [creator_data[0]],
                    "created_at": created_at
                },
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
            client = self._get_client()

            # Get player
            player = client.execute(
                "SELECT id, team_id FROM players WHERE name = ?",
                [player_name]
            )
            if len(player) == 0:
                return {
                    "success": False,
                    "message": "You must join the game before joining a team"
                }

            player_data = player[0]
            if player_data[1]:  # team_id is not None
                return {
                    "success": False,
                    "message": "You must leave your current team before joining another one"
                }

            # Get team
            team = client.execute(
                "SELECT id FROM teams WHERE name = ?",
                [team_name]
            )
            if len(team) == 0:
                return {
                    "success": False,
                    "message": f"Team '{team_name}' not found"
                }

            team_id = team[0][0]

            # Check team size
            members = client.execute(
                "SELECT COUNT(*) FROM team_members WHERE team_id = ?",
                [team_id]
            )
            if members[0][0] >= 2:
                return {
                    "success": False,
                    "message": f"Team '{team_name}' is already full"
                }

            # Update player's team
            client.execute(
                "UPDATE players SET team_id = ? WHERE id = ?",
                [team_id, player_data[0]]
            )

            # Add to team members
            joined_at = datetime.utcnow().isoformat()
            client.execute(
                "INSERT INTO team_members (team_id, player_id, joined_at) VALUES (?, ?, ?)",
                [team_id, player_data[0], joined_at]
            )

            # Get team members for response
            team_members = client.execute(
                "SELECT player_id FROM team_members WHERE team_id = ?",
                [team_id]
            )
            member_ids = [row[0] for row in team_members]

            return {
                "success": True,
                "team": {
                    "id": team_id,
                    "name": team_name,
                    "member_ids": member_ids,
                    "created_at": joined_at
                },
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
            client = self._get_client()

            # Get target player
            target = client.execute(
                "SELECT id, team_id FROM players WHERE name = ?",
                [target_player_name]
            )
            if len(target) == 0:
                return {
                    "success": False,
                    "message": f"Player '{target_player_name}' not found"
                }

            target_data = target[0]
            if not target_data[1]:  # team_id is None
                return {
                    "success": False,
                    "message": "Cannot poach a free agent"
                }

            # Get poacher team
            poacher = client.execute(
                "SELECT id FROM teams WHERE name = ?",
                [poacher_team_name]
            )
            if len(poacher) == 0:
                return {
                    "success": False,
                    "message": f"Team '{poacher_team_name}' not found"
                }

            poacher_team_id = poacher[0][0]

            # Check if poacher team is full
            poacher_members = client.execute(
                "SELECT COUNT(*) FROM team_members WHERE team_id = ?",
                [poacher_team_id]
            )
            if poacher_members[0][0] >= 2:
                return {
                    "success": False,
                    "message": "Cannot poach when your team is full"
                }

            # Don't poach from own team
            if target_data[1] == poacher_team_id:
                return {
                    "success": False,
                    "message": "Target player is already on your team"
                }

            # Get old team
            old_team = client.execute(
                "SELECT name FROM teams WHERE id = ?",
                [target_data[1]]
            )
            old_team_name = old_team[0][0]

            # Remove from old team members
            client.execute(
                "DELETE FROM team_members WHERE player_id = ?",
                [target_data[0]]
            )

            # Add to new team members
            poached_at = datetime.utcnow().isoformat()
            client.execute(
                "INSERT INTO team_members (team_id, player_id, joined_at) VALUES (?, ?, ?)",
                [poacher_team_id, target_data[0], poached_at]
            )

            # Update player's team
            client.execute(
                "UPDATE players SET team_id = ? WHERE id = ?",
                [poacher_team_id, target_data[0]]
            )

            # Check if old team is empty
            old_team_members = client.execute(
                "SELECT COUNT(*) FROM team_members WHERE team_id = ?",
                [target_data[1]]
            )

            old_team_response = None
            if old_team_members[0][0] == 0:
                # Delete empty team
                client.execute("DELETE FROM teams WHERE id = ?", [target_data[1]])
                client.execute(
                    "UPDATE game_stats SET stat_value = stat_value - 1 WHERE stat_key = 'total_teams'"
                )
                old_team_response = None
            else:
                # Get remaining members
                remaining = client.execute(
                    "SELECT player_id FROM team_members WHERE team_id = ?",
                    [target_data[1]]
                )
                old_team_response = {
                    "id": target_data[1],
                    "name": old_team_name,
                    "member_ids": [row[0] for row in remaining]
                }

            # Get new team members
            new_team_members = client.execute(
                "SELECT player_id FROM team_members WHERE team_id = ?",
                [poacher_team_id]
            )
            new_team_response = {
                "id": poacher_team_id,
                "name": poacher_team_name,
                "member_ids": [row[0] for row in new_team_members]
            }

            return {
                "success": True,
                "message": f"Player '{target_player_name}' poached to team '{poacher_team_name}'",
                "old_team": old_team_response,
                "new_team": new_team_response
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to poach player: {str(e)}"
            }

    async def get_status(self) -> Dict[str, Any]:
        """Get current game status"""
        try:
            client = self._get_client()

            # Get all players
            players = client.execute(
                "SELECT id, name, team_id, joined_at FROM players ORDER BY joined_at"
            )
            player_list = []
            for row in players:
                player_list.append({
                    "id": row[0],
                    "name": row[1],
                    "team_id": row[2],
                    "joined_at": row[3]
                })

            # Get all teams with member counts
            teams = client.execute("""
                SELECT t.id, t.name, t.created_at, COUNT(tm.player_id) as member_count
                FROM teams t
                LEFT JOIN team_members tm ON t.id = tm.team_id
                GROUP BY t.id, t.name, t.created_at
                ORDER BY t.created_at
            """)

            team_list = []
            for row in teams:
                team_dict = {
                    "id": row[0],
                    "name": row[1],
                    "member_ids": [],  # Will be populated below
                    "created_at": row[2],
                    "is_full": row[3] >= 2,
                    "member_count": row[3]
                }
                team_list.append(team_dict)

            # Populate member_ids for each team
            for team in team_list:
                members = client.execute(
                    "SELECT player_id FROM team_members WHERE team_id = ?",
                    [team["id"]]
                )
                team["member_ids"] = [row[0] for row in members]

            # Get free agents (players without teams)
            free_agents = [p for p in player_list if p["team_id"] is None]

            # Get stats
            stats = client.execute("SELECT stat_key, stat_value FROM game_stats")
            stats_dict = {row[0]: row[1] for row in stats}

            return {
                "players": player_list,
                "teams": team_list,
                "free_agents": free_agents,
                "total_players": stats_dict.get("total_players", 0),
                "total_teams": stats_dict.get("total_teams", 0),
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
