#!/usr/bin/env python3
"""
Interactive Text User Interface for Chess Bot Game Mode Selection

Provides a curses-based menu for selecting game modes before launching.
Falls back to simple text UI if curses is not available.
"""
import sys
from typing import Optional

from config.game_modes import GAME_MODES, GameMode, list_game_modes


class SimpleTUI:
    """Simple text-based UI fallback (no curses dependency)."""

    def __init__(self):
        self.modes = list_game_modes()

    def show_menu(self) -> Optional[str]:
        """Display menu and get user selection."""
        print("\n" + "=" * 60)
        print("           ♟  CHESS BOT - GAME MODE SELECTOR  ♟")
        print("=" * 60)
        print()
        print("Available Game Modes:")
        print()

        for idx, (mode_id, mode) in enumerate(self.modes, 1):
            print(f"  [{idx}] {mode.display_name:20s} - {mode.description}")

        print()
        print("  [0] Exit")
        print()

        while True:
            try:
                choice = input("Select game mode (1-8, or 0 to exit): ").strip()
                choice_num = int(choice)

                if choice_num == 0:
                    return None

                if 1 <= choice_num <= len(self.modes):
                    selected_mode_id, selected_mode = self.modes[choice_num - 1]
                    self._show_mode_details(selected_mode_id, selected_mode)
                    confirm = (
                        input(
                            "\nStart bot with this mode? (y/n): "
                        )
                        .strip()
                        .lower()
                    )
                    if confirm == "y":
                        return selected_mode_id
                    else:
                        print("\nReturning to menu...")
                else:
                    print("Invalid choice. Please try again.")
            except ValueError:
                print("Invalid input. Please enter a number.")
            except KeyboardInterrupt:
                return None

    def _show_mode_details(self, mode_id: str, mode: GameMode):
        """Display details of a selected mode."""
        print("\n" + "-" * 60)
        print(f"Mode: {mode.display_name}")
        print("-" * 60)
        print(f"  Time Control:        {mode.time_seconds}s + {mode.increment}s")
        print(f"  Engine Depth:        {mode.search_depth} ply")
        print(f"  Time Per Move:       {mode.time_limit:.1f}s")
        print(f"  Move Delay:          {mode.min_delay:.1f}s - {mode.max_delay:.1f}s")
        print(f"  Description:         {mode.description}")
        print("-" * 60)


