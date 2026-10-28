"""Unit tests for the Snake & Ladder BFS solver.

Run with:  python -m unittest discover -s tests -v
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from snake_ladder import Board, BoardError, generate_board, solve, solve_dijkstra
from snake_ladder.game import apply_move

CLASSIC_SNAKES = {16: 6, 47: 26, 49: 11, 56: 53, 62: 19,
                  64: 60, 87: 24, 93: 73, 95: 75, 98: 78}
CLASSIC_LADDERS = {1: 38, 4: 14, 9: 31, 21: 42, 28: 84,
                   36: 44, 51: 67, 71: 91, 80: 100}


class TestBoardValidation(unittest.TestCase):
    def test_valid_classic_board(self):
        Board(100, CLASSIC_SNAKES, CLASSIC_LADDERS)  # should not raise

    def test_snake_must_go_down(self):
        with self.assertRaises(BoardError):
            Board(100, snakes={50: 60})

    def test_ladder_must_go_up(self):
        with self.assertRaises(BoardError):
            Board(100, ladders={50: 40})

    def test_out_of_range(self):
        with self.assertRaises(BoardError):
            Board(100, snakes={200: 10})
        with self.assertRaises(BoardError):
            Board(100, ladders={5: 1000})

    def test_duplicate_base(self):
        with self.assertRaises(BoardError):
            Board(100, snakes={50: 20}, ladders={50: 80})

    def test_final_cell_cannot_be_a_base(self):
        with self.assertRaises(BoardError):
            Board(100, snakes={100: 5})

    def test_cycle_detected(self):
        with self.assertRaises(BoardError):
            Board(100, snakes={8: 4}, ladders={4: 8})

    def test_chain_is_allowed_when_acyclic(self):
        # 10 -> ladder -> 40 -> snake -> 20 : legal, just two hops
        b = Board(100, snakes={40: 20}, ladders={10: 40})
        self.assertEqual(b.jump(10), 20)


class TestGraphConstruction(unittest.TestCase):
    def test_edges_are_forward_or_snake_induced(self):
        b = Board(100, CLASSIC_SNAKES, CLASSIC_LADDERS)
        for u, edges in b.moves().items():
            for _, v in edges:
                if v <= u:
                    # A move can only go backwards by sliding down a snake,
                    # and the snake's head is always above u (you rolled up
                    # onto it from u).
                    self.assertTrue(
                        any(head > u and tail == v
                            for head, tail in b.snakes.items()),
                        f"edge {u}->{v} has no snake to explain it",
                    )

    def test_every_edge_costs_exactly_one_roll(self):
        b = Board(100, CLASSIC_SNAKES, CLASSIC_LADDERS)
        for u in range(1, b.target):
            edges = b.moves()[u]
            self.assertTrue(edges, f"cell {u} has no outgoing edge")
            for roll, _ in edges:
                self.assertTrue(1 <= roll <= 6)
        self.assertEqual(b.moves()[b.target], [])  # game is over at the finish

    def test_overshoot_reaches_target_by_default(self):
        b = Board(100, CLASSIC_SNAKES, CLASSIC_LADDERS)
        # 98 + 6 = 104 > 100, but overshoot counts as a win by default.
        dests = [v for _, v in b.moves()[98]]
        self.assertIn(100, dests)

    def test_exact_finish_blocks_overshoot(self):
        b = Board(100, exact_finish=True)
        moves97 = dict(b.moves()[97])
        # 97 + 6 = 103 is an illegal roll, so face 6 must not appear at all.
        self.assertNotIn(6, moves97)
        # The only legal way to finish from 97 is rolling exactly 3.
        self.assertEqual(moves97.get(3), 100)

    def test_out_degrees(self):
        b = Board(100, CLASSIC_SNAKES, CLASSIC_LADDERS)
        lo, hi = b.degree()
        self.assertLessEqual(hi, 6)          # never more edges than dice faces
        self.assertEqual(lo, 0)              # only the finish has out-degree 0
        # every playable cell can still move somewhere
        for u in range(1, b.target):
            self.assertGreaterEqual(len(b.moves()[u]), 1)


class TestBFSSolver(unittest.TestCase):
    def test_empty_board_is_linear(self):
        # With no snakes/ladders the optimum is ceil((size-1)/dice)
        b = Board(100)
        sol = solve(b)
        self.assertTrue(sol.reachable)
        self.assertEqual(sol.min_throws, 17)  # 99 cells / 6 = 16.5 -> 17
        self.assertEqual(sol.path[0], 1)
        self.assertEqual(sol.path[-1], 100)

    def test_path_is_valid_moves(self):
        b = Board(100, CLASSIC_SNAKES, CLASSIC_LADDERS)
        sol = solve(b)
        moves = b.moves()
        for a, c in zip(sol.path, sol.path[1:]):
            self.assertIn(c, [v for _, v in moves[a]],
                          f"no legal move {a} -> {c}")

    def test_rolls_match_path(self):
        b = Board(100, CLASSIC_SNAKES, CLASSIC_LADDERS)
        sol = solve(b)
        self.assertEqual(len(sol.rolls), len(sol.path) - 1)
        for roll in sol.rolls:
            self.assertTrue(1 <= roll <= 6)

    def test_ladder_shortens_the_path(self):
        with_lad = Board(100, ladders={2: 99})
        without = Board(100)
        self.assertLess(solve(with_lad).min_throws, solve(without).min_throws)

    def test_snake_lengthens_the_path(self):
        # 13 cells, no obstacles: 1 -6-> 7 -6-> 13  => 2 throws.
        plain = Board(13)
        self.assertEqual(solve(plain).min_throws, 2)
        # Put a snake on cell 7 so the straight shot is blocked.
        with_snk = Board(13, snakes={7: 2})
        self.assertEqual(solve(with_snk).min_throws, 3)
        self.assertGreater(solve(with_snk).min_throws, solve(plain).min_throws)

    def test_solution_from_mid_board(self):
        b = Board(100, CLASSIC_SNAKES, CLASSIC_LADDERS)
        sol = solve(b, start=95)   # 95 is a snake head
        self.assertTrue(sol.reachable)
        self.assertEqual(sol.path[0], 95)

    def test_start_equals_target(self):
        b = Board(50)
        sol = solve(b, start=50)
        self.assertEqual(sol.min_throws, 0)
        self.assertEqual(sol.path, [50])

    def test_invalid_start_rejected(self):
        b = Board(50)
        with self.assertRaises(ValueError):
            solve(b, start=0)
        with self.assertRaises(ValueError):
            solve(b, start=51)

    def test_classic_board_optimum(self):
        b = Board(100, CLASSIC_SNAKES, CLASSIC_LADDERS)
        sol = solve(b)
        self.assertEqual(sol.min_throws, 7)

    def test_levels_are_consistent(self):
        b = Board(100, CLASSIC_SNAKES, CLASSIC_LADDERS)
        sol = solve(b)
        lv = sol.levels
        self.assertEqual(sol.min_throws, lv[b.target])

        # 1. BFS visits nodes in non-decreasing order of their level.
        self.assertEqual(sol.bfs_order,
                         sorted(sol.bfs_order, key=lambda n: lv[n]))

        # 2. One edge can never shorten the distance by more than 1.
        for u, edges in b.moves().items():
            if u not in lv:
                continue
            for _, v in edges:
                if v in lv:
                    self.assertLessEqual(
                        lv[v], lv[u] + 1,
                        f"edge {u}->{v} skips a BFS level",
                    )

    def test_levels_are_tight(self):
        """Each level is *reachable*: a predecessor sits exactly one above.

        Combined with the "relaxes by at most 1" property checked above, this
        proves ``levels`` is the least solution of  d[start]=0,
        d[v] <= d[u] + 1  -- i.e. the true shortest distance in edges.
        """
        b = Board(100, CLASSIC_SNAKES, CLASSIC_LADDERS)
        sol = solve(b)
        lv = sol.levels
        incoming = {}
        for u, edges in b.moves().items():
            for _, v in edges:
                incoming.setdefault(v, []).append(u)

        self.assertEqual(lv[b.start], 0)
        for node, d in lv.items():
            if d == 0:
                continue
            preds = incoming.get(node, [])
            self.assertTrue(
                any(p in lv and lv[p] == d - 1 for p in preds),
                f"node {node} at level {d} has no predecessor at level {d - 1}",
            )


class TestBFSvsDijkstra(unittest.TestCase):
    def test_agree_on_empty_boards(self):
        for size in (10, 25, 60, 100, 144):
            b = Board(size)
            self.assertEqual(solve(b).min_throws, solve_dijkstra(b), f"size={size}")

    def test_agree_on_classic_board(self):
        b = Board(100, CLASSIC_SNAKES, CLASSIC_LADDERS)
        self.assertEqual(solve(b).min_throws, solve_dijkstra(b))

    def test_agree_on_many_random_boards(self):
        for seed in range(25):
            b = generate_board(seed=seed)
            self.assertEqual(solve(b).min_throws, solve_dijkstra(b), f"seed={seed}")

    def test_random_boards_are_always_solvable(self):
        for seed in range(25):
            b = generate_board(seed=seed)
            self.assertTrue(solve(b).reachable, f"seed={seed}")


class TestGameLogic(unittest.TestCase):
    def test_simple_move(self):
        b = Board(100)
        cell, msg = apply_move(b, 10, 4)
        self.assertEqual(cell, 14)
        self.assertIn("moved to 14", msg)

    def test_ladder_message(self):
        b = Board(100, ladders={4: 14})
        cell, msg = apply_move(b, 1, 3)
        self.assertEqual(cell, 14)
        self.assertIn("LADDER", msg)

    def test_snake_message(self):
        b = Board(100, snakes={16: 6})
        cell, msg = apply_move(b, 12, 4)
        self.assertEqual(cell, 6)
        self.assertIn("SNAKE", msg)

    def test_overshoot_counts_as_win(self):
        b = Board(100)
        cell, _ = apply_move(b, 97, 6)
        self.assertEqual(cell, 100)

    def test_exact_finish_stays_put(self):
        b = Board(100, exact_finish=True)
        cell, msg = apply_move(b, 97, 6)
        self.assertEqual(cell, 97)
        self.assertIn("overshoot", msg)


class TestRendering(unittest.TestCase):
    def test_render_contains_every_cell(self):
        b = Board(100, CLASSIC_SNAKES, CLASSIC_LADDERS)
        out = b.render()
        for n in range(1, 101):
            self.assertIn(str(n), out)

    def test_render_marks_snakes_and_ladders(self):
        b = Board(100, snakes={16: 6}, ladders={4: 14})
        out = b.render()
        self.assertIn("16S", out.replace(" ", ""))
        self.assertIn("4L", out.replace(" ", ""))


if __name__ == "__main__":
    unittest.main(verbosity=2)
