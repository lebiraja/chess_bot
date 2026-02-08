"""
Transposition Table for Chess Engine

Uses Zobrist hashing to cache position evaluations and avoid redundant calculations.
"""
import random
from dataclasses import dataclass
from enum import IntEnum
from typing import Optional

import chess


class NodeType(IntEnum):
    """Type of node in the search tree."""

    EXACT = 0  # Exact score
    LOWER_BOUND = 1  # Score is at least this (beta cutoff)
    UPPER_BOUND = 2  # Score is at most this (alpha cutoff)


@dataclass
class TTEntry:
    """Entry in the transposition table."""

    hash_key: int  # Zobrist hash of position
    depth: int  # Search depth
    score: int  # Evaluation score
    node_type: NodeType  # Type of score bound
    best_move: Optional[chess.Move]  # Best move found
    age: int  # When this entry was created


class TranspositionTable:
    """
    Transposition table using Zobrist hashing.

    Stores position evaluations to avoid recalculating the same positions.
    """

    def __init__(self, size_mb: int = 256):
        """
        Initialize the transposition table.

        Args:
            size_mb: Size of the table in megabytes
        """
        # Calculate number of entries based on size
        entry_size = 64  # Approximate bytes per entry
        self.max_entries = (size_mb * 1024 * 1024) // entry_size
        self.table: dict[int, TTEntry] = {}
        self.age = 0

        # Initialize Zobrist keys
        self._init_zobrist()

    def _init_zobrist(self):
        """Initialize random Zobrist hash keys."""
        random.seed(42)  # Deterministic for reproducibility

        # Keys for each piece type on each square
        # [piece_type][color][square]
        self.piece_keys = {}
        for piece_type in chess.PIECE_TYPES:
            self.piece_keys[piece_type] = {}
            for color in [chess.WHITE, chess.BLACK]:
                self.piece_keys[piece_type][color] = [
                    random.getrandbits(64) for _ in range(64)
                ]

        # Key for side to move
        self.side_key = random.getrandbits(64)

        # Keys for castling rights
        self.castling_keys = {
            "K": random.getrandbits(64),
            "Q": random.getrandbits(64),
            "k": random.getrandbits(64),
            "q": random.getrandbits(64),
        }

        # Keys for en passant file
        self.ep_keys = [random.getrandbits(64) for _ in range(8)]

    def hash_position(self, board: chess.Board) -> int:
        """
        Compute Zobrist hash for a board position.

        Args:
            board: The chess board to hash

        Returns:
            64-bit hash value
        """
        h = 0

        # Hash pieces
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece:
                h ^= self.piece_keys[piece.piece_type][piece.color][square]

        # Hash side to move
        if board.turn == chess.BLACK:
            h ^= self.side_key

        # Hash castling rights
        if board.has_kingside_castling_rights(chess.WHITE):
            h ^= self.castling_keys["K"]
        if board.has_queenside_castling_rights(chess.WHITE):
            h ^= self.castling_keys["Q"]
        if board.has_kingside_castling_rights(chess.BLACK):
            h ^= self.castling_keys["k"]
        if board.has_queenside_castling_rights(chess.BLACK):
            h ^= self.castling_keys["q"]

        # Hash en passant
        if board.ep_square is not None:
            h ^= self.ep_keys[chess.square_file(board.ep_square)]

        return h

    def store(
        self,
        board: chess.Board,
        depth: int,
        score: int,
        node_type: NodeType,
        best_move: Optional[chess.Move] = None,
    ):
        """
        Store a position evaluation in the table.

        Args:
            board: The chess board
            depth: Search depth of this evaluation
            score: The evaluation score
            node_type: Type of score bound
            best_move: Best move found (if any)
        """
        hash_key = self.hash_position(board)
        index = hash_key % self.max_entries

        # Check if we should replace existing entry
        existing = self.table.get(index)
        if existing is not None:
            # Replace if:
            # 1. Different position (collision)
            # 2. Deeper search
            # 3. Same depth but newer
            if existing.hash_key != hash_key or depth >= existing.depth:
                self.table[index] = TTEntry(
                    hash_key=hash_key,
                    depth=depth,
                    score=score,
                    node_type=node_type,
                    best_move=best_move,
                    age=self.age,
                )
        else:
            self.table[index] = TTEntry(
                hash_key=hash_key,
                depth=depth,
                score=score,
                node_type=node_type,
                best_move=best_move,
                age=self.age,
            )

    def probe(self, board: chess.Board) -> Optional[TTEntry]:
        """
        Look up a position in the table.

        Args:
            board: The chess board to look up

        Returns:
            TTEntry if found and hash matches, None otherwise
        """
        hash_key = self.hash_position(board)
        index = hash_key % self.max_entries

        entry = self.table.get(index)
        if entry is not None and entry.hash_key == hash_key:
            return entry

        return None

    def get_pv_line(self, board: chess.Board, max_length: int = 10) -> list[chess.Move]:
        """
        Extract principal variation from the table.

        Args:
            board: Starting position
            max_length: Maximum number of moves to extract

        Returns:
            List of moves forming the principal variation
        """
        pv = []
        board_copy = board.copy()

        for _ in range(max_length):
            entry = self.probe(board_copy)
            if entry is None or entry.best_move is None:
                break

            move = entry.best_move
            if move not in board_copy.legal_moves:
                break

            pv.append(move)
            board_copy.push(move)

        return pv

    def new_search(self):
        """Increment age for new search (helps with replacement)."""
        self.age += 1

    def clear(self):
        """Clear all entries from the table."""
        self.table.clear()
        self.age = 0

    def fill_rate(self) -> float:
        """Return the percentage of table slots filled."""
        return len(self.table) / self.max_entries * 100
