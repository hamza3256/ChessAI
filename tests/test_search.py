"""Tests for search algorithms (alpha-beta and MCTS)."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest
from engine.bitboard import parse_fen, make_move, decode_move, move_to_uci
from engine.transposition import TranspositionTable, EXACT, LOWER_BOUND, UPPER_BOUND
from search.alphabeta import AlphaBetaSearcher
from search.mcts import MCTSSearcher


class TestTranspositionTable:
    def test_store_and_probe_exact(self):
        tt = TranspositionTable(size=1024)
        tt.store(key=42, depth=5, score=100.0, flag=EXACT, best_move=123)
        score, best_move = tt.probe(key=42, depth=5, alpha=-1000, beta=1000)
        assert score == 100.0
        assert best_move == 123

    def test_probe_miss(self):
        tt = TranspositionTable(size=1024)
        score, best_move = tt.probe(key=99, depth=3, alpha=-1000, beta=1000)
        assert score is None
        assert best_move == 0

    def test_depth_insufficient(self):
        tt = TranspositionTable(size=1024)
        tt.store(key=42, depth=3, score=100.0, flag=EXACT, best_move=123)
        score, best_move = tt.probe(key=42, depth=5, alpha=-1000, beta=1000)
        assert score is None  # depth 3 < required depth 5
        assert best_move == 123  # best move still returned

    def test_lower_bound_cutoff(self):
        tt = TranspositionTable(size=1024)
        tt.store(key=42, depth=5, score=500.0, flag=LOWER_BOUND, best_move=123)
        score, _ = tt.probe(key=42, depth=5, alpha=-1000, beta=400)
        # score 500 >= beta 400, so should return
        assert score == 500.0

    def test_upper_bound_cutoff(self):
        tt = TranspositionTable(size=1024)
        tt.store(key=42, depth=5, score=-500.0, flag=UPPER_BOUND, best_move=123)
        score, _ = tt.probe(key=42, depth=5, alpha=-400, beta=1000)
        # score -500 <= alpha -400, so should return
        assert score == -500.0

    def test_clear(self):
        tt = TranspositionTable(size=1024)
        tt.store(key=42, depth=5, score=100.0, flag=EXACT, best_move=123)
        tt.clear()
        score, _ = tt.probe(key=42, depth=5, alpha=-1000, beta=1000)
        assert score is None

    def test_stats(self):
        tt = TranspositionTable(size=1024)
        tt.store(key=1, depth=1, score=0, flag=EXACT, best_move=0)
        tt.probe(key=1, depth=1, alpha=-1000, beta=1000)
        tt.probe(key=2, depth=1, alpha=-1000, beta=1000)
        stats = tt.stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1


class TestAlphaBeta:
    def test_finds_move_from_starting(self):
        state = parse_fen()
        searcher = AlphaBetaSearcher()
        move, score, info = searcher.search(state, max_depth=3, time_limit=10.0)
        assert move != 0
        assert info["depth"] >= 1
        assert info["nodes"] > 0

    def test_finds_mate_in_one(self):
        # White to move, Qh5# is mate
        fen = "rnbqkbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR b KQkq - 0 2"
        state = parse_fen(fen)
        # Actually let's use a proper mate-in-1 for black: Qh4-e1#
        # Simpler: scholar's mate setup where Qf7# is available
        fen2 = "r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5Q2/PPPP1PPP/RNB1K1NR w KQkq - 4 3"
        state2 = parse_fen(fen2)
        searcher = AlphaBetaSearcher()
        move, score, info = searcher.search(state2, max_depth=3, time_limit=10.0)
        uci = move_to_uci(move)
        # Qf3xf7# is the mate
        assert uci == "f3f7" or score > 50000

    def test_depth_increases_with_time(self):
        state = parse_fen()
        s1 = AlphaBetaSearcher()
        _, _, info1 = s1.search(state, max_depth=2, time_limit=30.0)
        s2 = AlphaBetaSearcher()
        _, _, info2 = s2.search(state, max_depth=4, time_limit=30.0)
        assert info2["nodes"] >= info1["nodes"]


class TestMCTS:
    def test_finds_move(self):
        state = parse_fen()
        searcher = MCTSSearcher()
        move, info = searcher.search(state, iterations=500, time_limit=5.0)
        assert move != 0
        assert info["iterations"] > 0

    def test_more_iterations_more_visits(self):
        state = parse_fen()
        s1 = MCTSSearcher()
        _, info1 = s1.search(state, iterations=100, time_limit=30.0)
        s2 = MCTSSearcher()
        _, info2 = s2.search(state, iterations=500, time_limit=30.0)
        assert info2["iterations"] >= info1["iterations"]
