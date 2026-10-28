"""Board model and graph construction for Snake & Ladder.

DSA concepts used here
----------------------
* Graph represented explicitly as an **adjacency list** (``dict[int, list[int]]``).
* Each cell is a node; an edge ``u -> v`` means "one dice roll can take me from
  ``u`` to ``v``" (after any snake/ladder jump has been applied).
* Because every edge costs exactly one dice throw, the graph is *unweighted*,
  which is what makes BFS (in ``solver.py``) the right algorithm.
"""

from __future__ import annotations

import random
from typing import Dict, List, Mapping, Optional, Tuple

DEFAULT_SIZE = 100
DEFAULT_DICE_FACES = 6


class BoardError(ValueError):
    """Raised when a board configuration is invalid."""


class Board:
    """A Snake & Ladder board.

    Parameters
    ----------
    size:
        Number of cells, numbered ``1 .. size``. Cell ``1`` is the start and
        cell ``size`` is the finish.
    snakes:
        Mapping of *head* cell -> *tail* cell (head is always above the tail).
    ladders:
        Mapping of *bottom* cell -> *top* cell (bottom is always below the top).
    dice_faces:
        Number of faces on the dice (default 6).
    exact_finish:
        When ``True`` a player must land exactly on ``size`` to win (overshoot
        rolls are illegal). When ``False`` (default) overshooting counts as a
        win, which is the usual convention in graph versions of this problem.
    """

    def __init__(
        self,
        size: int = DEFAULT_SIZE,
        snakes: Optional[Mapping[int, int]] = None,
        ladders: Optional[Mapping[int, int]] = None,
        dice_faces: int = DEFAULT_DICE_FACES,
        exact_finish: bool = False,
    ) -> None:
        if size < 2:
            raise BoardError("A board needs at least 2 cells.")
        if dice_faces < 2:
            raise BoardError("A dice needs at least 2 faces.")

        self.size = size
        self.dice_faces = dice_faces
        self.exact_finish = exact_finish
        self.snakes: Dict[int, int] = dict(snakes or {})
        self.ladders: Dict[int, int] = dict(ladders or {})
        # Single lookup table used by jump(): cell -> destination cell.
        self._jump_map: Dict[int, int] = {**self.ladders, **self.snakes}
        self.validate()

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    def validate(self) -> None:
        """Verify the configuration is legal and free of jump cycles."""
        owner: Dict[int, str] = {}

        for kind, mapping in (("snake", self.snakes), ("ladder", self.ladders)):
            for src, dst in mapping.items():
                if not 1 <= src <= self.size:
                    raise BoardError(f"{kind} base {src} is outside 1..{self.size}")
                if not 1 <= dst <= self.size:
                    raise BoardError(f"{kind} destination {dst} is outside 1..{self.size}")
                if src == self.size:
                    raise BoardError("The final cell cannot be a snake or ladder base.")
                if kind == "snake" and not src > dst:
                    raise BoardError(f"Snake at {src} must end below its head (got {dst})")
                if kind == "ladder" and not src < dst:
                    raise BoardError(f"Ladder at {src} must end above its base (got {dst})")
                if src in owner:
                    raise BoardError(
                        f"Cell {src} is used as both a {owner[src]} and a {kind}"
                    )
                owner[src] = kind

        # Follow every chain: snakes go down, ladders go up, so a cycle would
        # need an up-then-down loop (e.g. ladder 4->8 plus snake 8->4).
        for start in self._jump_map:
            path = []
            cur = start
            while cur in self._jump_map:
                if cur in path:
                    raise BoardError(
                        f"Jump cycle detected starting at {start}: "
                        f"{' -> '.join(map(str, path + [cur]))}"
                    )
                path.append(cur)
                cur = self._jump_map[cur]

    # ------------------------------------------------------------------
    # Board helpers
    # ------------------------------------------------------------------
    @property
    def start(self) -> int:
        return 1

    @property
    def target(self) -> int:
        return self.size

    def jump(self, pos: int) -> int:
        """Resolve a cell to its final resting place after any snakes/ladders."""
        cur = pos
        hops = 0
        while cur in self._jump_map:
            cur = self._jump_map[cur]
            hops += 1
            if hops > self.size:  # defensive; validate() already rejects cycles
                raise BoardError("Jump cycle detected")
        return cur

    # ------------------------------------------------------------------
    # Graph construction
    # ------------------------------------------------------------------
    def moves(self) -> Dict[int, List[Tuple[int, int]]]:
        """Build the *labelled* edge list of the board graph.

        ``moves[u]`` is a list of ``(dice_face, destination)`` pairs: every cell
        reachable from ``u`` with a single dice roll, snake/ladder jumps already
        applied.

        Ladders push forward and snakes pull *backwards*, so this graph may
        contain cycles (e.g. 10 -roll 6-> 16 -snake-> 6 -roll 4-> 10). That is
        exactly why the solver needs a visited set instead of plain recursion.
        """
        target = self.target
        moves: Dict[int, List[Tuple[int, int]]] = {u: [] for u in range(1, target + 1)}

        for u in range(1, target + 1):
            if u == target:
                continue  # the finish has no outgoing edges: the game is over
            seen: set = set()
            for roll in range(1, self.dice_faces + 1):
                v = u + roll
                if v > target:
                    if self.exact_finish:
                        continue  # illegal overshoot roll
                    v = target  # overshoot counts as reaching the finish
                dest = target if v == target else self.jump(v)
                if dest not in seen:
                    seen.add(dest)
                    moves[u].append((roll, dest))
        return moves

    def adjacency(self) -> Dict[int, List[int]]:
        """Unlabelled adjacency list: ``adj[u]`` = cells reachable from ``u``."""
        return {u: [dest for _, dest in edges] for u, edges in self.moves().items()}

    def degree(self) -> Tuple[int, int]:
        """Return ``(min_out_degree, max_out_degree)`` over all nodes.

        The finish node has out-degree 0 (the game is already over), every
        other cell has at least 1 and at most ``dice_faces`` outgoing edges.
        """
        adj = self.adjacency()
        degrees = [len(adj[u]) for u in adj]
        return min(degrees), max(degrees)

    # ------------------------------------------------------------------
    # Pretty printing
    # ------------------------------------------------------------------
    @property
    def columns(self) -> int:
        return 10 if self.size >= 10 else self.size

    @property
    def rows(self) -> int:
        return (self.size + self.columns - 1) // self.columns

    def render(self, player_positions: Optional[Dict[str, int]] = None) -> str:
        """Render the board as a boustrophedon (zig-zag) grid.

        ``player_positions`` maps a player name to their current cell so the
        tokens can be drawn on the board.
        """
        cols = self.columns
        digits = len(str(self.size))
        tok_w = 4 if player_positions else 0   # room for player initials
        width = tok_w + digits + 1
        player_positions = player_positions or {}

        # Group players by cell so we can print e.g. "AB" together.
        tokens: Dict[int, str] = {}
        for name, cell in player_positions.items():
            tokens.setdefault(cell, "")
            tokens[cell] += name[0].upper()

        lines: List[str] = []
        for r in range(self.rows - 1, -1, -1):
            lo = r * cols + 1
            hi = min((r + 1) * cols, self.size)
            cells = list(range(lo, hi + 1))
            if r % 2 == 1:  # odd rows run right-to-left so 11 sits above 10
                cells.reverse()

            row: List[str] = []
            for n in cells:
                if n in self.snakes:
                    tag = "S"
                elif n in self.ladders:
                    tag = "L"
                else:
                    tag = " "
                prefix = tokens.get(n, "")
                label = f"{prefix:<{tok_w}}{n:>{digits}}{tag}"
                row.append(label.ljust(width))
            lines.append("|" + "|".join(row) + "|")

        lines.append("+" + ("-" * (width + 1) + "+") * cols)
        return "\n".join(lines)

    def summary(self) -> str:
        s = ", ".join(f"{h}->{t}" for h, t in sorted(self.snakes.items()))
        l = ", ".join(f"{b}->{t}" for b, t in sorted(self.ladders.items()))
        return (
            f"Board size : {self.size} cells (dice: {self.dice_faces} faces, "
            f"exact finish: {self.exact_finish})\n"
            f"Snakes ({len(self.snakes)}): {s or '-'}\n"
            f"Ladders ({len(self.ladders)}): {l or '-'}"
        )

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return (
            f"Board(size={self.size}, snakes={self.snakes}, ladders={self.ladders}, "
            f"dice_faces={self.dice_faces}, exact_finish={self.exact_finish})"
        )


