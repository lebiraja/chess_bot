"""
Endgame Tablebase Integration

Uses Syzygy tablebases for perfect endgame play when few pieces remain.
"""
from pathlib import Path
from typing import Optional

import chess

# Try to import syzygy support
try:
    import chess.syzygy

    SYZYGY_AVAILABLE = True
except ImportError:
    SYZYGY_AVAILABLE = False


class EndgameTablebase:
    """
    Endgame tablebase for perfect play with few pieces.

    Uses Syzygy tablebases to provide optimal moves in endgames
    with 6 or fewer pieces.
    """

    def __init__(self, tablebase_path: Optional[Path] = None):
        """
        Initialize the endgame tablebase.

        Args:
            tablebase_path: Path to Syzygy tablebase files.
                           If None or not found, tablebase is disabled.
        """
        self.enabled = False
        self.tablebase = None
        self.max_pieces = 6  # Maximum pieces for tablebase lookup

        if not SYZYGY_AVAILABLE:
            print("Warning: chess.syzygy not available. Endgame tablebases disabled.")
            return

        if tablebase_path is None:
            tablebase_path = Path.home() / "chess" / "syzygy"

        if tablebase_path.exists():
            try:
                self.tablebase = chess.syzygy.open_tablebase(str(tablebase_path))
                self.enabled = True
                print(f"Loaded Syzygy tablebases from {tablebase_path}")
            except Exception as e:
                print(f"Warning: Could not load tablebases: {e}")
        else:
            print(
                f"Tablebase path not found: {tablebase_path}. "
                "Endgame tablebases disabled."
            )

    def probe_wdl(self, board: chess.Board) -> Optional[int]:
        """
        Probe the Win-Draw-Loss value for a position.

        Args:
            board: The chess board to probe

        Returns:
            WDL value: 2=win, 1=cursed win, 0=draw, -1=blessed loss, -2=loss
            None if position not in tablebase
        """
        if not self.enabled or not self._can_probe(board):
            return None

        try:
            return self.tablebase.probe_wdl(board)
        except KeyError:
            return None

    def probe_dtz(self, board: chess.Board) -> Optional[int]:
        """
        Probe the Distance-To-Zeroing value for a position.

        DTZ is the number of half-moves to the next capture or pawn move.

        Args:
            board: The chess board to probe

        Returns:
            DTZ value, or None if position not in tablebase
        """
        if not self.enabled or not self._can_probe(board):
            return None

        try:
            return self.tablebase.probe_dtz(board)
        except KeyError:
            return None

    def get_best_move(self, board: chess.Board) -> Optional[chess.Move]:
        """
        Get the best move according to the tablebase.

        For winning positions: Returns the move that leads to the fastest win.
        For drawing positions: Returns a move that maintains the draw.
        For losing positions: Returns the move that delays the loss longest.

        Args:
            board: The chess board

        Returns:
            The best move according to tablebase, or None if not available
        """
        if not self.enabled or not self._can_probe(board):
            return None

        wdl = self.probe_wdl(board)
        if wdl is None:
            return None

        best_move = None
        best_dtz = None

        for move in board.legal_moves:
            board.push(move)

            try:
                child_wdl = self.tablebase.probe_wdl(board)
                child_dtz = self.tablebase.probe_dtz(board)
            except KeyError:
                board.pop()
                continue

            board.pop()

            # After our move, the position is from opponent's perspective
            # So we negate the values
            child_wdl = -child_wdl
            child_dtz = -child_dtz if child_dtz is not None else 0

            # Prefer moves based on WDL and DTZ
            if best_move is None:
                best_move = move
                best_dtz = child_dtz
            elif wdl > 0:  # We're winning - minimize DTZ (fastest win)
                if child_wdl > 0 and (best_dtz is None or child_dtz < best_dtz):
                    best_move = move
                    best_dtz = child_dtz
            elif wdl == 0:  # Draw - maintain it
                if child_wdl == 0:
                    best_move = move
                    best_dtz = child_dtz
            else:  # We're losing - maximize DTZ (delay loss)
                if best_dtz is None or child_dtz > best_dtz:
                    best_move = move
                    best_dtz = child_dtz

        return best_move

    def _can_probe(self, board: chess.Board) -> bool:
        """Check if the position can be probed in the tablebase."""
        # Count pieces
        piece_count = len(board.piece_map())

        # Only probe if few pieces and no castling rights
        if piece_count > self.max_pieces:
            return False

        # Syzygy doesn't handle castling
        if board.has_castling_rights(chess.WHITE) or board.has_castling_rights(
            chess.BLACK
        ):
            return False

        return True

    def close(self):
        """Close the tablebase."""
        if self.tablebase:
            self.tablebase.close()
            self.tablebase = None
            self.enabled = False
