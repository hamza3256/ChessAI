import pygame

pygame.display.set_caption("ChessAI")
WIDTH, HEIGHT = 1000, 1000
BOARD_DISPLAY = pygame.display.set_mode((WIDTH, HEIGHT))
WHITE, BLACK, YELLOW, BLUE, GREY, LIGHT_GREY = (
    255, 255, 255), (0, 0, 0), (204, 204, 0), (50, 255, 255), (128, 128, 128), (64, 64, 64)

ASSETS_FOLDER = './assets1/'

board = [[None for _ in range(8)] for _ in range(8)]


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


class Piece:
    def __init__(self, colour, type, image, killable=False):
        self.colour = colour
        self.type = type
        self.image = image
        self.killable = killable


#  K = king, Q = queen, R = rook, B = bishop, P = pawn, N = knight
b_king = Piece('black', 'K', ASSETS_FOLDER + 'b_king.png')
w_king = Piece('white', 'K', ASSETS_FOLDER + 'w_king.png')
b_queen = Piece('black', 'Q', ASSETS_FOLDER + 'b_queen.png')
w_queen = Piece('white', 'Q', ASSETS_FOLDER + 'w_queen.png')
b_rook = Piece('black', 'R', ASSETS_FOLDER + 'b_rook.png')
w_rook = Piece('white', 'R', ASSETS_FOLDER + 'w_rook.png')
b_bishop = Piece('black', 'B', ASSETS_FOLDER + 'b_bishop.png')
w_bishop = Piece('white', 'B', ASSETS_FOLDER + 'w_bishop.png')
b_pawn = Piece('black', 'P', ASSETS_FOLDER + 'b_pawn.png')
w_pawn = Piece('white', 'P', ASSETS_FOLDER + 'w_pawn.png')
b_knight = Piece('black', 'N', ASSETS_FOLDER + 'b_knight.png')
w_knight = Piece('white', 'N', ASSETS_FOLDER + 'w_knight.png')

PIECES_ORDER = {
    (0, 0): pygame.image.load(b_rook.image), (1, 0): pygame.image.load(b_knight.image),
    (2, 0): pygame.image.load(b_bishop.image), (3, 0): pygame.image.load(b_queen.image),
    (4, 0): pygame.image.load(b_king.image), (5, 0): pygame.image.load(b_bishop.image),
    (6, 0): pygame.image.load(b_knight.image), (7, 0): pygame.image.load(b_rook.image),
    (0, 1): pygame.image.load(b_pawn.image), (1, 1): pygame.image.load(b_pawn.image),
    (2, 1): pygame.image.load(b_pawn.image), (3, 1): pygame.image.load(b_pawn.image),
    (4, 1): pygame.image.load(b_pawn.image), (5, 1): pygame.image.load(b_pawn.image),
    (6, 1): pygame.image.load(b_pawn.image), (7, 1): pygame.image.load(b_pawn.image),
    (0, 2): None, (1, 2): None, (2, 2): None, (3, 2): None,
    (4, 2): None, (5, 2): None, (6, 2): None, (7, 2): None,
    (0, 3): None, (1, 3): None, (2, 3): None, (3, 3): None,
    (4, 3): None, (5, 3): None, (6, 3): None, (7, 3): None,
    (0, 4): None, (1, 4): None, (2, 4): None, (3, 4): None,
    (4, 4): None, (5, 4): None, (6, 4): None, (7, 4): None,
    (0, 5): None, (1, 5): None, (2, 5): None, (3, 5): None,
    (4, 5): None, (5, 5): None, (6, 5): None, (7, 5): None,
    (0, 6): pygame.image.load(w_pawn.image), (1, 6): pygame.image.load(w_pawn.image),
    (2, 6): pygame.image.load(w_pawn.image), (3, 6): pygame.image.load(w_pawn.image),
    (4, 6): pygame.image.load(w_pawn.image), (5, 6): pygame.image.load(w_pawn.image),
    (6, 6): pygame.image.load(w_pawn.image), (7, 6): pygame.image.load(w_pawn.image),
    (0, 7): pygame.image.load(w_rook.image), (1, 7): pygame.image.load(w_knight.image),
    (2, 7): pygame.image.load(w_bishop.image), (3, 7): pygame.image.load(w_queen.image),
    (4, 7): pygame.image.load(w_king.image), (5, 7): pygame.image.load(w_bishop.image),
    (6, 7): pygame.image.load(w_knight.image), (7, 7): pygame.image.load(w_rook.image)
}


def populate_board():
    grid_size = WIDTH // 8
    for i in range(2):
        for j in range(8):
            chess_piece_resized = pygame.transform.scale(
                PIECES_ORDER[(j, i)], (0.9*grid_size, 0.9*grid_size))
            BOARD_DISPLAY.blit(chess_piece_resized,
                               ((j*grid_size), (i*grid_size)))

    for i in range(6, 8):
        for j in range(8):
            chess_piece_resized = pygame.transform.scale(
                PIECES_ORDER[(j, i)], (0.9*grid_size, 0.9*grid_size))
            BOARD_DISPLAY.blit(
                chess_piece_resized, ((j*grid_size), (i*grid_size)))


def main():
    is_running = True
    while(is_running):
        create_board()
        populate_board()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                is_running = False
                break
        pygame.display.update()
    pygame.quit()


if __name__ == "__main__":
    main()
