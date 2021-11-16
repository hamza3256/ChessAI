import pygame
import sys

pygame.display.set_caption("ChessAI")
WIDTH, HEIGHT = 1000, 1000
WIN = pygame.display.set_mode((WIDTH, HEIGHT))
WHITE, BLACK, YELLOW, BLUE, GREY = (
    255, 255, 255), (0, 0, 0), (204, 204, 0), (50, 255, 255), (128, 128, 128)
board = [['  ' for _ in range(8)] for _ in range(8)]


class Piece:
    def __init__(self, colour, type, image, killable=False):
        self.colour = colour
        self.type = type
        self.image = image
        self.killable = killable


#  K = king, Q = queen, R = rook, B = bishop, P = pawn, N = knight
black_K = Piece('black', 'K', './assets/king-black.png')
white_K = Piece('white', 'K', './assets/king-white.png')
black_Q = Piece('black', 'Q', './assets/queen-black.png')
white_Q = Piece('white', 'Q', './assets/queen-white.png')
black_R = Piece('black', 'R', './assets/rook-black.png')
white_R = Piece('white', 'R', './assets/rook-white.png')
black_B = Piece('black', 'B', './assets/bishop-black.png')
white_B = Piece('white', 'B', './assets/bishop-white.png')
black_P = Piece('black', 'P', './assets/pawn-black.png')
white_P = Piece('white', 'P', './assets/pawn-white.png')
black_N = Piece('black', 'N', './assets/knight-black.png')
white_N = Piece('white', 'N', './assets/knight-white.png')


PIECES_ORDER = {
    (0, 0): pygame.image.load(black_R.image), (1, 0): pygame.image.load(black_N.image),
    (2, 0): pygame.image.load(black_B.image), (3, 0): pygame.image.load(black_Q.image),
    (4, 0): pygame.image.load(black_K.image), (5, 0): pygame.image.load(black_B.image),
    (6, 0): pygame.image.load(black_N.image), (7, 0): pygame.image.load(black_R.image),
    (0, 1): pygame.image.load(black_P.image), (1, 1): pygame.image.load(black_P.image),
    (2, 1): pygame.image.load(black_P.image), (3, 1): pygame.image.load(black_P.image),
    (4, 1): pygame.image.load(black_P.image), (5, 1): pygame.image.load(black_P.image),
    (6, 1): pygame.image.load(black_P.image), (7, 1): pygame.image.load(black_P.image),
    (0, 2): None, (1, 2): None, (2, 2): None, (3, 2): None,
    (4, 2): None, (5, 2): None, (6, 2): None, (7, 2): None,
    (0, 3): None, (1, 3): None, (2, 3): None, (3, 3): None,
    (4, 3): None, (5, 3): None, (6, 3): None, (7, 3): None,
    (0, 4): None, (1, 4): None, (2, 4): None, (3, 4): None,
    (4, 4): None, (5, 4): None, (6, 4): None, (7, 4): None,
    (0, 5): None, (1, 5): None, (2, 5): None, (3, 5): None,
    (4, 5): None, (5, 5): None, (6, 5): None, (7, 5): None,
    (0, 6): pygame.image.load(white_P.image), (1, 6): pygame.image.load(white_P.image),
    (2, 6): pygame.image.load(white_P.image), (3, 6): pygame.image.load(white_P.image),
    (4, 6): pygame.image.load(white_P.image), (5, 6): pygame.image.load(white_P.image),
    (6, 6): pygame.image.load(white_P.image), (7, 6): pygame.image.load(white_P.image),
    (0, 7): pygame.image.load(white_R.image), (1, 7): pygame.image.load(white_N.image),
    (2, 7): pygame.image.load(white_B.image), (3, 7): pygame.image.load(white_Q.image),
    (4, 7): pygame.image.load(white_K.image), (5, 7): pygame.image.load(white_B.image),
    (6, 7): pygame.image.load(white_N.image), (7, 7): pygame.image.load(white_R.image)
}


def create_board(board):
    board[0] = [
        Piece('black', 'R', './assets/rook-black.png'), Piece('black',
                                                              'N', './assets/knight-black.png'),
        Piece('black', 'B', './assets/bishop-black.png'), Piece('black',
                                                                'Q', './assets/queen-black.png'),
        Piece('black', 'K', './assets/king-black.png'), Piece('black',
                                                              'B', './assets/bishop-black.png'),
        Piece('black', 'N', './assets/knight-black.png'), Piece('black',
                                                                'R', './assets/rook-black.png')
    ]

    board[7] = [
        Piece('white', 'R', './assets/rook-white.png'), Piece('white',
                                                              'N', './assets/knight-white.png'),
        Piece('white', 'B', './assets/bishop-white.png'), Piece('white',
                                                                'Q', './assets/queen-white.png'),
        Piece('white', 'K', './assets/king-white.png'), Piece('white',
                                                              'B', './assets/bishop-white.png'),
        Piece('white', 'N', './assets/knight-white.png'), Piece('white',
                                                                'R', './assets/rook-white.png')
    ]

    for i in range(8):
        board[1][i] = Piece('black', 'P', './assets/pawn-black.png')
        board[6][i] = Piece('white', 'P', './assets/pawn-white.png')

    return board


