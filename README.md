# ChessAI: High-Performance Python Game Engine

## Current Features
* High-performance chess engine with NumPy-backed bitboard representation
* Alpha-Beta pruning with iterative deepening and Zobrist hashing-backed transposition tables
* Monte Carlo Tree Search (MCTS) with UCT selection policy
* Parallelised search using `concurrent.futures` and `multiprocessing`
* Non-blocking game state analysis with Pygame GUI
* Piece-square table evaluation with material counting
* Special chess rules including en passant, castling, and pawn promotion
* Check, checkmate, and stalemate detection
* Performance profiling with `cProfile` and `line_profiler`
* Launch menu to choose your game mode (PvP, Alpha-Beta, MCTS, Parallel variants)

## Installation
1. Install Python 3
1. Install dependencies: `pip install -r requirements.txt`
1. Run `cd src && python main.py` to start the program

## Technologies
Python, NumPy, Pygame, Multiprocessing, `concurrent.futures`, Alpha-Beta Pruning, MCTS, Performance Profiling

## TODO
- [X] Implement NumPy-backed bitboard board representation
- [X] Add Zobrist hashing with incremental updates
- [X] Build transposition table with EXACT/LOWER/UPPER flags
- [X] Write legal move generation from bitboards
- [X] Implement piece-square table evaluation with NumPy
- [X] Add alpha-beta search with iterative deepening and TT integration
- [X] Implement MCTS with UCT selection policy
- [X] Parallelise search with `concurrent.futures.ProcessPoolExecutor`
- [X] Rewrite UI in Pygame with drag-and-drop and non-blocking AI
- [X] Add `cProfile` and `line_profiler` profiling and benchmarks
- [X] Write perft and search unit tests
- [X] Add checkmate and stalemate detection
- [X] Implement quiescence search to mitigate horizon effect
- [X] Special chess rules: en passant, castling, pawn upgrade
- [X] Launch menu to choose game mode
- [X] Local player versus player (on the same device)
- [ ] Add PGN logging
