"""Tests for the experiment helpers (owner: P4). Small sizes only, so they run fast."""
import unittest

from experiments.run_experiments import (
    _mod_n_change,
    benchmark_system,
    channel_sizes,
    compare_with_mod_n,
)
from hotel import HotelSystem
from hotel.errors import DuplicateNodeError
from hotel.mod_n import ModNRouter


def by_metric(rows: list[dict], method: str) -> dict:
    return {r["metric"]: r["value"] for r in rows if r["method"] == method}


class ChannelSizeTests(unittest.TestCase):
    def test_even_split(self):
        self.assertEqual(channel_sizes(1000), [100] * 10)

    def test_remainder_goes_to_first_channels(self):
        sizes = channel_sizes(1003)
        self.assertEqual(sum(sizes), 1003)
        self.assertEqual(sizes[:3], [101] * 3)
        self.assertEqual(max(sizes) - min(sizes), 1)


class ModNComparisonTests(unittest.TestCase):
    def setUp(self):
        self.system = HotelSystem.initialize(5, 8, channel_sizes(2000), salt="0")

    def expected_mod_n_moves(self, action: str, node_id: int) -> int:
        router = ModNRouter()
        router.build(self.system.node_ids())
        before = {g.id: router.node_for(g.pos) for g in self.system.guests()}
        router.add_node(node_id) if action == "add" else router.remove_node(node_id)
        return sum(before[g.id] != router.node_for(g.pos) for g in self.system.guests())

    def test_remove_uses_the_real_target_building(self):
        # Removing building 3 must differ from "removing the last building" (pos % (N-1) + 1).
        moved, _ = _mod_n_change(self.system, "remove", 3)
        self.assertEqual(moved, self.expected_mod_n_moves("remove", 3))
        last_style = sum((g.pos % 5) + 1 != (g.pos % 4) + 1 for g in self.system.guests())
        self.assertNotEqual(moved, last_style)

    def test_add_matches_router(self):
        moved, _ = _mod_n_change(self.system, "add", 6)
        self.assertEqual(moved, self.expected_mod_n_moves("add", 6))

    def test_building_order_is_used(self):
        system = HotelSystem.initialize(5, 1, [1], hash_fn=lambda _key: 5)
        system.add_building(7)
        system.add_building(6)
        order = [1, 2, 3, 4, 5, 7, 6]
        router = ModNRouter()
        router.build(order)
        positions = [guest.pos for guest in system.guests()]
        before = [router.node_for(pos) for pos in positions]
        # Removing 6 changes a different index in the two orders.
        router.remove_node(6)
        expected = sum(old != router.node_for(pos) for old, pos in zip(before, positions))

        moved, _ = _mod_n_change(system, "remove", 6, building_order=order)
        sorted_moves, _ = _mod_n_change(system, "remove", 6)
        rows = compare_with_mod_n(system, "remove", 6, building_order=order)

        self.assertEqual(moved, expected)
        self.assertNotEqual(moved, sorted_moves)
        self.assertEqual(by_metric(rows, "mod_n")["moves_remove"], expected)

    def test_building_order_must_match(self):
        for order in ([1, 2, 3], [1, 2, 3, 4, 6], [1, 2, 3, 4, 5, 5]):
            with self.subTest(order=order):
                with self.assertRaisesRegex(
                    ValueError, "building_order must contain exactly the current buildings"
                ):
                    _mod_n_change(self.system, "remove", 3, building_order=order)

    def test_compare_does_not_change_the_system(self):
        before = self.system.assignments()
        for action, node_id in (("add", 6), ("remove", 3)):
            rows = compare_with_mod_n(self.system, action, node_id)
            ch, mod = by_metric(rows, "consistent"), by_metric(rows, "mod_n")
            self.assertEqual(mod["moves_" + action], self.expected_mod_n_moves(action, node_id))
            self.assertAlmostEqual(ch["move_rate_" + action], ch["moves_" + action] / 2000)
            self.assertLess(ch["moves_" + action], mod["moves_" + action])
        self.assertEqual(self.system.assignments(), before)
        self.assertEqual(self.system.node_ids(), [1, 2, 3, 4, 5])
        self.system.verify_integrity()

    def test_invalid_change_raises_hotel_error(self):
        with self.assertRaises(DuplicateNodeError):
            compare_with_mod_n(self.system, "add", 2)

    def test_no_guests_gives_no_rate(self):
        empty = HotelSystem.initialize(3, 4, [0])
        rows = compare_with_mod_n(empty, "add", 4)
        for method in ("consistent", "mod_n"):
            self.assertIsNone(by_metric(rows, method)["move_rate_add"])
            self.assertEqual(by_metric(rows, method)["moves_add"], 0)


class BenchmarkTests(unittest.TestCase):
    def test_runs_and_does_not_change_the_system(self):
        system = HotelSystem.initialize(3, 4, [50, 50])
        before = system.assignments()
        rows = benchmark_system(system)
        metrics = {r["metric"] for r in rows}
        self.assertTrue({"time_search_guest", "time_search_room", "time_list_rooms",
                         "memory_current", "memory_peak"} <= metrics)
        self.assertTrue(all(r["K"] == 100 and r["N"] == 3 and r["V"] == 4 for r in rows))
        self.assertEqual(system.assignments(), before)

    def test_empty_hotel(self):
        rows = benchmark_system(HotelSystem.initialize(2, 2, [0]))
        self.assertEqual({r["metric"]: r["value"] for r in rows}["time_search_guest"], 0.0)


if __name__ == "__main__":
    unittest.main()
