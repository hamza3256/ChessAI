#!/usr/bin/env python3
"""Profile the chess engine search using cProfile and optionally line_profiler.

Usage:
    python -m profiling.profile_search              # cProfile
    kernprof -lv profiling/profile_search.py        # line_profiler

Run from the src/ directory.
"""

import cProfile
import pstats
import io
import os
import sys
import time

src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from engine.bitboard import parse_fen, STARTING_FEN
from engine.move_gen import generate_legal_moves, is_in_check
from engine.evaluation import evaluate
from search.alphabeta import AlphaBetaSearcher
from search.mcts import MCTSSearcher

# --- Test positions ---
POSITIONS = {
    "starting": STARTING_FEN,
    "italian_game": "r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3",
    "middlegame": "r1bq1rk1/ppp2ppp/2np1n2/2b1p3/2B1P3/2NP1N2/PPP2PPP/R1BQ1RK1 w - - 0 7",
    "endgame": "8/5pk1/6p1/8/3K4/8/1P6/8 w - - 0 40",
}


def profile_move_generation():
    """Profile legal move generation across several positions."""
    print("=" * 60)
    print("MOVE GENERATION PROFILING")
    print("=" * 60)

    for name, fen in POSITIONS.items():
        state = parse_fen(fen)
        start = time.perf_counter()
        for _ in range(1000):
            generate_legal_moves(state)
        elapsed = time.perf_counter() - start
        moves = generate_legal_moves(state)
        print(f"  {name:15s}: {len(moves):3d} moves | 1000 iters in {elapsed:.3f}s "
              f"({1000/elapsed:.0f} gen/s)")


def profile_evaluation():
    """Profile the evaluation function."""
    print("\n" + "=" * 60)
    print("EVALUATION PROFILING")
    print("=" * 60)

    for name, fen in POSITIONS.items():
        state = parse_fen(fen)
        start = time.perf_counter()
        for _ in range(10000):
            evaluate(state)
        elapsed = time.perf_counter() - start
        score = evaluate(state)
        print(f"  {name:15s}: score={score:+.0f}cp | 10k evals in {elapsed:.3f}s "
              f"({10000/elapsed:.0f} eval/s)")


# line_profiler decorators (active only under kernprof)
try:
    profile  # type: ignore[name-defined]
except NameError:
    def profile(func):
        return func


@profile
def profile_alphabeta_search():
    """Profile alpha-beta search with cProfile."""
    print("\n" + "=" * 60)
    print("ALPHA-BETA SEARCH PROFILING (depth 4)")
    print("=" * 60)

    state = parse_fen(POSITIONS["middlegame"])
    searcher = AlphaBetaSearcher()
    move, score, info = searcher.search(state, max_depth=4, time_limit=30.0)

    from engine.bitboard import move_to_uci
    print(f"  Best move: {move_to_uci(move)}")
    print(f"  Score: {score:+.0f}cp")
    print(f"  Depth: {info['depth']}")
    print(f"  Nodes: {info['nodes']}")
    print(f"  Time: {info['time']:.3f}s")
    print(f"  NPS: {info['nps']:.0f}")
    print(f"  TT: {info['tt_stats']}")


@profile
def profile_mcts_search():
    """Profile MCTS search with cProfile."""
    print("\n" + "=" * 60)
    print("MCTS SEARCH PROFILING (2000 iterations)")
    print("=" * 60)

    state = parse_fen(POSITIONS["middlegame"])
    searcher = MCTSSearcher()
    move, info = searcher.search(state, iterations=2000, time_limit=30.0)

    from engine.bitboard import move_to_uci
    print(f"  Best move: {move_to_uci(move)}")
    print(f"  Iterations: {info['iterations']}")
    print(f"  Time: {info['time']:.3f}s")
    print(f"  IPS: {info['ips']:.0f}")
    print(f"  Best visits: {info['best_visits']}")
    print(f"  Best winrate: {info['best_winrate']:.2%}")


def run_cprofile():
    """Run all profiling functions under cProfile."""
    print("\n" + "=" * 60)
    print("cProfile DETAILED OUTPUT (alpha-beta search)")
    print("=" * 60)

    state = parse_fen(POSITIONS["middlegame"])
    searcher = AlphaBetaSearcher()

    pr = cProfile.Profile()
    pr.enable()
    searcher.search(state, max_depth=4, time_limit=30.0)
    pr.disable()

    stream = io.StringIO()
    ps = pstats.Stats(pr, stream=stream).sort_stats("cumulative")
    ps.print_stats(30)
    print(stream.getvalue())


if __name__ == "__main__":
    profile_move_generation()
    profile_evaluation()
    profile_alphabeta_search()
    profile_mcts_search()
    run_cprofile()
