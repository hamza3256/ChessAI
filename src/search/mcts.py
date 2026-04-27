"""Monte Carlo Tree Search with UCT (Upper Confidence bounds applied
to Trees) selection policy.

An alternative stochastic search strategy to alpha-beta.
"""

from __future__ import annotations

import math
import random
import time
from typing import Optional

from engine.bitboard import BoardState, make_move, WHITE, BLACK
from engine.move_gen import generate_legal_moves, is_checkmate, game_over
from engine.evaluation import evaluate


class MCTSNode:
    __slots__ = (
        "state", "parent", "move", "children",
        "wins", "visits", "untried_moves",
    )

    def __init__(self, state: BoardState, parent: Optional[MCTSNode] = None,
                 move: int = 0):
        self.state = state
        self.parent = parent
        self.move = move
        self.children: list[MCTSNode] = []
        self.wins = 0.0
        self.visits = 0
        self.untried_moves: Optional[list[int]] = None

    def _ensure_untried(self) -> None:
        if self.untried_moves is None:
            self.untried_moves = generate_legal_moves(self.state)
            random.shuffle(self.untried_moves)

    def is_fully_expanded(self) -> bool:
        self._ensure_untried()
        return len(self.untried_moves) == 0  # type: ignore[arg-type]

    def is_terminal(self) -> bool:
        over, _ = game_over(self.state)
        return over

    def uct_value(self, exploration: float = 1.414) -> float:
        if self.visits == 0:
            return float("inf")
        exploit = self.wins / self.visits
        explore = exploration * math.sqrt(math.log(self.parent.visits) / self.visits)
        return exploit + explore


def _select(node: MCTSNode) -> MCTSNode:
    """Walk tree using UCT until reaching a leaf or unexpanded node."""
    while not node.is_terminal() and node.is_fully_expanded():
        node = max(node.children, key=lambda c: c.uct_value())
    return node


def _expand(node: MCTSNode) -> MCTSNode:
    """Expand one untried child."""
    node._ensure_untried()
    if not node.untried_moves:
        return node
    move = node.untried_moves.pop()
    new_state = make_move(node.state, move)
    child = MCTSNode(new_state, parent=node, move=move)
    node.children.append(child)
    return child


def _simulate(state: BoardState, max_depth: int = 80) -> float:
    """Random playout from *state* to a terminal or depth limit.

    Returns result from White's perspective: 1.0 = White win,
    0.0 = Black win, 0.5 = draw.
    """
    current = state
    for _ in range(max_depth):
        over, reason = game_over(current)
        if over:
            if "White wins" in reason:
                return 1.0
            elif "Black wins" in reason:
                return 0.0
            return 0.5
        moves = generate_legal_moves(current)
        if not moves:
            return 0.5
        current = make_move(current, random.choice(moves))

    # Depth limit reached: use heuristic evaluation
    score = evaluate(current)
    if score > 200:
        return 0.8
    elif score < -200:
        return 0.2
    return 0.5


def _backpropagate(node: MCTSNode, result: float) -> None:
    """Update visit counts and win scores up the tree."""
    while node is not None:
        node.visits += 1
        # Flip result at each level since we alternate perspectives
        if node.state.side_to_move == BLACK:
            node.wins += result
        else:
            node.wins += 1.0 - result
        node = node.parent


class MCTSSearcher:
    """MCTS with UCT selection policy."""

    def __init__(self, exploration: float = 1.414):
        self.exploration = exploration
        self.iterations_done = 0

    def search(self, state: BoardState, iterations: int = 5000,
               time_limit: float = 5.0) -> tuple[int, dict]:
        """Run MCTS and return (best_move, info_dict)."""
        root = MCTSNode(state)
        start_time = time.time()
        self.iterations_done = 0

        for i in range(iterations):
            if time.time() - start_time > time_limit:
                break

            leaf = _select(root)

            if not leaf.is_terminal():
                leaf = _expand(leaf)

            result = _simulate(leaf.state)
            _backpropagate(leaf, result)
            self.iterations_done = i + 1

        # Return the child with the most visits (most robust choice)
        if not root.children:
            moves = generate_legal_moves(state)
            return (moves[0] if moves else 0), {"iterations": 0}

        best = max(root.children, key=lambda c: c.visits)

        elapsed = time.time() - start_time
        info = {
            "iterations": self.iterations_done,
            "time": elapsed,
            "ips": self.iterations_done / elapsed if elapsed > 0 else 0,
            "best_visits": best.visits,
            "best_winrate": best.wins / best.visits if best.visits else 0,
            "children": len(root.children),
        }
        return best.move, info
