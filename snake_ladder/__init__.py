"""Snake & Ladder mini project built around BFS.

Modules
-------
board   -> board model + explicit graph (adjacency-list) construction
solver  -> BFS shortest path (minimum dice throws) + Dijkstra cross-check
game    -> interactive command-line play
"""

from .board import Board, BoardError, generate_board
from .solver import Solution, solve, solve_dijkstra

__all__ = [
    "Board",
    "BoardError",
    "generate_board",
    "Solution",
    "solve",
    "solve_dijkstra",
]
