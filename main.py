#!/usr/bin/env python3
"""Snake & Ladder - an application mini-project demonstrating DSA concepts.

Run:  python main.py
"""

from __future__ import annotations

import os
import sys
import time

from snake_ladder import Board, BoardError, generate_board, solve, solve_dijkstra
from snake_ladder.game import play_game

# A classic 100-cell layout.
CLASSIC_SNAKES = {16: 6, 47: 26, 49: 11, 56: 53, 62: 19,
                  64: 60, 87: 24, 93: 73, 95: 75, 98: 78}
CLASSIC_LADDERS = {1: 38, 4: 14, 9: 31, 21: 42, 28: 84,
                   36: 44, 51: 67, 71: 91, 80: 100}


def classic_board() -> Board:
    return Board(100, CLASSIC_SNAKES, CLASSIC_LADDERS)


def ask_int(prompt: str, default: int, lo: int, hi: int) -> int:
    """Read an int from stdin, falling back to ``default`` on blank/invalid."""
    raw = input(f"{prompt} [{default}]: ").strip()
    if not raw:
        return default
    try:
        val = int(raw)
    except ValueError:
        print("  ! not a number, using default")
        return default
    if not lo <= val <= hi:
        print(f"  ! out of range {lo}..{hi}, using default")
        return default
    return val


_MENU_TITLE = "SNAKE & LADDER  -  BFS mini project"
_MENU_ITEMS = [
    "1. Play a game (vs computer / 2 humans)",
    "2. Solve a board: minimum dice throws  [BFS]",
    "3. Visualise the BFS exploration order",
    "4. BFS vs Dijkstra (heap) cross-check",
    "5. Generate a random board and solve it",
    "6. Render a board",
    "0. Exit",
]


def menu() -> str:
    width = max(len(_MENU_TITLE), *(len(i) for i in _MENU_ITEMS)) + 4
    rule = "+" + "-" * width + "+"
    print("\n" + rule)
    print(f"|{_MENU_TITLE:^{width}}|")
    print(rule)
    for item in _MENU_ITEMS:
        print(f"|  {item:<{width - 2}}|")
    print(rule)
    return input("Select: ").strip()


