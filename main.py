import random
import os
import tkinter as tk
import copy

# Tile colors
TILE_COLORS = {
    0: "#cdc1b4", 2: "#eee4da", 4: "#ede0c8", 8: "#f2b179",
    16: "#f59563", 32: "#f67c5f", 64: "#f65e3b", 128: "#edcf72",
    256: "#edcc61", 512: "#edc850", 1024: "#edc53f", 2048: "#edc22e",
}

# We are using a 2D list to simulate our 2048 game 
def initialize_board():
    board = [[0 for _ in range(4)] for _ in range(4)]
    add_new_tile(board)
    add_new_tile(board)
    return board

def print_board(board): # function to print the board in command propmt
    os.system('cls' if os.name=='nt' else 'clear') # clears the command line, cls is the command used for windows(its name is 'nt'), clear is used for other operating systems like UNIX 
    print("+----" * 4 + "+")
    for row in board:
        for tile in row:
            print(f"|{tile:^4}", end="")
        print("|")
        print("+----" * 4 + "+")

# function to add a new tile which is either 2 or 4 at random to any of the empty spaces
def add_new_tile(board):
    empty = [(i, j) for i in range(4) for j in range(4) if board[i][j] == 0]
    if not empty:
        return
    i, j = random.choice(empty)
    board[i][j] = 2 if random.random() < 0.9 else 4
# function to extract all the non zero numbers which will be used for merging and moving forward in the game
def compress(row):
    row = [num for num in row if num != 0]
    i = 0
    while i < len(row) - 1:
        if row[i] == row[i + 1]:
            row[i] *= 2
            del row[i + 1]
        i += 1
    row += [0] * (4 - len(row))
    return row
# function to move left
def move_left(board):
    return [compress(row) for row in board]
# reverse the function to move left to get the function to move right
def move_right(board):
    return [compress(row[::-1])[::-1] for row in board]
# transpose the move left function to get function to move up
def move_up(board):
    transposed = list(zip(*board))
    moved = [compress(list(row)) for row in transposed]
    return [list(row) for row in zip(*moved)]
#""
def move_down(board):
    transposed = list(zip(*board))
    moved = [compress(list(row)[::-1])[::-1] for row in transposed]
    return [list(row) for row in zip(*moved)]
# function to check if there are any valid moves to play and if not declare game over
def is_game_over(board):
    if any(0 in row for row in board):
        return False
    for i in range(4):
        for j in range(3):
            if board[i][j] == board[i][j + 1] or board[j][i] == board[j + 1][i]:
                return False
    return True
# one of the metrics which will be used to evaulate the hueristics
def sum_of_squares(board):
    return sum(tile**2 for row in board for tile in row)
# one of the metrics which will be used to evaluate the hueristics 
def calculate_smoothness(board):
    score = 0
    for i in range(4):
        for j in range(3):
            if board[i][j] and board[i][j + 1]:
                score -= abs(board[i][j] - board[i][j + 1])
            if board[j][i] and board[j + 1][i]:
                score -= abs(board[j][i] - board[j + 1][i])
    return score
# one of the metrics which will be used to evaluate the hueristics 
def calculate_monotonicity(board):
    score = 0
    for row in board:
        for i in range(3):
            if row[i] >= row[i + 1]:
                score += 1
    for col in zip(*board):
        for i in range(3):
            if col[i] >= col[i + 1]:
                score += 1
    return score
# adaptive depth inorder to improve the performance in the endgame and the number of empty and usable tiles decrease    
def get_adaptive_depth(board):
    empty = sum(row.count(0) for row in board)
    return 5 if empty <= 3 else 3
# prioritizing the empty tiles and giving a penalty if the board has less than or equal to two tiles
def panic_penalty(board):
    empty_tiles = sum(row.count(0) for row in board)
    if empty_tiles <= 2:
        return -2000  # big penalty when the board is full
    return 0
'''
# one of the metrics which will be used to evaluate the hueristics (did not work thats why its commented out)

def vertical_stack_bonus(board):
    stack_score = 0
    for j in range(4):
        col = [board[i][j] for i in range(4)]
        if col[0] >= col[1] >= col[2] >= col[3] and all(x != 0 for x in col):
            stack_score += col[0]
    return stack_score
'''
# corner bonus to keep the max tile in the corner which makes it easier for the rest of the tiles to merge
def corner_bonus(board):
    max_tile = max(max(row) for row in board)
    corners = [board[0][0], board[0][3], board[3][0], board[3][3]]
    return 500 if max_tile in corners else 0


#function to evalaute the board and to decide which is the best move
def evaluate_heuristic(board):
    empty_tiles = sum(row.count(0) for row in board)
    return (
        0.05 * sum_of_squares(board) +
        1.5 * calculate_monotonicity(board) +
        calculate_smoothness(board) +
        1000 * empty_tiles +
        corner_bonus(board)
        
        
    )
