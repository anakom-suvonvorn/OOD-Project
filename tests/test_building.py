"""Tests for adding / removing buildings and moving guests (owner: P3)."""
import random
import unittest

from hotel.errors import (
    DuplicateNodeError,
    InvalidInputError,
    LastNodeError,
    NodeNotFoundError,
)
from hotel.hotel_system import HotelSystem
from hotel.models import Move, MoveReport, RingPoint

# PDF section 9.1: ring of size 100, V = 1, A=20 B=50 C=80, D added at 35.
# Buildings A, B, C, D are node ids 1, 2, 3, 4. Guests are (1, 1) .. (1, 7).
A, B, C, D = 1, 2, 3, 4
EXAMPLE_POS = {"node:1:0": 20, "node:2:0": 50, "node:3:0": 80, "node:4:0": 35}
EXAMPLE_GUEST_POS = [10, 20, 25, 35, 50, 70, 90]
EXAMPLE_POS.update({f"guest:1:{i + 1}": p for i, p in enumerate(EXAMPLE_GUEST_POS)})
fake_hash = EXAMPLE_POS.__getitem__

# Expected building of guest (1, s) for each state of the PDF table.
START = {(1, 1): A, (1, 2): A, (1, 3): B, (1, 4): B, (1, 5): B, (1, 6): C, (1, 7): A}
AFTER_ADD_D = {(1, 1): A, (1, 2): A, (1, 3): D, (1, 4): D, (1, 5): B, (1, 6): C, (1, 7): A}
AFTER_REMOVE_B = {(1, 1): A, (1, 2): A, (1, 3): C, (1, 4): C, (1, 5): C, (1, 6): C, (1, 7): A}


def example_system() -> HotelSystem:
    return HotelSystem.initialize(3, 1, [7], hash_fn=fake_hash)


def real_system(n: int = 10, v: int = 8, per_channel: int = 300, salt: str = "") -> HotelSystem:
    """N buildings, 10 channels x per_channel guests, real SHA-256 positions."""
    return HotelSystem.initialize(n, v, [per_channel] * 10, salt=salt)


def addresses(system: HotelSystem) -> dict[tuple[int, int], tuple[int, int]]:
    """{(c, s): (node_id, room_no)} for every guest."""
    return {g.id: (g.node_id, g.room_no) for g in system.guests()}


def changed(before: dict, after: dict) -> dict[tuple[int, int], tuple[int, int]]:
    """Recheck-everyone oracle: {(c, s): (old_node, new_node)} for ids whose node differs."""
    return {gid: (before[gid], after[gid]) for gid in before if before[gid] != after[gid]}


def reported(report: MoveReport) -> dict[tuple[int, int], tuple[int, int]]:
    return {(m.c, m.s): (m.old_node, m.new_node) for m in report.moves}


# ---------------------------------------------------------------------------- PDF 9.1


class TestExampleRing(unittest.TestCase):
    """The ring of size 100 from PDF 9.1, run through HotelSystem."""

    def test_start_state(self):
        system = example_system()
        self.assertEqual(system.assignments(), START)
        system.verify_integrity()

    def test_add_d_moves_two_guests_into_d(self):
        system = example_system()
        rooms_before = {g.id: g.room_no for g in system.guests()}
        report = system.add_building(D)

        self.assertEqual(system.assignments(), AFTER_ADD_D)
        self.assertEqual(report.action, "add")
        self.assertEqual(report.node_id, D)
        self.assertEqual(report.total_guests, 7)
        self.assertEqual(report.moved_count, 2)
        self.assertAlmostEqual(report.move_rate, 2 / 7)
        self.assertEqual(
            report.moves,
            [Move(1, 3, B, D, rooms_before[(1, 3)]), Move(1, 4, B, D, rooms_before[(1, 4)])],
        )
        self.assertEqual({g.id: g.room_no for g in system.guests()}, rooms_before)
        system.verify_integrity()

    def test_remove_b_moves_three_guests_to_c(self):
        system = example_system()
        rooms_before = {g.id: g.room_no for g in system.guests()}
        report = system.remove_building(B)

        self.assertEqual(system.assignments(), AFTER_REMOVE_B)
        self.assertEqual(report.action, "remove")
        self.assertEqual(report.total_guests, 7)
        self.assertEqual(report.moved_count, 3)
        self.assertEqual(reported(report), {(1, 3): (B, C), (1, 4): (B, C), (1, 5): (B, C)})
        for m in report.moves:
            self.assertEqual(m.room_no, rooms_before[(m.c, m.s)])
        self.assertEqual({g.id: g.room_no for g in system.guests()}, rooms_before)
        system.verify_integrity()

    def test_wrap_around_guest_stays_in_a(self):
        system = example_system()
        system.add_building(D)
        self.assertEqual(system.find_guest(1, 7).node_id, A)  # position 90 wraps to A at 20

    def test_room_lookup_follows_the_move(self):
        """Consistency example: after a move, search by address finds the guest in the new building."""
        system = example_system()
        room = system.find_guest(1, 3).room_no
        self.assertEqual(system.find_by_room(B, room).id, (1, 3))
        system.add_building(D)
        self.assertEqual(system.find_by_room(D, room).id, (1, 3))
        with self.assertRaises(Exception):
            system.find_by_room(B, room)

    def test_add_then_remove_d_restores_start(self):
        system = example_system()
        system.add_building(D)
        report = system.remove_building(D)
        self.assertEqual(reported(report), {(1, 3): (D, B), (1, 4): (D, B)})
        self.assertEqual(system.assignments(), START)
        system.verify_integrity()