def choose_board() -> Board:
    print("\n  a) Classic 100-cell board")
    print("  b) Random board")
    print("  c) Enter my own snakes & ladders")
    choice = input("Board [a]: ").strip().lower() or "a"

    if choice == "b":
        size = ask_int("  Board size", 100, 6, 1000)
        ns = ask_int("  Number of snakes", max(1, size // 20), 0, size // 2)
        nl = ask_int("  Number of ladders", max(1, size // 20), 0, size // 2)
        seed = ask_int("  Random seed", 42, 0, 10_000_000)
        exact = input("  Exact finish required? (y/N): ").strip().lower() == "y"
        b = generate_board(size, ns, nl, exact_finish=exact, seed=seed)
    elif choice == "c":
        size = ask_int("  Board size", 100, 6, 1000)
        print("  Enter snakes as head:tail pairs, comma separated (blank for none)")
        snakes = _parse_pairs(input("  Snakes: ").strip())
        print("  Enter ladders as base:top pairs, comma separated (blank for none)")
        ladders = _parse_pairs(input("  Ladders: ").strip())
        b = Board(size, snakes, ladders)
    else:
        b = classic_board()
    print("\n" + b.summary())
    return b


def _parse_pairs(text: str) -> dict:
    out = {}
    if not text:
        return out
    for chunk in text.replace(";", ",").split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            a, b = chunk.split(":")
            out[int(a.strip())] = int(b.strip())
        except ValueError:
            raise BoardError(f"cannot parse '{chunk}' (expected form 12:34)")
    return out


# ----------------------------------------------------------------------
# Menu actions
# ----------------------------------------------------------------------
def action_play() -> None:
    board = choose_board()
    n = ask_int("  Number of players", 2, 1, 4)
    cpu = ask_int("  How many are computers", 1 if n > 1 else 0, 0, n)
    seed = ask_int("  Random seed (0 = true random)", 42, 0, 10_000_000)
    play_game(board, n_players=n, computer_players=cpu,
              seed=seed or None, delay=0.4 if cpu else 0.0)


def action_solve() -> None:
    board = choose_board()
    start = ask_int("  Start cell", board.start, 1, board.target)
    t0 = time.perf_counter()
    sol = solve(board, start)
    ms = (time.perf_counter() - t0) * 1000
    print("\n--- BFS result ---")
    print(sol.describe())
    print(f"(computed in {ms:.3f} ms)")


def action_visualise() -> None:
    board = choose_board()
    sol = solve(board)
    if not sol.reachable:
        print("Target unreachable.")
        return
    print(f"\nBFS visitation order ({len(sol.bfs_order)} nodes reached):")
    for i in range(0, len(sol.bfs_order), 15):
        chunk = sol.bfs_order[i:i + 15]
        print("  " + " -> ".join(f"{c:>4}" for c in chunk))
    print("\nEvery node sits at distance `dist` from the start, where")
    print("dist[node] = number of edges = number of dice throws.")
    print("The shortest path to the target is therefore "
          f"{sol.min_throws} throw(s).")


def action_cross_check() -> None:
    board = choose_board()
    sol = solve(board)

    t0 = time.perf_counter()
    dijk = solve_dijkstra(board)
    ms = (time.perf_counter() - t0) * 1000

    print("\n--- BFS  vs  Dijkstra (binary heap) ---")
    print(f"  BFS              : {sol.min_throws}")
    print(f"  Dijkstra + heapq : {dijk}")
    print("  -> both agree  ✓" if sol.min_throws == dijk else "  -> MISMATCH ✗")
    print(f"(Dijkstra ran in {ms:.3f} ms)")
    print("\nWhy they agree: every edge costs exactly 1 throw, so Dijkstra is a")
    print("weighted BFS. BFS exploits that with a FIFO queue -> O(V + E),")
    print("while Dijkstra needs a priority queue -> O((V + E) log V).")

    lo, hi = board.degree()
    print(f"\nGraph: V = {board.target} nodes, out-degree min/max = {lo}/{hi}")
    print(f"BFS explored {sol.nodes_explored} node(s) of {board.target} "
          f"({100 * sol.nodes_explored / board.target:.0f}%)")


def action_random() -> None:
    print("\nRandom board generator")
    size = ask_int("  Board size", 100, 6, 1000)
    ns = ask_int("  Number of snakes", max(1, size // 20), 0, size // 2)
    nl = ask_int("  Number of ladders", max(1, size // 20), 0, size // 2)
    seed = ask_int("  Random seed", 42, 0, 10_000_000)
    board = generate_board(size, ns, nl, seed=seed)
    sol = solve(board)
    print()
    print(board.render())
    print()
    print(sol.describe())
    print(f"Cross-check (Dijkstra): {solve_dijkstra(board)}")


def action_render() -> None:
    board = choose_board()
    print()
    print(board.render())
    print("\nLegend: 'S' = snake head, 'L' = ladder base")


ACTIONS = {
    "1": action_play,
    "2": action_solve,
    "3": action_visualise,
    "4": action_cross_check,
    "5": action_random,
    "6": action_render,
}


def main() -> int:
    if os.name == "nt":  # nicer Unicode output in the Windows console
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    while True:
        choice = menu()
        if choice == "0":
            print("Bye!")
            return 0
        action = ACTIONS.get(choice)
        if action is None:
            print("Unknown option.")
            continue
        try:
            action()
        except BoardError as exc:
            print(f"\n[board error] {exc}")
        except KeyboardInterrupt:
            print("\nAborted.")
            return 1
        except EOFError:
            print("\nBye!")
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
