# Chess Bot Architecture

This document explains the internal architecture of the chess bot for developers who want to understand or modify the code.

## Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                          main.py                                 │
│                       (ChessBot class)                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   Engine    │  │  Database   │  │      Automation         │  │
│  │             │  │             │  │                         │  │
│  │ - minimax   │  │ - openings  │  │ - browser    - board    │  │
│  │ - evaluator │  │ - tablebase │  │ - executor   - detector │  │
│  │ - transpos. │  │             │  │                         │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │   chess.com     │
                    │   (Browser)     │
                    └─────────────────┘
```

## Module Details

### 1. Engine Module (`engine/`)

The chess engine is the brain of the bot.

#### `minimax.py` - Search Algorithm

```python
class ChessEngine:
    def find_best_move(board) -> Move
    def _search_root(board, depth) -> (score, move)
    def _alpha_beta(board, depth, alpha, beta) -> score
    def _quiescence(board, alpha, beta, depth) -> score
    def _order_moves(board, depth, hash_move) -> list[Move]
```

**Key concepts:**

- **Alpha-Beta Pruning**: Maintains alpha (best score for maximizer) and beta (best score for minimizer). If alpha >= beta, we can prune the remaining branches.

- **Iterative Deepening**: Instead of searching directly to depth 5, we search depth 1, 2, 3, 4, 5. This gives us a best move at each depth in case we run out of time.

- **Move Ordering**: We search the most promising moves first:
  1. Hash move (from transposition table)
  2. Captures (ordered by MVV-LVA: Most Valuable Victim - Least Valuable Attacker)
  3. Killer moves (moves that caused beta cutoffs at this depth before)
  4. History heuristic (moves that have been good in the past)

- **Quiescence Search**: At leaf nodes, we continue searching captures to avoid the "horizon effect" (missing a queen capture just beyond our search depth).

#### `evaluator.py` - Position Evaluation

```python
class Evaluator:
    def evaluate(board) -> int  # Centipawns, positive = good for side to move
    def _evaluate_material(board) -> int
    def _evaluate_piece_positions(board) -> int
    def _evaluate_mobility(board) -> int
    def _evaluate_pawn_structure(board) -> int
    def _evaluate_king_safety(board) -> int
```

**Evaluation components:**

| Component | Weight | Description |
|-----------|--------|-------------|
| Material | 1.0 | Sum of piece values |
| Position | 0.3 | Piece-square table bonuses |
| Mobility | 0.1 | Legal move count difference |
| Pawn Structure | 0.2 | Doubled, isolated, passed pawns |
| King Safety | 0.5 | Pawn shield, open files (middlegame only) |

**Piece-Square Tables**: 8x8 arrays that give bonuses/penalties for each piece type on each square. For example, knights get bonuses for central squares, pawns get bonuses for advancing.

#### `transposition.py` - Position Cache

```python
class TranspositionTable:
    def hash_position(board) -> int  # Zobrist hash
    def store(board, depth, score, node_type, best_move)
    def probe(board) -> TTEntry | None
    def get_pv_line(board) -> list[Move]
```

**Zobrist Hashing**: Creates a unique 64-bit hash for each position:
- XOR random numbers for each piece on each square
- XOR for side to move
- XOR for castling rights
- XOR for en passant file

**Node Types**:
- `EXACT`: Score is exact
- `LOWER_BOUND`: Score is at least this (beta cutoff)
- `UPPER_BOUND`: Score is at most this (alpha cutoff)

### 2. Database Module (`database/`)

#### `opening_book.py` - Opening Theory

```python
class OpeningBook:
    def get_move(board, random_choice=True) -> Move | None
    def is_in_book(board) -> bool
    def add_move(board, move, weight)
```

The opening book maps FEN positions to lists of moves with weights. Higher weight = more likely to be chosen.

Format in `openings.json`:
```json
{
  "fen_position": [
    {"move": "e2e4", "weight": 40},
    {"move": "d2d4", "weight": 35}
  ]
}
```

#### `endgame_tablebase.py` - Perfect Endgame Play

```python
class EndgameTablebase:
    def probe_wdl(board) -> int  # Win/Draw/Loss: 2/0/-2
    def probe_dtz(board) -> int  # Distance To Zeroing (capture/pawn move)
    def get_best_move(board) -> Move | None
```

Uses Syzygy tablebases via `python-chess`. Only probes when:
- ≤6 pieces on board
- No castling rights (Syzygy doesn't include these)

### 3. Automation Module (`automation/`)

#### `browser.py` - Browser Control

```python
class BrowserController:
    def initialize(url)  # Launch Chrome, navigate
    def wait_for_board(timeout)
    def close()
    def refresh()
```

**Persistent Context**: Uses `launch_persistent_context` to save cookies/session to `~/.chess-bot/browser-data/`. This means you only need to log in once.

**Anti-Detection**: Removes the `webdriver` flag that sites use to detect automation.

#### `board_reader.py` - Read Chess.com DOM

```python
class BoardReader:
    def read_board() -> chess.Board
    def detect_last_move() -> Move | None
    def is_board_flipped() -> bool