# function which uses the expectimax function to make a decision and decide the best move 
def expectimax_decision(board, depth=4):
    moves = {'w': move_up, 'a': move_left, 's': move_down, 'd': move_right}
    best_score = float('-inf')
    best_move = None
    for move_key, move_func in moves.items():
        new_board = move_func(copy.deepcopy(board))
        if new_board != board:
            score = expectimax(new_board, depth - 1, False)
            if score > best_score:
                best_score = score
                best_move = move_key
    return best_move
#expectimax function which uses the decision tree of max and chance nodes to return a expected value of a board
def expectimax(board, depth, is_player):
    if depth == 0 or is_game_over(board):
        return evaluate_heuristic(board)
    if is_player:
        return max(expectimax(move(copy.deepcopy(board)), (depth or get_adaptive_depth(board)) - 1, False)
                   for move in [move_up, move_down, move_left, move_right]
                   if move(copy.deepcopy(board)) != board)
    empty = [(i, j) for i in range(4) for j in range(4) if board[i][j] == 0]
    if not empty:
        return evaluate_heuristic(board)
    score = 0
    for i, j in empty:
        for val, prob in [(2, 0.9), (4, 0.1)]:
            new_board = copy.deepcopy(board)
            new_board[i][j] = val
            score += prob * expectimax(new_board, depth - 1, True)
    return score / len(empty)

#----------------------------------------------------------------------------------
def cli_main(): # the main function to run and display the 4*4 board in the command line interface
    board = initialize_board()
    
    while True:
        print_board(board)
        move = input("Enter move (WASD or Q to quit): ").lower()

        if move == 'q':
            print("Thanks for playing!")
            break

        old_board = [row[:] for row in board]

        if move == 'a':
            board = move_left(board)
        elif move == 'd':
            board = move_right(board)
        elif move == 'w':
            board = move_up(board)
        elif move == 's':
            board = move_down(board)
        else:
            print("Invalid input! Use W/A/S/D or Q.")
            continue

        if board != old_board:
            add_new_tile(board)

        if is_game_over():# to check if the game is over and there are no more possible moves
            print_board(board)
            print("GAME OVER ur ass ")
            break
#----------------------------------------------------------------------------------




# main GUI function
class Game2048GUI:
    def __init__(self, root, board):
        self.root = root
        self.board = board
        self.move_count = 0

        self.move_label = tk.Label(root, text="Moves: 0", font=("Helvetica", 14))
        self.move_label.grid()

        self.grid_frame = tk.Frame(root, bg="#bbada0", bd=10)
        self.grid_frame.grid()

        self.cells = []
        for i in range(4):
            row = []
            for j in range(4):
                cell = tk.Label(self.grid_frame, text="", width=4, height=2,
                                font=("Helvetica", 32, "bold"), bg="#cdc1b4", fg="#776e65", relief="ridge", bd=4)
                cell.grid(row=i, column=j, padx=5, pady=5)
                row.append(cell)
            self.cells.append(row)

        self.update_board()
        self.autoplay()

    def update_board(self):
        for i in range(4):
            for j in range(4):
                value = self.board[i][j]
                self.cells[i][j].config(
                    text=str(value) if value != 0 else "",
                    bg=TILE_COLORS.get(value, "#3c3a32")
                )

    def make_move(self, move_func):
        old_board = [row[:] for row in self.board]
        self.board = move_func(self.board)
        if self.board != old_board:
            add_new_tile(self.board)
            self.update_board()
            if is_game_over(self.board):
                self.show_game_over()

    def show_game_over(self):
        tk.Label(self.root, text="GAME OVER", font=("Helvetica", 24, "bold"), fg="red").grid()

    def autoplay(self):
        if is_game_over(self.board):
            self.show_game_over()
            return

        move = expectimax_decision(self.board, depth=4)
        if move:
            direction_map = {'w': move_up, 'a': move_left, 's': move_down, 'd': move_right}
            self.make_move(direction_map[move])
            self.move_count += 1
            self.move_label.config(text=f"Moves: {self.move_count}")

        self.root.after(100, self.autoplay)

if __name__ == "__main__":
    USE_GUI = True
    if USE_GUI:
        root = tk.Tk()
        root.title("2048 Game")
        Game2048GUI(root, initialize_board())
        root.mainloop()


'''
#--------------------------------------------------
# Greedy algorithm implementation- works on a points basis where a board is given points on the basis of the number of empty tiles and the max tiles that it has and the algorthm uses that metric inorder to move forward 
# ie: to make the move which will give the board with the most points
#--------------------------------------------------
def get_possible_moves(board):
    directions = {
        'w': move_up,
        'a': move_left,
        's': move_down,
        'd': move_right
    }

    possible_moves = []

    for key in directions:
        board_copy = copy.deepcopy(board)
        new_board = directions[key](board_copy)

        if new_board != board:
            possible_moves.append((key, new_board))

    return possible_moves

def evaluate_board(board):
    empty_spaces = sum(row.count(0) for row in board)
    max_tile = max(max(row) for row in board)
    return empty_spaces + 0.1 * max_tile

def get_best_move(board):
    moves = get_possible_moves(board)
    if not moves:
        return None

    best_move = max(moves, key=lambda x: evaluate_board(x[1]))
    return best_move[0]
'''
