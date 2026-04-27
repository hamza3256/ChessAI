"""Parallel search dispatcher using concurrent.futures and multiprocessing.

Provides two parallelisation strategies:
  1. Root parallelisation for alpha-beta: distributes root moves across
     CPU cores via ProcessPoolExecutor.
  2. Tree parallelisation for MCTS: runs independent MCTS playouts in
     parallel and aggregates visit counts.

Also provides an async dispatcher that wraps search in a Future so the
Pygame UI loop can poll for results without blocking.
"""

from __future__ import annotations

import os
import time
from concurrent.futures import ProcessPoolExecutor, Future
from multiprocessing import cpu_count
from typing import Optional

from engine.bitboard import BoardState, make_move, decode_move, move_to_uci, WHITE
from engine.move_gen import generate_legal_moves, is_in_check
from engine.evaluation import evaluate
from engine.transposition import TranspositionTable
from search.alphabeta import AlphaBetaSearcher, INF, CHECKMATE_SCORE
from search.mcts import MCTSSearcher


# ---------------------------------------------------------------------------
# Worker functions (must be top-level for pickling)
# ---------------------------------------------------------------------------

def _ab_worker(state_fen: str, move: int, depth: int,
               time_limit: float) -> tuple[int, float]:
    """Search a single root move in a child process."""
    from engine.bitboard import parse_fen, make_move
    state = parse_fen(state_fen)
    ns = make_move(state, move)

    searcher = AlphaBetaSearcher()
    # Search from opponent's perspective, negate score
    _, score, _ = searcher.search(ns, max_depth=depth - 1,
                                  time_limit=time_limit)
    return move, -score


def _mcts_worker(state_fen: str, iterations: int,
                 time_limit: float, seed: int) -> dict[int, tuple[int, float]]:
    """Run MCTS from the root position and return move -> (visits, wins)."""
    import random
    random.seed(seed)
    from engine.bitboard import parse_fen
    state = parse_fen(state_fen)

    searcher = MCTSSearcher()
    searcher.search(state, iterations=iterations, time_limit=time_limit)

    # We need to access root node internals, so re-run and collect
    from search.mcts import MCTSNode, _select, _expand, _simulate, _backpropagate
    root = MCTSNode(state)
    import time as _time
    start = _time.time()
    for _ in range(iterations):
        if _time.time() - start > time_limit:
            break
        leaf = _select(root)
        if not leaf.is_terminal():
            leaf = _expand(leaf)
        result = _simulate(leaf.state)
        _backpropagate(leaf, result)

    results = {}
    for child in root.children:
        results[child.move] = (child.visits, child.wins)
    return results


# ---------------------------------------------------------------------------
# Parallel Alpha-Beta (root parallelisation)
# ---------------------------------------------------------------------------

class ParallelAlphaBeta:
    """Distributes root moves across processes using concurrent.futures."""

    def __init__(self, num_workers: Optional[int] = None):
        self.num_workers = num_workers or cpu_count()

    def search(self, state: BoardState, max_depth: int = 6,
               time_limit: float = 10.0) -> tuple[int, float, dict]:
        from engine.bitboard import to_fen
        fen = to_fen(state)
        moves = generate_legal_moves(state)

        if not moves:
            return 0, 0.0, {}
        if len(moves) == 1:
            return moves[0], 0.0, {"depth": 1, "single_move": True}

        per_move_time = time_limit / 1.5
        start = time.time()

        best_move = moves[0]
        best_score = -INF

        with ProcessPoolExecutor(max_workers=self.num_workers) as executor:
            futures = {
                executor.submit(_ab_worker, fen, m, max_depth, per_move_time): m
                for m in moves
            }

            for future in futures:
                try:
                    move, score = future.result(timeout=time_limit + 2)
                    if score > best_score:
                        best_score = score
                        best_move = move
                except Exception:
                    pass

        elapsed = time.time() - start
        info = {
            "depth": max_depth,
            "time": elapsed,
            "workers": self.num_workers,
            "root_moves": len(moves),
        }
        return best_move, best_score, info


