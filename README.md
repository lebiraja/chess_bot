# Chess Bot for Chess.com

A powerful Python chess bot that plays automatically on chess.com using the **Minimax algorithm with Alpha-Beta pruning**. The bot reads the board state directly from the browser, calculates optimal moves, and clicks to play them.

## Features

- **Minimax with Alpha-Beta Pruning** - Efficient search algorithm looking 5+ moves ahead
- **Iterative Deepening** - Searches progressively deeper for better time management
- **Transposition Table** - Caches positions using Zobrist hashing to avoid recalculation
- **Move Ordering** - Searches captures and strong moves first for faster pruning
- **Quiescence Search** - Extends search for tactical positions (captures, checks)
- **Opening Book** - Pre-computed opening moves for strong early game
- **Endgame Tablebases** - Perfect play with 6 or fewer pieces (optional, requires Syzygy files)
- **Persistent Login** - Remembers your chess.com session between runs
- **Human-like Delays** - Configurable delays to appear more natural
- **Auto-detection** - Automatically detects game start, your color, and turns

## Requirements

- Python 3.10+
- Google Chrome (installed automatically by Playwright)

## Installation

### 1. Clone or navigate to the project

```bash
cd /path/to/chess
```

### 2. Create a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Install Playwright browsers

```bash
playwright install chromium
```

## Usage

### Basic Usage

```bash
python main.py
```

This will:
1. Open a Chrome browser
2. Navigate to chess.com
3. Wait for you to log in (first time only - session is saved)
4. Wait for a game to start
5. Automatically play moves when it's your turn

### Command Line Options

| Option | Default | Description |
|--------|---------|-------------|
| `--depth` | 5 | Search depth in ply (half-moves) |
| `--time-limit` | 10.0 | Maximum seconds per move calculation |
| `--min-delay` | 1.0 | Minimum seconds before making a move |
| `--max-delay` | 3.0 | Maximum seconds before making a move |
| `--headless` | False | Run browser without visible window |
| `--no-book` | False | Disable opening book |
| `--url` | chess.com/play/online | Starting URL |

### Examples

```bash
# Play instantly (no delay) - for bullet/blitz
python main.py --min-delay 0 --max-delay 0

# Deeper search (stronger but slower) - for rapid/classical
python main.py --depth 6 --time-limit 15

# Quick and light - for bullet
python main.py --depth 4 --time-limit 5 --min-delay 0 --max-delay 0.5

# Disable opening book (pure calculation from move 1)
python main.py --no-book

# Run in headless mode (no visible browser)
python main.py --headless
```

## How It Works

### 1. Board Reading
The bot reads the chess board directly from chess.com's DOM:
- Parses piece positions from CSS classes (e.g., `.piece.wk.square-51` = White King on e1)
- Detects board orientation to know which color you're playing
- Monitors for board changes to detect opponent moves

### 2. Move Calculation
When it's your turn, the bot calculates the best move:

1. **Opening Book** (moves 1-10): Looks up the position in a database of known strong openings
2. **Endgame Tablebase** (≤6 pieces): If available, uses pre-computed perfect endgame play
3. **Minimax Search**: For all other positions:
   - Searches the game tree to the configured depth
   - Uses Alpha-Beta pruning to eliminate bad branches
   - Orders moves (captures first) for better pruning
   - Uses quiescence search to avoid tactical blunders
   - Caches positions in a transposition table

### 3. Position Evaluation
The engine evaluates positions based on:
- **Material**: Piece values (P=1, N/B=3, R=5, Q=9)
- **Piece Position**: Piece-square tables reward good placement
- **Pawn Structure**: Penalties for doubled/isolated pawns, bonuses for passed pawns
- **King Safety**: Pawn shield, open files near king
- **Mobility**: Number of legal moves

### 4. Move Execution
Once a move is calculated:
- Clicks the source square
- Clicks the destination square
- Handles pawn promotion if needed
- Waits for the move to register before continuing

## Project Structure

```
chess/
├── main.py                  # Main entry point and game loop
├── requirements.txt         # Python dependencies
├── README.md               # This file
│
├── config/
│   ├── settings.py         # Configuration options
│   └── openings.json       # Opening book database
│
├── engine/
│   ├── minimax.py          # Minimax search with Alpha-Beta
│   ├── evaluator.py        # Position evaluation function
│   └── transposition.py    # Transposition table (position cache)
│
├── database/
│   ├── opening_book.py     # Opening book handler
│   └── endgame_tablebase.py # Syzygy tablebase integration
│
└── automation/
    ├── browser.py          # Playwright browser control
    ├── board_reader.py     # Read board from chess.com DOM
    ├── move_executor.py    # Click squares to make moves
    └── game_detector.py    # Detect game state and turns
```

