"""Legal move generation using bitboard attack tables.

Precomputes knight, king, and pawn attack tables at import time.
Sliding piece attacks use a loop-based ray approach for clarity.
Generates pseudo-legal moves then filters to legal by checking
whether the own king is left in check.
"""

from __future__ import annotations
from .bitboard import (
    BoardState, encode_move, decode_move,
    WHITE, BLACK,
    WHITE_PAWN, WHITE_KNIGHT, WHITE_BISHOP, WHITE_ROOK, WHITE_QUEEN, WHITE_KING,
    BLACK_PAWN, BLACK_KNIGHT, BLACK_BISHOP, BLACK_ROOK, BLACK_QUEEN, BLACK_KING,
    QUIET, DOUBLE_PAWN, KING_CASTLE, QUEEN_CASTLE, CAPTURE, EP_CAPTURE,
    PROMO_N, PROMO_B, PROMO_R, PROMO_Q,
    PROMO_CAPTURE_N, PROMO_CAPTURE_B, PROMO_CAPTURE_R, PROMO_CAPTURE_Q,
    WK_CASTLE, WQ_CASTLE, BK_CASTLE, BQ_CASTLE,
    make_move,
)

# ---------------------------------------------------------------------------
# Pre-computed attack tables
# ---------------------------------------------------------------------------

KNIGHT_ATTACKS = [0] * 64
KING_ATTACKS = [0] * 64
WHITE_PAWN_ATTACKS_TABLE = [0] * 64
BLACK_PAWN_ATTACKS_TABLE = [0] * 64

_KNIGHT_OFFSETS = [(-2, -1), (-2, 1), (-1, -2), (-1, 2),
                   (1, -2), (1, 2), (2, -1), (2, 1)]
_KING_OFFSETS = [(-1, -1), (-1, 0), (-1, 1), (0, -1),
                 (0, 1), (1, -1), (1, 0), (1, 1)]

for _sq in range(64):
    _rank, _file = _sq >> 3, _sq & 7
    for _dr, _df in _KNIGHT_OFFSETS:
        _r, _f = _rank + _dr, _file + _df
        if 0 <= _r < 8 and 0 <= _f < 8:
            KNIGHT_ATTACKS[_sq] |= 1 << (_r * 8 + _f)
    for _dr, _df in _KING_OFFSETS:
        _r, _f = _rank + _dr, _file + _df
        if 0 <= _r < 8 and 0 <= _f < 8:
            KING_ATTACKS[_sq] |= 1 << (_r * 8 + _f)
    if _rank < 7:
        if _file > 0:
            WHITE_PAWN_ATTACKS_TABLE[_sq] |= 1 << (_sq + 7)
        if _file < 7:
            WHITE_PAWN_ATTACKS_TABLE[_sq] |= 1 << (_sq + 9)
    if _rank > 0:
        if _file > 0:
            BLACK_PAWN_ATTACKS_TABLE[_sq] |= 1 << (_sq - 9)
        if _file < 7:
            BLACK_PAWN_ATTACKS_TABLE[_sq] |= 1 << (_sq - 7)

ROOK_DELTAS = [8, -8, 1, -1]
BISHOP_DELTAS = [9, 7, -9, -7]

# ---------------------------------------------------------------------------
# Sliding attack generation
# ---------------------------------------------------------------------------

def sliding_attacks(sq: int, occupied: int, deltas: list[int]) -> int:
    attacks = 0
    for delta in deltas:
        s = sq
        while True:
            prev_file = s & 7
            s += delta
            if s < 0 or s >= 64:
                break
            curr_file = s & 7
            if abs(curr_file - prev_file) > 1:
                break
            attacks |= 1 << s
            if (1 << s) & occupied:
                break
    return attacks


def rook_attacks(sq: int, occupied: int) -> int:
    return sliding_attacks(sq, occupied, ROOK_DELTAS)


def bishop_attacks(sq: int, occupied: int) -> int:
    return sliding_attacks(sq, occupied, BISHOP_DELTAS)


def queen_attacks(sq: int, occupied: int) -> int:
    return sliding_attacks(sq, occupied, ROOK_DELTAS + BISHOP_DELTAS)


# ---------------------------------------------------------------------------
# Square-attack query (used for check detection and castling)
# ---------------------------------------------------------------------------

