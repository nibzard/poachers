# ABOUTME: Global game state management for team poaching game
from models import GameState
from typing import Dict, Any
import threading

# Global game state instance
game_state = GameState()
state_lock = threading.Lock()


def get_game_state() -> GameState:
    """Get the current game state (thread-safe)"""
    with state_lock:
        return game_state.copy(deep=True)


def update_game_state(updater_func) -> Dict[str, Any]:
    """Update game state with provided function (thread-safe)"""
    with state_lock:
        return updater_func(game_state)


class GameManager:
    """Centralized game management with thread safety"""

    @staticmethod
    def join_game(player_name: str) -> Dict[str, Any]:
        """Add a new player to the game"""
        def update(state: GameState) -> Dict[str, Any]:
            try:
                player = state.add_player(player_name)
                return {
                    "success": True,
                    "player": player,
                    "message": f"Player '{player_name}' joined the game"
                }
            except ValueError as e:
                return {
                    "success": False,
                    "error": str(e),
                    "message": f"Failed to join game: {str(e)}"
                }

        return update_game_state(update)

    @staticmethod
    def create_team(team_name: str, creator_name: str) -> Dict[str, Any]:
        """Create a new team with the creator as first member"""
        def update(state: GameState) -> Dict[str, Any]:
            try:
                creator = state.get_player_by_name(creator_name)
                if not creator:
                    return {
                        "success": False,
                        "error": f"Player '{creator_name}' not found",
                        "message": "You must join the game before creating a team"
                    }

                if creator.team_id:
                    return {
                        "success": False,
                        "error": "Player is already on a team",
                        "message": "You must leave your current team before creating a new one"
                    }

                team = state.create_team(team_name, creator.id)
                return {
                    "success": True,
                    "team": team,
                    "message": f"Team '{team_name}' created by '{creator_name}'"
                }
            except ValueError as e:
                return {
                    "success": False,
                    "error": str(e),
                    "message": f"Failed to create team: {str(e)}"
                }

        return update_game_state(update)

    @staticmethod
    def join_team(team_name: str, player_name: str) -> Dict[str, Any]:
        """Join an existing team"""
        def update(state: GameState) -> Dict[str, Any]:
            try:
                player = state.get_player_by_name(player_name)
                if not player:
                    return {
                        "success": False,
                        "error": f"Player '{player_name}' not found",
                        "message": "You must join the game before joining a team"
                    }

                if player.team_id:
                    return {
                        "success": False,
                        "error": "Player is already on a team",
                        "message": "You must leave your current team before joining another one"
                    }

                team = state.join_team(team_name, player.id)
                return {
                    "success": True,
                    "team": team,
                    "message": f"Player '{player_name}' joined team '{team_name}'"
                }
            except ValueError as e:
                return {
                    "success": False,
                    "error": str(e),
                    "message": f"Failed to join team: {str(e)}"
                }

        return update_game_state(update)

    @staticmethod
    def poach_player(target_player_name: str, poacher_team_name: str) -> Dict[str, Any]:
        """Poach a player from another team"""
        def update(state: GameState) -> Dict[str, Any]:
            try:
                target_player = state.get_player_by_name(target_player_name)
                if not target_player:
                    return {
                        "success": False,
                        "error": f"Player '{target_player_name}' not found",
                        "message": "Cannot poach non-existent player"
                    }

                poacher_team = state.get_team_by_name(poacher_team_name)
                if not poacher_team:
                    return {
                        "success": False,
                        "error": f"Team '{poacher_team_name}' not found",
                        "message": "Cannot poach with non-existent team"
                    }

                if not target_player.team_id:
                    return {
                        "success": False,
                        "error": "Target player is not on a team",
                        "message": "Cannot poach a free agent"
                    }

                if poacher_team.is_full:
                    return {
                        "success": False,
                        "error": "Poacher team is already full",
                        "message": "Cannot poach when your team is full"
                    }

                # Check if poacher team is trying to poach from itself
                if target_player.team_id == poacher_team.id:
                    return {
                        "success": False,
                        "error": "Cannot poach from your own team",
                        "message": "Target player is already on your team"
                    }

                result = state.poach_player(target_player.id, poacher_team.id)
                old_team = result["old_team"]
                new_team = result["new_team"]

                return {
                    "success": True,
                    "message": f"Player '{target_player_name}' poached from team to team '{poacher_team_name}'",
                    "old_team": old_team if not old_team.is_empty else None,
                    "new_team": new_team
                }
            except ValueError as e:
                return {
                    "success": False,
                    "error": str(e),
                    "message": f"Failed to poach player: {str(e)}"
                }

        return update_game_state(update)

    @staticmethod
    def get_status() -> Dict[str, Any]:
        """Get current game status"""
        state = get_game_state()
        return {
            "players": list(state.players.values()),
            "teams": list(state.teams.values()),
            "free_agents": state.free_agents,
            "total_players": len(state.players),
            "total_teams": len(state.teams),
            "free_agents_count": len(state.free_agents)
        }