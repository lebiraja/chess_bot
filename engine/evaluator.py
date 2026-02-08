"""
Board Evaluation Function for Chess Engine

Evaluates board positions in centipawns (1 pawn = 100 centipawns).
Positive scores favor White, negative scores favor Black.
"""
import chess
import numpy as np

# Piece values in centipawns
PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 20000,
}

# Mate score (high value to ensure checkmate is prioritized)
MATE_SCORE = 100000

# Piece-Square Tables (from White's perspective, flip for Black)
# Values represent positional bonuses/penalties for each square

PAWN_TABLE = np.array([
    [  0,   0,   0,   0,   0,   0,   0,   0],
    [ 50,  50,  50,  50,  50,  50,  50,  50],
    [ 10,  10,  20,  30,  30,  20,  10,  10],
    [  5,   5,  10,  25,  25,  10,   5,   5],
    [  0,   0,   0,  20,  20,   0,   0,   0],
    [  5,  -5, -10,   0,   0, -10,  -5,   5],
    [  5,  10,  10, -20, -20,  10,  10,   5],
    [  0,   0,   0,   0,   0,   0,   0,   0],
])

KNIGHT_TABLE = np.array([
    [-50, -40, -30, -30, -30, -30, -40, -50],
    [-40, -20,   0,   0,   0,   0, -20, -40],
    [-30,   0,  10,  15,  15,  10,   0, -30],
    [-30,   5,  15,  20,  20,  15,   5, -30],
    [-30,   0,  15,  20,  20,  15,   0, -30],
    [-30,   5,  10,  15,  15,  10,   5, -30],
    [-40, -20,   0,   5,   5,   0, -20, -40],
    [-50, -40, -30, -30, -30, -30, -40, -50],
])

BISHOP_TABLE = np.array([
    [-20, -10, -10, -10, -10, -10, -10, -20],
    [-10,   0,   0,   0,   0,   0,   0, -10],
    [-10,   0,   5,  10,  10,   5,   0, -10],
    [-10,   5,   5,  10,  10,   5,   5, -10],
    [-10,   0,  10,  10,  10,  10,   0, -10],
    [-10,  10,  10,  10,  10,  10,  10, -10],
    [-10,   5,   0,   0,   0,   0,   5, -10],
    [-20, -10, -10, -10, -10, -10, -10, -20],
])

ROOK_TABLE = np.array([
    [  0,   0,   0,   0,   0,   0,   0,   0],
    [  5,  10,  10,  10,  10,  10,  10,   5],
    [ -5,   0,   0,   0,   0,   0,   0,  -5],
    [ -5,   0,   0,   0,   0,   0,   0,  -5],
    [ -5,   0,   0,   0,   0,   0,   0,  -5],
    [ -5,   0,   0,   0,   0,   0,   0,  -5],
    [ -5,   0,   0,   0,   0,   0,   0,  -5],
    [  0,   0,   0,   5,   5,   0,   0,   0],
])

QUEEN_TABLE = np.array([
    [-20, -10, -10,  -5,  -5, -10, -10, -20],
    [-10,   0,   0,   0,   0,   0,   0, -10],
    [-10,   0,   5,   5,   5,   5,   0, -10],
    [ -5,   0,   5,   5,   5,   5,   0,  -5],
    [  0,   0,   5,   5,   5,   5,   0,  -5],
    [-10,   5,   5,   5,   5,   5,   0, -10],
    [-10,   0,   5,   0,   0,   0,   0, -10],
    [-20, -10, -10,  -5,  -5, -10, -10, -20],
])

KING_MIDDLEGAME_TABLE = np.array([
    [-30, -40, -40, -50, -50, -40, -40, -30],
    [-30, -40, -40, -50, -50, -40, -40, -30],
    [-30, -40, -40, -50, -50, -40, -40, -30],
    [-30, -40, -40, -50, -50, -40, -40, -30],
    [-20, -30, -30, -40, -40, -30, -30, -20],
    [-10, -20, -20, -20, -20, -20, -20, -10],
    [ 20,  20,   0,   0,   0,   0,  20,  20],
    [ 20,  30,  10,   0,   0,  10,  30,  20],
])

