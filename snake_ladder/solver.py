"""Solvers: minimum number of dice throws to finish the board.

DSA concepts used here
----------------------
* **BFS (Breadth-First Search)** on an unweighted graph -> guaranteed shortest
  path, because BFS explores nodes in order of their distance (in *edges*) from
  the source. One edge here == one dice throw.
* **Queue** (``collections.deque``) used as the FIFO frontier.
* **Visited set** (the ``levels`` dict doubles as the visited marker, so the
  cycles created by snakes cannot trap the search).
* **Parent map** used to reconstruct the actual path afterwards.
* **Dijkstra's algorithm** with a binary **heap** (``heapq``) is provided as a
  second, independent solution so the two can be cross-checked — every edge has
  weight 1, so both must return the same answer, but Dijkstra pays an extra
  ``log V`` factor for the priority queue.
"""

from __future__ import annotations

import heapq
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .board import Board


@dataclass
class Solution:
    """Result of solving a board."""

    reachable: bool
    min_throws: Optional[int]
    path: List[int] = field(default_factory=list)
    rolls: List[int] = field(default_factory=list)   # dice face needed on each step
    jumps: List[Tuple[int, int]] = field(default_factory=list)  # (head/bottom, tail/top)
    bfs_order: List[int] = field(default_factory=list)  # nodes in BFS visitation order
    levels: Dict[int, int] = field(default_factory=dict)  # node -> throws from start

    @property
    def snakes_hit(self) -> List[Tuple[int, int]]:
        return [j for j in self.jumps if j[0] > j[1]]

    @property
    def ladders_hit(self) -> List[Tuple[int, int]]:
        return [j for j in self.jumps if j[0] < j[1]]

    @property
    def nodes_explored(self) -> int:
        return len(self.bfs_order)

    def describe(self) -> str:
        if not self.reachable:
            return "The target is unreachable from the start."
        lines = [f"Minimum dice throws: {self.min_throws}"]
        lines.append(f"Nodes explored by BFS: {self.nodes_explored}")
        lines.append("Path: " + " -> ".join(map(str, self.path)))
        lines.append("Rolls: " + ", ".join(str(r) for r in self.rolls))
        if self.ladders_hit:
            lines.append(
                "Ladders climbed: "
                + ", ".join(f"{b}->{t}" for b, t in self.ladders_hit)
            )
        if self.snakes_hit:
            lines.append(
                "Snakes slid down: "
                + ", ".join(f"{h}->{t}" for h, t in self.snakes_hit)
            )
        return "\n".join(lines)


# ----------------------------------------------------------------------
# Primary solution: BFS
# ----------------------------------------------------------------------
def solve(board: Board, start: Optional[int] = None) -> Solution:
    """BFS shortest path: minimum dice throws from ``start`` to the target.

    Complexity
    ----------
    * Time  : O(V + E) where V = size and E <= size * dice_faces
    * Space : O(V) for the queue, levels and parent maps
    """
    src = board.start if start is None else start
    dst = board.target
    if not 1 <= src <= dst:
        raise ValueError(f"start {src} outside 1..{dst}")

    moves = board.moves()

    queue: deque = deque([src])
    levels: Dict[int, int] = {src: 0}
    parent: Dict[int, int] = {src: -1}
    parent_roll: Dict[int, int] = {src: 0}
    order: List[int] = [src]  # BFS visitation order (used for visualisation)

    while queue:
        u = queue.popleft()
        if u == dst:
            break  # BFS guarantees the first time we pop dst it is optimal
        for roll, v in moves[u]:
            if v not in levels:          # visited check breaks snake cycles
                levels[v] = levels[u] + 1
                parent[v] = u
                parent_roll[v] = roll
                order.append(v)
                queue.append(v)

    if dst not in levels:
        return Solution(reachable=False, min_throws=None,
                        bfs_order=order, levels=levels)

    # ---- reconstruct the path by walking the parent pointers backwards ----
    path: List[int] = []
    node = dst
    while node != -1:
        path.append(node)
        node = parent[node]
    path.reverse()

    rolls = [parent_roll[n] for n in path[1:]]

    jumps: List[Tuple[int, int]] = []
    for a, b, roll in zip(path, path[1:], rolls):
        landed = a + roll
        if landed > board.target and not board.exact_finish:
            landed = board.target
        if landed != b:  # a snake or ladder fired
            if landed in board.snakes:
                jumps.append((landed, board.snakes[landed]))
            elif landed in board.ladders:
                jumps.append((landed, board.ladders[landed]))

    return Solution(
        reachable=True,
        min_throws=levels[dst],
        path=path,
        rolls=rolls,
        jumps=jumps,
        bfs_order=order,
        levels=levels,
    )


# ----------------------------------------------------------------------
# Cross-check solution: Dijkstra with a binary heap
# ----------------------------------------------------------------------
def solve_dijkstra(board: Board, start: Optional[int] = None) -> Optional[int]:
    """Dijkstra's algorithm — an independent way to reach the same answer.

    Every edge costs 1 throw, so Dijkstra degenerates to a "weighted BFS" and
    must agree with :func:`solve`. It is included to show the trade-off: the
    heap gives O((V + E) log V) instead of BFS's O(V + E).

    Returns ``None`` when the target is unreachable.
    """
    src = board.start if start is None else start
    dst = board.target
    moves = board.moves()

    dist: Dict[int, int] = {src: 0}
    heap: List[Tuple[int, int]] = [(0, src)]

    while heap:
        d, u = heapq.heappop(heap)
        if d > dist.get(u, -1):
            continue              # stale entry — already settled with a better d
        if u == dst:
            return d
        for _, v in moves[u]:
            nd = d + 1
            if nd < dist.get(v, 1 << 60):
                dist[v] = nd
                heapq.heappush(heap, (nd, v))

    return None
