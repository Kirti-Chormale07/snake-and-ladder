"""Interactive command-line Snake & Ladder game.

The interesting bit is that after every turn the BFS solver is re-run from the
player's current cell, so you can see the *theoretical* minimum number of
throws still needed — i.e. how lucky you need to be from here.
"""

from __future__ import annotations

import random
import time
from typing import Dict, List, Optional, Tuple

from .board import Board
from .solver import solve

PLAYER_COLORS = ("P1", "P2", "P3", "P4")


def roll_dice(board: Board, rng: random.Random) -> int:
    return rng.randint(1, board.dice_faces)


def apply_move(board: Board, cell: int, roll: int) -> Tuple[int, str]:
    """Advance ``cell`` by ``roll``; returns ``(new_cell, message)``."""
    if cell == board.target:
        return cell, ""

    target = board.target
    new_cell = cell + roll

    if new_cell > target:
        if board.exact_finish:
            return cell, f"rolled {roll} - would overshoot {target}, staying on {cell}"
        new_cell = target

    if new_cell == target:
        return target, f"rolled {roll} - raced to {target}!"

    jumped = board.jump(new_cell)
    if jumped == new_cell:
        return new_cell, f"rolled {roll} -> moved to {new_cell}"
    if jumped < new_cell:
        return jumped, f"rolled {roll} -> landed on {new_cell}, SNAKE down to {jumped}!"
    return jumped, f"rolled {roll} -> landed on {new_cell}, LADDER up to {jumped}!"


def play_game(
    board: Board,
    n_players: int = 2,
    computer_players: int = 0,
    seed: Optional[int] = None,
    show_board: bool = True,
    delay: float = 0.0,
) -> List[Dict]:
    """Run a full game. Returns a list of per-player result dictionaries."""
    rng = random.Random(seed)
    names = list(PLAYER_COLORS[:n_players])
    for i in range(computer_players):
        names[-(i + 1)] = f"CPU{i + 1}"

    positions: Dict[str, int] = {n: board.start for n in names}
    throws: Dict[str, int] = {n: 0 for n in names}
    finished: List[str] = []
    turn = 0

    print("\n" + "=" * 62)
    print(" SNAKE & LADDER  -  players:", ", ".join(names))
    print("=" * 62)
    print(board.summary())
    if show_board:
        print()
        print(board.render(positions))

    while len(finished) < len(names):
        name = names[turn % len(names)]
        turn += 1
        if name in finished:
            continue

        is_cpu = name.startswith("CPU")
        if is_cpu:
            if delay:
                time.sleep(delay)
            r = roll_dice(board, rng)
        else:
            input(f"\n>>> {name} (on {positions[name]}), press ENTER to roll... ")
            r = roll_dice(board, rng)

        throws[name] += 1
        old = positions[name]
        new, msg = apply_move(board, old, r)
        positions[name] = new
        print(f"    {name}: {msg}")

        if new == board.target:
            finished.append(name)
            print(f"    *** {name} finished in {throws[name]} throws! ***")
        else:
            # Re-run BFS from the new cell: how many throws are still possible?
            hint = solve(board, new)
            if hint.reachable:
                print(f"    [BFS] best case from {new}: {hint.min_throws} more throw(s)")

        if show_board:
            print()
            print(board.render(positions))

    print("\n" + "-" * 62)
    print("FINAL STANDINGS")
    board_best = solve(board, board.start)
    floor = board_best.min_throws if board_best.reachable else "?"
    for rank, name in enumerate(finished, start=1):
        tag = "winner" if rank == 1 else f"#{rank}"
        print(f"  {rank}. {name:<5} {throws[name]:>3} throws   "
              f"(board optimum: {floor}, you: {tag})")
    print("-" * 62)

    return [
        {"player": name, "position": positions[name], "throws": throws[name],
         "rank": i + 1}
        for i, name in enumerate(finished)
    ]