```

**Chess.com DOM Structure**:
```html
<chess-board class="board flipped">  <!-- flipped = playing Black -->
  <div class="piece wk square-51"></div>  <!-- White King on e1 -->
  <div class="piece bp square-57"></div>  <!-- Black Pawn on e7 -->
</chess-board>
```

**Square Numbering**: `square-{file}{rank}` where file=1-8 (a-h), rank=1-8
- a1 = square-11
- e4 = square-54
- h8 = square-88

**Piece Codes**: `{color}{piece}` - w/b + p/n/b/r/q/k

#### `move_executor.py` - Click to Move

```python
class MoveExecutor:
    def make_move(move, is_flipped, delay) -> bool
    def _click_square(selector)
    def _handle_promotion(piece_type)
```

Clicks the source square, then the destination square. Adds random human-like delays between clicks.

#### `game_detector.py` - Game State Detection

```python
class GameDetector:
    def detect_player_color() -> chess.WHITE | chess.BLACK
    def is_our_turn(player_color) -> bool
    def wait_for_game_start(timeout) -> bool
    def get_game_state() -> GameState
    def is_game_over() -> (bool, GameResult)
```

**Turn Detection Methods** (tries in order):
1. Clock highlighting (`.clock-bottom.clock-player-turn`)
2. Piece interactivity (cursor style)
3. Move indicator class

### 4. Main Orchestrator (`main.py`)

```python
class ChessBot:
    def run()  # Main loop
    def play_game() -> str  # Play one game
    def calculate_best_move() -> Move
    def _sync_board(actual_board)
    def _is_our_turn(current_board) -> bool
```

**Game Loop**:
```
1. Initialize browser, navigate to chess.com
2. Wait for game to start
3. Detect player color
4. Loop:
   a. Read board from DOM
   b. Check if board changed
   c. If our turn:
      - Calculate best move (book → tablebase → engine)
      - Execute move (click squares)
      - Wait for move to register
   d. Check for game over
5. Wait for next game
```

## Data Flow

```
┌─────────────┐    read_board()    ┌─────────────┐
│ chess.com   │ ──────────────────→│ BoardReader │
│    DOM      │                    └──────┬──────┘
└─────────────┘                           │
                                          │ chess.Board
                                          ▼
                              ┌───────────────────────┐
                              │      ChessBot         │
                              │   _sync_board()       │
                              │   _is_our_turn()      │
                              └───────────┬───────────┘
                                          │
                    ┌─────────────────────┼─────────────────────┐
                    ▼                     ▼                     ▼
            ┌───────────────┐    ┌───────────────┐    ┌───────────────┐
            │ OpeningBook   │    │ Tablebase    │    │ ChessEngine   │
            │ get_move()    │    │ get_best_move│    │ find_best_move│
            └───────┬───────┘    └───────┬───────┘    └───────┬───────┘
                    │                    │                    │
                    └────────────────────┴────────────────────┘
                                         │
                                         │ chess.Move
                                         ▼
                              ┌───────────────────────┐
                              │    MoveExecutor       │
                              │    make_move()        │
                              └───────────┬───────────┘
                                          │ click events
                                          ▼
                              ┌───────────────────────┐
                              │     chess.com         │
                              │      Browser          │
                              └───────────────────────┘
```

## Search Tree Example

For position after 1.e4 e5 2.Nf3, searching depth 3:

```
Root (White to move)
├── Bb5 (Ruy Lopez)
│   ├── a6
│   │   ├── Ba4 → eval: +25
│   │   ├── Bxc6 → eval: +15
│   │   └── ...
│   ├── Nf6
│   │   ├── O-O → eval: +20
│   │   └── ...
│   └── ...
├── Bc4 (Italian)
│   ├── Bc5
│   │   ├── c3 → eval: +18
│   │   └── ...
│   └── ...
├── d4 (Scotch)  ← Alpha-beta prunes if score < alpha
│   └── ...
└── ...

Best move: Bb5 (score: +25)
```

## Performance Characteristics

| Depth | Typical Nodes | Time (approx) |
|-------|--------------|---------------|
| 3 | 2,000 | 0.5s |
| 4 | 15,000 | 2s |
| 5 | 50,000 | 5s |
| 6 | 200,000 | 15s |

With good move ordering and transposition table, alpha-beta typically searches only √(branching factor) nodes compared to pure minimax.

## Future Improvements

- **Null Move Pruning**: Skip a turn to quickly detect positions where we're much better
- **Late Move Reductions**: Search later moves with reduced depth since they're less likely to be best
- **Aspiration Windows**: Use narrow alpha-beta window initially, widen if needed
- **Parallel Search**: Use multiple threads for deeper searches
- **Neural Network Evaluation**: Replace hand-crafted eval with learned model
- **Monte Carlo Tree Search**: Alternative to minimax, used by AlphaZero
