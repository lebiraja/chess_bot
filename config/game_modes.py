"""
Game Mode Definitions for Chess Bot

Defines various chess game modes with appropriate engine settings,
time management, and move delays for human-like play.
"""
from dataclasses import dataclass


@dataclass
class GameMode:
    """Configuration for a specific chess game mode."""

    id: str  # Unique identifier
    display_name: str  # Display name for UI
    time_seconds: int  # Total time per player (seconds)
    increment: int  # Time increment per move (seconds)
    search_depth: int  # Engine search depth (ply)
    time_limit: float  # Max seconds per move calculation
    min_delay: float  # Minimum human-like delay (seconds)
    max_delay: float  # Maximum human-like delay (seconds)
    description: str  # Human-readable description


# Game mode definitions
GAME_MODES = {
    "bullet_1": GameMode(
        id="bullet_1",
        display_name="Bullet 1+0",
        time_seconds=60,
        increment=0,
        search_depth=3,
        time_limit=1.5,
        min_delay=0.0,
        max_delay=0.3,
        description="Ultra-fast bullet - minimal think time",
    ),
    "bullet_2": GameMode(
        id="bullet_2",
        display_name="Bullet 2+1",
        time_seconds=120,
        increment=1,
        search_depth=3,
        time_limit=2.0,
        min_delay=0.0,
        max_delay=0.5,
        description="Bullet with small increment",
    ),
    "blitz_3": GameMode(
        id="blitz_3",
        display_name="Blitz 3+0",
        time_seconds=180,
        increment=0,
        search_depth=4,
        time_limit=3.0,
        min_delay=0.3,
        max_delay=0.8,
        description="Standard blitz - moderate thinking time",
    ),
    "blitz_5": GameMode(
        id="blitz_5",
        display_name="Blitz 5+0",
        time_seconds=300,
        increment=0,
        search_depth=5,
        time_limit=5.0,
        min_delay=0.5,
        max_delay=1.0,
        description="Comfortable blitz - standard format",
    ),
    "blitz_5_3": GameMode(
        id="blitz_5_3",
        display_name="Blitz 5+3",
        time_seconds=300,
        increment=3,
        search_depth=5,
        time_limit=6.0,
        min_delay=0.5,
        max_delay=1.5,
        description="Blitz with increment - more time for tactics",
    ),
    "rapid_10": GameMode(
        id="rapid_10",
        display_name="Rapid 10+0",
        time_seconds=600,
        increment=0,
        search_depth=5,
        time_limit=8.0,
        min_delay=1.0,
        max_delay=2.0,
        description="Rapid - time for positional play",
    ),
    "rapid_15": GameMode(
        id="rapid_15",
        display_name="Rapid 15+10",
        time_seconds=900,
        increment=10,
        search_depth=6,
        time_limit=12.0,
        min_delay=1.0,
        max_delay=3.0,
        description="Rapid with increment - best analysis time",
    ),
    "classical": GameMode(
        id="classical",
        display_name="Classical 30+0",
        time_seconds=1800,
        increment=0,
        search_depth=7,
        time_limit=20.0,
        min_delay=2.0,
        max_delay=5.0,
        description="Classical - full engine power",
    ),
}


def get_game_mode(mode_id: str) -> GameMode | None:
    """Get a game mode by ID."""
    return GAME_MODES.get(mode_id)


def list_game_modes() -> list[tuple[str, GameMode]]:
    """Get list of all game modes for UI display."""
    return sorted(GAME_MODES.items(), key=lambda x: x[1].time_seconds)
