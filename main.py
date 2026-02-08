#!/usr/bin/env python3
"""
Chess Bot for Chess.com

Main orchestrator that combines the chess engine, opening book,
endgame tablebase, and browser automation to play chess on chess.com.
"""
import argparse
import asyncio
import sys
from pathlib import Path

import chess

from config.settings import Settings
from database.endgame_tablebase import EndgameTablebase
from database.opening_book import OpeningBook
from engine.minimax import ChessEngine
from automation.board_reader import BoardReader
from automation.browser import BrowserController
from automation.game_detector import GameDetector, GameResult, GameState
from automation.move_executor import MoveExecutor


class ChessBot:
    """
    Main chess bot that plays on chess.com.

    Combines:
    - Minimax engine with alpha-beta pruning
    - Opening book for early game
    - Endgame tablebases for perfect endgame play
    - Browser automation for chess.com interaction
    """

    def __init__(self, settings: Settings = None):
        """
        Initialize the chess bot.

        Args:
            settings: Configuration settings (uses defaults if None)
        """
        self.settings = settings or Settings()

        # Initialize chess engine
        self.engine = ChessEngine(
            max_depth=self.settings.search_depth,
            time_limit=self.settings.time_limit,
            use_quiescence=self.settings.use_quiescence,
            quiescence_depth=self.settings.quiescence_depth,
            tt_size_mb=self.settings.tt_size_mb,
        )

        # Initialize opening book
        self.opening_book = OpeningBook(
            self.settings.opening_book_path
            if self.settings.use_opening_book
            else None
        )

        # Initialize endgame tablebase
        self.tablebase = EndgameTablebase(
            self.settings.tablebase_path
            if self.settings.use_tablebase
            else None
        )

        # Browser components (initialized async)
        self.browser: BrowserController = None
        self.board_reader: BoardReader = None
        self.move_executor: MoveExecutor = None
        self.game_detector: GameDetector = None

        # Game state
        self.player_color: bool = chess.WHITE
        self.internal_board: chess.Board = chess.Board()
        self.move_count = 0

    async def initialize(self):
        """Initialize the browser and connect to chess.com."""
        print("Initializing chess bot...")

        # Create browser controller
        self.browser = BrowserController(headless=self.settings.headless)
        await self.browser.initialize(self.settings.chess_com_url)

        # Wait for board to appear
        await self.browser.wait_for_board()

        # Initialize automation components
        page = await self.browser.get_page()
        self.board_reader = BoardReader(page)
        self.move_executor = MoveExecutor(
            page,
            min_delay=self.settings.min_move_delay,
            max_delay=self.settings.max_move_delay,
        )
        self.game_detector = GameDetector(page)

        print("Chess bot initialized successfully!")
        print(f"Engine depth: {self.settings.search_depth}")
        print(f"Opening book: {'enabled' if self.settings.use_opening_book else 'disabled'}")
        print(f"Tablebases: {'enabled' if self.tablebase.enabled else 'disabled'}")

    async def run(self):
        """
        Main bot loop.

        Continuously plays games on chess.com.
        """
        try:
            await self.initialize()

            while True:
                # Wait for a game to start
                game_started = await self.game_detector.wait_for_game_start()

                if not game_started:
                    print("Timeout waiting for game. Refreshing page...")
                    await self.browser.refresh()
                    continue

                # Detect player color
                self.player_color = await self.game_detector.detect_player_color()
                color_name = "White" if self.player_color == chess.WHITE else "Black"
                print(f"\nGame started! Playing as {color_name}")

                # Reset for new game
                self.internal_board = chess.Board()
                self.move_count = 0
                self.engine.reset()

                # Play the game
                result = await self.play_game()

                print(f"\nGame ended: {result}")
                print("Waiting for next game...\n")

                # Wait a bit before looking for next game
                await asyncio.sleep(3)

        except KeyboardInterrupt:
            print("\nBot stopped by user")
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await self.cleanup()

    async def play_game(self) -> str:
        """
        Play a single game.

        Returns:
            Game result string
        """
        while True:
            # Check if game is over
            is_over, result = await self.game_detector.is_game_over()
            if is_over:
                return self._format_result(result)

            # Read current board state
            try:
                current_board = await self.board_reader.read_board()
            except Exception as e:
                print(f"Error reading board: {e}")
                await asyncio.sleep(0.5)
                continue

            # Sync internal board with actual board
            self._sync_board(current_board)

            # Check if it's our turn
            is_our_turn = await self.game_detector.is_our_turn(self.player_color)

            if not is_our_turn:
                # Wait for opponent's move
                await asyncio.sleep(0.3)
                continue

            # Calculate and make our move
            best_move = await self.calculate_best_move()

            if best_move is None:
                print("No legal moves available!")
                break

            # Execute the move
            print(f"Playing: {self.internal_board.san(best_move)}")
            success = await self.move_executor.make_move(
                best_move,
                is_flipped=(self.player_color == chess.BLACK),
            )

            if success:
                # Update internal board
                self.internal_board.push(best_move)
                self.move_count += 1

                if self.settings.log_moves:
                    print(f"Move {self.move_count}: {best_move.uci()}")

            # Wait a bit before checking again
            await asyncio.sleep(0.5)

        return "Game ended"

    async def calculate_best_move(self) -> chess.Move:
        """
        Calculate the best move for the current position.

        Uses opening book, endgame tablebases, or the engine.

        Returns:
            The best move found
        """
        # 1. Try opening book (first ~10 moves)
        if (
            self.settings.use_opening_book
            and self.move_count < self.settings.opening_book_depth * 2  # fullmove vs halfmove
        ):
            book_move = self.opening_book.get_move(self.internal_board)
            if book_move:
                print("(Opening book)")
                return book_move

        # 2. Try endgame tablebase
        if self.tablebase.enabled:
            tb_move = self.tablebase.get_best_move(self.internal_board)
            if tb_move:
                print("(Tablebase)")
                return tb_move

        # 3. Use the engine
        print("(Calculating...)")
        best_move = await asyncio.to_thread(
            self.engine.find_best_move,
            self.internal_board,
        )

        return best_move

    def _sync_board(self, actual_board: chess.Board):
        """
        Sync internal board with the actual board from chess.com.

        This handles cases where moves were made that we missed.
        """
        # Compare piece positions (ignore move counters)
        internal_pieces = self.internal_board.fen().split()[0]
        actual_pieces = actual_board.fen().split()[0]

        if internal_pieces != actual_pieces:
            # Board has changed - try to find the move that was made
            # For now, just copy the board state
            # TODO: Track actual moves for better accuracy
            self.internal_board = actual_board.copy()

            # Set turn based on player color and whether we think it's our turn
            # (the actual_board may not have accurate turn info)

    def _format_result(self, result: GameResult) -> str:
        """Format game result as string."""
        if result == GameResult.WHITE_WINS:
            if self.player_color == chess.WHITE:
                return "Victory! (White wins)"
            return "Defeat (White wins)"
        elif result == GameResult.BLACK_WINS:
            if self.player_color == chess.BLACK:
                return "Victory! (Black wins)"
            return "Defeat (Black wins)"
        elif result == GameResult.DRAW:
            return "Draw"
        return "Unknown result"

    async def cleanup(self):
        """Clean up resources."""
        if self.tablebase:
            self.tablebase.close()
        if self.browser:
            await self.browser.close()


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Chess Bot for Chess.com",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--depth",
        type=int,
        default=5,
        help="Search depth (ply)",
    )
    parser.add_argument(
        "--time-limit",
        type=float,
        default=10.0,
        help="Maximum time per move (seconds)",
    )
    parser.add_argument(
        "--min-delay",
        type=float,
        default=1.0,
        help="Minimum delay before moving (seconds)",
    )
    parser.add_argument(
        "--max-delay",
        type=float,
        default=3.0,
        help="Maximum delay before moving (seconds)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode",
    )
    parser.add_argument(
        "--no-book",
        action="store_true",
        help="Disable opening book",
    )
    parser.add_argument(
        "--url",
        type=str,
        default="https://www.chess.com/play/online",
        help="Chess.com URL to navigate to",
    )

    args = parser.parse_args()

    # Create settings
    settings = Settings(
        search_depth=args.depth,
        time_limit=args.time_limit,
        min_move_delay=args.min_delay,
        max_move_delay=args.max_delay,
        headless=args.headless,
        use_opening_book=not args.no_book,
        chess_com_url=args.url,
    )

    # Run the bot
    bot = ChessBot(settings)
    await bot.run()


if __name__ == "__main__":
    asyncio.run(main())
