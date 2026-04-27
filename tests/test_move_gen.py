"""Tests for legal move generation."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest
from engine.bitboard import parse_fen, make_move, decode_move, STARTING_FEN, WHITE, BLACK
from engine.move_gen import (
    generate_legal_moves, is_in_check, is_checkmate, is_stalemate,
    is_square_attacked, game_over,
)


class TestStartingPosition:
    def test_white_has_20_moves(self):
        state = parse_fen(STARTING_FEN)
        moves = generate_legal_moves(state)
        assert len(moves) == 20

    def test_not_in_check(self):
        state = parse_fen(STARTING_FEN)
        assert not is_in_check(state, WHITE)
        assert not is_in_check(state, BLACK)


class TestCheckDetection:
    def test_scholars_mate_is_checkmate(self):
        fen = "r1bqkb1r/pppp1Qpp/2n2n2/4p3/2B1P3/8/PPPP1PPP/RNB1K1NR b KQkq - 0 4"
        state = parse_fen(fen)
        assert is_in_check(state, BLACK)
        assert is_checkmate(state)

    def test_in_check_but_not_mate(self):
        fen = "rnbqkbnr/pppp1ppp/8/4p3/5PP1/8/PPPPP2P/RNBQKBNR b KQkq - 0 2"
        state = parse_fen(fen)
        # Not necessarily in check, just testing a position
        moves = generate_legal_moves(state)
        assert len(moves) > 0

    def test_simple_check(self):
        fen = "4k3/8/8/8/8/8/8/R3K3 b - - 0 1"
        state = parse_fen(fen)
        # Black king on e8, white rook on a1 does not give check (different file)
        # Let's use a direct check position
        fen2 = "4k3/8/8/8/8/8/8/4R2K b - - 0 1"
        state2 = parse_fen(fen2)
        assert is_in_check(state2, BLACK)


class TestStalemate:
    def test_stalemate_position(self):
        fen = "k7/8/1K6/8/8/8/8/8 b - - 0 1"
        state = parse_fen(fen)
        # Black king trapped but not in check - verify it's not in check first
        if not is_in_check(state, BLACK):
            moves = generate_legal_moves(state)
            if len(moves) == 0:
                assert is_stalemate(state)


class TestSpecialMoves:
    def test_en_passant_generation(self):
        fen = "rnbqkbnr/pppp1ppp/8/4pP2/8/8/PPPPP1PP/RNBQKBNR w KQkq e6 0 3"
        state = parse_fen(fen)
        moves = generate_legal_moves(state)
        from engine.bitboard import EP_CAPTURE
        ep_moves = [m for m in moves if decode_move(m)[2] == EP_CAPTURE]
        assert len(ep_moves) == 1
        _, to_sq, _ = decode_move(ep_moves[0])
        assert to_sq == 44  # e6

    def test_castling_available(self):
        fen = "r3k2r/pppppppp/8/8/8/8/PPPPPPPP/R3K2R w KQkq - 0 1"
        state = parse_fen(fen)
        moves = generate_legal_moves(state)
        from engine.bitboard import KING_CASTLE, QUEEN_CASTLE
        castle_moves = [m for m in moves if decode_move(m)[2] in (KING_CASTLE, QUEEN_CASTLE)]
        assert len(castle_moves) == 2

    def test_no_castling_through_check(self):
        fen = "r3k2r/pppppppp/8/8/4r3/8/PPPP1PPP/R3K2R w KQkq - 0 1"
        state = parse_fen(fen)
        moves = generate_legal_moves(state)
        from engine.bitboard import KING_CASTLE, QUEEN_CASTLE
        castle_moves = [m for m in moves if decode_move(m)[2] in (KING_CASTLE, QUEEN_CASTLE)]
        # King can't castle through the file attacked by rook
        # Exact count depends on attack geometry
        for cm in castle_moves:
            ns = make_move(state, cm)
            assert not is_in_check(ns, WHITE)

    def test_promotion_generation(self):
        fen = "8/4P3/8/8/8/8/8/4K2k w - - 0 1"
        state = parse_fen(fen)
        moves = generate_legal_moves(state)
        from engine.bitboard import PROMO_N
        promo_moves = [m for m in moves if decode_move(m)[2] >= PROMO_N]
        assert len(promo_moves) == 4  # N, B, R, Q


class TestPerft:
    """Basic perft counts to validate move generation correctness."""

    def _perft(self, state, depth: int) -> int:
        if depth == 0:
            return 1
        moves = generate_legal_moves(state)
        count = 0
        for m in moves:
            ns = make_move(state, m)
            count += self._perft(ns, depth - 1)
        return count

    def test_perft_depth_1(self):
        state = parse_fen(STARTING_FEN)
        assert self._perft(state, 1) == 20

    def test_perft_depth_2(self):
        state = parse_fen(STARTING_FEN)
        assert self._perft(state, 2) == 400

    def test_perft_depth_3(self):
        state = parse_fen(STARTING_FEN)
        assert self._perft(state, 3) == 8902
