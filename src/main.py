#!/usr/bin/env python3
"""ChessAI - High-Performance Python Game Engine.

Entry point: launches the Pygame-based chess game with mode selection.
"""

import os
import sys

def main():
    src_dir = os.path.dirname(os.path.abspath(__file__))
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)

    image_dir = os.path.join(src_dir, "images")

    from game.chess_game import ChessGame
    game = ChessGame(image_dir=image_dir)
    game.run()


if __name__ == "__main__":
    main()
