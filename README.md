# Team Poaching Game

A multiplayer FastAPI-based game where students can join, create teams (max 2 members), poach players from other teams, and leave teams to become free agents.

🚀 **Live Demo:** https://poachers.vercel.app

## Game Rules

- Teams have a maximum of 2 members
- Player names must be unique
- Team names must be unique
- Players can only poach if their team has space available
- You cannot poach from your own team
- Players can leave their team to become free agents
- Teams are automatically dissolved when they have no members

## Quick Start

The easiest way to use the API is via the live deployment:

**API Base URL:** https://poachers.vercel.app

No setup required! Jump directly to the [Example Game Flow](#example-game-flow) section.

## Local Development Setup

This project uses [uv](https://docs.astral.sh/uv/) for Python management.

1. **Clone the repository:**
   ```bash
   git clone https://github.com/nibzard/poachers.git
   cd poachers
   ```

2. **Install dependencies with uv:**
   ```bash
   uv sync
   ```

3. **Set up environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your Turso database credentials
   ```

4. **Run the development server:**
   ```bash
   uv run python main.py
   ```

5. **Game will be available at:** `http://localhost:8002`


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

### POST /leave
Leave your current team and become a free agent.

**Request:**
```json
{
  "player_name": "PlayerName"
}
```

**Response (200):**
```json
{
  "message": "Player 'PlayerName' left team 'TeamName' and is now a free agent",
  "player": {
    "id": "uuid",
    "name": "PlayerName",
    "team_id": null,
    "joined_at": "2024-01-01T12:00:00"
  },
  "team_dissolved": false
}
```

**Note:** If you're the last member of a team, the team will be automatically dissolved and `team_dissolved` will be `true`.

### GET /
Root endpoint with game information and rules.

## Example Game Flow

**Using the live API (https://poachers.vercel.app):**

1. **Players join:**
   ```bash
   curl -X POST https://poachers.vercel.app/join -H "Content-Type: application/json" -d '{"name": "Alice"}'
   curl -X POST https://poachers.vercel.app/join -H "Content-Type: application/json" -d '{"name": "Bob"}'
   curl -X POST https://poachers.vercel.app/join -H "Content-Type: application/json" -d '{"name": "Charlie"}'
   ```

2. **Create teams:**
   ```bash
   curl -X POST https://poachers.vercel.app/team -H "Content-Type: application/json" -d '{"action": "create", "team_name": "TeamAlpha", "creator_name": "Alice"}'
   curl -X POST https://poachers.vercel.app/team -H "Content-Type: application/json" -d '{"action": "join", "team_name": "TeamAlpha", "player_name": "Bob"}'
   ```

3. **Check status:**
   ```bash
   curl https://poachers.vercel.app/status
   ```

4. **Poach players:**
   ```bash
   # Charlie creates a new team first
   curl -X POST https://poachers.vercel.app/team -H "Content-Type: application/json" -d '{"action": "create", "team_name": "TeamBeta", "creator_name": "Charlie"}'

   # Now Charlie can poach Bob from TeamAlpha
   curl -X POST https://poachers.vercel.app/poach -H "Content-Type: application/json" -d '{"target_player_name": "Bob", "poacher_team_name": "TeamBeta"}'
   ```

5. **Leave a team:**
   ```bash
   # Alice leaves TeamAlpha (team will be dissolved since she's the only member)
   curl -X POST https://poachers.vercel.app/leave -H "Content-Type: application/json" -d '{"player_name": "Alice"}'
   ```

**For local development, replace `https://poachers.vercel.app` with `http://localhost:8002`**

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

## Technology Stack

- **FastAPI** - Modern Python web framework for building APIs
- **Turso** - Distributed SQLite database for persistent storage
- **Pydantic** - Data validation and serialization
- **Mangum** - ASGI adapter for serverless deployment
- **uv** - Fast Python package and project manager
- **Vercel** - Serverless deployment platform

## Database

This game uses [Turso](https://turso.tech/) - a distributed SQLite database for persistent data storage across serverless deployments.

### Setting Up Your Own Database

1. **Create Turso database:**
   ```bash
   # Install Turso CLI
   curl -sSfL https://get.tur.so/install.sh | sh

   # Create database
   turso db create poachers

   # Get connection URL and auth token
   turso db show poachers --url
   turso db tokens create poachers
   ```

2. **Configure environment variables:**
   ```bash
   # For local development
   cp .env.example .env
   # Edit .env with your Turso credentials:
   # TURSO_DATABASE_URL=libsql://your-database-url
   # TURSO_AUTH_TOKEN=your-auth-token
   ```

3. **For Vercel deployment:**
   ```bash
   # Set environment variables in Vercel
   vercel env add TURSO_DATABASE_URL
   vercel env add TURSO_AUTH_TOKEN
   ```

The database schema is automatically initialized on first connection. Tables created:
- `players` - Player information
- `teams` - Team information  
- `team_members` - Team membership relationships
- `game_stats` - Game statistics

## Deployment

The game is deployed on Vercel at https://poachers.vercel.app

To deploy your own instance:

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy (will prompt for configuration)
vercel

# Deploy to production
vercel --prod
```

Make sure to set up the Turso environment variables in your Vercel project settings.

## File Structure

```
├── main.py              # FastAPI app and API endpoints
├── models.py            # Pydantic data models and request/response schemas
├── game_state.py        # In-memory game state (for local development)
├── turso_game_state.py  # Turso database operations (used in production)
├── api/
│   ├── index.py         # Vercel serverless function entry point
│   └── requirements.txt # Python dependencies for deployment
├── db/
│   └── schema.sql       # Database schema definition (embedded in code)
├── .env.example         # Environment variables template
├── pyproject.toml       # uv project configuration
├── requirements.txt     # Generated Python dependencies
├── vercel.json          # Vercel deployment configuration
└── README.md            # This file
```

## Contributing

Contributions are welcome! Feel free to open issues or submit pull requests.

## License

MIT