def boundary_validate(position):
    return position[0] > -1 and position[1] > -1 and position[0] < 8 and position[1] < 8


def convert_to_readable(board):
    output = ''

    for i in board:
        for j in i:
            try:
                output += j.colour + j.type + ', '
            except:
                output += j + ', '
        output += '\n'
    return output


def highlight(board):
    highlighted = []
    for i in range(len(board)):
        for j in range(len(board[0])):
            if board[i][j] == 'x ':
                highlighted.append((i, j))
            else:
                try:
                    if board[i][j].killable:
                        highlighted.append((i, j))
                except:
                    pass
    return highlighted


def deselect():
    for row in range(len(board)):
        for column in range(len(board[0])):
            if board[row][column] == 'x ':
                board[row][column] = '  '
            else:
                try:
                    board[row][column].killable = False
                except:
                    pass
    return convert_to_readable(board)


def check_colour(moves, index):
    row, col = index
    if moves % 2 == 0:
        if board[row][col].colour == 'white':
            return True
    else:
        if board[row][col].colour == 'black':
            return True


def select_move(piece, index, moves):
    if check_colour(moves, index):
        if piece.type == 'P':
            if piece.colour == 'black':
                return highlight(move_pawn_b(index))
            else:
                return highlight(move_pawn_w(index))
        if piece.type == 'K':
            return highlight(move_king(index))

        if piece.type == 'R':
            return highlight(move_rook(index))

        if piece.type == 'B':
            return highlight(move_bishop(index))

        if piece.type == 'Q':
            return highlight(move_queen(index))

        if piece.type == 'N':
            return highlight(move_knight(index))


def move_pawn_b(index):
    if index[0] == 1:
        if board[index[0] + 2][index[1]] == '  ' and board[index[0] + 1][index[1]] == '  ':
            board[index[0] + 2][index[1]] = 'x '
    bottom3 = [[index[0] + 1, index[1] + i] for i in range(-1, 2)]

    for positions in bottom3:
        if boundary_validate(positions):
            if bottom3.index(positions) % 2 == 0:
                try:
                    if board[positions[0]][positions[1]].colour != 'black':
                        board[positions[0]][positions[1]].killable = True
                except:
                    pass
            else:
                if board[positions[0]][positions[1]] == '  ':
                    board[positions[0]][positions[1]] = 'x '
    return board


def move_pawn_w(index):
    if index[0] == 6:
        if board[index[0] - 2][index[1]] == '  ' and board[index[0] - 1][index[1]] == '  ':
            board[index[0] - 2][index[1]] = 'x '
    top3 = [[index[0] - 1, index[1] + i] for i in range(-1, 2)]

    for positions in top3:
        if boundary_validate(positions):
            if top3.index(positions) % 2 == 0:
                try:
                    if board[positions[0]][positions[1]].colour != 'white':
                        board[positions[0]][positions[1]].killable = True
                except:
                    pass
            else:
                if board[positions[0]][positions[1]] == '  ':
                    board[positions[0]][positions[1]] = 'x '
    return board


def move_king(index):
    for y in range(3):
        for x in range(3):
            if boundary_validate((index[0] - 1 + y, index[1] - 1 + x)):
                if board[index[0] - 1 + y][index[1] - 1 + x] == '  ':
                    board[index[0] - 1 + y][index[1] - 1 + x] = 'x '
                else:
                    if board[index[0] - 1 + y][index[1] - 1 + x].colour != board[index[0]][index[1]].colour:
                        board[index[0] - 1 + y][index[1] - 1 + x].killable = True
    return board


def move_bishop(index):
    diagonals = [[[index[0] + i, index[1] + i] for i in range(1, 8)],
                 [[index[0] + i, index[1] - i] for i in range(1, 8)],
                 [[index[0] - i, index[1] + i] for i in range(1, 8)],
                 [[index[0] - i, index[1] - i] for i in range(1, 8)]]

    for direction in diagonals:
        for positions in direction:
            if boundary_validate(positions):
                if board[positions[0]][positions[1]] == '  ':
                    board[positions[0]][positions[1]] = 'x '
                else:
                    if board[positions[0]][positions[1]].colour != board[index[0]][index[1]].colour:
                        board[positions[0]][positions[1]].killable = True
                    break
    return board


def move_rook(index):
    cross = [[[index[0] + i, index[1]] for i in range(1, 8 - index[0])],
             [[index[0] - i, index[1]] for i in range(1, index[0] + 1)],
             [[index[0], index[1] + i] for i in range(1, 8 - index[1])],
             [[index[0], index[1] - i] for i in range(1, index[1] + 1)]]

    for direction in cross:
        for positions in direction:
            if boundary_validate(positions):
                if board[positions[0]][positions[1]] == '  ':
                    board[positions[0]][positions[1]] = 'x '
                else:
                    if board[positions[0]][positions[1]].colour != board[index[0]][index[1]].colour:
                        board[positions[0]][positions[1]].killable = True
                    break
    return board


