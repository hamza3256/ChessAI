"""Zobrist hashing for chess board states.

Pre-generates random 64-bit keys for all piece-square combinations,
side-to-move, castling rights, and en-passant files. Supports O(1)
incremental hash updates on make/unmake.
"""

import numpy as np

NUM_PIECE_TYPES = 12
NUM_SQUARES = 64
NUM_CASTLING = 16
NUM_EP_FILES = 8

_rng = np.random.RandomState(seed=0xDEADBEEF)

PIECE_SQUARE_KEYS: np.ndarray = _rng.randint(
    0, 2**63, size=(NUM_PIECE_TYPES, NUM_SQUARES), dtype=np.uint64
)

SIDE_TO_MOVE_KEY: int = int(_rng.randint(0, 2**63, dtype=np.uint64))

CASTLING_KEYS: np.ndarray = _rng.randint(
    0, 2**63, size=NUM_CASTLING, dtype=np.uint64
)

EP_FILE_KEYS: np.ndarray = _rng.randint(
    0, 2**63, size=NUM_EP_FILES, dtype=np.uint64
)


def compute_hash(pieces: list[int], side_to_move: int,
                 castling_rights: int, ep_square: int) -> int:
    """Compute full Zobrist hash from scratch."""
    h = 0
    for piece_idx in range(NUM_PIECE_TYPES):
        bb = pieces[piece_idx]
        while bb:
            sq = (bb & -bb).bit_length() - 1
            h ^= int(PIECE_SQUARE_KEYS[piece_idx, sq])
            bb &= bb - 1
    if side_to_move:
        h ^= SIDE_TO_MOVE_KEY
    h ^= int(CASTLING_KEYS[castling_rights])
    if ep_square >= 0:
        h ^= int(EP_FILE_KEYS[ep_square & 7])
    return h


def update_piece(h: int, piece_idx: int, sq: int) -> int:
    """Toggle a piece on/off a square (XOR is its own inverse)."""
    return h ^ int(PIECE_SQUARE_KEYS[piece_idx, sq])


def update_side(h: int) -> int:
    return h ^ SIDE_TO_MOVE_KEY


def update_castling(h: int, old_rights: int, new_rights: int) -> int:
    return h ^ int(CASTLING_KEYS[old_rights]) ^ int(CASTLING_KEYS[new_rights])


def update_ep(h: int, old_ep: int, new_ep: int) -> int:
    if old_ep >= 0:
        h ^= int(EP_FILE_KEYS[old_ep & 7])
    if new_ep >= 0:
        h ^= int(EP_FILE_KEYS[new_ep & 7])
    return h
