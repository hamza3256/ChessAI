#!/usr/bin/env python3
"""Benchmark alpha-beta vs MCTS search strategies.

Runs both algorithms from the same positions and compares:
  - Nodes/iterations evaluated
  - Time per move
  - Search depth / iterations reached
  - Quality of chosen move (evaluation score)

Usage:
    python -m profiling.benchmark

Run from the src/ directory.
"""

import os
import sys
import time

src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from engine.bitboard import parse_fen, make_move, move_to_uci
from engine.evaluation import evaluate
from search.alphabeta import AlphaBetaSearcher
from search.mcts import MCTSSearcher

POSITIONS = {
    "starting": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
    "italian_game": "r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3",
    "middlegame": "r1bq1rk1/ppp2ppp/2np1n2/2b1p3/2B1P3/2NP1N2/PPP2PPP/R1BQ1RK1 w - - 0 7",
    "tactical": "r2q1rk1/pp2ppbp/2p2np1/6B1/3PP1b1/2N2N2/PPQ2PPP/R3KB1R w KQ - 0 10",
    "endgame": "8/5pk1/6p1/8/3K4/8/1P6/8 w - - 0 40",
}

TIME_LIMIT = 3.0
AB_DEPTH = 5
MCTS_ITERS = 5000


def benchmark_position(name: str, fen: str) -> dict:
    state = parse_fen(fen)
    results = {"position": name, "fen": fen}

    # Alpha-Beta
    ab = AlphaBetaSearcher()
    ab_move, ab_score, ab_info = ab.search(
        state, max_depth=AB_DEPTH, time_limit=TIME_LIMIT
    )
    ab_result_state = make_move(state, ab_move) if ab_move else state
    results["ab"] = {
        "move": move_to_uci(ab_move) if ab_move else "none",
        "score": ab_score,
        "depth": ab_info.get("depth", 0),
        "nodes": ab_info.get("nodes", 0),
        "time": ab_info.get("time", 0),
        "nps": ab_info.get("nps", 0),
        "eval_after": evaluate(ab_result_state),
    }

    # MCTS
    mcts = MCTSSearcher()
    mcts_move, mcts_info = mcts.search(
        state, iterations=MCTS_ITERS, time_limit=TIME_LIMIT
    )
    mcts_result_state = make_move(state, mcts_move) if mcts_move else state
    results["mcts"] = {
        "move": move_to_uci(mcts_move) if mcts_move else "none",
        "iterations": mcts_info.get("iterations", 0),
        "time": mcts_info.get("time", 0),
        "ips": mcts_info.get("ips", 0),
        "best_visits": mcts_info.get("best_visits", 0),
        "best_winrate": mcts_info.get("best_winrate", 0),
        "eval_after": evaluate(mcts_result_state),
    }

    return results


def print_results(all_results: list[dict]) -> None:
    print("\n" + "=" * 90)
    print(f"{'BENCHMARK RESULTS':^90}")
    print("=" * 90)
    print(f"\nTime limit: {TIME_LIMIT}s | AB depth: {AB_DEPTH} | MCTS iters: {MCTS_ITERS}")

    header = (f"{'Position':15s} | {'':^35s} | {'':^35s}")
    ab_header = f"{'Move':6s} {'Depth':>5s} {'Nodes':>8s} {'Time':>5s} {'NPS':>8s} {'Score':>7s}"
    mcts_header = f"{'Move':6s} {'Iters':>6s} {'Time':>5s} {'IPS':>7s} {'WR':>6s} {'Eval':>7s}"

    print(f"\n{'Position':15s} | {'Alpha-Beta':^35s} | {'MCTS':^35s}")
    print(f"{'-'*15:s}-+-{'-'*35:s}-+-{'-'*35:s}")
    print(f"{'':15s} | {ab_header} | {mcts_header}")
    print(f"{'-'*15:s}-+-{'-'*35:s}-+-{'-'*35:s}")

    for r in all_results:
        ab = r["ab"]
        mcts = r["mcts"]
        ab_str = (f"{ab['move']:6s} {ab['depth']:5d} {ab['nodes']:8d} "
                  f"{ab['time']:5.1f} {ab['nps']:8.0f} {ab['score']:+7.0f}")
        mcts_str = (f"{mcts['move']:6s} {mcts['iterations']:6d} "
                    f"{mcts['time']:5.1f} {mcts['ips']:7.0f} "
                    f"{mcts['best_winrate']:6.1%} {mcts['eval_after']:+7.0f}")
        print(f"{r['position']:15s} | {ab_str} | {mcts_str}")

    print("=" * 90)


def main():
    print("Running benchmarks...")
    print(f"Positions: {len(POSITIONS)}")
    print(f"Time limit per position per algorithm: {TIME_LIMIT}s")
    print()

    all_results = []
    for name, fen in POSITIONS.items():
        print(f"  Benchmarking: {name}...", end=" ", flush=True)
        result = benchmark_position(name, fen)
        ab_time = result["ab"]["time"]
        mcts_time = result["mcts"]["time"]
        print(f"done (AB: {ab_time:.1f}s, MCTS: {mcts_time:.1f}s)")
        all_results.append(result)

    print_results(all_results)


if __name__ == "__main__":
    main()