# ------------------------------------------------------------- PDF 9.2 item 5 (V > 1)


class TestMovesWithVirtualNodes(unittest.TestCase):
    """Real SHA-256 positions, V > 1, compared against recheck-everyone."""

    def check_add(self, system: HotelSystem, node_id: int) -> MoveReport:
        before_addr = addresses(system)
        before = system.assignments()
        report = system.add_building(node_id)
        after = system.assignments()

        self.assertEqual(reported(report), changed(before, after))  # bucket == recheck everyone
        self.assertEqual(len(after), len(before))  # nobody lost or added
        self.assertEqual(report.total_guests, len(before))
        self.assertEqual(report.moved_count, len(report.moves))
        self.assertEqual(len({(m.c, m.s) for m in report.moves}), report.moved_count)  # once each
        for m in report.moves:
            self.assertEqual(m.new_node, node_id)  # movers go ONLY into the new building
            self.assertEqual(before_addr[(m.c, m.s)], (m.old_node, m.room_no))
            self.assertEqual(system.find_guest(m.c, m.s).room_no, m.room_no)  # room unchanged
        system.verify_integrity()
        return report

    def check_remove(self, system: HotelSystem, node_id: int) -> MoveReport:
        before_addr = addresses(system)
        before = system.assignments()
        own_guests = {gid for gid, node in before.items() if node == node_id}
        report = system.remove_building(node_id)
        after = system.assignments()

        self.assertEqual(reported(report), changed(before, after))
        self.assertEqual(set(reported(report)), own_guests)  # exactly its guests, nobody else
        self.assertEqual(len(after), len(before))
        self.assertEqual(report.moved_count, len(report.moves))
        for m in report.moves:
            self.assertEqual(m.old_node, node_id)
            self.assertNotEqual(m.new_node, node_id)
            self.assertEqual(before_addr[(m.c, m.s)], (m.old_node, m.room_no))
        self.assertNotIn(node_id, system.node_ids())
        self.assertNotIn(node_id, system.load_stats().counts)
        system.verify_integrity()
        return report

    def test_add_building_v8(self):
        system = real_system(n=10, v=8)
        report = self.check_add(system, 11)
        self.assertGreater(report.moved_count, 0)

    def test_remove_building_v8(self):
        system = real_system(n=10, v=8)
        report = self.check_remove(system, 6)
        self.assertGreater(report.moved_count, 0)

    def test_many_salts_and_sizes(self):
        for salt in ("0", "1", "2"):
            for n, v in ((1, 4), (3, 1), (5, 8), (10, 32)):
                with self.subTest(salt=salt, n=n, v=v):
                    self.check_add(real_system(n=n, v=v, per_channel=100, salt=salt), n + 1)
                    if n > 1:
                        self.check_remove(real_system(n=n, v=v, per_channel=100, salt=salt), n // 2 + 1)

    def test_random_sequence_of_operations(self):
        """Random adds/removes of buildings mixed with guest changes, checked after every step."""
        for seed in range(5):
            rng = random.Random(seed)
            system = real_system(n=4, v=8, per_channel=50, salt=str(seed))
            next_id = 5
            for _ in range(25):
                action = rng.choice(["add", "remove", "guests"])
                if action == "add":
                    self.check_add(system, next_id)
                    next_id += 1
                elif action == "remove" and len(system.node_ids()) > 1:
                    self.check_remove(system, rng.choice(system.node_ids()))
                else:
                    c = rng.randint(1, 12)
                    s = rng.randint(1, 80)
                    if (c, s) in system.store:
                        system.remove_guest(c, s)
                    else:
                        system.add_guest(c, s)
                    system.verify_integrity()

    def test_non_consecutive_building_id(self):
        system = real_system(n=3, v=8, per_channel=50)
        self.check_add(system, 100)
        self.check_remove(system, 2)
        self.assertEqual(system.node_ids(), [1, 3, 100])

    def test_move_count_is_about_k_over_n(self):
        """Not exact (it is an expected value), but should be the right order of magnitude."""
        system = real_system(n=10, v=32, per_channel=1000)  # K = 10,000
        k = system.guest_count
        moved = self.check_add(system.clone(), 11).moved_count
        self.assertTrue(k / 11 / 3 < moved < k / 11 * 3, moved)
        moved = self.check_remove(system.clone(), 6).moved_count
        self.assertTrue(k / 10 / 3 < moved < k / 10 * 3, moved)


# ------------------------------------------------------------------ ties (PDF 4.3 rule 4)


class TestTies(unittest.TestCase):
    def test_new_point_on_same_position_as_old_point(self):
        """New building 1 lands on 50, where building 3 already is. Key (pos, node_id, j) puts
        the new point first, so it takes the guests at 45 and exactly at 50."""
        pos = {"node:2:0": 20, "node:3:0": 50, "node:4:0": 80, "node:1:0": 50}
        guest_pos = [10, 45, 50, 60]
        pos.update({f"guest:1:{i + 1}": p for i, p in enumerate(guest_pos)})
        system = HotelSystem(1, hash_fn=pos.__getitem__)
        system.ring.build([2, 3, 4])
        system.add_guests(1, 1, 4)

        before = system.assignments()
        report = system.add_building(1)  # RingPoint(50, 1, 0) < RingPoint(50, 3, 0)
        self.assertEqual(reported(report), {(1, 2): (3, 1), (1, 3): (3, 1)})
        self.assertEqual(reported(report), changed(before, system.assignments()))
        system.verify_integrity()

    def test_new_point_tied_but_sorted_after_old_point(self):
        """Same position but larger node id -> sorts after the old point and takes nothing there."""
        pos = {"node:1:0": 20, "node:2:0": 50, "node:3:0": 80, "node:9:0": 50}
        guest_pos = [10, 45, 50, 60]
        pos.update({f"guest:1:{i + 1}": p for i, p in enumerate(guest_pos)})
        system = HotelSystem.initialize(3, 1, [4], hash_fn=pos.__getitem__)
        report = system.add_building(9)
        self.assertEqual(report.moved_count, 0)
        system.verify_integrity()

    def test_adjacent_new_points(self):
        """Two new points next to each other: both take guests from the same old point."""
        pos = {"node:1:0": 20, "node:1:1": 90, "node:2:0": 60, "node:2:1": 70,
               "node:3:0": 30, "node:3:1": 40}
        guest_pos = [25, 35, 45, 65, 75, 95]
        pos.update({f"guest:1:{i + 1}": p for i, p in enumerate(guest_pos)})
        system = HotelSystem.initialize(2, 2, [6], hash_fn=pos.__getitem__)
        # Before: 25,35,45 -> 60 (node 2); 65 -> 70 (node 2); 75 -> 90 (node 1); 95 -> 20 (node 1)
        before = system.assignments()
        report = system.add_building(3)
        self.assertEqual(reported(report), {(1, 1): (2, 3), (1, 2): (2, 3)})
        self.assertEqual(reported(report), changed(before, system.assignments()))
        system.verify_integrity()


# ------------------------------------------------------------- PDF 4.5 edge cases


class TestBuildingEdgeCases(unittest.TestCase):
    def assert_unchanged(self, system: HotelSystem, before: dict, nodes: list[int]) -> None:
        self.assertEqual(addresses(system), before)
        self.assertEqual(system.node_ids(), nodes)
        self.assertEqual(len(system.ring), len(nodes) * system.V)
        system.verify_integrity()

    def test_add_existing_building(self):
        system = real_system(n=3, v=4, per_channel=20)
        before, nodes = addresses(system), system.node_ids()
        with self.assertRaises(DuplicateNodeError):
            system.add_building(2)
        self.assert_unchanged(system, before, nodes)

    def test_remove_missing_building(self):
        system = real_system(n=3, v=4, per_channel=20)
        before, nodes = addresses(system), system.node_ids()
        with self.assertRaises(NodeNotFoundError):
            system.remove_building(99)
        self.assert_unchanged(system, before, nodes)

    def test_remove_last_building(self):
        system = real_system(n=1, v=4, per_channel=20)
        before, nodes = addresses(system), system.node_ids()
        with self.assertRaises(LastNodeError):
            system.remove_building(1)
        self.assert_unchanged(system, before, nodes)

    def test_remove_last_building_without_guests(self):
        system = HotelSystem.initialize(1, 4, [])
        with self.assertRaises(LastNodeError):
            system.remove_building(1)
        self.assertEqual(system.node_ids(), [1])

    def test_remove_down_to_one_then_last_fails(self):
        system = real_system(n=3, v=4, per_channel=20)
        system.remove_building(1)
        system.remove_building(3)
        self.assertEqual(system.node_ids(), [2])
        self.assertEqual(system.load_stats().counts, {2: system.guest_count})
        with self.assertRaises(LastNodeError):
            system.remove_building(2)
        system.verify_integrity()

    def test_bad_building_ids(self):
        system = real_system(n=3, v=4, per_channel=20)
        before, nodes = addresses(system), system.node_ids()
        for bad in (0, -1, "4", 4.0, None, True):
            with self.subTest(bad=bad):
                with self.assertRaises(InvalidInputError):
                    system.add_building(bad)
                with self.assertRaises(InvalidInputError):
                    system.remove_building(bad)
        self.assert_unchanged(system, before, nodes)

    def test_no_guests(self):
        system = HotelSystem.initialize(3, 4, [])
        report = system.add_building(4)
        self.assertEqual((report.moved_count, report.total_guests, report.move_rate), (0, 0, None))
        report = system.remove_building(1)
        self.assertEqual((report.moved_count, report.move_rate), (0, None))
        self.assertEqual(system.node_ids(), [2, 3, 4])
        system.verify_integrity()

    def test_add_to_empty_hotel(self):
        """HotelSystem(V) without initialize has no buildings; the first add must not loop forever."""
        system = HotelSystem(4)
        report = system.add_building(1)
        self.assertEqual(report.moved_count, 0)
        self.assertEqual(system.node_ids(), [1])
        system.add_guests(1, 1, 10)
        self.assertEqual(system.load_stats().counts, {1: 10})
        system.verify_integrity()

    def test_new_building_with_zero_guests_shows_in_stats(self):
        pos = {"node:1:0": 20, "node:2:0": 50, "node:3:0": 80, "node:4:0": 85, "guest:1:1": 10}
        system = HotelSystem.initialize(3, 1, [1], hash_fn=pos.__getitem__)
        report = system.add_building(4)
        self.assertEqual(report.moved_count, 0)
        self.assertEqual(system.load_stats().counts[4], 0)


# ----------------------------------------------------------- compute_node / assignments


class TestHelpers(unittest.TestCase):
    def test_compute_node_matches_stored_node(self):
        system = real_system(n=5, v=8, per_channel=50)
        for g in system.guests():
            self.assertEqual(system.compute_node(g.c, g.s), g.node_id)

    def test_compute_node_uses_current_ring(self):
        system = example_system()
        self.assertEqual(system.compute_node(1, 3), B)
        system.add_building(D)
        self.assertEqual(system.compute_node(1, 3), D)

    def test_compute_node_for_guest_not_staying(self):
        system = example_system()
        system.remove_guest(1, 3)
        self.assertEqual(system.compute_node(1, 3), B)

    def test_compute_node_bad_input(self):
        system = example_system()
        with self.assertRaises(InvalidInputError):
            system.compute_node(0, 1)

    def test_assignments_is_a_snapshot(self):
        system = example_system()
        snap = system.assignments()
        system.add_building(D)
        self.assertEqual(snap, START)

    def test_verify_integrity_detects_broken_index(self):
        system = example_system()
        guest = system.find_guest(1, 3)
        del system.store.room_index[(guest.node_id, guest.room_no)]
        with self.assertRaises(AssertionError):
            system.verify_integrity()

    def test_verify_integrity_detects_wrong_owner(self):
        system = example_system()
        guest = system.find_guest(1, 3)
        guest.point = RingPoint(80, C, 0)  # bypasses GuestStore.move on purpose
        with self.assertRaises(AssertionError):
            system.verify_integrity()

    def test_clone_is_independent(self):
        system = real_system(n=5, v=8, per_channel=50)
        before = system.assignments()
        copy = system.clone()
        copy.add_building(6)
        copy.remove_building(1)
        self.assertEqual(system.assignments(), before)
        self.assertEqual(system.node_ids(), [1, 2, 3, 4, 5])
        system.verify_integrity()
        copy.verify_integrity()


if __name__ == "__main__":
    unittest.main()