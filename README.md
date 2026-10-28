# Snake & Ladder — a BFS mini project

An application-based mini project that implements **Snake and Ladder** and uses
**Breadth-First Search (BFS)** to compute the *minimum number of dice throws*
needed to finish a board.

Pure Python standard library — no third-party dependencies.

---

## Quick start

```bash
cd snake-ladder-bfs

python main.py                 # interactive menu
# or
python -m snake_ladder         # same menu as a module

# run the test suite
python -m unittest discover -s tests -v
```

Sample session:

```
Select: 2
Board [a]: a
  Start cell [1]:
--- BFS result ---
Minimum dice throws: 7
Nodes explored by BFS: 82
Path: 1 -> 14 -> 17 -> 22 -> 84 -> 88 -> 94 -> 100
Rolls: 3, 3, 5, 6, 4, 6, 6
Ladders climbed: 4->14, 28->84
```

---

## What the menu does

| # | Feature | DSA concept |
|---|---------|-------------|
| 1 | Play a game (humans and/or computer) | live BFS "best case left" hint after every turn |
| 2 | Solve a board → minimum dice throws, path, rolls, jumps | **BFS** shortest path |
| 3 | Visualise the BFS visitation order | **level-by-level frontier expansion** |
| 4 | BFS vs Dijkstra cross-check | **queue vs priority queue (heap)** |
| 5 | Generate a random board and solve it | **graph construction** + validation |
| 6 | Render a board (ASCII grid, snake/ladder markers) | board model |

Boards can be the classic 100-cell layout, randomly generated, or entered by
hand (`Snakes: 16:6,47:26` / `Ladders: 1:38,4:14`).

---

## How the problem becomes a graph

Each **cell is a node**. From cell `u` there is an **edge to every cell
reachable with one dice roll**, after resolving any snake/ladder you land on:

```
u --roll r-->  v = u + r          (if v <= size)
u --roll r-->  target             (if v >  size, overshoot counts as a win)
v = jump(v)                        (apply snake / ladder / chained jumps)
```

The result is an explicit **adjacency list** (`dict[int, list[int]]`) built by
`Board.moves()`.

Key observations:

* **Every edge costs exactly one dice throw** → the graph is *unweighted* →
  BFS yields the true shortest path.
* **Snakes create backward edges**, so the graph is **not** acyclic — e.g. on
  the classic board `10 →(roll 6)→ 16 →(snake)→ 6 →(roll 4)→ 10` is a cycle.
  This is exactly why BFS needs a *visited set*: plain recursion would loop
  forever.
* Out-degree is between 0 and 6 (only the finish has out-degree 0).

---

## The algorithm

```python
queue  = deque([start])
levels = {start: 0}          # doubles as the visited set
parent = {start: -1}

while queue:
    u = queue.popleft()
    if u == target: break                # first pop == optimal (unweighted)
    for roll, v in moves[u]:
        if v not in levels:              # breaks snake-induced cycles
            levels[v] = levels[u] + 1
            parent[v] = u
            queue.append(v)
```

The path is rebuilt by walking `parent` backwards; `parent_roll` records which
dice face produced each hop, so the exact roll sequence can be printed.

### Complexity

| | Time | Space |
|---|---|---|
| **BFS** (`solve`) | `O(V + E)`, `E ≤ V × dice_faces` | `O(V)` |
| **Dijkstra** (`solve_dijkstra`) | `O((V + E) log V)` with `heapq` | `O(V)` |

Both are cross-checked against each other in the tests and in menu option 4.
They must agree because all edge weights are 1 — Dijkstra is effectively a
"weighted BFS", but it pays a `log V` tax for the priority queue.

---

## Project layout

```
snake-ladder-bfs/
├── main.py                      # interactive CLI menu
├── README.md
├── snake_ladder/
│   ├── __init__.py
│   ├── __main__.py              # python -m snake_ladder
│   ├── board.py                 # board model, validation, graph construction, rendering
│   ├── solver.py                # BFS solver + Dijkstra cross-check
│   └── game.py                  # interactive game loop
└── tests/
    └── test_solver.py           # 35 unit tests
```

### Module responsibilities

* **`board.py`** — `Board` holds snakes/ladders, validates the configuration
  (direction of each snake/ladder, range, duplicate bases, **jump cycles** such
  as `ladder 4→8` + `snake 8→4`), builds the adjacency list, generates random
  boards, and renders the ASCII grid.
* **`solver.py`** — `solve()` (BFS) returns a `Solution` with the minimum throw
  count, the reconstructed path, the dice rolls, any snakes/ladders hit, the
  BFS visitation order and the level map.
* **`game.py`** — the playable game; after each turn it re-runs BFS from the
  player's cell to print the *theoretical* best case remaining.

---

## Rules implemented

* Start on cell 1, finish on cell `size`.
* Default: rolling past the finish counts as a win (`exact_finish=False`).
  Pass `exact_finish=True` to require an exact landing — then overshoot rolls
  are simply illegal moves.
* Landing on a snake head slides you down; landing on a ladder base lifts you
  up. Chained jumps (a ladder that tops out on a snake head) are followed, and
  chains are rejected at construction time if they form a cycle.
* The final cell can never be a snake/ladder base.

---

## Tests

```bash
python -m unittest discover -s tests -v
```

35 tests covering:

* board validation (direction, ranges, duplicate bases, jump cycles)
* graph construction (forward/snake-induced edges, out-degrees, exact-finish)
* BFS correctness (valid path, roll sequence, level consistency, level
  tightness — i.e. the levels really are the *shortest* distances)
* BFS vs Dijkstra agreement across the classic board and 25 random boards
* game move logic (plain moves, snakes, ladders, overshoot)
* ASCII rendering
"# snake-and-ladder" 