class CursesTUI:
    """Curses-based terminal UI with enhanced interactivity."""

    def __init__(self):
        try:
            import curses

            self.curses = curses
            self.enabled = True
        except ImportError:
            self.enabled = False
            return

        self.modes = list_game_modes()
        self.selected_idx = 0

    def show_menu(self) -> Optional[str]:
        """Display interactive menu using curses."""
        if not self.enabled:
            return None

        try:
            return self.curses.wrapper(self._run_menu)
        except Exception:
            # Fall back to simple UI on error
            return None

    def _run_menu(self, stdscr):
        """Main menu loop (called by curses.wrapper)."""
        self.curses.curs_set(0)  # Hide cursor
        stdscr.nodelay(1)  # Non-blocking getch()

        max_y, max_x = stdscr.getmaxyx()
        if max_x < 60 or max_y < 20:
            return None  # Terminal too small

        # Initialize colors
        self.curses.init_pair(1, self.curses.COLOR_CYAN, self.curses.COLOR_BLACK)
        self.curses.init_pair(2, self.curses.COLOR_WHITE, self.curses.COLOR_BLUE)
        self.curses.init_pair(3, self.curses.COLOR_GREEN, self.curses.COLOR_BLACK)
        self.curses.init_pair(4, self.curses.COLOR_YELLOW, self.curses.COLOR_BLACK)

        selected = None

        while True:
            stdscr.clear()
            self._draw_menu(stdscr)
            stdscr.refresh()

            ch = stdscr.getch()
            if ch == -1:  # No input
                continue
            elif ch in (self.curses.KEY_UP, ord("w")):
                self.selected_idx = max(0, self.selected_idx - 1)
            elif ch in (self.curses.KEY_DOWN, ord("s")):
                self.selected_idx = min(len(self.modes) - 1, self.selected_idx + 1)
            elif ch == ord("\n"):  # Enter
                selected = self._confirm_selection(stdscr)
                if selected is not None:
                    return selected
            elif ch == ord("q"):
                return None

    def _draw_menu(self, stdscr):
        """Draw the menu."""
        stdscr.addstr(
            1, 2, "♟  CHESS BOT - GAME MODE SELECTOR  ♟", self.curses.color_pair(1)
        )

        stdscr.addstr(3, 2, "SELECT GAME MODE", self.curses.color_pair(4))
        stdscr.addstr(4, 2, "─" * 50)

        for idx, (mode_id, mode) in enumerate(self.modes):
            y = 6 + idx
            if idx == self.selected_idx:
                stdscr.addstr(y, 2, f"> ", self.curses.color_pair(2))
                stdscr.addstr(
                    y, 4, f"[{idx + 1}] {mode.display_name:12} ", self.curses.color_pair(2)
                )
                stdscr.addstr(
                    y, 22, mode.description[: 50 - 22], self.curses.color_pair(2)
                )
            else:
                stdscr.addstr(y, 2, "  ", self.curses.color_pair(3))
                stdscr.addstr(y, 4, f"[{idx + 1}] {mode.display_name:12} ", self.curses.color_pair(3))
                stdscr.addstr(y, 22, mode.description[: 50 - 22], self.curses.color_pair(3))

        stdscr.addstr(6 + len(self.modes) + 2, 2, "─" * 50)
        stdscr.addstr(
            6 + len(self.modes) + 3,
            2,
            "↑↓ Navigate | Enter: Select | Q: Quit",
            self.curses.color_pair(4),
        )

    def _confirm_selection(self, stdscr):
        """Show confirmation for selected mode."""
        mode_id, mode = self.modes[self.selected_idx]

        stdscr.clear()
        stdscr.addstr(1, 2, f"Mode: {mode.display_name}", self.curses.color_pair(1))
        stdscr.addstr(2, 2, "─" * 50)

        details = [
            f"  Time Control:    {mode.time_seconds}s + {mode.increment}s",
            f"  Engine Depth:    {mode.search_depth} ply",
            f"  Time Per Move:   {mode.time_limit:.1f}s",
            f"  Move Delay:      {mode.min_delay:.1f}s - {mode.max_delay:.1f}s",
            f"  Description:     {mode.description}",
        ]

        for idx, detail in enumerate(details):
            stdscr.addstr(4 + idx, 2, detail)

        stdscr.addstr(10, 2, "─" * 50)
        stdscr.addstr(11, 2, "Start bot with this mode? (Y/N)", self.curses.color_pair(4))
        stdscr.refresh()

        while True:
            ch = stdscr.getch()
            if ch == ord("y") or ch == ord("Y"):
                return mode_id
            elif ch == ord("n") or ch == ord("N"):
                return None


def select_game_mode() -> Optional[str]:
    """
    Show interactive TUI for game mode selection.

    Returns:
        Selected game mode ID, or None if cancelled/exited.
    """
    # Try curses first, fall back to simple TUI
    if sys.stdout.isatty():
        tui = CursesTUI()
        if tui.enabled:
            result = tui.show_menu()
            if result is not None:
                return result

    # Fall back to simple text UI
    simple_tui = SimpleTUI()
    return simple_tui.show_menu()


if __name__ == "__main__":
    selected = select_game_mode()
    if selected:
        print(f"\nSelected mode: {selected}")
        mode = GAME_MODES[selected]
        print(f"Starting bot with {mode.display_name}...")
    else:
        print("\nExiting...")