KING_ENDGAME_TABLE = np.array([
    [-50, -40, -30, -20, -20, -30, -40, -50],
    [-30, -20, -10,   0,   0, -10, -20, -30],
    [-30, -10,  20,  30,  30,  20, -10, -30],
    [-30, -10,  30,  40,  40,  30, -10, -30],
    [-30, -10,  30,  40,  40,  30, -10, -30],
    [-30, -10,  20,  30,  30,  20, -10, -30],
    [-30, -30,   0,   0,   0,   0, -30, -30],
    [-50, -30, -30, -30, -30, -30, -30, -50],
])


class Evaluator:
    """Evaluates chess board positions."""

    def __init__(
        self,
        material_weight: float = 1.0,
        position_weight: float = 0.3,
        mobility_weight: float = 0.1,
        king_safety_weight: float = 0.5,
        pawn_structure_weight: float = 0.2,
    ):
        self.material_weight = material_weight
        self.position_weight = position_weight
        self.mobility_weight = mobility_weight
        self.king_safety_weight = king_safety_weight
        self.pawn_structure_weight = pawn_structure_weight

        # Precompute flipped tables for Black
        self.piece_tables = {
            chess.WHITE: {
                chess.PAWN: PAWN_TABLE,
                chess.KNIGHT: KNIGHT_TABLE,
                chess.BISHOP: BISHOP_TABLE,
                chess.ROOK: ROOK_TABLE,
                chess.QUEEN: QUEEN_TABLE,
                chess.KING: KING_MIDDLEGAME_TABLE,
            },
            chess.BLACK: {
                chess.PAWN: np.flip(PAWN_TABLE, axis=0),
                chess.KNIGHT: np.flip(KNIGHT_TABLE, axis=0),
                chess.BISHOP: np.flip(BISHOP_TABLE, axis=0),
                chess.ROOK: np.flip(ROOK_TABLE, axis=0),
                chess.QUEEN: np.flip(QUEEN_TABLE, axis=0),
                chess.KING: np.flip(KING_MIDDLEGAME_TABLE, axis=0),
            },
        }

        self.king_endgame_tables = {
            chess.WHITE: KING_ENDGAME_TABLE,
            chess.BLACK: np.flip(KING_ENDGAME_TABLE, axis=0),
        }

    def evaluate(self, board: chess.Board) -> int:
        """
        Evaluate the board position.

        Returns:
            Score in centipawns from the perspective of the side to move.
            Positive = good for side to move, negative = bad.
        """
        # Check for game-ending positions
        if board.is_checkmate():
            return -MATE_SCORE  # Current side is checkmated

        if board.is_stalemate() or board.is_insufficient_material():
            return 0

        if board.can_claim_draw():
            return 0

        # Calculate evaluation components
        score = 0
        score += self.material_weight * self._evaluate_material(board)
        score += self.position_weight * self._evaluate_piece_positions(board)
        score += self.mobility_weight * self._evaluate_mobility(board)
        score += self.pawn_structure_weight * self._evaluate_pawn_structure(board)

        # King safety is more important in middlegame
        if not self._is_endgame(board):
            score += self.king_safety_weight * self._evaluate_king_safety(board)

        # Return score from perspective of side to move
        return score if board.turn == chess.WHITE else -score

    def _evaluate_material(self, board: chess.Board) -> int:
        """Count material difference."""
        score = 0
        for piece_type in PIECE_VALUES:
            white_pieces = len(board.pieces(piece_type, chess.WHITE))
            black_pieces = len(board.pieces(piece_type, chess.BLACK))
            score += PIECE_VALUES[piece_type] * (white_pieces - black_pieces)

        # Bishop pair bonus
        if len(board.pieces(chess.BISHOP, chess.WHITE)) >= 2:
            score += 50
        if len(board.pieces(chess.BISHOP, chess.BLACK)) >= 2:
            score -= 50

        return score

    def _evaluate_piece_positions(self, board: chess.Board) -> int:
        """Evaluate piece positions using piece-square tables."""
        score = 0
        is_endgame = self._is_endgame(board)

        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece is None:
                continue

            # Get row and column (0-7)
            row = 7 - (square // 8)  # Flip row for correct orientation
            col = square % 8

            # Use endgame king table if in endgame
            if piece.piece_type == chess.KING and is_endgame:
                table = self.king_endgame_tables[piece.color]
            else:
                table = self.piece_tables[piece.color][piece.piece_type]

            value = int(table[row, col])

            if piece.color == chess.WHITE:
                score += value
            else:
                score -= value

        return score

    def _evaluate_mobility(self, board: chess.Board) -> int:
        """Evaluate piece mobility (number of legal moves)."""
        # Count moves for current side
        current_moves = board.legal_moves.count()

        # Switch sides and count opponent moves
        board.push(chess.Move.null())
        opponent_moves = board.legal_moves.count() if not board.is_check() else 0
        board.pop()

        mobility = current_moves - opponent_moves

        # Adjust perspective
        if board.turn == chess.BLACK:
            mobility = -mobility

        return mobility * 10  # Scale factor

    def _evaluate_pawn_structure(self, board: chess.Board) -> int:
        """Evaluate pawn structure (doubled, isolated, passed pawns)."""
        score = 0

        for color in [chess.WHITE, chess.BLACK]:
            pawns = board.pieces(chess.PAWN, color)
            pawn_files = [chess.square_file(sq) for sq in pawns]
            multiplier = 1 if color == chess.WHITE else -1

            # Doubled pawns penalty
            for file in range(8):
                count = pawn_files.count(file)
                if count > 1:
                    score -= 20 * (count - 1) * multiplier

            # Isolated pawns penalty
            for pawn_sq in pawns:
                file = chess.square_file(pawn_sq)
                has_neighbor = False
                for adj_file in [file - 1, file + 1]:
                    if 0 <= adj_file <= 7 and adj_file in pawn_files:
                        has_neighbor = True
                        break
                if not has_neighbor:
                    score -= 15 * multiplier

            # Passed pawns bonus
            for pawn_sq in pawns:
                if self._is_passed_pawn(board, pawn_sq, color):
                    rank = chess.square_rank(pawn_sq)
                    if color == chess.WHITE:
                        bonus = 20 + (rank - 1) * 10  # More advanced = more valuable
                    else:
                        bonus = 20 + (6 - rank) * 10
                    score += bonus * multiplier

        return score

    def _is_passed_pawn(
        self, board: chess.Board, pawn_square: int, color: bool
    ) -> bool:
        """Check if a pawn is passed (no enemy pawns blocking or attacking)."""
        file = chess.square_file(pawn_square)
        rank = chess.square_rank(pawn_square)
        enemy_pawns = board.pieces(chess.PAWN, not color)

        for enemy_sq in enemy_pawns:
            enemy_file = chess.square_file(enemy_sq)
            enemy_rank = chess.square_rank(enemy_sq)

            # Check if enemy pawn is on same or adjacent file
            if abs(enemy_file - file) <= 1:
                # Check if enemy pawn is ahead
                if color == chess.WHITE and enemy_rank > rank:
                    return False
                if color == chess.BLACK and enemy_rank < rank:
                    return False

        return True

    def _evaluate_king_safety(self, board: chess.Board) -> int:
        """Evaluate king safety (pawn shield, open files near king)."""
        score = 0

        for color in [chess.WHITE, chess.BLACK]:
            king_sq = board.king(color)
            if king_sq is None:
                continue

            king_file = chess.square_file(king_sq)
            king_rank = chess.square_rank(king_sq)
            multiplier = 1 if color == chess.WHITE else -1

            # Pawn shield evaluation
            shield_rank = king_rank + (1 if color == chess.WHITE else -1)
            if 0 <= shield_rank <= 7:
                for f in [king_file - 1, king_file, king_file + 1]:
                    if 0 <= f <= 7:
                        shield_sq = chess.square(f, shield_rank)
                        piece = board.piece_at(shield_sq)
                        if piece and piece.piece_type == chess.PAWN and piece.color == color:
                            score += 10 * multiplier

            # Penalty for king on open file
            own_pawns = board.pieces(chess.PAWN, color)
            file_has_pawn = any(chess.square_file(sq) == king_file for sq in own_pawns)
            if not file_has_pawn:
                score -= 20 * multiplier

        return score

    def _is_endgame(self, board: chess.Board) -> bool:
        """Determine if position is an endgame."""
        # Simple heuristic: endgame if queens are off or few pieces remain
        white_queens = len(board.pieces(chess.QUEEN, chess.WHITE))
        black_queens = len(board.pieces(chess.QUEEN, chess.BLACK))

        if white_queens == 0 and black_queens == 0:
            return True

        # Count non-pawn, non-king pieces
        piece_count = 0
        for piece_type in [chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN]:
            piece_count += len(board.pieces(piece_type, chess.WHITE))
            piece_count += len(board.pieces(piece_type, chess.BLACK))

        return piece_count <= 6
