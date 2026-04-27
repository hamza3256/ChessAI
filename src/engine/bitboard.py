"""NumPy-backed bitboard representation for chess.

Stores the board as 12 uint64 bitboards (one per piece-type/color) inside a
NumPy array, plus game-state metadata.  Provides copy-make move application
with incremental Zobrist hash updates.

Square mapping:  a1=0, b1=1, …, h1=7, a2=8, …, h8=63.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from . import zobrist

# ---------------------------------------------------------------------------
# Piece indices (into the 12-element pieces array)
# ---------------------------------------------------------------------------
WHITE_PAWN, WHITE_KNIGHT, WHITE_BISHOP = 0, 1, 2
WHITE_ROOK, WHITE_QUEEN, WHITE_KING = 3, 4, 5
BLACK_PAWN, BLACK_KNIGHT, BLACK_BISHOP = 6, 7, 8
BLACK_ROOK, BLACK_QUEEN, BLACK_KING = 9, 10, 11

PIECE_CHARS = "PNBRQKpnbrqk"
CHAR_TO_PIECE = {c: i for i, c in enumerate(PIECE_CHARS)}

WHITE, BLACK = 0, 1

# Castling right flags
WK_CASTLE = 1
WQ_CASTLE = 2
BK_CASTLE = 4
BQ_CASTLE = 8
ALL_CASTLE = WK_CASTLE | WQ_CASTLE | BK_CASTLE | BQ_CASTLE

# ---------------------------------------------------------------------------
# Move encoding  (16-bit int: 6 from | 6 to | 4 flags)
# ---------------------------------------------------------------------------
QUIET = 0
DOUBLE_PAWN = 1
KING_CASTLE = 2
QUEEN_CASTLE = 3
CAPTURE = 4
EP_CAPTURE = 5
PROMO_N = 8
PROMO_B = 9
PROMO_R = 10
PROMO_Q = 11
PROMO_CAPTURE_N = 12
PROMO_CAPTURE_B = 13
PROMO_CAPTURE_R = 14
PROMO_CAPTURE_Q = 15


def encode_move(from_sq: int, to_sq: int, flags: int = QUIET) -> int:
    return from_sq | (to_sq << 6) | (flags << 12)


def decode_move(move: int) -> tuple[int, int, int]:
    return move & 0x3F, (move >> 6) & 0x3F, (move >> 12) & 0xF


def move_to_uci(move: int) -> str:
    from_sq, to_sq, flags = decode_move(move)
    promo = ""
    if flags >= PROMO_N:
        promo = "nbrq"[flags & 3]
    fr = chr(ord('a') + (from_sq & 7)) + str((from_sq >> 3) + 1)
    tr = chr(ord('a') + (to_sq & 7)) + str((to_sq >> 3) + 1)
    return fr + tr + promo


# ---------------------------------------------------------------------------
# Board state
# ---------------------------------------------------------------------------
@dataclass
class BoardState:
    """Complete chess position backed by NumPy uint64 bitboards."""

    pieces: list[int] = field(default_factory=lambda: [0] * 12)
    side_to_move: int = WHITE
    castling_rights: int = ALL_CASTLE
    ep_square: int = -1
    halfmove_clock: int = 0
    fullmove_number: int = 1
    zobrist_hash: int = 0

    # ---- helpers ----------------------------------------------------------

    def copy(self) -> BoardState:
        return BoardState(
            pieces=self.pieces[:],
            side_to_move=self.side_to_move,
            castling_rights=self.castling_rights,
            ep_square=self.ep_square,
            halfmove_clock=self.halfmove_clock,
            fullmove_number=self.fullmove_number,
            zobrist_hash=self.zobrist_hash,
        )

    def white_occ(self) -> int:
        return self.pieces[0] | self.pieces[1] | self.pieces[2] | \
               self.pieces[3] | self.pieces[4] | self.pieces[5]

    def black_occ(self) -> int:
        return self.pieces[6] | self.pieces[7] | self.pieces[8] | \
               self.pieces[9] | self.pieces[10] | self.pieces[11]

    def occupied(self) -> int:
        return self.white_occ() | self.black_occ()

    def friendly_occ(self) -> int:
        return self.white_occ() if self.side_to_move == WHITE else self.black_occ()

    def enemy_occ(self) -> int:
        return self.black_occ() if self.side_to_move == WHITE else self.white_occ()

    def piece_at(self, sq: int) -> int:
        """Return piece index (0-11) at *sq*, or -1 if empty."""
        mask = 1 << sq
        for i in range(12):
            if self.pieces[i] & mask:
                return i
        return -1

    def king_sq(self, color: int) -> int:
        bb = self.pieces[WHITE_KING if color == WHITE else BLACK_KING]
        return (bb & -bb).bit_length() - 1

    def to_numpy(self) -> np.ndarray:
        """Return pieces as a (12,) NumPy uint64 array."""
        return np.array(self.pieces, dtype=np.uint64)

    def recompute_hash(self) -> None:
        self.zobrist_hash = zobrist.compute_hash(
            self.pieces, self.side_to_move,
            self.castling_rights, self.ep_square,
        )

    # ---- pretty print -----------------------------------------------------

    def __str__(self) -> str:
        rows: list[str] = []
        for rank in range(7, -1, -1):
            row = f" {rank + 1}  "
            for file in range(8):
                sq = rank * 8 + file
                p = self.piece_at(sq)
                row += (PIECE_CHARS[p] if p >= 0 else ".") + " "
            rows.append(row)
        rows.append("    a b c d e f g h")
        return "\n".join(rows)


# ---------------------------------------------------------------------------
# FEN parsing / generation
# ---------------------------------------------------------------------------
STARTING_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"


def parse_fen(fen: str = STARTING_FEN) -> BoardState:
    parts = fen.split()
    state = BoardState()

    # Piece placement
    sq = 56  # start from a8
    for ch in parts[0]:
        if ch == '/':
            sq -= 16  # go down one rank
        elif ch.isdigit():
            sq += int(ch)
        else:
            idx = CHAR_TO_PIECE[ch]
            state.pieces[idx] |= 1 << sq
            sq += 1

    state.side_to_move = WHITE if parts[1] == 'w' else BLACK

    state.castling_rights = 0
    for ch in parts[2]:
        if ch == 'K': state.castling_rights |= WK_CASTLE
        elif ch == 'Q': state.castling_rights |= WQ_CASTLE
        elif ch == 'k': state.castling_rights |= BK_CASTLE
        elif ch == 'q': state.castling_rights |= BQ_CASTLE

    if parts[3] != '-':
        file = ord(parts[3][0]) - ord('a')
        rank = int(parts[3][1]) - 1
        state.ep_square = rank * 8 + file
    else:
        state.ep_square = -1

    state.halfmove_clock = int(parts[4]) if len(parts) > 4 else 0
    state.fullmove_number = int(parts[5]) if len(parts) > 5 else 1

    state.recompute_hash()
    return state


def to_fen(state: BoardState) -> str:
    parts: list[str] = []

    # Piece placement
    rows: list[str] = []
    for rank in range(7, -1, -1):
        empty = 0
        row = ""
        for file in range(8):
            sq = rank * 8 + file
            p = state.piece_at(sq)
            if p < 0:
                empty += 1
            else:
                if empty:
                    row += str(empty)
                    empty = 0
                row += PIECE_CHARS[p]
        if empty:
            row += str(empty)
        rows.append(row)
    parts.append("/".join(rows))

    parts.append("w" if state.side_to_move == WHITE else "b")

    castling = ""
    if state.castling_rights & WK_CASTLE: castling += "K"
    if state.castling_rights & WQ_CASTLE: castling += "Q"
    if state.castling_rights & BK_CASTLE: castling += "k"
    if state.castling_rights & BQ_CASTLE: castling += "q"
    parts.append(castling or "-")

    if state.ep_square >= 0:
        f = chr(ord('a') + (state.ep_square & 7))
        r = str((state.ep_square >> 3) + 1)
        parts.append(f + r)
    else:
        parts.append("-")

    parts.append(str(state.halfmove_clock))
    parts.append(str(state.fullmove_number))
    return " ".join(parts)


# ---------------------------------------------------------------------------
# Make move  (copy-make approach with incremental Zobrist update)
# ---------------------------------------------------------------------------

# Squares that must be updated when castling rights change
_CASTLING_MASK = [0] * 64
_CASTLING_MASK[0] = WQ_CASTLE   # a1 rook
_CASTLING_MASK[7] = WK_CASTLE   # h1 rook
_CASTLING_MASK[4] = WK_CASTLE | WQ_CASTLE  # e1 king
_CASTLING_MASK[56] = BQ_CASTLE  # a8 rook
_CASTLING_MASK[63] = BK_CASTLE  # h8 rook
_CASTLING_MASK[60] = BK_CASTLE | BQ_CASTLE  # e8 king


def make_move(state: BoardState, move: int) -> BoardState:
    """Apply *move* and return a new BoardState (copy-make)."""
    from_sq, to_sq, flags = decode_move(move)
    ns = state.copy()
    h = state.zobrist_hash
    piece = state.piece_at(from_sq)

    # Remove piece from origin
    ns.pieces[piece] &= ~(1 << from_sq)
    h = zobrist.update_piece(h, piece, from_sq)

    # Handle captures (including ep)
    captured = -1
    if flags == EP_CAPTURE:
        cap_sq = to_sq + (-8 if state.side_to_move == WHITE else 8)
        captured = BLACK_PAWN if state.side_to_move == WHITE else WHITE_PAWN
        ns.pieces[captured] &= ~(1 << cap_sq)
        h = zobrist.update_piece(h, captured, cap_sq)
    elif flags & CAPTURE:
        captured = state.piece_at(to_sq)
        if captured >= 0:
            ns.pieces[captured] &= ~(1 << to_sq)
            h = zobrist.update_piece(h, captured, to_sq)

    # Place piece at destination (handle promotions)
    if flags >= PROMO_N:
        base = WHITE_KNIGHT if state.side_to_move == WHITE else BLACK_KNIGHT
        promo_piece = base + (flags & 3)
        ns.pieces[promo_piece] |= 1 << to_sq
        h = zobrist.update_piece(h, promo_piece, to_sq)
    else:
        ns.pieces[piece] |= 1 << to_sq
        h = zobrist.update_piece(h, piece, to_sq)

    # Castling rook movement
    if flags == KING_CASTLE:
        if state.side_to_move == WHITE:
            rook, rf, rt = WHITE_ROOK, 7, 5
        else:
            rook, rf, rt = BLACK_ROOK, 63, 61
        ns.pieces[rook] &= ~(1 << rf)
        ns.pieces[rook] |= 1 << rt
        h = zobrist.update_piece(h, rook, rf)
        h = zobrist.update_piece(h, rook, rt)
    elif flags == QUEEN_CASTLE:
        if state.side_to_move == WHITE:
            rook, rf, rt = WHITE_ROOK, 0, 3
        else:
            rook, rf, rt = BLACK_ROOK, 56, 59
        ns.pieces[rook] &= ~(1 << rf)
        ns.pieces[rook] |= 1 << rt
        h = zobrist.update_piece(h, rook, rf)
        h = zobrist.update_piece(h, rook, rt)

    # Castling rights update
    old_cr = state.castling_rights
    new_cr = old_cr & ~(_CASTLING_MASK[from_sq] | _CASTLING_MASK[to_sq])
    if new_cr != old_cr:
        h = zobrist.update_castling(h, old_cr, new_cr)
    ns.castling_rights = new_cr

    # En-passant square update
    old_ep = state.ep_square
    if flags == DOUBLE_PAWN:
        ns.ep_square = (from_sq + to_sq) // 2
    else:
        ns.ep_square = -1
    h = zobrist.update_ep(h, old_ep, ns.ep_square)

    # Halfmove clock
    if piece in (WHITE_PAWN, BLACK_PAWN) or captured >= 0:
        ns.halfmove_clock = 0
    else:
        ns.halfmove_clock += 1

    # Fullmove number
    if state.side_to_move == BLACK:
        ns.fullmove_number += 1

    # Side to move
    ns.side_to_move ^= 1
    h = zobrist.update_side(h)
    ns.zobrist_hash = h

    return ns
