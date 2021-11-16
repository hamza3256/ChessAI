import pygame

pygame.display.set_caption("ChessAI")
WIDTH, HEIGHT = 1000, 1000
BOARD_DISPLAY = pygame.display.set_mode((WIDTH, HEIGHT))
WHITE, BLACK, YELLOW, BLUE, GREY = (
    255, 255, 255), (0, 0, 0), (204, 204, 0), (50, 255, 255), (128, 128, 128)


def create_board():
    grid_size = WIDTH // 8
    pygame.font.init()
    my_font = pygame.font.SysFont('merida', 30)
    for i in range(8):
        for j in range(8):
            if i % 2 == 0:
                if j % 2 == 0:
                    grid = pygame.Rect(
                        i*grid_size, j*grid_size, grid_size, grid_size)
                    pygame.draw.rect(BOARD_DISPLAY, WHITE, grid)
                else:
                    grid = pygame.Rect(
                        i*grid_size, j*grid_size, grid_size, grid_size)
                    pygame.draw.rect(BOARD_DISPLAY, BLACK, grid)
            else:
                if j % 2 == 0:
                    grid = pygame.Rect(
                        i*grid_size, j*grid_size, grid_size, grid_size)
                    pygame.draw.rect(BOARD_DISPLAY, BLACK, grid)
                else:
                    grid = pygame.Rect(
                        i*grid_size, j*grid_size, grid_size, grid_size)
                    pygame.draw.rect(BOARD_DISPLAY, WHITE, grid)
            if j == 0:
                if i % 2 == 0:
                    notation = my_font.render(str(8-i), False, BLACK)
                    BOARD_DISPLAY.blit(
                        notation, (j*grid_size+5, i*grid_size+5))
                else:
                    notation = my_font.render(str(8-i), False, WHITE)
                    BOARD_DISPLAY.blit(
                        notation, (j*grid_size+5, i*grid_size+5))
            if i == 7:
                if j % 2 == 0:
                    notation = my_font.render(chr(97+j), False, WHITE)
                    BOARD_DISPLAY.blit(
                        notation, (j*grid_size+110, i*grid_size+105))
                else:
                    notation = my_font.render(chr(97+j), False, BLACK)
                    BOARD_DISPLAY.blit(
                        notation, (j*grid_size+110, i*grid_size+105))


def populate_board():
    pass


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
