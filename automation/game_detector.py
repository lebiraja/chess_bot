"""
Game Detector for Chess.com

Detects game state, player color, and turn information.
"""
import asyncio
from enum import Enum
from typing import Optional, Tuple

import chess
from playwright.async_api import Page


class GameState(Enum):
    """Possible game states."""

    NO_GAME = "no_game"
    WAITING = "waiting"
    IN_PROGRESS = "in_progress"
    GAME_OVER = "game_over"


class GameResult(Enum):
    """Possible game results."""

    WHITE_WINS = "white_wins"
    BLACK_WINS = "black_wins"
    DRAW = "draw"
    ONGOING = "ongoing"


class GameDetector:
    """
    Detects game-related information from chess.com.

    Monitors the page to detect:
    - Game start
    - Player color
    - Whose turn it is
    - Game end and result
    """

    def __init__(self, page: Page):
        """
        Initialize the game detector.

        Args:
            page: Playwright page instance
        """
        self.page = page
        self._player_color: Optional[bool] = None
        self._game_state = GameState.NO_GAME

    async def detect_player_color(self) -> bool:
        """
        Detect which color the player is.

        Returns:
            chess.WHITE or chess.BLACK
        """
        # Check if board is flipped
        board_elem = await self.page.query_selector(
            "chess-board, wc-chess-board, .board"
        )

        if board_elem:
            classes = await board_elem.get_attribute("class")
            if classes and "flipped" in classes:
                self._player_color = chess.BLACK
                return chess.BLACK

        # Alternative: check player name positions
        # On chess.com, your username appears at the bottom
        bottom_player = await self.page.query_selector(
            ".player-component.player-bottom .user-username-component"
        )

        if bottom_player:
            # If there's a bottom player element, we're playing
            # Check board orientation again
            pass

        self._player_color = chess.WHITE
        return chess.WHITE

    async def is_our_turn(self, player_color: bool) -> bool:
        """
        Check if it's the player's turn.

        Args:
            player_color: The color we're playing as

        Returns:
            True if it's our turn
        """
        # Method 1: Check for clock highlighting
        clock_selector = ".clock-bottom.clock-player-turn, .clock-component.clock-bottom.clock-running"
        our_clock = await self.page.query_selector(clock_selector)

        if our_clock:
            return True

        # Method 2: Check if board is interactive
        # When it's not our turn, pieces may not be draggable
        try:
            is_interactive = await self.page.evaluate("""
                () => {
                    const board = document.querySelector('chess-board, wc-chess-board');
                    if (!board) return false;

                    // Check if we can interact with pieces
                    const pieces = board.querySelectorAll('.piece');
                    for (const piece of pieces) {
                        const style = window.getComputedStyle(piece);
                        if (style.cursor === 'grab' || style.cursor === 'pointer') {
                            return true;
                        }
                    }
                    return false;
                }
            """)
            return is_interactive
        except Exception:
            pass

        # Method 3: Check move indicator
        move_indicator = await self.page.query_selector(".move-indicator")
        if move_indicator:
            classes = await move_indicator.get_attribute("class")
            if classes:
                # The move indicator shows whose turn it is
                if "white" in classes.lower():
                    return player_color == chess.WHITE
                elif "black" in classes.lower():
                    return player_color == chess.BLACK

        # Default: assume it might be our turn
        return False

    async def wait_for_game_start(self, timeout: float = 120.0) -> bool:
        """
        Wait for a game to start.

        Args:
            timeout: Maximum time to wait in seconds

        Returns:
            True if game started, False if timeout
        """
        print("Waiting for game to start...")

        start_time = asyncio.get_event_loop().time()

        while asyncio.get_event_loop().time() - start_time < timeout:
            state = await self.get_game_state()

            if state == GameState.IN_PROGRESS:
                print("Game started!")
                self._game_state = GameState.IN_PROGRESS
                return True

            await asyncio.sleep(0.5)

        return False

    async def get_game_state(self) -> GameState:
        """
        Get the current game state.

        Returns:
            GameState enum value
        """
        # Check for game over modal
        game_over = await self.page.query_selector(
            ".game-over-modal, .game-review-modal, [class*='game-over']"
        )
        if game_over:
            return GameState.GAME_OVER

        # Check for active game
        board = await self.page.query_selector(
            "chess-board, wc-chess-board, .board"
        )

        if board:
            # Check if there are pieces on the board
            pieces = await self.page.query_selector_all(".piece")
            if len(pieces) > 0:
                # Check for waiting state (seeking game)
                seeking = await self.page.query_selector(
                    ".seeking-component, .challenge-component, [class*='seeking']"
                )
                if seeking:
                    return GameState.WAITING

                return GameState.IN_PROGRESS

        return GameState.NO_GAME

    async def is_game_over(self) -> Tuple[bool, Optional[GameResult]]:
        """
        Check if the game is over.

        Returns:
            Tuple of (is_over, result)
        """
        # Check for game over modal
        game_over_selectors = [
            ".game-over-modal",
            ".game-review-modal",
            "[class*='game-over']",
            ".modal-game-over",
        ]

        for selector in game_over_selectors:
            modal = await self.page.query_selector(selector)
            if modal:
                result = await self._parse_game_result(modal)
                return True, result

        # Check for game end in move list
        result_elem = await self.page.query_selector(
            ".result, .game-result, [class*='result']"
        )
        if result_elem:
            text = await result_elem.inner_text()
            if text:
                result = self._parse_result_text(text)
                if result != GameResult.ONGOING:
                    return True, result

        return False, None

    async def _parse_game_result(self, modal) -> GameResult:
        """Parse the game result from the game over modal."""
        try:
            text = await modal.inner_text()
            return self._parse_result_text(text)
        except Exception:
            return GameResult.ONGOING

    def _parse_result_text(self, text: str) -> GameResult:
        """Parse result from text."""
        text = text.lower()

        if "white" in text and ("win" in text or "won" in text):
            return GameResult.WHITE_WINS
        elif "black" in text and ("win" in text or "won" in text):
            return GameResult.BLACK_WINS
        elif "1-0" in text:
            return GameResult.WHITE_WINS
        elif "0-1" in text:
            return GameResult.BLACK_WINS
        elif "draw" in text or "1/2" in text or "stalemate" in text:
            return GameResult.DRAW
        elif "checkmate" in text:
            # Need more context to determine winner
            return GameResult.ONGOING

        return GameResult.ONGOING

    async def wait_for_opponent_move(
        self,
        current_fen: str,
        timeout: float = 300.0
    ) -> bool:
        """
        Wait for the opponent to make a move.

        Args:
            current_fen: Current board FEN to compare against
            timeout: Maximum time to wait in seconds

        Returns:
            True if opponent moved, False if timeout or game over
        """
        from .board_reader import BoardReader

        board_reader = BoardReader(self.page)
        start_time = asyncio.get_event_loop().time()

        while asyncio.get_event_loop().time() - start_time < timeout:
            # Check if game is over
            is_over, _ = await self.is_game_over()
            if is_over:
                return False

            # Check if board has changed
            try:
                new_board = await board_reader.read_board()
                if new_board.fen().split()[0] != current_fen.split()[0]:
                    return True
            except Exception:
                pass

            await asyncio.sleep(0.3)

        return False

    async def get_time_remaining(self) -> Tuple[Optional[float], Optional[float]]:
        """
        Get remaining time for both players.

        Returns:
            Tuple of (our_time, opponent_time) in seconds, or None if not available
        """
        our_time = None
        opp_time = None

        try:
            # Get bottom clock (our clock)
            bottom_clock = await self.page.query_selector(".clock-bottom .clock-time")
            if bottom_clock:
                time_text = await bottom_clock.inner_text()
                our_time = self._parse_time(time_text)

            # Get top clock (opponent's clock)
            top_clock = await self.page.query_selector(".clock-top .clock-time")
            if top_clock:
                time_text = await top_clock.inner_text()
                opp_time = self._parse_time(time_text)

        except Exception:
            pass

        return our_time, opp_time

    def _parse_time(self, time_str: str) -> float:
        """Parse time string (MM:SS or H:MM:SS) to seconds."""
        try:
            parts = time_str.strip().split(":")
            if len(parts) == 2:
                return int(parts[0]) * 60 + float(parts[1])
            elif len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        except (ValueError, IndexError):
            pass
        return 0.0