# ----------------------------------------------------------------------
# Random board generation
# ----------------------------------------------------------------------
def generate_board(
    size: int = DEFAULT_SIZE,
    n_snakes: Optional[int] = None,
    n_ladders: Optional[int] = None,
    dice_faces: int = DEFAULT_DICE_FACES,
    exact_finish: bool = False,
    seed: Optional[int] = None,
) -> Board:
    """Create a random, validated board.

    The generator never puts a snake/ladder on the final cell, keeps every
    base unique, and simply retries if the random layout happens to form a
    jump cycle (rare, and the retry loop guarantees termination).
    """
    if size < 6:
        raise BoardError("size must be >= 6 to place snakes and ladders")

    rng = random.Random(seed)
    n_snakes = max(1, size // 20) if n_snakes is None else n_snakes
    n_ladders = max(1, size // 20) if n_ladders is None else n_ladders

    # Snakes can only sit on cells 3..size-1 (need at least 2 cells of drop).
    snake_cells = rng.sample(range(3, size), min(n_snakes, size - 3))
    # Ladders can only sit on cells 1..size-2 (need at least 2 cells of climb).
    ladder_pool = [c for c in range(1, size - 1) if c not in snake_cells]
    ladder_cells = rng.sample(ladder_pool, min(n_ladders, len(ladder_pool)))

    snakes = {c: rng.randrange(1, c) for c in snake_cells}
    ladders = {c: rng.randrange(c + 2, size + 1) for c in ladder_cells}

    for _ in range(200):
        try:
            return Board(size, snakes, ladders, dice_faces, exact_finish)
        except BoardError:
            # Remove a random base and try again (breaks up rare cycles).
            if snakes:
                snakes.pop(rng.choice(list(snakes)))
            elif ladders:
                ladders.pop(rng.choice(list(ladders)))
            else:  # pragma: no cover - defensive
                break

    raise BoardError("Could not generate a valid board; try a different size.")