def is_square_attacked(state: BoardState, sq: int, by_color: int) -> bool:
    """Return True if *sq* is attacked by any piece of *by_color*."""
    occ = state.occupied()

    if by_color == WHITE:
        if KNIGHT_ATTACKS[sq] & state.pieces[WHITE_KNIGHT]:
            return True
        if KING_ATTACKS[sq] & state.pieces[WHITE_KING]:
            return True
        if BLACK_PAWN_ATTACKS_TABLE[sq] & state.pieces[WHITE_PAWN]:
            return True
        rq = state.pieces[WHITE_ROOK] | state.pieces[WHITE_QUEEN]
        if rq and rook_attacks(sq, occ) & rq:
            return True
        bq = state.pieces[WHITE_BISHOP] | state.pieces[WHITE_QUEEN]
        if bq and bishop_attacks(sq, occ) & bq:
            return True
    else:
        if KNIGHT_ATTACKS[sq] & state.pieces[BLACK_KNIGHT]:
            return True
        if KING_ATTACKS[sq] & state.pieces[BLACK_KING]:
            return True
        if WHITE_PAWN_ATTACKS_TABLE[sq] & state.pieces[BLACK_PAWN]:
            return True
        rq = state.pieces[BLACK_ROOK] | state.pieces[BLACK_QUEEN]
        if rq and rook_attacks(sq, occ) & rq:
            return True
        bq = state.pieces[BLACK_BISHOP] | state.pieces[BLACK_QUEEN]
        if bq and bishop_attacks(sq, occ) & bq:
            return True

    return False


def is_in_check(state: BoardState, color: int) -> bool:
    ksq = state.king_sq(color)
    return is_square_attacked(state, ksq, color ^ 1)


# ---------------------------------------------------------------------------
# Bit scanning helpers
# ---------------------------------------------------------------------------

def iter_bits(bb: int):
    """Yield squares (bit indices) that are set."""
    while bb:
        sq = (bb & -bb).bit_length() - 1
        yield sq
        bb &= bb - 1


# ---------------------------------------------------------------------------
# Pseudo-legal move generation
# ---------------------------------------------------------------------------

def _gen_pawn_moves(state: BoardState, moves: list[int]) -> None:
    stm = state.side_to_move
    occ = state.occupied()
    enemy = state.enemy_occ()

    if stm == WHITE:
        pawns = state.pieces[WHITE_PAWN]
        promo_rank_mask = 0xFF00000000000000  # rank 8
        start_rank_mask = 0x000000000000FF00  # rank 2
        direction = 8
    else:
        pawns = state.pieces[BLACK_PAWN]
        promo_rank_mask = 0x00000000000000FF  # rank 1
        start_rank_mask = 0x00FF000000000000  # rank 7
        direction = -8

    for sq in iter_bits(pawns):
        # Single push
        to = sq + direction
        if 0 <= to < 64 and not (occ & (1 << to)):
            if (1 << to) & promo_rank_mask:
                for pf in (PROMO_N, PROMO_B, PROMO_R, PROMO_Q):
                    moves.append(encode_move(sq, to, pf))
            else:
                moves.append(encode_move(sq, to, QUIET))
                # Double push
                if (1 << sq) & start_rank_mask:
                    to2 = to + direction
                    if not (occ & (1 << to2)):
                        moves.append(encode_move(sq, to2, DOUBLE_PAWN))

        # Captures
        if stm == WHITE:
            att = WHITE_PAWN_ATTACKS_TABLE[sq]
        else:
            att = BLACK_PAWN_ATTACKS_TABLE[sq]

        for to in iter_bits(att & enemy):
            if (1 << to) & promo_rank_mask:
                for pf in (PROMO_CAPTURE_N, PROMO_CAPTURE_B,
                           PROMO_CAPTURE_R, PROMO_CAPTURE_Q):
                    moves.append(encode_move(sq, to, pf))
            else:
                moves.append(encode_move(sq, to, CAPTURE))

        # En passant
        if state.ep_square >= 0 and att & (1 << state.ep_square):
            moves.append(encode_move(sq, state.ep_square, EP_CAPTURE))


def _gen_knight_moves(state: BoardState, moves: list[int]) -> None:
    stm = state.side_to_move
    knights = state.pieces[WHITE_KNIGHT if stm == WHITE else BLACK_KNIGHT]
    friendly = state.friendly_occ()
    enemy = state.enemy_occ()

    for sq in iter_bits(knights):
        targets = KNIGHT_ATTACKS[sq] & ~friendly
        for to in iter_bits(targets & enemy):
            moves.append(encode_move(sq, to, CAPTURE))
        for to in iter_bits(targets & ~enemy):
            moves.append(encode_move(sq, to, QUIET))


