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

            # Embed schema SQL directly to avoid file system issues in serverless
            schema_sql = """
-- Players table - stores individual player information
CREATE TABLE IF NOT EXISTS players (
    id TEXT PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    team_id TEXT,
    joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE SET NULL
);

-- Teams table - stores team information
CREATE TABLE IF NOT EXISTS teams (
    id TEXT PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Team members junction table - many-to-many relationship
CREATE TABLE IF NOT EXISTS team_members (
    team_id TEXT NOT NULL,
    player_id TEXT NOT NULL,
    joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (team_id, player_id),
    FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE,
    FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE CASCADE
);

-- Indexes for better performance
CREATE INDEX IF NOT EXISTS idx_players_name ON players(name);
CREATE INDEX IF NOT EXISTS idx_players_team_id ON players(team_id);
CREATE INDEX IF NOT EXISTS idx_teams_name ON teams(name);
CREATE INDEX IF NOT EXISTS idx_team_members_team_id ON team_members(team_id);
CREATE INDEX IF NOT EXISTS idx_team_members_player_id ON team_members(player_id);

-- Game statistics table
CREATE TABLE IF NOT EXISTS game_stats (
    stat_key TEXT PRIMARY KEY,
    stat_value INTEGER NOT NULL DEFAULT 0
);

-- Initialize game statistics
INSERT OR IGNORE INTO game_stats (stat_key, stat_value) VALUES ('total_players', 0);
INSERT OR IGNORE INTO game_stats (stat_key, stat_value) VALUES ('total_teams', 0);
"""

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
            max_team_size = await self.get_max_team_size()
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
            max_team_size = await self.get_max_team_size()

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

    async def leave_team(self, player_name: str) -> Dict[str, Any]:
        """Remove a player from their team and make them a free agent"""
        try:
            client = self._get_client()

            # Get player
            player_data = client.execute(
                "SELECT id, team_id FROM players WHERE name = ?",
                [player_name]
            )
            if len(player_data) == 0:
                return {
                    "success": False,
                    "message": f"Player '{player_name}' not found"
                }

            player_id = player_data[0][0]
            team_id = player_data[0][1]

            if not team_id:
                return {
                    "success": False,
                    "message": f"Player '{player_name}' is not on a team"
                }

            # Get team name before removal
            team_info = client.execute(
                "SELECT name FROM teams WHERE id = ?",
                [team_id]
            )
            team_name = team_info[0][0] if team_info else "Unknown"

            # Remove from team_members
            client.execute(
                "DELETE FROM team_members WHERE team_id = ? AND player_id = ?",
                [team_id, player_id]
            )

            # Update player's team_id to NULL
            client.execute(
                "UPDATE players SET team_id = NULL WHERE id = ?",
                [player_id]
            )

            # Check if team is now empty
            remaining_members = client.execute(
                "SELECT COUNT(*) FROM team_members WHERE team_id = ?",
                [team_id]
            )

            team_dissolved = False
            if remaining_members[0][0] == 0:
                # Delete empty team
                client.execute("DELETE FROM teams WHERE id = ?", [team_id])
                client.execute(
                    "UPDATE game_stats SET stat_value = stat_value - 1 WHERE stat_key = 'total_teams'"
                )
                team_dissolved = True

            # Get updated player info
            player_updated = client.execute(
                "SELECT id, name, team_id, joined_at FROM players WHERE id = ?",
                [player_id]
            )

            return {
                "success": True,
                "message": f"Player '{player_name}' left team '{team_name}' and is now a free agent" + 
                          (f". Team '{team_name}' was dissolved." if team_dissolved else ""),
                "player": {
                    "id": player_updated[0][0],
                    "name": player_updated[0][1],
                    "team_id": player_updated[0][2],
                    "joined_at": player_updated[0][3]
                },
                "team_dissolved": team_dissolved
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to leave team: {str(e)}"
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

    async def reset_database(self) -> Dict[str, Any]:
        """Reset the entire database - delete all data"""
        try:
            client = self._get_client()
            
            # Delete all data
            client.execute("DELETE FROM team_members")
            client.execute("DELETE FROM teams")
            client.execute("DELETE FROM players")
            client.execute("UPDATE game_stats SET stat_value = 0 WHERE stat_key IN ('total_players', 'total_teams')")
            
            return {
                "success": True,
                "message": "Database reset successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to reset database: {str(e)}"
            }

    async def delete_player(self, player_name: str) -> Dict[str, Any]:
        """Delete a player and remove them from their team"""
        try:
            client = self._get_client()
            
            # Get player info
            player_data = client.execute(
                "SELECT id, team_id FROM players WHERE name = ?",
                [player_name]
            )
            
            if len(player_data) == 0:
                return {
                    "success": False,
                    "message": f"Player '{player_name}' not found"
                }
            
            player_id = player_data[0][0]
            team_id = player_data[0][1]
            
            # Delete from team_members if in a team
            if team_id:
                client.execute(
                    "DELETE FROM team_members WHERE player_id = ?",
                    [player_id]
                )
                
                # Check if team is now empty
                remaining = client.execute(
                    "SELECT COUNT(*) FROM team_members WHERE team_id = ?",
                    [team_id]
                )
                
                if remaining[0][0] == 0:
                    # Delete empty team
                    client.execute("DELETE FROM teams WHERE id = ?", [team_id])
                    client.execute(
                        "UPDATE game_stats SET stat_value = stat_value - 1 WHERE stat_key = 'total_teams'"
                    )
            
            # Delete player
            client.execute("DELETE FROM players WHERE id = ?", [player_id])
            client.execute(
                "UPDATE game_stats SET stat_value = stat_value - 1 WHERE stat_key = 'total_players'"
            )
            
            return {
                "success": True,
                "message": f"Player '{player_name}' deleted successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to delete player: {str(e)}"
            }

    async def delete_team(self, team_name: str) -> Dict[str, Any]:
        """Delete a team and set all members as free agents"""
        try:
            client = self._get_client()
            
            # Get team info
            team_data = client.execute(
                "SELECT id FROM teams WHERE name = ?",
                [team_name]
            )
            
            if len(team_data) == 0:
                return {
                    "success": False,
                    "message": f"Team '{team_name}' not found"
                }
            
            team_id = team_data[0][0]
            
            # Set all team members as free agents
            client.execute(
                "UPDATE players SET team_id = NULL WHERE team_id = ?",
                [team_id]
            )
            
            # Delete team_members relationships
            client.execute(
                "DELETE FROM team_members WHERE team_id = ?",
                [team_id]
            )
            
            # Delete team
            client.execute("DELETE FROM teams WHERE id = ?", [team_id])
            client.execute(
                "UPDATE game_stats SET stat_value = stat_value - 1 WHERE stat_key = 'total_teams'"
            )
            
            return {
                "success": True,
                "message": f"Team '{team_name}' deleted successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to delete team: {str(e)}"
            }

    async def create_test_data(self) -> Dict[str, Any]:
        """Create test data for development"""
        try:
            # Create test players
            test_players = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank"]
            created_players = []
            
            for name in test_players:
                result = await self.join_game(name)
                if result["success"]:
                    created_players.append(name)
            
            # Create test teams
            if len(created_players) >= 4:
                await self.create_team("TeamAlpha", created_players[0])
                await self.join_team("TeamAlpha", created_players[1])
                
                await self.create_team("TeamBeta", created_players[2])
                await self.join_team("TeamBeta", created_players[3])
            
            return {
                "success": True,
                "message": f"Created {len(created_players)} test players and 2 teams"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to create test data: {str(e)}"
            }

    async def get_max_team_size(self) -> int:
        """Get the current max team size setting"""
        try:
            client = self._get_client()
            
            # Check if setting exists
            result = client.execute(
                "SELECT stat_value FROM game_stats WHERE stat_key = 'max_team_size'"
            )
            
            if len(result) > 0:
                return result[0][0]
            else:
                # Default to 2 if not set
                client.execute(
                    "INSERT OR IGNORE INTO game_stats (stat_key, stat_value) VALUES ('max_team_size', 2)"
                )
                return 2
        except Exception as e:
            return 2  # Default fallback

    async def set_max_team_size(self, size: int) -> Dict[str, Any]:
        """Set the maximum team size"""
        try:
            if size < 1 or size > 10:
                return {
                    "success": False,
                    "message": "Team size must be between 1 and 10"
                }
            
            client = self._get_client()
            
            # Insert or update the setting
            client.execute(
                "INSERT OR REPLACE INTO game_stats (stat_key, stat_value) VALUES ('max_team_size', ?)",
                [size]
            )
            
            return {
                "success": True,
                "message": f"Max team size set to {size}"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to set max team size: {str(e)}"
            }

    async def auto_assign_free_agents(self) -> Dict[str, Any]:
        """Automatically assign free agents to teams"""
        import random
        
        try:
            client = self._get_client()
            max_team_size = await self.get_max_team_size()
            
            # Get all free agents
            free_agents = client.execute(
                "SELECT id, name FROM players WHERE team_id IS NULL ORDER BY joined_at"
            )
            
            if len(free_agents) == 0:
                return {
                    "success": False,
                    "message": "No free agents to assign"
                }
            
            # Get teams with available spots
            all_teams = client.execute("""
                SELECT t.id, t.name, COUNT(tm.player_id) as member_count
                FROM teams t
                LEFT JOIN team_members tm ON t.id = tm.team_id
                GROUP BY t.id, t.name
                HAVING COUNT(tm.player_id) < ?
                ORDER BY member_count ASC
            """, [max_team_size])
            
            available_teams = list(all_teams)
            assigned_count = 0
            teams_created = 0
            
            # Adjectives and animals for team names
            adjectives = [
                "Lucky", "Happy", "Brave", "Swift", "Mighty", "Clever", "Bold",
                "Fierce", "Gentle", "Wise", "Quick", "Strong", "Bright", "Wild",
                "Noble", "Proud", "Fearless", "Agile", "Cosmic", "Magic"
            ]
            
            animals = [
                "Parakeet", "Monkey", "Tiger", "Eagle", "Dragon", "Phoenix", 
                "Wolf", "Lion", "Falcon", "Panther", "Bear", "Fox", "Hawk",
                "Leopard", "Dolphin", "Shark", "Cobra", "Jaguar", "Raven", "Owl"
            ]
            
            for player_id, player_name in free_agents:
                team_assigned = False
                
                # Try to assign to existing team with space
                for team_id, team_name, member_count in available_teams:
                    current_count = client.execute(
                        "SELECT COUNT(*) FROM team_members WHERE team_id = ?",
                        [team_id]
                    )
                    
                    if current_count[0][0] < max_team_size:
                        # Add player to this team
                        joined_at = datetime.utcnow().isoformat()
                        client.execute(
                            "INSERT INTO team_members (team_id, player_id, joined_at) VALUES (?, ?, ?)",
                            [team_id, player_id, joined_at]
                        )
                        client.execute(
                            "UPDATE players SET team_id = ? WHERE id = ?",
                            [team_id, player_id]
                        )
                        assigned_count += 1
                        team_assigned = True
                        
                        # Update the available teams list if team is now full
                        if current_count[0][0] + 1 >= max_team_size:
                            available_teams = [(tid, tname, tcount) for tid, tname, tcount in available_teams if tid != team_id]
                        
                        break
                
                # If no team available, create a new one
                if not team_assigned:
                    # Generate unique team name
                    max_attempts = 50
                    for _ in range(max_attempts):
                        adj = random.choice(adjectives)
                        animal = random.choice(animals)
                        new_team_name = f"{adj}{animal}"
                        
                        # Check if name exists
                        existing = client.execute(
                            "SELECT id FROM teams WHERE name = ?",
                            [new_team_name]
                        )
                        
                        if len(existing) == 0:
                            # Create new team with this player
                            team_id = await self.get_next_id()
                            created_at = datetime.utcnow().isoformat()
                            
                            client.execute(
                                "INSERT INTO teams (id, name, created_at) VALUES (?, ?, ?)",
                                [team_id, new_team_name, created_at]
                            )
                            
                            # Add player to team
                            client.execute(
                                "INSERT INTO team_members (team_id, player_id, joined_at) VALUES (?, ?, ?)",
                                [team_id, player_id, created_at]
                            )
                            client.execute(
                                "UPDATE players SET team_id = ? WHERE id = ?",
                                [team_id, player_id]
                            )
                            
                            # Update stats
                            client.execute(
                                "UPDATE game_stats SET stat_value = stat_value + 1 WHERE stat_key = 'total_teams'"
                            )
                            
                            assigned_count += 1
                            teams_created += 1
                            
                            # Add to available teams if not full
                            if max_team_size > 1:
                                available_teams.append((team_id, new_team_name, 1))
                            
                            break
            
            message = f"Assigned {assigned_count} free agents to teams"
            if teams_created > 0:
                message += f" (created {teams_created} new teams)"
            
            return {
                "success": True,
                "message": message,
                "assigned_count": assigned_count,
                "teams_created": teams_created
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to auto-assign free agents: {str(e)}"
            }