def move_queen(index):
    board = move_rook(index)
    board = move_bishop(index)
    return board


def move_knight(index):
    for i in range(-2, 3):
        for j in range(-2, 3):
            if i ** 2 + j ** 2 == 5:
                if boundary_validate((index[0] + i, index[1] + j)):
                    if board[index[0] + i][index[1] + j] == '  ':
                        board[index[0] + i][index[1] + j] = 'x '
                    else:
                        if board[index[0] + i][index[1] + j].colour != board[index[0]][index[1]].colour:
                            board[index[0] + i][index[1] + j].killable = True
    return board


class Node:
    def __init__(self, row, col, width):
        self.row = row
        self.col = col
        self.x = int(row * width)
        self.y = int(col * width)
        self.colour = WHITE
        self.occupied = None

    def draw(self, WIN):
        pygame.draw.rect(WIN, self.colour,
                         (self.x, self.y, WIDTH / 8, WIDTH / 8))

    def setup(self, WIN):
        if PIECES_ORDER[(self.row, self.col)]:
            if PIECES_ORDER[(self.row, self.col)] == None:
                pass
            else:
                piece_image_resize = pygame.transform.scale(
                    PIECES_ORDER[(self.row, self.col)], (WIDTH//8, HEIGHT//8))
                WIN.blit(piece_image_resize, (self.x, self.y))


def make_grid(rows, width):
    grid = []
    gap = WIDTH // rows
    print(gap)
    for i in range(rows):
        grid.append([])
        for j in range(rows):
            node = Node(j, i, gap)
            grid[i].append(node)
            if (i+j) % 2 == 1:
                grid[i][j].colour = GREY
    return grid


def draw_grid(win, rows, width):
    gap = width // 8
    for i in range(rows):
        pygame.draw.line(win, BLACK, (0, i * gap), (width, i * gap))
        for j in range(rows):
            pygame.draw.line(win, BLACK, (j * gap, 0), (j * gap, width))


def update_display(win, grid, rows, width):
    for row in grid:
        for spot in row:
            spot.draw(win)
            spot.setup(win)
    draw_grid(win, rows, width)
    pygame.display.update()


def find_node(pos, WIDTH):
    interval = WIDTH / 8
    y, x = pos
    rows = y // interval
    columns = x // interval
    return int(rows), int(columns)


def display_potential_moves(positions, grid):
    for i in positions:
        x, y = i
        grid[x][y].colour = BLUE
        """
        Displays all the potential moves
        """


def perform_move(inital_position, final_position, WIN):
    PIECES_ORDER[final_position] = PIECES_ORDER[inital_position]
    PIECES_ORDER[inital_position] = None


def remove_highlight(grid):
    for i in range(len(grid)):
        for j in range(len(grid[0])):
            if (i+j) % 2 == 0:
                grid[i][j].colour = WHITE
            else:
                grid[i][j].colour = GREY
    return grid


def main(WIN, WIDTH):
    moves = 0
    selected = False
    piece_to_move = []
    grid = make_grid(8, WIDTH)
    while True:
        pygame.time.delay(50)  # stops cpu dying
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.MOUSEBUTTONDOWN:
                pos = pygame.mouse.get_pos()
                y, x = find_node(pos, WIDTH)
                if selected == False:
                    try:
                        possible = select_move((board[x][y]), (x, y), moves)
                        for positions in possible:
                            row, col = positions
                            grid[row][col].colour = BLUE
                        piece_to_move = x, y
                        selected = True
                    except:
                        piece_to_move = []
                        print('Can\'t select')
                    # print(piece_to_move)

                else:
                    try:
                        if board[x][y].killable == True:
                            row, col = piece_to_move  # coords of original piece
                            board[x][y] = board[row][col]
                            board[row][col] = '  '
                            deselect()
                            remove_highlight(grid)
                            perform_move((col, row), (y, x), WIN)
                            moves += 1
                            print(convert_to_readable(board))
                        else:
                            deselect()
                            remove_highlight(grid)
                            selected = False
                            print("Deselected")
                    except:
                        if board[x][y] == 'x ':
                            row, col = piece_to_move
                            board[x][y] = board[row][col]
                            board[row][col] = '  '
                            deselect()
                            remove_highlight(grid)
                            perform_move((col, row), (y, x), WIN)
                            moves += 1
                            print(convert_to_readable(board))
                        else:
                            deselect()
                            remove_highlight(grid)
                            selected = False
                            print("Invalid move")
                    selected = False

            update_display(WIN, grid, 8, WIDTH)


if __name__ == "__main__":
    create_board(board)
    main(WIN, WIDTH)
