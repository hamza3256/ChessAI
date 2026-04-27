"""Tests for bitboard representation, FEN parsing, and make_move."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest
from engine.bitboard import (
    BoardState, parse_fen, to_fen, make_move, encode_move, decode_move,
    move_to_uci, STARTING_FEN, WHITE, BLACK,
    WHITE_PAWN, WHITE_KNIGHT, WHITE_BISHOP, WHITE_ROOK, WHITE_QUEEN, WHITE_KING,
    BLACK_PAWN, BLACK_KNIGHT, BLACK_KING,
    QUIET, DOUBLE_PAWN, KING_CASTLE, QUEEN_CASTLE, CAPTURE,
    WK_CASTLE, WQ_CASTLE, BK_CASTLE, BQ_CASTLE,
)


class TestFEN:
    def test_starting_position_roundtrip(self):
        state = parse_fen(STARTING_FEN)
        assert to_fen(state) == STARTING_FEN

    def test_starting_position_pieces(self):
        state = parse_fen()
        assert state.side_to_move == WHITE
        assert state.castling_rights == (WK_CASTLE | WQ_CASTLE | BK_CASTLE | BQ_CASTLE)
        assert state.ep_square == -1
        assert state.piece_at(0) == WHITE_ROOK  # a1
        assert state.piece_at(4) == WHITE_KING  # e1
        assert state.piece_at(60) == BLACK_KING  # e8
        assert state.piece_at(8) == WHITE_PAWN  # a2
        assert state.piece_at(48) == BLACK_PAWN  # a7

    def test_custom_fen(self):
        fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
        state = parse_fen(fen)
        assert state.side_to_move == BLACK
        assert state.ep_square == 20  # e3
        assert state.piece_at(28) == WHITE_PAWN  # e4
        assert to_fen(state) == fen

    def test_empty_squares(self):
        state = parse_fen()
        for sq in range(16, 48):
            assert state.piece_at(sq) == -1


class TestMoveEncoding:
    def test_encode_decode_quiet(self):
        m = encode_move(12, 28, QUIET)
        f, t, flags = decode_move(m)
        assert f == 12
        assert t == 28
        assert flags == QUIET

    def test_encode_decode_capture(self):
        m = encode_move(27, 36, CAPTURE)
        f, t, flags = decode_move(m)
        assert f == 27
        assert t == 36
        assert flags == CAPTURE

    def test_uci_notation(self):
        m = encode_move(12, 28, QUIET)  # e2-e4
        assert move_to_uci(m) == "e2e4"

    def test_uci_promotion(self):
        from engine.bitboard import PROMO_Q
        m = encode_move(52, 60, PROMO_Q)  # e7-e8q
        assert move_to_uci(m) == "e7e8q"


class TestMakeMove:
    def test_pawn_push(self):
        state = parse_fen()
        m = encode_move(12, 20, QUIET)  # e2-e3
        ns = make_move(state, m)
        assert ns.piece_at(12) == -1
        assert ns.piece_at(20) == WHITE_PAWN
        assert ns.side_to_move == BLACK

    def test_double_pawn_push_sets_ep(self):
        state = parse_fen()
        m = encode_move(12, 28, DOUBLE_PAWN)  # e2-e4
        ns = make_move(state, m)
        assert ns.ep_square == 20  # e3
        assert ns.piece_at(28) == WHITE_PAWN

    def test_capture_removes_enemy(self):
        fen = "rnbqkbnr/ppp1pppp/8/3p4/4P3/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 2"
        state = parse_fen(fen)
        m = encode_move(28, 35, CAPTURE)  # e4xd5
        ns = make_move(state, m)
        assert ns.piece_at(35) == WHITE_PAWN
        assert ns.piece_at(28) == -1

    def test_castling_kingside(self):
        fen = "r3k2r/pppppppp/8/8/8/8/PPPPPPPP/R3K2R w KQkq - 0 1"
        state = parse_fen(fen)
        m = encode_move(4, 6, KING_CASTLE)
        ns = make_move(state, m)
        assert ns.piece_at(6) == WHITE_KING
        assert ns.piece_at(5) == WHITE_ROOK
        assert ns.piece_at(4) == -1
        assert ns.piece_at(7) == -1
        assert not (ns.castling_rights & WK_CASTLE)
        assert not (ns.castling_rights & WQ_CASTLE)

    def test_castling_queenside(self):
        fen = "r3k2r/pppppppp/8/8/8/8/PPPPPPPP/R3K2R w KQkq - 0 1"
        state = parse_fen(fen)
        m = encode_move(4, 2, QUEEN_CASTLE)
        ns = make_move(state, m)
        assert ns.piece_at(2) == WHITE_KING
        assert ns.piece_at(3) == WHITE_ROOK
        assert ns.piece_at(0) == -1
        assert ns.piece_at(4) == -1

    def test_zobrist_changes(self):
        state = parse_fen()
        m = encode_move(12, 28, DOUBLE_PAWN)
        ns = make_move(state, m)
        assert ns.zobrist_hash != state.zobrist_hash

    def test_zobrist_consistent(self):
        state = parse_fen()
        m = encode_move(12, 28, DOUBLE_PAWN)
        ns = make_move(state, m)
        ns.recompute_hash()
        assert ns.zobrist_hash == ns.zobrist_hash


class TestBoardState:
    def test_king_sq(self):
        state = parse_fen()
        assert state.king_sq(WHITE) == 4  # e1
        assert state.king_sq(BLACK) == 60  # e8

    def test_occupied(self):
        state = parse_fen()
        occ = state.occupied()
        assert bin(occ).count('1') == 32

    def test_copy_independence(self):
        state = parse_fen()
        copy = state.copy()
        copy.pieces[0] = 0
        assert state.pieces[0] != 0
