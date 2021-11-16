import pygame
import sys

from main import boundary_validate

pygame.display.set_caption("ChessAI")
WIDTH, HEIGHT = 1000, 1000
BOARD = pygame.display.set_mode((WIDTH, HEIGHT))
WHITE, BLACK, YELLOW, BLUE, GREY = (
    255, 255, 255), (0, 0, 0), (204, 204, 0), (50, 255, 255), (128, 128, 128)


def create_board():
    grid_size = WIDTH // 8
    for i in range(8):
        for j in range(8):
            if i % 2 == 0:
                if j % 2 == 0:
                    grid = pygame.Rect(
                        i*grid_size, j*grid_size, grid_size, grid_size)
                    pygame.draw.rect(BOARD, WHITE, grid)
                else:
                    grid = pygame.Rect(
                        i*grid_size, j*grid_size, grid_size, grid_size)
                    pygame.draw.rect(BOARD, BLACK, grid)
            else:
                if j % 2 == 0:
                    grid = pygame.Rect(
                        i*grid_size, j*grid_size, grid_size, grid_size)
                    pygame.draw.rect(BOARD, BLACK, grid)
                else:
                    grid = pygame.Rect(
                        i*grid_size, j*grid_size, grid_size, grid_size)
                    pygame.draw.rect(BOARD, WHITE, grid)


def main():
    is_running = True
    while(is_running):
        create_board()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                is_running = False
                break
        pygame.display.update()
    pygame.quit()


if __name__ == "__main__":
    main()