# ---------------------------------------------------------------------------
# Parallel MCTS (tree parallelisation)
# ---------------------------------------------------------------------------

class ParallelMCTS:
    """Runs independent MCTS searches in parallel and aggregates results."""

    def __init__(self, num_workers: Optional[int] = None):
        self.num_workers = num_workers or cpu_count()

    def search(self, state: BoardState, iterations: int = 10000,
               time_limit: float = 10.0) -> tuple[int, dict]:
        from engine.bitboard import to_fen
        fen = to_fen(state)
        per_worker_iters = iterations // self.num_workers
        start = time.time()

        aggregated: dict[int, list[float]] = {}  # move -> [total_visits, total_wins]

        with ProcessPoolExecutor(max_workers=self.num_workers) as executor:
            futures = [
                executor.submit(
                    _mcts_worker, fen, per_worker_iters,
                    time_limit * 0.9, seed=i * 42
                )
                for i in range(self.num_workers)
            ]

            for future in futures:
                try:
                    results = future.result(timeout=time_limit + 2)
                    for move, (visits, wins) in results.items():
                        if move not in aggregated:
                            aggregated[move] = [0.0, 0.0]
                        aggregated[move][0] += visits
                        aggregated[move][1] += wins
                except Exception:
                    pass

        if not aggregated:
            moves = generate_legal_moves(state)
            return (moves[0] if moves else 0), {}

        best_move = max(aggregated, key=lambda m: aggregated[m][0])
        elapsed = time.time() - start

        total_visits = sum(v[0] for v in aggregated.values())
        info = {
            "total_iterations": total_visits,
            "time": elapsed,
            "workers": self.num_workers,
            "best_visits": aggregated[best_move][0],
            "best_winrate": (aggregated[best_move][1] / aggregated[best_move][0]
                             if aggregated[best_move][0] else 0),
        }
        return best_move, info


# ---------------------------------------------------------------------------
# Async dispatcher for non-blocking UI integration
# ---------------------------------------------------------------------------

_executor: Optional[ProcessPoolExecutor] = None


def _get_executor() -> ProcessPoolExecutor:
    global _executor
    if _executor is None:
        _executor = ProcessPoolExecutor(max_workers=cpu_count())
    return _executor


def _run_search_sync(fen: str, mode: str, depth: int,
                     time_limit: float, iterations: int) -> tuple:
    """Synchronous search entry point for the worker process."""
    from engine.bitboard import parse_fen
    state = parse_fen(fen)

    if mode == "alphabeta":
        searcher = AlphaBetaSearcher()
        move, score, info = searcher.search(state, max_depth=depth,
                                            time_limit=time_limit)
        return move, score, info
    elif mode == "parallel_ab":
        pab = ParallelAlphaBeta()
        return pab.search(state, max_depth=depth, time_limit=time_limit)
    elif mode == "mcts":
        searcher = MCTSSearcher()
        move, info = searcher.search(state, iterations=iterations,
                                     time_limit=time_limit)
        return move, 0.0, info
    elif mode == "parallel_mcts":
        pmcts = ParallelMCTS()
        move, info = pmcts.search(state, iterations=iterations,
                                  time_limit=time_limit)
        return move, 0.0, info
    else:
        raise ValueError(f"Unknown search mode: {mode}")


def submit_search(state: BoardState, mode: str = "alphabeta",
                  depth: int = 6, time_limit: float = 5.0,
                  iterations: int = 5000) -> Future:
    """Submit a search to the background process pool.

    Returns a Future whose result is (best_move, score, info_dict).
    The Pygame loop can poll future.done() each frame.
    """
    from engine.bitboard import to_fen
    fen = to_fen(state)
    executor = _get_executor()
    return executor.submit(_run_search_sync, fen, mode, depth,
                           time_limit, iterations)


def shutdown_executor() -> None:
    global _executor
    if _executor is not None:
        _executor.shutdown(wait=False)
        _executor = None
