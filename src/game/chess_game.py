"""Pygame chess game loop with non-blocking AI integration.

Handles input, game state, and delegates rendering to the Renderer.
AI computation runs via concurrent.futures so the UI never freezes.
"""

from __future__ import annotations

import sys
import os
from concurrent.futures import Future
from typing import Optional

import pygame

from engine.bitboard import (
    BoardState, parse_fen, make_move, decode_move, encode_move,
    move_to_uci, PIECE_CHARS, WHITE, BLACK, STARTING_FEN,
    PROMO_Q, PROMO_R, PROMO_B, PROMO_N,
    PROMO_CAPTURE_Q, PROMO_CAPTURE_R, PROMO_CAPTURE_B, PROMO_CAPTURE_N,
    CAPTURE,
)
from engine.move_gen import (
    generate_legal_moves, is_in_check, is_checkmate,
    is_stalemate, game_over,
)
from game.renderer import (
    Renderer, WINDOW_WIDTH, WINDOW_HEIGHT, BOARD_SIZE, SQUARE_SIZE,
)
from search.parallel import submit_search, shutdown_executor


class ChessGame:
    """Main game controller."""

    def __init__(self, image_dir: str):
        pygame.init()
        pygame.display.set_caption("ChessAI")
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.clock = pygame.time.Clock()
        self.renderer = Renderer(image_dir)

        self.state: BoardState = parse_fen(STARTING_FEN)
        self.game_mode: str = ""
        self.in_menu = True

        self.selected_sq: int = -1
        self.legal_targets: list[int] = []
        self.legal_moves_cache: list[int] = []
        self.last_move: int = 0

        self.dragging = False
        self.drag_piece: Optional[str] = None
        self.drag_from_sq: int = -1
        self.drag_pos: tuple[int, int] = (0, 0)

        self.ai_future: Optional[Future] = None
        self.ai_thinking = False
        self.status: str = ""
        self.search_info: str = ""

        self.promoting = False
        self.promo_from: int = -1
        self.promo_to: int = -1
        self.promo_is_capture: bool = False

        self.game_ended = False

    def run(self) -> None:
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif self.in_menu:
                    self._handle_menu_event(event)
                elif self.promoting:
                    self._handle_promotion_event(event)
                else:
                    self._handle_game_event(event)

            self._poll_ai()
            self._draw()
            self.clock.tick(60)

        shutdown_executor()
        pygame.quit()

    # ------------------------------------------------------------------ menu

    def _handle_menu_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            buttons = self.renderer.draw_menu(self.screen)
            for rect, label, mode_id in buttons:
                if rect.collidepoint(event.pos):
                    self.game_mode = mode_id
                    self.in_menu = False
                    self.state = parse_fen(STARTING_FEN)
                    self._refresh_legal()
                    return

    # ------------------------------------------------------------ game input

    def _handle_game_event(self, event: pygame.event.Event) -> None:
        if self.game_ended or self.ai_thinking:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                self._reset_game()
            return

        if self._is_ai_turn():
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._on_mouse_down(event.pos)
        elif event.type == pygame.MOUSEMOTION:
            if self.dragging:
                self.drag_pos = event.pos
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._on_mouse_up(event.pos)
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r:
                self._reset_game()

    def _on_mouse_down(self, pos: tuple[int, int]) -> None:
        if pos[1] >= BOARD_SIZE:
            return
        sq = self.renderer.pixel_to_sq(pos[0], pos[1])
        if sq < 0:
            return

        piece = self.state.piece_at(sq)
        is_own = piece >= 0 and ((piece < 6) == (self.state.side_to_move == WHITE))

        if self.selected_sq >= 0 and sq in self.legal_targets:
            self._try_move(self.selected_sq, sq)
            self.selected_sq = -1
            self.legal_targets = []
            return

        if is_own:
            self.selected_sq = sq
            self.legal_targets = self._targets_from(sq)
            self.dragging = True
            self.drag_from_sq = sq
            self.drag_piece = PIECE_CHARS[piece]
            self.drag_pos = pos
        else:
            self.selected_sq = -1
            self.legal_targets = []

    def _on_mouse_up(self, pos: tuple[int, int]) -> None:
        if not self.dragging:
            return
        self.dragging = False
        sq = self.renderer.pixel_to_sq(pos[0], pos[1])

        if sq >= 0 and sq in self.legal_targets:
            self._try_move(self.drag_from_sq, sq)
            self.selected_sq = -1
            self.legal_targets = []
        self.drag_piece = None
        self.drag_from_sq = -1

    def _targets_from(self, sq: int) -> list[int]:
        targets = []
        for m in self.legal_moves_cache:
            from_sq, to_sq, _ = decode_move(m)
            if from_sq == sq:
                targets.append(to_sq)
        return targets

    # --------------------------------------------------------------- moves

    def _try_move(self, from_sq: int, to_sq: int) -> None:
        candidates = [
            m for m in self.legal_moves_cache
            if decode_move(m)[0] == from_sq and decode_move(m)[1] == to_sq
        ]
        if not candidates:
            return

        promos = [m for m in candidates if decode_move(m)[2] >= PROMO_N]
        if promos:
            self.promoting = True
            self.promo_from = from_sq
            self.promo_to = to_sq
            is_cap = self.state.piece_at(to_sq) >= 0
            self.promo_is_capture = is_cap
            return

        self._apply_move(candidates[0])

    def _apply_move(self, move: int) -> None:
        self.state = make_move(self.state, move)
        self.last_move = move
        self.status = ""
        self.search_info = ""
        self._refresh_legal()
        self._check_game_over()

        if not self.game_ended and self._is_ai_turn():
            self._start_ai()

    def _refresh_legal(self) -> None:
        self.legal_moves_cache = generate_legal_moves(self.state)

    def _check_game_over(self) -> None:
        over, reason = game_over(self.state)
        if over:
            self.status = reason
            self.game_ended = True
        elif is_in_check(self.state, self.state.side_to_move):
            self.status = "Check!"

    # ----------------------------------------------------------- promotion

    def _handle_promotion_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            color = 'w' if self.state.side_to_move == WHITE else 'b'
            buttons = self.renderer.draw_promotion_dialog(self.screen, color)
            for rect, pc in buttons:
                if rect.collidepoint(event.pos):
                    promo_map = {
                        'Q': PROMO_Q, 'R': PROMO_R, 'B': PROMO_B, 'N': PROMO_N,
                        'q': PROMO_Q, 'r': PROMO_R, 'b': PROMO_B, 'n': PROMO_N,
                    }
                    flag = promo_map[pc]
                    if self.promo_is_capture:
                        flag += 4  # capture flag offset
                    move = encode_move(self.promo_from, self.promo_to, flag)
                    self.promoting = False
                    self._apply_move(move)
                    return

    # ------------------------------------------------------------------ AI

    def _is_ai_turn(self) -> bool:
        if self.game_mode == "pvp":
            return False
        return self.state.side_to_move == BLACK

    def _start_ai(self) -> None:
        self.ai_thinking = True
        self.status = "AI thinking..."

        depth = 5
        time_limit = 5.0
        iterations = 5000

        mode = self.game_mode
        if mode in ("alphabeta", "parallel_ab"):
            self.ai_future = submit_search(
                self.state, mode=mode, depth=depth, time_limit=time_limit
            )
        else:
            self.ai_future = submit_search(
                self.state, mode=mode, iterations=iterations,
                time_limit=time_limit
            )

    def _poll_ai(self) -> None:
        if self.ai_future is None or not self.ai_future.done():
            return
        try:
            move, score, info = self.ai_future.result()
            if move:
                uci = move_to_uci(move)
                depth_info = info.get("depth", "")
                nodes = info.get("nodes", info.get("iterations",
                                 info.get("total_iterations", "")))
                elapsed = info.get("time", 0)
                self.search_info = (
                    f"Move: {uci}  "
                    f"{'Depth: ' + str(depth_info) + '  ' if depth_info else ''}"
                    f"{'Nodes: ' + str(nodes) + '  ' if nodes else ''}"
                    f"Time: {elapsed:.1f}s"
                )
                self._apply_move(move)
        except Exception as e:
            self.status = f"AI error: {e}"
        finally:
            self.ai_future = None
            self.ai_thinking = False

    # ---------------------------------------------------------------- draw

    def _draw(self) -> None:
        self.screen.fill((0, 0, 0))

        if self.in_menu:
            self.renderer.draw_menu(self.screen)
        else:
            check_sq = -1
            if not self.game_ended and is_in_check(
                    self.state, self.state.side_to_move):
                check_sq = self.state.king_sq(self.state.side_to_move)

            self.renderer.draw_board(
                self.screen, self.state,
                selected_sq=self.selected_sq,
                legal_targets=self.legal_targets,
                last_move=self.last_move,
                in_check_sq=check_sq,
                dragging_piece=self.drag_piece if self.dragging else None,
                drag_pos=self.drag_pos if self.dragging else None,
                drag_from_sq=self.drag_from_sq if self.dragging else -1,
            )

            mode_labels = {
                "pvp": "Player vs Player",
                "alphabeta": "Alpha-Beta + Iterative Deepening",
                "mcts": "MCTS + UCT",
                "parallel_ab": "Parallel Alpha-Beta",
                "parallel_mcts": "Parallel MCTS",
            }

            self.renderer.draw_panel(
                self.screen, self.state,
                status=self.status,
                search_info=self.search_info,
                game_mode=mode_labels.get(self.game_mode, ""),
            )

            if self.promoting:
                color = 'w' if self.state.side_to_move == WHITE else 'b'
                self.renderer.draw_promotion_dialog(self.screen, color)

        pygame.display.flip()

    # --------------------------------------------------------------- reset

    def _reset_game(self) -> None:
        self.state = parse_fen(STARTING_FEN)
        self.selected_sq = -1
        self.legal_targets = []
        self.last_move = 0
        self.status = ""
        self.search_info = ""
        self.game_ended = False
        self.ai_thinking = False
        self.ai_future = None
        self.promoting = False
        self._refresh_legal()