## Configuration

### Session Data
Your chess.com login is saved to `~/.chess-bot/browser-data/`. Delete this folder to reset and log in fresh.

### Opening Book
The opening book is stored in `config/openings.json`. You can add more positions by editing this file. Format:
```json
{
  "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq": [
    {"move": "e2e4", "weight": 40},
    {"move": "d2d4", "weight": 35}
  ]
}
```

### Endgame Tablebases (Optional)
For perfect endgame play, download Syzygy tablebases:
1. Download from https://syzygy-tables.info/
2. Place files in `~/chess/syzygy/`
3. The bot will automatically use them when ≤6 pieces remain

Sizes:
- 3-4 piece: ~7 MB
- 5 piece: ~1 GB
- 6 piece: ~150 GB

## Performance Tips

### For Stronger Play
- Increase `--depth` (each +1 roughly doubles thinking time)
- Increase `--time-limit` for more time per move
- Install Syzygy tablebases for perfect endgames

### For Faster Play
- Decrease `--depth` to 3-4 for bullet
- Set `--min-delay 0 --max-delay 0` for instant moves
- Reduce `--time-limit` to 3-5 seconds

### Typical Settings by Time Control

| Time Control | Recommended Settings |
|--------------|---------------------|
| Bullet (1+0) | `--depth 3 --time-limit 2 --min-delay 0 --max-delay 0` |
| Blitz (3+0) | `--depth 4 --time-limit 5 --min-delay 0 --max-delay 0.5` |
| Blitz (5+0) | `--depth 5 --time-limit 8 --min-delay 0.5 --max-delay 1` |
| Rapid (10+0) | `--depth 5 --time-limit 10 --min-delay 1 --max-delay 2` |
| Rapid (15+10) | `--depth 6 --time-limit 15 --min-delay 1 --max-delay 3` |

## Troubleshooting

### "Tablebase path not found"
This is just a warning - the bot works fine without tablebases. To enable:
1. Download Syzygy files from https://syzygy-tables.info/
2. Place in `~/chess/syzygy/`

### Bot not making moves
- Make sure you're logged into chess.com
- Ensure a game is active and it's your turn
- Check if the game window is visible (not minimized)

### "Board unchanged for too long"
This happens when waiting for your turn or if the opponent is thinking. The bot will continue when the board changes.

### Session expired
Delete `~/.chess-bot/browser-data/` and run again to log in fresh.

### Browser crashes
Try running without headless mode to see what's happening:
```bash
python main.py  # (headless is off by default)
```

## Technical Details

### Algorithm: Minimax with Alpha-Beta Pruning
The bot uses the classic minimax algorithm with alpha-beta pruning:
- **Minimax**: Assumes both players play optimally, finds the move that maximizes our minimum guaranteed score
- **Alpha-Beta**: Prunes branches that can't affect the final decision, reducing nodes searched by ~90%
- **Iterative Deepening**: Searches depth 1, then 2, then 3... until time runs out

### Search Enhancements
- **Move Ordering**: Searches captures (MVV-LVA), killer moves, and hash moves first
- **Transposition Table**: Zobrist hashing to cache and reuse position evaluations
- **Quiescence Search**: Extends tactical positions to avoid horizon effect
- **Null Move Pruning**: (planned) Skip a turn to detect zugzwang positions

### Evaluation Function
Scores are in centipawns (100 = 1 pawn advantage):
- Material: P=100, N=320, B=330, R=500, Q=900
- Position: Piece-square tables (+/- 50 centipawns typical)
- Pawn structure: Doubled (-20), isolated (-15), passed (+20-80)
- King safety: Pawn shield (+10 each), open files near king (-20)
- Mobility: ~10 centipawns per extra legal move

## Disclaimer

**Using bots on chess.com violates their Terms of Service** and may result in account bans. This project is for educational purposes only. Use responsibly and at your own risk.

## License

MIT License - Use freely for learning and personal projects.

---

**Happy chess botting!** 🤖♟️
