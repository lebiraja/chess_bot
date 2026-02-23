"""
Chess Bot Configuration Settings
"""
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Settings:
    """Configuration settings for the chess bot."""

    # Game mode
    game_mode: str = "blitz_5"  # Selected game mode ID

    # Engine settings
    search_depth: int = 5  # Ply (half-moves) to search
    time_limit: float = 10.0  # Max seconds per move
    use_quiescence: bool = True  # Extend search for captures/checks
    quiescence_depth: int = 8  # Max depth for quiescence search

    # Opening book settings
    opening_book_path: Path = field(
        default_factory=lambda: Path(__file__).parent / "openings.json"
    )
    opening_book_depth: int = 10  # Use book for first N moves
    use_opening_book: bool = True

    # Endgame tablebase settings
    tablebase_path: Path = field(
        default_factory=lambda: Path.home() / "chess" / "syzygy"
    )
    use_tablebase: bool = True

    # Browser automation settings
    headless: bool = False  # Show browser window
    chess_com_url: str = "https://www.chess.com/play/online"

    # Move timing (human-like behavior)
    min_move_delay: float = 1.0  # Minimum seconds before moving
    max_move_delay: float = 3.0  # Maximum seconds before moving

    # Evaluation weights (for tuning)
    material_weight: float = 1.0
    position_weight: float = 0.3
    mobility_weight: float = 0.1
    king_safety_weight: float = 0.5
    pawn_structure_weight: float = 0.2

    # Transposition table
    tt_size_mb: int = 256  # Size of transposition table in MB

    # Logging
    log_level: str = "INFO"
    log_moves: bool = True  # Log each move made


# Default settings instance
default_settings = Settings()
