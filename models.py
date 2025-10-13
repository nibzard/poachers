# ABOUTME: Data models for team poaching game using Pydantic
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime
from uuid import UUID, uuid4


class Player(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str = Field(..., min_length=1, max_length=50)
    team_id: Optional[UUID] = None
    joined_at: datetime = Field(default_factory=datetime.utcnow)


class Team(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str = Field(..., min_length=1, max_length=50)
    member_ids: List[UUID] = Field(default_factory=list, max_length=2)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def is_full(self) -> bool:
        return len(self.member_ids) >= 2

    @property
    def is_empty(self) -> bool:
        return len(self.member_ids) == 0

    def add_member(self, player_id: UUID) -> bool:
        if self.is_full:
            return False
        if player_id not in self.member_ids:
            self.member_ids.append(player_id)
        return True

    def remove_member(self, player_id: UUID) -> bool:
        if player_id in self.member_ids:
            self.member_ids.remove(player_id)
            return True
        return False


class GameState(BaseModel):
    players: Dict[UUID, Player] = Field(default_factory=dict)
    teams: Dict[UUID, Team] = Field(default_factory=dict)

    @property
    def free_agents(self) -> List[Player]:
        return [player for player in self.players.values() if player.team_id is None]

    def get_player_by_name(self, name: str) -> Optional[Player]:
        for player in self.players.values():
            if player.name == name:
                return player
        return None

    def get_team_by_name(self, name: str) -> Optional[Team]:
        for team in self.teams.values():
            if team.name == name:
                return team
        return None

    def add_player(self, name: str) -> Player:
        if self.get_player_by_name(name):
            raise ValueError(f"Player with name '{name}' already exists")

        player = Player(name=name)
        self.players[player.id] = player
        return player

    def create_team(self, name: str, creator_id: UUID) -> Team:
        if self.get_team_by_name(name):
            raise ValueError(f"Team with name '{name}' already exists")

        team = Team(name=name)
        team.add_member(creator_id)

        self.teams[team.id] = team

        if creator_id in self.players:
            self.players[creator_id].team_id = team.id

        return team

    def join_team(self, team_name: str, player_id: UUID) -> Team:
        team = self.get_team_by_name(team_name)
        if not team:
            raise ValueError(f"Team '{team_name}' not found")

        if team.is_full:
            raise ValueError(f"Team '{team_name}' is already full")

        if player_id not in self.players:
            raise ValueError("Player not found")

        existing_player = self.players[player_id]
        if existing_player.team_id:
            raise ValueError("Player is already on a team")

        team.add_member(player_id)
        existing_player.team_id = team.id

        return team

    def poach_player(self, target_player_id: UUID, poacher_team_id: UUID) -> Dict[str, Team]:
        if target_player_id not in self.players:
            raise ValueError("Target player not found")

        if poacher_team_id not in self.teams:
            raise ValueError("Poacher team not found")

        target_player = self.players[target_player_id]
        poacher_team = self.teams[poacher_team_id]

        if not target_player.team_id:
            raise ValueError("Target player is not on a team")

        if poacher_team.is_full:
            raise ValueError("Poacher team is already full")

        old_team_id = target_player.team_id
        old_team = self.teams[old_team_id]

        old_team.remove_member(target_player_id)

        if old_team.is_empty:
            del self.teams[old_team_id]

        poacher_team.add_member(target_player_id)
        target_player.team_id = poacher_team_id

        return {"old_team": old_team, "new_team": poacher_team}


class JoinRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)


class TeamCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    creator_name: str = Field(..., min_length=1, max_length=50)


class TeamJoinRequest(BaseModel):
    team_name: str = Field(..., min_length=1, max_length=50)
    player_name: str = Field(..., min_length=1, max_length=50)


class PoachRequest(BaseModel):
    target_player_name: str = Field(..., min_length=1, max_length=50)
    poacher_team_name: str = Field(..., min_length=1, max_length=50)


class StatusResponse(BaseModel):
    players: List[Player]
    teams: List[Team]
    free_agents: List[Player]