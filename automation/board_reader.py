"""
Board Reader for Chess.com

Reads the current board state from the chess.com DOM.
"""
import re
from typing import Optional

import chess
from playwright.async_api import Page


class BoardReader:
    """
    Reads chess board state from chess.com's DOM.

    Parses piece positions from the page and converts to a python-chess Board.
    """

    # Piece class to chess piece mapping
    PIECE_MAP = {
        "wp": chess.Piece(chess.PAWN, chess.WHITE),
        "wn": chess.Piece(chess.KNIGHT, chess.WHITE),
        "wb": chess.Piece(chess.BISHOP, chess.WHITE),
        "wr": chess.Piece(chess.ROOK, chess.WHITE),
        "wq": chess.Piece(chess.QUEEN, chess.WHITE),
        "wk": chess.Piece(chess.KING, chess.WHITE),
        "bp": chess.Piece(chess.PAWN, chess.BLACK),
        "bn": chess.Piece(chess.KNIGHT, chess.BLACK),
        "bb": chess.Piece(chess.BISHOP, chess.BLACK),
        "br": chess.Piece(chess.ROOK, chess.BLACK),
        "bq": chess.Piece(chess.QUEEN, chess.BLACK),
        "bk": chess.Piece(chess.KING, chess.BLACK),
    }

    def __init__(self, page: Page):
        """
        Initialize the board reader.

        Args:
            page: Playwright page instance
        """
        self.page = page
        self._last_board: Optional[chess.Board] = None
        self._move_history: list[chess.Move] = []

    async def read_board(self) -> chess.Board:
        """
        Read the current board state from chess.com.

        Returns:
            A chess.Board object representing the current position
        """
        board = chess.Board()
        board.clear()

        # Get all piece elements
        pieces = await self.page.query_selector_all(".piece")

        for piece_elem in pieces:
            classes = await piece_elem.get_attribute("class")
            if not classes:
                continue

            # Parse piece type and square from classes
            piece_info = self._parse_piece_classes(classes)
            if piece_info:
                piece, square = piece_info
                board.set_piece_at(square, piece)

        # Try to determine castling rights based on piece positions
        self._infer_castling_rights(board)

        # Store for comparison
        self._last_board = board.copy()

        return board

    def _parse_piece_classes(
        self, classes: str
    ) -> Optional[tuple[chess.Piece, chess.Square]]:
        """
        Parse piece type and square from CSS classes.

        Chess.com uses classes like: "piece wk square-51"
        - wk = white king
        - square-51 = e1 (file 5, rank 1)

        Args:
            classes: CSS class string

        Returns:
            Tuple of (piece, square) or None if parsing fails
        """
        piece = None
        square = None

        # Find piece type (two-letter code)
        for piece_code in self.PIECE_MAP:
            if piece_code in classes.split():
                piece = self.PIECE_MAP[piece_code]
                break
            # Also check for just the letters in the class list
            if f" {piece_code} " in f" {classes} ":
                piece = self.PIECE_MAP[piece_code]
                break

        # Find square (square-XY format)
        square_match = re.search(r"square-(\d)(\d)", classes)
        if square_match:
            file = int(square_match.group(1)) - 1  # 1-8 to 0-7
            rank = int(square_match.group(2)) - 1  # 1-8 to 0-7
            if 0 <= file <= 7 and 0 <= rank <= 7:
                square = chess.square(file, rank)

        if piece is not None and square is not None:
            return (piece, square)
        return None

    def _infer_castling_rights(self, board: chess.Board):
        """
        Infer castling rights from piece positions.

        This is a heuristic - if kings and rooks are on starting squares,
        we assume castling is possible.
        """
        # Reset castling rights
        board.castling_rights = chess.BB_EMPTY

        # Check white castling
        if board.piece_at(chess.E1) == chess.Piece(chess.KING, chess.WHITE):
            if board.piece_at(chess.H1) == chess.Piece(chess.ROOK, chess.WHITE):
                board.castling_rights |= chess.BB_H1
            if board.piece_at(chess.A1) == chess.Piece(chess.ROOK, chess.WHITE):
                board.castling_rights |= chess.BB_A1

        # Check black castling
        if board.piece_at(chess.E8) == chess.Piece(chess.KING, chess.BLACK):
            if board.piece_at(chess.H8) == chess.Piece(chess.ROOK, chess.BLACK):
                board.castling_rights |= chess.BB_H8
            if board.piece_at(chess.A8) == chess.Piece(chess.ROOK, chess.BLACK):
                board.castling_rights |= chess.BB_A8

    async def detect_last_move(self) -> Optional[chess.Move]:
        """
        Detect the last move made by looking at highlighted squares.

        Returns:
            The last move made, or None if not detectable
        """
        # Chess.com highlights the from and to squares of the last move
        highlights = await self.page.query_selector_all(".highlight")

        squares = []
        for highlight in highlights:
            classes = await highlight.get_attribute("class")
            if classes:
                match = re.search(r"square-(\d)(\d)", classes)
                if match:
                    file = int(match.group(1)) - 1
                    rank = int(match.group(2)) - 1
                    if 0 <= file <= 7 and 0 <= rank <= 7:
                        squares.append(chess.square(file, rank))

        if len(squares) == 2:
            # Determine which is from/to based on piece positions
            board = await self.read_board()
            # The destination square should have a piece
            if board.piece_at(squares[1]):
                return chess.Move(squares[0], squares[1])
            elif board.piece_at(squares[0]):
                return chess.Move(squares[1], squares[0])

        return None

    async def is_board_flipped(self) -> bool:
        """
        Check if the board is flipped (playing as Black).

        Returns:
            True if board is flipped (Black's perspective)
        """
        # Check for flipped class on board element
        board_elem = await self.page.query_selector("chess-board, wc-chess-board, .board")
        if board_elem:
            classes = await board_elem.get_attribute("class")
            if classes and "flipped" in classes:
                return True

        # Alternative: check if white pieces are at top
        # by looking at square-18 (a8) - should have white pieces if flipped
        return False

    async def get_fen(self) -> str:
        """
        Get the FEN string for the current position.

        Returns:
            FEN string (may not have accurate move counters)
        """
        board = await self.read_board()
        return board.fen()

    def square_to_selector(self, square: chess.Square) -> str:
        """
        Convert a chess square to a CSS selector.

        Args:
            square: Chess square (0-63)

        Returns:
            CSS selector for that square
        """
        file = chess.square_file(square) + 1  # 0-7 to 1-8
        rank = chess.square_rank(square) + 1  # 0-7 to 1-8
        return f".square-{file}{rank}"

    async def wait_for_board_change(self, timeout: float = 30.0) -> bool:
        """
        Wait for the board to change from the last known state.

        Args:
            timeout: Maximum time to wait in seconds

        Returns:
            True if board changed, False if timeout
        """
        import asyncio

        start_fen = self._last_board.fen() if self._last_board else None
        start_time = asyncio.get_event_loop().time()

        while asyncio.get_event_loop().time() - start_time < timeout:
            current_board = await self.read_board()
            if start_fen is None or current_board.fen() != start_fen:
                return True
            await asyncio.sleep(0.2)

        return False
