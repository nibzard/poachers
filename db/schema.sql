-- ABOUTME: Database schema for team poaching game using Turso SQLite
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