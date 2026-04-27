"""Position evaluation using material counting and NumPy-backed
piece-square tables (PST).

Positive scores favour White; negative favour Black.
"""

from __future__ import annotations

import numpy as np
from .bitboard import (
    BoardState, WHITE, BLACK,
    WHITE_PAWN, WHITE_KNIGHT, WHITE_BISHOP, WHITE_ROOK, WHITE_QUEEN, WHITE_KING,
    BLACK_PAWN, BLACK_KNIGHT, BLACK_BISHOP, BLACK_ROOK, BLACK_QUEEN, BLACK_KING,
)
from .move_gen import iter_bits

# ---------------------------------------------------------------------------
# Material values (centipawns)
# ---------------------------------------------------------------------------
MATERIAL = np.array([
    100,   # WHITE_PAWN
    320,   # WHITE_KNIGHT
    330,   # WHITE_BISHOP
    500,   # WHITE_ROOK
    900,   # WHITE_QUEEN
    20000, # WHITE_KING
    -100,  # BLACK_PAWN
    -320,  # BLACK_KNIGHT
    -330,  # BLACK_BISHOP
    -500,  # BLACK_ROOK
    -900,  # BLACK_QUEEN
    -20000,# BLACK_KING
], dtype=np.float64)

# ---------------------------------------------------------------------------
# Piece-square tables  (from White's perspective, flipped for Black)
# Index 0 = a1, 63 = h8
# ---------------------------------------------------------------------------

_PAWN_PST = np.array([
     0,  0,  0,  0,  0,  0,  0,  0,
    50, 50, 50, 50, 50, 50, 50, 50,
    10, 10, 20, 30, 30, 20, 10, 10,
     5,  5, 10, 25, 25, 10,  5,  5,
     0,  0,  0, 20, 20,  0,  0,  0,
     5, -5,-10,  0,  0,-10, -5,  5,
     5, 10, 10,-20,-20, 10, 10,  5,
     0,  0,  0,  0,  0,  0,  0,  0,
], dtype=np.float64)

_KNIGHT_PST = np.array([
    -50,-40,-30,-30,-30,-30,-40,-50,
    -40,-20,  0,  0,  0,  0,-20,-40,
    -30,  0, 10, 15, 15, 10,  0,-30,
    -30,  5, 15, 20, 20, 15,  5,-30,
    -30,  0, 15, 20, 20, 15,  0,-30,
    -30,  5, 10, 15, 15, 10,  5,-30,
    -40,-20,  0,  5,  5,  0,-20,-40,
    -50,-40,-30,-30,-30,-30,-40,-50,
], dtype=np.float64)

_BISHOP_PST = np.array([
    -20,-10,-10,-10,-10,-10,-10,-20,
    -10,  0,  0,  0,  0,  0,  0,-10,
    -10,  0,  5, 10, 10,  5,  0,-10,
    -10,  5,  5, 10, 10,  5,  5,-10,
    -10,  0, 10, 10, 10, 10,  0,-10,
    -10, 10, 10, 10, 10, 10, 10,-10,
    -10,  5,  0,  0,  0,  0,  5,-10,
    -20,-10,-10,-10,-10,-10,-10,-20,
], dtype=np.float64)

_ROOK_PST = np.array([
     0,  0,  0,  0,  0,  0,  0,  0,
     5, 10, 10, 10, 10, 10, 10,  5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
     0,  0,  0,  5,  5,  0,  0,  0,
], dtype=np.float64)

_QUEEN_PST = np.array([
    -20,-10,-10, -5, -5,-10,-10,-20,
    -10,  0,  0,  0,  0,  0,  0,-10,
    -10,  0,  5,  5,  5,  5,  0,-10,
     -5,  0,  5,  5,  5,  5,  0, -5,
      0,  0,  5,  5,  5,  5,  0, -5,
    -10,  5,  5,  5,  5,  5,  0,-10,
    -10,  0,  5,  0,  0,  0,  0,-10,
    -20,-10,-10, -5, -5,-10,-10,-20,
], dtype=np.float64)

_KING_MID_PST = np.array([
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -20,-30,-30,-40,-40,-30,-30,-20,
    -10,-20,-20,-20,-20,-20,-20,-10,
     20, 20,  0,  0,  0,  0, 20, 20,
     20, 30, 10,  0,  0, 10, 30, 20,
], dtype=np.float64)

def _flip_pst(pst: np.ndarray) -> np.ndarray:
    """Flip a PST vertically for Black's perspective and negate values."""
    return -pst.reshape(8, 8)[::-1].ravel().copy()

# White PSTs indexed by piece type; Black PSTs are the flipped/negated versions.
# Combined into a single (12, 64) array for vectorised lookup.
PST = np.zeros((12, 64), dtype=np.float64)
PST[WHITE_PAWN]   = _PAWN_PST
PST[WHITE_KNIGHT] = _KNIGHT_PST
PST[WHITE_BISHOP] = _BISHOP_PST
PST[WHITE_ROOK]   = _ROOK_PST
PST[WHITE_QUEEN]  = _QUEEN_PST
PST[WHITE_KING]   = _KING_MID_PST
PST[BLACK_PAWN]   = _flip_pst(_PAWN_PST)
PST[BLACK_KNIGHT] = _flip_pst(_KNIGHT_PST)
PST[BLACK_BISHOP] = _flip_pst(_BISHOP_PST)
PST[BLACK_ROOK]   = _flip_pst(_ROOK_PST)
PST[BLACK_QUEEN]  = _flip_pst(_QUEEN_PST)
PST[BLACK_KING]   = _flip_pst(_KING_MID_PST)


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

def popcount(bb: int) -> int:
    return bin(bb).count('1')


def evaluate(state: BoardState) -> float:
    """Return evaluation in centipawns (positive = White advantage).

    Uses NumPy for vectorised material counting and PST scoring.
    """
    score = 0.0

    pieces_np = state.to_numpy()

    # Material counting via popcount (vectorised across piece types)
    counts = np.array([popcount(int(pieces_np[i])) for i in range(12)],
                      dtype=np.float64)
    score += float(np.dot(counts, MATERIAL))

    # PST scoring: for each piece on the board, add its PST value
    for piece_idx in range(12):
        bb = state.pieces[piece_idx]
        for sq in iter_bits(bb):
            score += PST[piece_idx, sq]

    return score
