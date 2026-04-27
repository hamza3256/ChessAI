"""Pygame board and piece renderer.

Handles drawing the chess board, pieces, highlights for selected squares
and legal moves, and status text overlays.
"""

from __future__ import annotations

import os
from typing import Optional

import pygame

from engine.bitboard import BoardState, PIECE_CHARS, WHITE, decode_move

SQUARE_SIZE = 90
BOARD_SIZE = SQUARE_SIZE * 8
PANEL_HEIGHT = 60
WINDOW_WIDTH = BOARD_SIZE
WINDOW_HEIGHT = BOARD_SIZE + PANEL_HEIGHT

LIGHT_SQ = (240, 217, 181)
DARK_SQ = (181, 136, 99)
HIGHLIGHT_COLOR = (247, 247, 105, 160)
LEGAL_MOVE_COLOR = (130, 151, 105, 180)
LAST_MOVE_COLOR = (205, 210, 106, 120)
CHECK_COLOR = (235, 97, 80, 180)
BG_COLOR = (48, 46, 43)
TEXT_COLOR = (255, 255, 255)
SUBTLE_TEXT = (180, 180, 180)

PIECE_IMAGE_MAP = {
    'P': 'white_pawn', 'N': 'white_knight', 'B': 'white_bishop',
    'R': 'white_rook', 'Q': 'white_queen', 'K': 'white_king',
    'p': 'black_pawn', 'n': 'black_knight', 'b': 'black_bishop',
    'r': 'black_rook', 'q': 'black_queen', 'k': 'black_king',
}


