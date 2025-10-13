# Team Poaching Game

A multiplayer FastAPI-based game where students can join, create teams (max 2 members), and poach players from other teams.

## Game Rules

- Teams have a maximum of 2 members
- Player names must be unique
- Team names must be unique
- Players can only poach if their team has space available
- You cannot poach from your own team
- Teams are dissolved when they have no members

## Setup

This project uses [uv](https://docs.astral.sh/uv/) for Python management.

1. Clone the repository:
```bash
git clone https://github.com/nibzard/poachers.git
cd poachers
```

2. Install dependencies with uv:
```bash
uv sync
```

3. Run the server:
```bash
uv run python main.py
```

4. Game will be available at `http://localhost:8002`

### Alternative Setup (pip)

If you prefer to use pip:

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the server:
```bash
python main.py
```

## API Endpoints

### POST /join
Join the game as a new player.

**Request:**
```json
{
  "name": "PlayerName"
}
```

**Response (201):**
```json
{
  "message": "Player 'PlayerName' joined the game",
  "player": {
    "id": "uuid",
    "name": "PlayerName",
    "team_id": null,
    "joined_at": "2024-01-01T12:00:00"
  }
}
```

### POST /team
Create a new team or join an existing team.

**Create Team Request:**
```json
{
  "action": "create",
  "team_name": "TeamName",
  "creator_name": "CreatorName"
}
```

**Join Team Request:**
```json
{
  "action": "join",
  "team_name": "TeamName",
  "player_name": "PlayerName"
}
```

**Response (200):**
```json
{
  "message": "Team 'TeamName' created by 'CreatorName'",
  "team": {
    "id": "uuid",
    "name": "TeamName",
    "member_ids": ["uuid1", "uuid2"],
    "created_at": "2024-01-01T12:00:00",
    "is_full": false
  }
}
```

### GET /status
Get current game state including all players, teams, and free agents.

**Response (200):**
```json
{
  "game_stats": {
    "total_players": 5,
    "total_teams": 2,
    "free_agents_count": 1
  },
  "players": [
    {
      "id": "uuid",
      "name": "PlayerName",
      "team_id": "team-uuid",
      "joined_at": "2024-01-01T12:00:00"
    }
  ],
  "teams": [
    {
      "id": "uuid",
      "name": "TeamName",
      "member_ids": ["uuid1", "uuid2"],
      "created_at": "2024-01-01T12:00:00",
      "is_full": true,
      "member_count": 2
    }
  ],
  "free_agents": [
    {
      "id": "uuid",
      "name": "FreePlayer",
      "joined_at": "2024-01-01T12:00:00"
    }
  ]
}
```

### POST /poach
Poach a player from another team.

**Request:**
```json
{
  "target_player_name": "TargetPlayer",
  "poacher_team_name": "YourTeam"
}
```

**Response (200):**
```json
{
  "message": "Player 'TargetPlayer' poached from team to team 'YourTeam'",
  "new_team": {
    "id": "uuid",
    "name": "YourTeam",
    "member_ids": ["uuid1", "uuid2"],
    "is_full": true
  },
  "old_team": {
    "id": "uuid",
    "name": "OldTeam",
    "member_ids": ["remaining-uuid"],
    "is_full": false
  }
}
```

### GET /
Root endpoint with game information and rules.

## Example Game Flow

1. **Players join:**
   ```bash
   curl -X POST http://localhost:8002/join -H "Content-Type: application/json" -d '{"name": "Alice"}'
   curl -X POST http://localhost:8002/join -H "Content-Type: application/json" -d '{"name": "Bob"}'
   curl -X POST http://localhost:8002/join -H "Content-Type: application/json" -d '{"name": "Charlie"}'
   ```

2. **Create teams:**
   ```bash
   curl -X POST http://localhost:8002/team -H "Content-Type: application/json" -d '{"action": "create", "team_name": "TeamAlpha", "creator_name": "Alice"}'
   curl -X POST http://localhost:8002/team -H "Content-Type: application/json" -d '{"action": "join", "team_name": "TeamAlpha", "player_name": "Bob"}'
   ```

3. **Check status:**
   ```bash
   curl http://localhost:8002/status
   ```

4. **Poach players:**
   ```bash
   # Charlie creates a new team first
   curl -X POST http://localhost:8002/team -H "Content-Type: application/json" -d '{"action": "create", "team_name": "TeamBeta", "creator_name": "Charlie"}'

   # Now Charlie can poach
   curl -X POST http://localhost:8002/poach -H "Content-Type: application/json" -d '{"target_player_name": "Bob", "poacher_team_name": "TeamBeta"}'
   ```

## Error Handling

All endpoints return appropriate HTTP status codes and error messages:

- **400 Bad Request**: Invalid input data or game rule violations
- **500 Internal Server Error**: Unexpected server errors

Example error response:
```json
{
  "detail": "Player with name 'Alice' already exists"
}
```

## Architecture

- **FastAPI**: Web framework and API
- **Pydantic**: Data validation and serialization
- **uv**: Modern Python package and project management
- **Threading**: Thread-safe game state management
- **UUID**: Unique identifiers for players and teams

## File Structure

```
├── main.py              # FastAPI app and API endpoints
├── models.py            # Pydantic data models
├── game_state.py        # Game state management and business logic
├── pyproject.toml       # uv project configuration
├── uv.lock             # uv dependency lock file
├── requirements.txt     # Pip fallback dependencies
└── README.md           # This file
```