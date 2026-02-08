"""
Minimax Chess Engine with Alpha-Beta Pruning

Implements the core search algorithm for finding the best chess moves.
"""
import time
from typing import Optional

import chess

from .evaluator import MATE_SCORE, Evaluator
from .transposition import NodeType, TranspositionTable


class ChessEngine:
    """
    Chess engine using Minimax with Alpha-Beta pruning.

    Features:
    - Alpha-beta pruning for efficient search
    - Iterative deepening for time management
    - Transposition table for caching
    - Move ordering for better pruning
    - Quiescence search for tactical stability
    """

    def __init__(
        self,
        max_depth: int = 5,
        time_limit: float = 10.0,
        use_quiescence: bool = True,
        quiescence_depth: int = 8,
        tt_size_mb: int = 256,
    ):
        """
        Initialize the chess engine.

        Args:
            max_depth: Maximum search depth (ply)
            time_limit: Maximum time per move in seconds
            use_quiescence: Whether to use quiescence search
            quiescence_depth: Maximum depth for quiescence search
            tt_size_mb: Transposition table size in MB
        """
        self.max_depth = max_depth
        self.time_limit = time_limit
        self.use_quiescence = use_quiescence
        self.quiescence_depth = quiescence_depth

        self.evaluator = Evaluator()
        self.tt = TranspositionTable(tt_size_mb)

        # Search statistics
        self.nodes_searched = 0
        self.tt_hits = 0
        self.start_time = 0.0

        # Killer moves (moves that caused beta cutoffs)
        self.killer_moves: list[list[Optional[chess.Move]]] = [
            [None, None] for _ in range(64)
        ]

        # History heuristic (tracks move success)
        self.history: dict[tuple[int, int], int] = {}

    def find_best_move(self, board: chess.Board) -> Optional[chess.Move]:
        """
        Find the best move for the current position.

        Uses iterative deepening to search progressively deeper
        until time limit is reached.

        Args:
            board: The current board position

        Returns:
            The best move found, or None if no legal moves
        """
        if not list(board.legal_moves):
            return None

        self.nodes_searched = 0
        self.tt_hits = 0
        self.start_time = time.time()
        self.tt.new_search()

        best_move = None
        best_score = -MATE_SCORE

        # Iterative deepening
        for depth in range(1, self.max_depth + 1):
            if self._time_up():
                break

            score, move = self._search_root(board, depth)

            if move is not None and not self._time_up():
                best_move = move
                best_score = score

                # Print search info
                elapsed = time.time() - self.start_time
                nps = self.nodes_searched / elapsed if elapsed > 0 else 0
                pv = self.tt.get_pv_line(board)
                pv_str = " ".join(m.uci() for m in pv)

                print(
                    f"depth {depth:2d}  score {score:+6d}  "
                    f"nodes {self.nodes_searched:8d}  "
                    f"nps {nps:8.0f}  "
                    f"pv {pv_str}"
                )

            # Stop early if we found a forced mate
            if abs(score) > MATE_SCORE - 100:
                break

        return best_move

    def _search_root(
        self, board: chess.Board, depth: int
    ) -> tuple[int, Optional[chess.Move]]:
        """
        Search at the root node.

        Args:
            board: The current board position
            depth: Search depth

        Returns:
            Tuple of (best score, best move)
        """
        alpha = -MATE_SCORE
        beta = MATE_SCORE
        best_move = None
        best_score = -MATE_SCORE

        # Order moves for better pruning
        moves = self._order_moves(board, depth)

        for move in moves:
            if self._time_up():
                break

            board.push(move)
            score = -self._alpha_beta(board, depth - 1, -beta, -alpha)
            board.pop()

            if score > best_score:
                best_score = score
                best_move = move

                if score > alpha:
                    alpha = score

        return best_score, best_move

    def _alpha_beta(
        self, board: chess.Board, depth: int, alpha: int, beta: int
    ) -> int:
        """
        Alpha-beta search with transposition table.

        Args:
            board: The current board position
            depth: Remaining search depth
            alpha: Alpha bound (best score for maximizing player)
            beta: Beta bound (best score for minimizing player)

        Returns:
            The evaluation score for the position
        """
        self.nodes_searched += 1

        # Check for time limit periodically
        if self.nodes_searched % 4096 == 0 and self._time_up():
            return 0

        # Terminal node checks
        if board.is_checkmate():
            return -MATE_SCORE + board.ply()  # Prefer shorter mates

        if board.is_stalemate() or board.is_insufficient_material() or board.can_claim_draw():
            return 0

        # Transposition table lookup
        tt_entry = self.tt.probe(board)
        if tt_entry is not None and tt_entry.depth >= depth:
            self.tt_hits += 1
            if tt_entry.node_type == NodeType.EXACT:
                return tt_entry.score
            elif tt_entry.node_type == NodeType.LOWER_BOUND:
                alpha = max(alpha, tt_entry.score)
            elif tt_entry.node_type == NodeType.UPPER_BOUND:
                beta = min(beta, tt_entry.score)

            if alpha >= beta:
                return tt_entry.score

        # Leaf node - evaluate or quiescence search
        if depth <= 0:
            if self.use_quiescence:
                return self._quiescence(board, alpha, beta, self.quiescence_depth)
            return self.evaluator.evaluate(board)

        # Search all moves
        best_score = -MATE_SCORE
        best_move = None
        original_alpha = alpha

        moves = self._order_moves(board, depth, tt_entry.best_move if tt_entry else None)

        for move in moves:
            board.push(move)
            score = -self._alpha_beta(board, depth - 1, -beta, -alpha)
            board.pop()

            if score > best_score:
                best_score = score
                best_move = move

            if score > alpha:
                alpha = score

                # Update history heuristic for quiet moves
                if not board.is_capture(move):
                    key = (move.from_square, move.to_square)
                    self.history[key] = self.history.get(key, 0) + depth * depth

            if alpha >= beta:
                # Beta cutoff - store killer move
                if not board.is_capture(move):
                    self._store_killer(move, depth)
                break

        # Store in transposition table
        if best_score <= original_alpha:
            node_type = NodeType.UPPER_BOUND
        elif best_score >= beta:
            node_type = NodeType.LOWER_BOUND
        else:
            node_type = NodeType.EXACT

        self.tt.store(board, depth, best_score, node_type, best_move)

        return best_score

    def _quiescence(
        self, board: chess.Board, alpha: int, beta: int, depth: int
    ) -> int:
        """
        Quiescence search - only consider captures and checks.

        Extends the search until the position is "quiet" to avoid
        horizon effects.

        Args:
            board: The current board position
            alpha: Alpha bound
            beta: Beta bound
            depth: Remaining quiescence depth

        Returns:
            The evaluation score
        """
        self.nodes_searched += 1

        # Stand pat - evaluate current position
        stand_pat = self.evaluator.evaluate(board)

        if depth <= 0:
            return stand_pat

        if stand_pat >= beta:
            return beta

        if stand_pat > alpha:
            alpha = stand_pat

        # Only search captures (and checks at depth > 0)
        for move in self._get_captures(board):
            board.push(move)

            # Skip if puts us in check (illegal after opponent move)
            if board.is_check():
                score = -self._quiescence(board, -beta, -alpha, depth - 1)
            else:
                score = -self._quiescence(board, -beta, -alpha, depth - 1)

            board.pop()

            if score >= beta:
                return beta

            if score > alpha:
                alpha = score

        return alpha

    def _order_moves(
        self,
        board: chess.Board,
        depth: int,
        hash_move: Optional[chess.Move] = None,
    ) -> list[chess.Move]:
        """
        Order moves for better alpha-beta pruning.

        Move ordering priority:
        1. Hash move (from transposition table)
        2. Captures (ordered by MVV-LVA)
        3. Killer moves
        4. History heuristic
        5. Other moves

        Args:
            board: The current board position
            depth: Current search depth
            hash_move: Best move from transposition table

        Returns:
            Ordered list of legal moves
        """
        moves = list(board.legal_moves)
        scored_moves = []

        for move in moves:
            score = 0

            # Hash move gets highest priority
            if move == hash_move:
                score = 10000000
            # Captures scored by MVV-LVA
            elif board.is_capture(move):
                victim = board.piece_at(move.to_square)
                attacker = board.piece_at(move.from_square)
                if victim and attacker:
                    # MVV-LVA: Most Valuable Victim - Least Valuable Attacker
                    score = 1000000 + victim.piece_type * 100 - attacker.piece_type
                else:
                    score = 1000000
            # Killer moves
            elif depth < len(self.killer_moves):
                if move == self.killer_moves[depth][0]:
                    score = 900000
                elif move == self.killer_moves[depth][1]:
                    score = 800000
            # Promotions
            elif move.promotion:
                score = 700000 + move.promotion
            # History heuristic
            else:
                key = (move.from_square, move.to_square)
                score = self.history.get(key, 0)

            scored_moves.append((score, move))

        # Sort by score descending
        scored_moves.sort(key=lambda x: x[0], reverse=True)
        return [move for _, move in scored_moves]

    def _get_captures(self, board: chess.Board) -> list[chess.Move]:
        """Get all capture moves, ordered by MVV-LVA."""
        captures = []
        for move in board.legal_moves:
            if board.is_capture(move):
                victim = board.piece_at(move.to_square)
                attacker = board.piece_at(move.from_square)
                if victim and attacker:
                    score = victim.piece_type * 100 - attacker.piece_type
                else:
                    score = 0
                captures.append((score, move))

        captures.sort(key=lambda x: x[0], reverse=True)
        return [move for _, move in captures]

    def _store_killer(self, move: chess.Move, depth: int):
        """Store a killer move (caused beta cutoff)."""
        if depth >= len(self.killer_moves):
            return

        # Don't store duplicates
        if move != self.killer_moves[depth][0]:
            self.killer_moves[depth][1] = self.killer_moves[depth][0]
            self.killer_moves[depth][0] = move

    def _time_up(self) -> bool:
        """Check if time limit has been exceeded."""
        return time.time() - self.start_time >= self.time_limit

    def reset(self):
        """Reset engine state for a new game."""
        self.tt.clear()
        self.killer_moves = [[None, None] for _ in range(64)]
        self.history.clear()
