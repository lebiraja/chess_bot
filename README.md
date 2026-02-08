# Chess Bot for Chess.com

A Python chess bot that plays on chess.com using the Minimax algorithm with Alpha-Beta pruning.

## Features

- **Minimax with Alpha-Beta Pruning**: Efficient search algorithm that looks 5-6 moves ahead
- **Opening Book**: Pre-computed opening moves for strong early game play
- **Endgame Tablebases**: Perfect play with 6 or fewer pieces (requires Syzygy tablebases)
- **Browser Automation**: Fully automated play using Playwright
- **Human-like Behavior**: Random delays between moves to appear more natural
- **Auto-detection**: Automatically detects your color, game start/end, and whose turn it is

## Warning

Using bots on chess.com violates their Terms of Service and may result in account bans. Use this bot responsibly and at your own risk.

## Installation

1. **Create a virtual environment** (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or: venv\Scripts\activate  # Windows
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Install Playwright browsers**:
   ```bash
   playwright install chromium
   ```

4. **Optional: Download Syzygy tablebases** for perfect endgame play:
   - Download from https://syzygy-tables.info/
   - Place in `~/chess/syzygy/` or specify path in settings
   - 3-4-5 piece endings are ~1GB, 6-piece is ~150GB

## Usage

### Basic usage:
```bash
python main.py
```

### With options:
```bash
# Deeper search (stronger but slower)
python main.py --depth 6

# Faster moves (for bullet/blitz)
python main.py --depth 4 --min-delay 0.5 --max-delay 1.5

# Headless mode (no visible browser)
python main.py --headless

# Disable opening book
python main.py --no-book
```

### All options:
```
--depth        Search depth in ply (default: 5)
--time-limit   Maximum time per move in seconds (default: 10.0)
--min-delay    Minimum delay before moving in seconds (default: 1.0)
--max-delay    Maximum delay before moving in seconds (default: 3.0)
--headless     Run browser without visible window
--no-book      Disable opening book
--url          Chess.com URL to navigate to
```

## How It Works

### 1. Chess Engine
The engine uses the Minimax algorithm with Alpha-Beta pruning to search for the best move:
- **Minimax**: Assumes both players play optimally and finds the best move
- **Alpha-Beta Pruning**: Eliminates branches that don't need to be searched
- **Transposition Table**: Caches position evaluations to avoid redundant calculations
- **Move Ordering**: Searches promising moves first for better pruning
- **Quiescence Search**: Extends the search for captures/checks to avoid horizon effects

### 2. Board Evaluation
Positions are evaluated based on:
- **Material**: Piece values (Pawn=1, Knight/Bishop=3, Rook=5, Queen=9)
- **Piece Position**: Piece-square tables reward good piece placement
- **Pawn Structure**: Penalties for doubled/isolated pawns, bonuses for passed pawns
- **King Safety**: Pawn shield, open files near king
- **Mobility**: Number of legal moves

### 3. Opening Book
Uses pre-computed opening theory for the first ~10 moves to:
- Save calculation time
- Play well-established opening lines
- Avoid early game blunders

### 4. Endgame Tablebases
With Syzygy tablebases installed, the bot plays perfectly in endgames with 6 or fewer pieces.

### 5. Browser Automation
Uses Playwright to:
- Read the board state from the DOM
- Detect whose turn it is
- Click squares to make moves
- Detect game start and end

## Project Structure

```
chess/
├── config/
│   ├── settings.py      # Configuration
│   └── openings.json    # Opening book data
├── engine/
│   ├── minimax.py       # Search algorithm
│   ├── evaluator.py     # Position evaluation
│   └── transposition.py # Position cache
├── database/
│   ├── opening_book.py  # Opening book handler
│   └── endgame_tablebase.py  # Syzygy integration
├── automation/
│   ├── browser.py       # Browser control
│   ├── board_reader.py  # Read board from DOM
│   ├── move_executor.py # Click to make moves
│   └── game_detector.py # Detect game state
├── main.py              # Main entry point
└── requirements.txt     # Dependencies
```

## Tuning

### For Stronger Play
- Increase `--depth` (but moves take longer)
- Install Syzygy tablebases for perfect endgame
- Add more positions to the opening book

### For Faster Play
- Decrease `--depth` (weaker but faster)
- Reduce `--time-limit`
- Reduce `--min-delay` and `--max-delay`

## Troubleshooting

### "Could not find chess board on page"
- Make sure you're logged into chess.com
- Try refreshing the page
- Check if chess.com's DOM structure has changed

### Bot not making moves
- Verify the game is active and it's your turn
- Check console output for errors
- Try increasing delays if moves are too fast

### "chess.syzygy not available"
- This is just a warning - the bot will work without tablebases
- To enable: `pip install chess[syzygy]` and download tablebase files

## Contributing

Feel free to improve the bot by:
- Adding more opening book positions
- Improving the evaluation function
- Adding new search optimizations
- Updating selectors if chess.com changes their DOM

## License

This project is for educational purposes only. Use responsibly.