def _gen_sliding_moves(state: BoardState, moves: list[int],
                       piece_idx: int, attack_fn) -> None:
    bb = state.pieces[piece_idx]
    friendly = state.friendly_occ()
    enemy = state.enemy_occ()
    occ = state.occupied()

    for sq in iter_bits(bb):
        targets = attack_fn(sq, occ) & ~friendly
        for to in iter_bits(targets & enemy):
            moves.append(encode_move(sq, to, CAPTURE))
        for to in iter_bits(targets & ~enemy):
            moves.append(encode_move(sq, to, QUIET))


def _gen_king_moves(state: BoardState, moves: list[int]) -> None:
    stm = state.side_to_move
    king = state.pieces[WHITE_KING if stm == WHITE else BLACK_KING]
    friendly = state.friendly_occ()
    enemy = state.enemy_occ()

    ksq = (king & -king).bit_length() - 1
    targets = KING_ATTACKS[ksq] & ~friendly
    for to in iter_bits(targets & enemy):
        moves.append(encode_move(ksq, to, CAPTURE))
    for to in iter_bits(targets & ~enemy):
        moves.append(encode_move(ksq, to, QUIET))

    # Castling
    occ = state.occupied()
    opp = stm ^ 1
    if stm == WHITE:
        if state.castling_rights & WK_CASTLE:
            if not (occ & ((1 << 5) | (1 << 6))):
                if (not is_square_attacked(state, 4, opp) and
                        not is_square_attacked(state, 5, opp) and
                        not is_square_attacked(state, 6, opp)):
                    moves.append(encode_move(4, 6, KING_CASTLE))
        if state.castling_rights & WQ_CASTLE:
            if not (occ & ((1 << 1) | (1 << 2) | (1 << 3))):
                if (not is_square_attacked(state, 4, opp) and
                        not is_square_attacked(state, 3, opp) and
                        not is_square_attacked(state, 2, opp)):
                    moves.append(encode_move(4, 2, QUEEN_CASTLE))
    else:
        if state.castling_rights & BK_CASTLE:
            if not (occ & ((1 << 61) | (1 << 62))):
                if (not is_square_attacked(state, 60, opp) and
                        not is_square_attacked(state, 61, opp) and
                        not is_square_attacked(state, 62, opp)):
                    moves.append(encode_move(60, 62, KING_CASTLE))
        if state.castling_rights & BQ_CASTLE:
            if not (occ & ((1 << 57) | (1 << 58) | (1 << 59))):
                if (not is_square_attacked(state, 60, opp) and
                        not is_square_attacked(state, 59, opp) and
                        not is_square_attacked(state, 58, opp)):
                    moves.append(encode_move(60, 58, QUEEN_CASTLE))


def generate_pseudo_legal(state: BoardState) -> list[int]:
    moves: list[int] = []
    stm = state.side_to_move

    _gen_pawn_moves(state, moves)
    _gen_knight_moves(state, moves)

    if stm == WHITE:
        _gen_sliding_moves(state, moves, WHITE_BISHOP, bishop_attacks)
        _gen_sliding_moves(state, moves, WHITE_ROOK, rook_attacks)
        _gen_sliding_moves(state, moves, WHITE_QUEEN, queen_attacks)
    else:
        _gen_sliding_moves(state, moves, BLACK_BISHOP, bishop_attacks)
        _gen_sliding_moves(state, moves, BLACK_ROOK, rook_attacks)
        _gen_sliding_moves(state, moves, BLACK_QUEEN, queen_attacks)

    _gen_king_moves(state, moves)
    return moves


def generate_legal_moves(state: BoardState) -> list[int]:
    """Generate all legal moves for the current side to move."""
    pseudo = generate_pseudo_legal(state)
    legal: list[int] = []
    stm = state.side_to_move
    for m in pseudo:
        ns = make_move(state, m)
        if not is_in_check(ns, stm):
            legal.append(m)
    return legal


# ---------------------------------------------------------------------------
# Game-state queries
# ---------------------------------------------------------------------------

def is_checkmate(state: BoardState) -> bool:
    return is_in_check(state, state.side_to_move) and len(generate_legal_moves(state)) == 0


def is_stalemate(state: BoardState) -> bool:
    return not is_in_check(state, state.side_to_move) and len(generate_legal_moves(state)) == 0


def is_draw(state: BoardState) -> bool:
    if state.halfmove_clock >= 100:
        return True
    if is_stalemate(state):
        return True
    return False


def game_over(state: BoardState) -> tuple[bool, str]:
    """Return (is_over, reason_string)."""
    if is_checkmate(state):
        winner = "Black" if state.side_to_move == WHITE else "White"
        return True, f"Checkmate - {winner} wins"
    if is_stalemate(state):
        return True, "Stalemate - Draw"
    if state.halfmove_clock >= 100:
        return True, "50-move rule - Draw"
    return False, ""