class Renderer:

    def __init__(self, image_dir: str):
        self.image_dir = image_dir
        self.piece_images: dict[str, pygame.Surface] = {}
        self._load_images()
        self.font: Optional[pygame.font.Font] = None
        self.small_font: Optional[pygame.font.Font] = None

    def _load_images(self) -> None:
        for char, name in PIECE_IMAGE_MAP.items():
            path = os.path.join(self.image_dir, f"{name}.png")
            if os.path.exists(path):
                img = pygame.image.load(path).convert_alpha()
                self.piece_images[char] = pygame.transform.smoothscale(
                    img, (SQUARE_SIZE - 10, SQUARE_SIZE - 10)
                )

    def _ensure_fonts(self) -> None:
        if self.font is None:
            self.font = pygame.font.SysFont("Arial", 22, bold=True)
            self.small_font = pygame.font.SysFont("Arial", 16)

    def sq_to_pixel(self, sq: int, flip: bool = False) -> tuple[int, int]:
        file, rank = sq & 7, sq >> 3
        if flip:
            file = 7 - file
            rank = 7 - rank
        else:
            rank = 7 - rank
        return file * SQUARE_SIZE, rank * SQUARE_SIZE

    def pixel_to_sq(self, x: int, y: int, flip: bool = False) -> int:
        file = x // SQUARE_SIZE
        rank = 7 - (y // SQUARE_SIZE)
        if flip:
            file = 7 - file
            rank = 7 - rank
        if 0 <= file < 8 and 0 <= rank < 8:
            return rank * 8 + file
        return -1

    def draw_board(self, surface: pygame.Surface,
                   state: BoardState,
                   selected_sq: int = -1,
                   legal_targets: list[int] | None = None,
                   last_move: int = 0,
                   in_check_sq: int = -1,
                   flip: bool = False,
                   dragging_piece: Optional[str] = None,
                   drag_pos: Optional[tuple[int, int]] = None,
                   drag_from_sq: int = -1) -> None:
        """Render the full board to *surface*."""
        legal_targets = legal_targets or []

        # Draw squares
        for rank in range(8):
            for file in range(8):
                sq = rank * 8 + file
                px, py = self.sq_to_pixel(sq, flip)
                is_light = (rank + file) % 2 == 0
                color = LIGHT_SQ if is_light else DARK_SQ
                pygame.draw.rect(surface, color,
                                 (px, py, SQUARE_SIZE, SQUARE_SIZE))

        # Last move highlight
        if last_move:
            from_sq, to_sq, _ = decode_move(last_move)
            for sq in (from_sq, to_sq):
                px, py = self.sq_to_pixel(sq, flip)
                overlay = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE),
                                         pygame.SRCALPHA)
                overlay.fill(LAST_MOVE_COLOR)
                surface.blit(overlay, (px, py))

        # Check highlight
        if in_check_sq >= 0:
            px, py = self.sq_to_pixel(in_check_sq, flip)
            overlay = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE),
                                     pygame.SRCALPHA)
            overlay.fill(CHECK_COLOR)
            surface.blit(overlay, (px, py))

        # Selected square highlight
        if selected_sq >= 0:
            px, py = self.sq_to_pixel(selected_sq, flip)
            overlay = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE),
                                     pygame.SRCALPHA)
            overlay.fill(HIGHLIGHT_COLOR)
            surface.blit(overlay, (px, py))

        # Legal move indicators
        for sq in legal_targets:
            px, py = self.sq_to_pixel(sq, flip)
            center = (px + SQUARE_SIZE // 2, py + SQUARE_SIZE // 2)
            if state.piece_at(sq) >= 0:
                pygame.draw.circle(surface, LEGAL_MOVE_COLOR[:3],
                                   center, SQUARE_SIZE // 2, 4)
            else:
                circ_surface = pygame.Surface(
                    (SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
                pygame.draw.circle(circ_surface, LEGAL_MOVE_COLOR,
                                   (SQUARE_SIZE // 2, SQUARE_SIZE // 2), 14)
                surface.blit(circ_surface, (px, py))

        # Draw pieces
        for piece_idx in range(12):
            char = PIECE_CHARS[piece_idx]
            if char not in self.piece_images:
                continue
            bb = state.pieces[piece_idx]
            while bb:
                sq = (bb & -bb).bit_length() - 1
                bb &= bb - 1
                if sq == drag_from_sq:
                    continue
                px, py = self.sq_to_pixel(sq, flip)
                img = self.piece_images[char]
                surface.blit(img, (px + 5, py + 5))

        # Draw dragged piece
        if dragging_piece and drag_pos and dragging_piece in self.piece_images:
            img = self.piece_images[dragging_piece]
            surface.blit(img, (drag_pos[0] - img.get_width() // 2,
                               drag_pos[1] - img.get_height() // 2))

    def draw_panel(self, surface: pygame.Surface, state: BoardState,
                   status: str, search_info: str = "",
                   game_mode: str = "") -> None:
        """Draw the information panel below the board."""
        self._ensure_fonts()
        panel_rect = pygame.Rect(0, BOARD_SIZE, WINDOW_WIDTH, PANEL_HEIGHT)
        pygame.draw.rect(surface, BG_COLOR, panel_rect)

        turn = "White" if state.side_to_move == WHITE else "Black"
        turn_text = self.font.render(f"{turn}'s turn", True, TEXT_COLOR)
        surface.blit(turn_text, (10, BOARD_SIZE + 6))

        if status:
            status_text = self.font.render(status, True, (255, 200, 50))
            surface.blit(status_text, (10, BOARD_SIZE + 6))

        if game_mode:
            mode_text = self.small_font.render(game_mode, True, SUBTLE_TEXT)
            surface.blit(mode_text, (WINDOW_WIDTH - mode_text.get_width() - 10,
                                     BOARD_SIZE + 8))

        if search_info:
            info_text = self.small_font.render(search_info, True, SUBTLE_TEXT)
            surface.blit(info_text, (10, BOARD_SIZE + 34))

    def draw_menu(self, surface: pygame.Surface) -> list[tuple[pygame.Rect, str, str]]:
        """Draw mode-selection menu and return clickable button rects."""
        self._ensure_fonts()
        surface.fill(BG_COLOR)

        title_font = pygame.font.SysFont("Arial", 36, bold=True)
        title = title_font.render("ChessAI", True, TEXT_COLOR)
        surface.blit(title, (WINDOW_WIDTH // 2 - title.get_width() // 2, 60))

        subtitle = self.small_font.render(
            "High-Performance Python Game Engine", True, SUBTLE_TEXT)
        surface.blit(subtitle,
                     (WINDOW_WIDTH // 2 - subtitle.get_width() // 2, 110))

        buttons: list[tuple[pygame.Rect, str, str]] = []
        modes = [
            ("Player vs Player", "pvp"),
            ("CPU - Alpha-Beta", "alphabeta"),
            ("CPU - MCTS", "mcts"),
            ("CPU - Parallel Alpha-Beta", "parallel_ab"),
            ("CPU - Parallel MCTS", "parallel_mcts"),
        ]

        y_start = 180
        btn_w, btn_h = 360, 55
        spacing = 15

        for i, (label, mode_id) in enumerate(modes):
            x = WINDOW_WIDTH // 2 - btn_w // 2
            y = y_start + i * (btn_h + spacing)
            rect = pygame.Rect(x, y, btn_w, btn_h)

            mouse_pos = pygame.mouse.get_pos()
            hover = rect.collidepoint(mouse_pos)
            color = (90, 90, 90) if hover else (65, 65, 65)

            pygame.draw.rect(surface, color, rect, border_radius=8)
            pygame.draw.rect(surface, (120, 120, 120), rect, 1,
                             border_radius=8)

            text = self.font.render(label, True, TEXT_COLOR)
            surface.blit(text, (rect.centerx - text.get_width() // 2,
                                rect.centery - text.get_height() // 2))

            buttons.append((rect, label, mode_id))

        footer = self.small_font.render(
            "Python | NumPy | Pygame | Multiprocessing", True, SUBTLE_TEXT)
        surface.blit(footer,
                     (WINDOW_WIDTH // 2 - footer.get_width() // 2,
                      WINDOW_HEIGHT - 40))

        return buttons

    def draw_promotion_dialog(self, surface: pygame.Surface,
                              color: str) -> list[tuple[pygame.Rect, str]]:
        """Draw promotion piece selection and return clickable rects."""
        self._ensure_fonts()
        pieces = ['Q', 'R', 'B', 'N'] if color == 'w' else ['q', 'r', 'b', 'n']
        dialog_w = 4 * SQUARE_SIZE + 40
        dialog_h = SQUARE_SIZE + 30
        x_start = (WINDOW_WIDTH - dialog_w) // 2
        y_start = (BOARD_SIZE - dialog_h) // 2

        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        surface.blit(overlay, (0, 0))

        pygame.draw.rect(surface, BG_COLOR,
                         (x_start - 5, y_start - 5, dialog_w + 10, dialog_h + 10),
                         border_radius=10)

        buttons: list[tuple[pygame.Rect, str]] = []
        for i, pc in enumerate(pieces):
            rect = pygame.Rect(
                x_start + 10 + i * (SQUARE_SIZE + 5),
                y_start + 5,
                SQUARE_SIZE, SQUARE_SIZE
            )
            pygame.draw.rect(surface, (80, 80, 80), rect, border_radius=6)
            if pc in self.piece_images:
                img = self.piece_images[pc]
                surface.blit(img,
                             (rect.x + 5, rect.y + 5))
            buttons.append((rect, pc))

        return buttons
