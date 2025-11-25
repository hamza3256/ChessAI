# Chess with multithreading using Alpha-Beta pruning and minimax algorithm

## Current Features
* Fully working chess game written from scratch
* CPU opponent built using alpha-beta pruning and the minimax algorithm
* **LLM Integration** - Play against AI chess LLMs (OpenAI GPT-4, Claude, etc.)
* Multithreading
* Special chess rules including en passant, castling, and pawn upgrade
* Launch menu to choose your game mode
* Local player versus player (on the same device)
* Random cpu opponent

## Installation
1. Install Python 3
2. Install core dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   Or install individually:
   ```bash
   pip install anytree Pillow
   ```
3. For LLM integration (optional):
   ```bash
   pip install openai anthropic
   ```
4. Set up API keys (for LLM mode):
   - Option 1: Set environment variables:
     ```bash
     export OPENAI_API_KEY="your-key-here"
     # or
     export ANTHROPIC_API_KEY="your-key-here"
     ```
   - Option 2: Copy `llm_config.json.example` to `llm_config.json` and add your API keys
5. Run main.py to start the program:
   ```bash
   python src/main.py
   ```

## LLM Integration

This project demonstrates strong foundational experience with complex AI algorithm design, optimization, and decision-making systems through LLM integration for chess gameplay.

### Features
- **FEN Notation Conversion**: Converts board state to standard FEN (Forsyth-Edwards Notation) for LLM understanding
- **Algebraic Notation Parsing**: Parses LLM responses in standard chess notation (e.g., "e4", "Nf3", "Qxe5")
- **Multi-Provider Support**: Works with OpenAI (GPT-4, GPT-3.5) and Anthropic (Claude) APIs
- **Error Handling**: Robust error handling with retry mechanisms and fallback behavior
- **Move Validation**: Validates LLM-generated moves before applying them to the board

### How It Works
1. Board state is converted to FEN notation
2. FEN is sent to LLM with a chess-specific prompt
3. LLM responds with a move in algebraic notation
4. Response is parsed and converted to board coordinates
5. Move is validated and applied to the board

### Supported Providers
- **OpenAI**: GPT-4, GPT-4 Turbo, GPT-3.5 Turbo
- **Anthropic**: Claude 3 Opus, Claude 3 Sonnet, Claude 3 Haiku

### Configuration
See `llm_config.json.example` for configuration options. The LLM player will automatically:
- Load API keys from environment variables or config file
- Use appropriate models based on provider
- Handle API errors gracefully
- Retry failed requests up to 3 times

## TODO
- [X] Write neural network game mode
- [X] Add checkmate indication - checkmate rules are in place
- [X] Write local network multiplayer
- [X] More thoroughly document items
- [X] Clean up parts - many parts are implemented inefficiently
- [X] Fix unknown bugs in the game
- [X] Implement smooth drag and drop graphics
- [X] Make more compatible with alternate resolutions
- [X] Add rule where a player can get more queens from pawn upgrade
- [X] Allow the CPU opponent to perform pawn upgrades
- [X] Integrate LLM models
