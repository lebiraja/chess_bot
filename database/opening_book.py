"""
Opening Book for Chess Engine

Provides pre-computed opening moves to avoid calculation in the early game.
"""
import json
import random
from pathlib import Path
from typing import Optional

import chess


class OpeningBook:
    """
    Opening book that provides known good moves for common positions.

    Uses a dictionary mapping FEN positions to weighted move choices.
    """

    def __init__(self, book_path: Optional[Path] = None):
        """
        Initialize the opening book.

        Args:
            book_path: Path to the opening book JSON file.
                      If None, uses built-in openings.
        """
        self.book: dict[str, list[dict]] = {}

        if book_path and book_path.exists():
            self._load_from_file(book_path)
        else:
            self._load_builtin()

    def _load_from_file(self, path: Path):
        """Load opening book from JSON file."""
        with open(path) as f:
            self.book = json.load(f)

    def _load_builtin(self):
        """Load built-in opening moves."""
        # Common opening positions with weighted moves
        # Format: FEN (position only) -> [{move, weight}, ...]
        self.book = {
            # Starting position
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq": [
                {"move": "e2e4", "weight": 40},  # King's Pawn
                {"move": "d2d4", "weight": 35},  # Queen's Pawn
                {"move": "g1f3", "weight": 15},  # Reti Opening
                {"move": "c2c4", "weight": 10},  # English Opening
            ],
            # After 1.e4
            "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq": [
                {"move": "e7e5", "weight": 35},  # Open Game
                {"move": "c7c5", "weight": 30},  # Sicilian
                {"move": "e7e6", "weight": 20},  # French
                {"move": "c7c6", "weight": 15},  # Caro-Kann
            ],
            # After 1.e4 e5
            "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq": [
                {"move": "g1f3", "weight": 60},  # King's Knight
                {"move": "f1c4", "weight": 20},  # Italian Game
                {"move": "f2f4", "weight": 10},  # King's Gambit
                {"move": "b1c3", "weight": 10},  # Vienna
            ],
            # After 1.e4 e5 2.Nf3
            "rnbqkbnr/pppp1ppp/8/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq": [
                {"move": "b8c6", "weight": 70},  # Knight defense
                {"move": "g8f6", "weight": 20},  # Petrov
                {"move": "d7d6", "weight": 10},  # Philidor
            ],
            # After 1.e4 e5 2.Nf3 Nc6
            "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq": [
                {"move": "f1b5", "weight": 50},  # Ruy Lopez
                {"move": "f1c4", "weight": 30},  # Italian
                {"move": "d2d4", "weight": 20},  # Scotch
            ],
            # After 1.d4
            "rnbqkbnr/pppppppp/8/8/3P4/8/PPP1PPPP/RNBQKBNR b KQkq": [
                {"move": "d7d5", "weight": 40},  # Queen's Pawn Game
                {"move": "g8f6", "weight": 35},  # Indian Defenses
                {"move": "e7e6", "weight": 15},  # Queen's Pawn Game
                {"move": "f7f5", "weight": 10},  # Dutch
            ],
            # After 1.d4 d5
            "rnbqkbnr/ppp1pppp/8/3p4/3P4/8/PPP1PPPP/RNBQKBNR w KQkq": [
                {"move": "c2c4", "weight": 60},  # Queen's Gambit
                {"move": "g1f3", "weight": 25},  # Quiet
                {"move": "b1c3", "weight": 15},  # Veresov
            ],
            # After 1.d4 d5 2.c4 (Queen's Gambit)
            "rnbqkbnr/ppp1pppp/8/3p4/2PP4/8/PP2PPPP/RNBQKBNR b KQkq": [
                {"move": "e7e6", "weight": 45},  # QGD
                {"move": "c7c6", "weight": 35},  # Slav
                {"move": "d5c4", "weight": 20},  # QGA
            ],
            # After 1.d4 Nf6
            "rnbqkb1r/pppppppp/5n2/8/3P4/8/PPP1PPPP/RNBQKBNR w KQkq": [
                {"move": "c2c4", "weight": 50},  # Main line
                {"move": "g1f3", "weight": 30},  # Quiet
                {"move": "c1g5", "weight": 20},  # Trompowsky
            ],
            # After 1.d4 Nf6 2.c4
            "rnbqkb1r/pppppppp/5n2/8/2PP4/8/PP2PPPP/RNBQKBNR b KQkq": [
                {"move": "e7e6", "weight": 35},  # QID/Nimzo
                {"move": "g7g6", "weight": 35},  # King's Indian
                {"move": "c7c5", "weight": 20},  # Benoni
                {"move": "e7e5", "weight": 10},  # Budapest
            ],
            # Sicilian after 1.e4 c5
            "rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq": [
                {"move": "g1f3", "weight": 50},  # Open Sicilian
                {"move": "b1c3", "weight": 25},  # Closed
                {"move": "c2c3", "weight": 15},  # Alapin
                {"move": "d2d4", "weight": 10},  # Smith-Morra
            ],
            # French after 1.e4 e6
            "rnbqkbnr/pppp1ppp/4p3/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq": [
                {"move": "d2d4", "weight": 70},  # Main line
                {"move": "d2d3", "weight": 20},  # King's Indian Attack
                {"move": "g1f3", "weight": 10},  # Quiet
            ],
            # Caro-Kann after 1.e4 c6
            "rnbqkbnr/pp1ppppp/2p5/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq": [
                {"move": "d2d4", "weight": 60},  # Main line
                {"move": "b1c3", "weight": 25},  # Two Knights
                {"move": "g1f3", "weight": 15},  # Quiet
            ],
        }

    def get_move(
        self, board: chess.Board, random_choice: bool = True
    ) -> Optional[chess.Move]:
        """
        Get an opening book move for the current position.

        Args:
            board: The current board position
            random_choice: If True, choose randomly weighted by weights.
                          If False, always choose the highest weight.

        Returns:
            A chess.Move if the position is in the book, None otherwise.
        """
        # Get position key (FEN without move counters and en passant)
        fen_parts = board.fen().split()
        position_key = " ".join(fen_parts[:4])  # position, turn, castling, ep

        # Try without en passant if not found
        if position_key not in self.book:
            position_key = " ".join(fen_parts[:3])  # position, turn, castling

        if position_key not in self.book:
            return None

        moves = self.book[position_key]

        if random_choice:
            # Weighted random choice
            total_weight = sum(m["weight"] for m in moves)
            r = random.uniform(0, total_weight)
            cumulative = 0
            for m in moves:
                cumulative += m["weight"]
                if r <= cumulative:
                    move_uci = m["move"]
                    break
            else:
                move_uci = moves[0]["move"]
        else:
            # Choose highest weight
            move_uci = max(moves, key=lambda x: x["weight"])["move"]

        # Parse and validate the move
        try:
            move = chess.Move.from_uci(move_uci)
            if move in board.legal_moves:
                return move
        except ValueError:
            pass

        return None

    def is_in_book(self, board: chess.Board) -> bool:
        """Check if the current position is in the opening book."""
        fen_parts = board.fen().split()
        position_key = " ".join(fen_parts[:4])
        if position_key in self.book:
            return True
        position_key = " ".join(fen_parts[:3])
        return position_key in self.book

    def add_move(
        self, board: chess.Board, move: chess.Move, weight: int = 50
    ):
        """
        Add a move to the opening book.

        Args:
            board: The position before the move
            move: The move to add
            weight: The weight for this move
        """
        fen_parts = board.fen().split()
        position_key = " ".join(fen_parts[:3])

        if position_key not in self.book:
            self.book[position_key] = []

        # Check if move already exists
        move_uci = move.uci()
        for m in self.book[position_key]:
            if m["move"] == move_uci:
                m["weight"] = weight
                return

        self.book[position_key].append({"move": move_uci, "weight": weight})

    def save(self, path: Path):
        """Save the opening book to a JSON file."""
        with open(path, "w") as f:
            json.dump(self.book, f, indent=2)
