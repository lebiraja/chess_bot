"""
Move Executor for Chess.com

Executes chess moves by clicking on the board.
"""
import asyncio
import random
from typing import Optional, Tuple

import chess
from playwright.async_api import Page


class MoveExecutor:
    """
    Executes chess moves on chess.com by simulating mouse clicks.

    Includes human-like delays and mouse movements.
    """

    def __init__(
        self,
        page: Page,
        min_delay: float = 1.0,
        max_delay: float = 3.0,
    ):
        """
        Initialize the move executor.

        Args:
            page: Playwright page instance
            min_delay: Minimum delay before making a move (seconds)
            max_delay: Maximum delay before making a move (seconds)
        """
        self.page = page
        self.min_delay = min_delay
        self.max_delay = max_delay

    async def make_move(
        self,
        move: chess.Move,
        is_flipped: bool = False,
        delay: bool = True,
    ) -> bool:
        """
        Execute a chess move by clicking squares.

        Args:
            move: The chess move to make
            is_flipped: Whether the board is flipped (playing as Black)
            delay: Whether to add human-like delay before moving

        Returns:
            True if move was executed successfully
        """
        # Add human-like delay
        if delay:
            wait_time = random.uniform(self.min_delay, self.max_delay)
            await asyncio.sleep(wait_time)

        # Get square selectors
        from_selector = self._square_to_selector(move.from_square)
        to_selector = self._square_to_selector(move.to_square)

        try:
            # Click the source square
            await self._click_square(from_selector)

            # Small delay between clicks (human-like)
            await asyncio.sleep(random.uniform(0.1, 0.3))

            # Click the destination square
            await self._click_square(to_selector)

            # Handle pawn promotion
            if move.promotion:
                await self._handle_promotion(move.promotion)

            return True

        except Exception as e:
            print(f"Error making move {move}: {e}")
            return False

    async def _click_square(self, selector: str):
        """
        Click a square on the chess board.

        Args:
            selector: CSS selector for the square
        """
        # Try to find and click the square
        # Chess.com uses different structures, try multiple approaches

        # First, try clicking the piece on that square
        piece_selector = f".piece{selector.replace('.', '')}"
        element = await self.page.query_selector(piece_selector)

        if element is None:
            # Try clicking the square itself
            element = await self.page.query_selector(selector)

        if element is None:
            # Try with different selector format
            # Extract square numbers from selector like ".square-54"
            import re
            match = re.search(r"square-(\d)(\d)", selector)
            if match:
                file, rank = match.groups()
                alt_selector = f'[class*="square-{file}{rank}"]'
                element = await self.page.query_selector(alt_selector)

        if element:
            # Get element bounding box for clicking
            box = await element.bounding_box()
            if box:
                # Click in the center of the square with slight randomization
                x = box["x"] + box["width"] / 2 + random.uniform(-5, 5)
                y = box["y"] + box["height"] / 2 + random.uniform(-5, 5)
                await self.page.mouse.click(x, y)
                return

        # Fallback: try clicking by coordinates based on board position
        await self._click_by_board_position(selector)

    async def _click_by_board_position(self, selector: str):
        """
        Click a square by calculating its position on the board.

        Fallback method when selectors don't work.
        """
        import re

        # Extract file and rank from selector
        match = re.search(r"square-(\d)(\d)", selector)
        if not match:
            raise ValueError(f"Invalid square selector: {selector}")

        file = int(match.group(1))  # 1-8
        rank = int(match.group(2))  # 1-8

        # Find the board element
        board = await self.page.query_selector(
            "chess-board, wc-chess-board, .board, #board-single"
        )

        if not board:
            raise RuntimeError("Could not find chess board element")

        box = await board.bounding_box()
        if not box:
            raise RuntimeError("Could not get board bounding box")

        # Check if board is flipped
        classes = await board.get_attribute("class") or ""
        is_flipped = "flipped" in classes

        # Calculate square position
        square_width = box["width"] / 8
        square_height = box["height"] / 8

        if is_flipped:
            # Flipped board: a1 is at top-right
            x = box["x"] + (8 - file + 0.5) * square_width
            y = box["y"] + (rank - 0.5) * square_height
        else:
            # Normal board: a1 is at bottom-left
            x = box["x"] + (file - 0.5) * square_width
            y = box["y"] + (8 - rank + 0.5) * square_height

        # Add slight randomization
        x += random.uniform(-5, 5)
        y += random.uniform(-5, 5)

        await self.page.mouse.click(x, y)

    async def _handle_promotion(self, promotion_piece: chess.PieceType):
        """
        Handle pawn promotion by selecting the promotion piece.

        Args:
            promotion_piece: The piece type to promote to
        """
        # Wait for promotion dialog
        await asyncio.sleep(0.3)

        # Map piece type to class name
        piece_names = {
            chess.QUEEN: "queen",
            chess.ROOK: "rook",
            chess.BISHOP: "bishop",
            chess.KNIGHT: "knight",
        }

        piece_name = piece_names.get(promotion_piece, "queen")

        # Try different selectors for promotion dialog
        selectors = [
            f".promotion-piece.{piece_name}",
            f".promotion-{piece_name}",
            f'[class*="promotion"][class*="{piece_name}"]',
            f'.promotion-menu .{piece_name}',
        ]

        for selector in selectors:
            try:
                element = await self.page.query_selector(selector)
                if element:
                    await element.click()
                    return
            except Exception:
                continue

        # Fallback: try clicking at a position in the promotion menu
        print(f"Warning: Could not find promotion piece selector, trying fallback")

    def _square_to_selector(self, square: chess.Square) -> str:
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

    async def premove(self, move: chess.Move) -> bool:
        """
        Make a premove (move before it's your turn).

        Args:
            move: The move to premove

        Returns:
            True if premove was set successfully
        """
        # Premoves work the same as regular moves on chess.com
        return await self.make_move(move, delay=False)

    async def cancel_premove(self):
        """Cancel any existing premove."""
        # Right-click anywhere on the board to cancel premove
        board = await self.page.query_selector(
            "chess-board, wc-chess-board, .board"
        )
        if board:
            box = await board.bounding_box()
            if box:
                x = box["x"] + box["width"] / 2
                y = box["y"] + box["height"] / 2
                await self.page.mouse.click(x, y, button="right")
