"""Transposition table backed by a fixed-size hash map.

Each entry stores a Zobrist key (for collision detection), search depth,
score, flag type (EXACT / LOWER / UPPER), and the best move found.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

# Flag types for TT entries
EXACT = 0
LOWER_BOUND = 1   # score is a lower bound (failed high)
UPPER_BOUND = 2   # score is an upper bound (failed low)

DEFAULT_SIZE = 1 << 20  # ~1 million entries


@dataclass(slots=True)
class TTEntry:
    key: int
    depth: int
    score: float
    flag: int
    best_move: int  # encoded move, or 0 if none


class TranspositionTable:
    """Fixed-size replacement-scheme transposition table."""

    def __init__(self, size: int = DEFAULT_SIZE):
        self.size = size
        self.table: list[Optional[TTEntry]] = [None] * size
        self.hits = 0
        self.misses = 0
        self.stores = 0

    def _index(self, key: int) -> int:
        return key % self.size

    def probe(self, key: int, depth: int, alpha: float, beta: float
              ) -> tuple[Optional[float], int]:
        """Look up a position in the TT.

        Returns (score_or_None, best_move).  *score* is not None only
        when the stored entry has sufficient depth and the flag allows
        a cutoff.  *best_move* (possibly 0) is always returned for
        move ordering even when the score cannot be used.
        """
        idx = self._index(key)
        entry = self.table[idx]

        if entry is None or entry.key != key:
            self.misses += 1
            return None, 0

        self.hits += 1
        best_move = entry.best_move

        if entry.depth >= depth:
            if entry.flag == EXACT:
                return entry.score, best_move
            if entry.flag == LOWER_BOUND and entry.score >= beta:
                return entry.score, best_move
            if entry.flag == UPPER_BOUND and entry.score <= alpha:
                return entry.score, best_move

        return None, best_move

    def store(self, key: int, depth: int, score: float,
              flag: int, best_move: int) -> None:
        """Store a search result, using depth-preferred replacement."""
        idx = self._index(key)
        existing = self.table[idx]

        # Replace if empty or new entry has >= depth (depth-preferred)
        if existing is None or existing.key == key or depth >= existing.depth:
            self.table[idx] = TTEntry(key, depth, score, flag, best_move)
            self.stores += 1

    def clear(self) -> None:
        self.table = [None] * self.size
        self.hits = 0
        self.misses = 0
        self.stores = 0

    def occupancy(self) -> float:
        filled = sum(1 for e in self.table if e is not None)
        return filled / self.size

    def stats(self) -> dict:
        total = self.hits + self.misses
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": self.hits / total if total else 0.0,
            "stores": self.stores,
            "occupancy": self.occupancy(),
        }
