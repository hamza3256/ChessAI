"""Alpha-Beta search with iterative deepening, transposition table
integration, and time control.

The search uses negamax formulation with alpha-beta pruning.
Move ordering is driven by the TT best-move and MVV-LVA heuristic.
"""

from __future__ import annotations

import time
from typing import Optional

from engine.bitboard import (
    BoardState, make_move, decode_move,
    WHITE, BLACK, CAPTURE, EP_CAPTURE,
    WHITE_PAWN, WHITE_KNIGHT, WHITE_BISHOP, WHITE_ROOK, WHITE_QUEEN, WHITE_KING,
)
from engine.move_gen import (
    generate_legal_moves, is_in_check, is_checkmate, is_stalemate, iter_bits,
)
from engine.evaluation import evaluate
from engine.transposition import (
    TranspositionTable, EXACT, LOWER_BOUND, UPPER_BOUND,
)

INF = 1_000_000.0
CHECKMATE_SCORE = 100_000.0

# MVV-LVA piece values for move ordering (victim value - attacker value / 10)
_PIECE_VAL = [100, 320, 330, 500, 900, 20000,
              100, 320, 330, 500, 900, 20000]


def _move_score(state: BoardState, move: int, tt_move: int) -> int:
    """Heuristic score for move ordering (higher = searched first)."""
    if move == tt_move:
        return 10_000_000

    _, to_sq, flags = decode_move(move)

    if flags & CAPTURE or flags == EP_CAPTURE:
        victim = state.piece_at(to_sq)
        if victim >= 0:
            return 1_000_000 + _PIECE_VAL[victim] * 10
        return 1_000_000
    return 0


class AlphaBetaSearcher:
    """Iterative-deepening alpha-beta searcher with TT."""

    def __init__(self, tt: Optional[TranspositionTable] = None):
        self.tt = tt or TranspositionTable()
        self.nodes = 0
        self.max_depth_reached = 0
        self._start_time = 0.0
        self._time_limit = 0.0
        self._timed_out = False

    def _check_time(self) -> bool:
        if self._time_limit and time.time() - self._start_time > self._time_limit:
            self._timed_out = True
            return True
        return False

    def _negamax(self, state: BoardState, depth: int,
                 alpha: float, beta: float, color: int, ply: int) -> float:
        self.nodes += 1

        if self.nodes & 4095 == 0 and self._check_time():
            return 0.0

        alpha_orig = alpha

        # TT probe
        tt_score, tt_move = self.tt.probe(
            state.zobrist_hash, depth, alpha, beta
        )
        if tt_score is not None:
            return tt_score

        # Terminal / depth-0
        if depth <= 0:
            return self._quiesce(state, alpha, beta, color, ply)

        moves = generate_legal_moves(state)
        if not moves:
            if is_in_check(state, state.side_to_move):
                return -(CHECKMATE_SCORE - ply)
            return 0.0  # stalemate

        # Move ordering
        moves.sort(key=lambda m: _move_score(state, m, tt_move), reverse=True)

        best_move = moves[0]
        best_score = -INF

        for move in moves:
            if self._timed_out:
                break
            ns = make_move(state, move)
            score = -self._negamax(ns, depth - 1, -beta, -alpha, -color, ply + 1)

            if score > best_score:
                best_score = score
                best_move = move
            alpha = max(alpha, score)
            if alpha >= beta:
                break

        # TT store
        if not self._timed_out:
            if best_score <= alpha_orig:
                flag = UPPER_BOUND
            elif best_score >= beta:
                flag = LOWER_BOUND
            else:
                flag = EXACT
            self.tt.store(state.zobrist_hash, depth, best_score,
                          flag, best_move)

        return best_score

    def _quiesce(self, state: BoardState, alpha: float, beta: float,
                 color: int, ply: int) -> float:
        """Quiescence search: only examine captures to avoid horizon effect."""
        self.nodes += 1

        stand_pat = evaluate(state) * (1 if state.side_to_move == WHITE else -1)
        if stand_pat >= beta:
            return beta
        alpha = max(alpha, stand_pat)

        moves = generate_legal_moves(state)
        captures = []
        for m in moves:
            _, _, flags = decode_move(m)
            if flags & CAPTURE or flags == EP_CAPTURE:
                captures.append(m)

        captures.sort(key=lambda m: _move_score(state, m, 0), reverse=True)

        for move in captures:
            if self._timed_out:
                break
            ns = make_move(state, move)
            score = -self._quiesce(ns, -beta, -alpha, -color, ply + 1)

            if score >= beta:
                return beta
            alpha = max(alpha, score)

        return alpha

    def search(self, state: BoardState, max_depth: int = 64,
               time_limit: float = 5.0) -> tuple[int, float, dict]:
        """Run iterative-deepening search.

        Returns (best_move, score, info_dict).
        """
        self.nodes = 0
        self.max_depth_reached = 0
        self._start_time = time.time()
        self._time_limit = time_limit
        self._timed_out = False

        color = 1 if state.side_to_move == WHITE else -1
        best_move = 0
        best_score = -INF

        for depth in range(1, max_depth + 1):
            if self._timed_out:
                break

            score = self._negamax(state, depth, -INF, INF, color, 0)

            if not self._timed_out:
                best_score = score
                # Retrieve best move from TT
                _, tt_move = self.tt.probe(
                    state.zobrist_hash, 0, -INF, INF
                )
                if tt_move:
                    best_move = tt_move
                self.max_depth_reached = depth

        elapsed = time.time() - self._start_time
        nps = self.nodes / elapsed if elapsed > 0 else 0

        info = {
            "depth": self.max_depth_reached,
            "nodes": self.nodes,
            "time": elapsed,
            "nps": nps,
            "score": best_score,
            "tt_stats": self.tt.stats(),
        }

        return best_move, best_score, info
