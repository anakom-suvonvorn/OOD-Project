"""Tests for hashing.py and ring.py (owner: P1)."""
import os
import subprocess
import sys
import unittest

from hotel.errors import (
    DuplicateNodeError,
    EmptyRingError,
    InvalidInputError,
    LastNodeError,
    NodeNotFoundError,
)
from hotel.hashing import RING_SIZE, guest_key, hash64, node_key
from hotel.models import RingPoint
from hotel.ring import HashRing

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# PDF section 9.1: ring of size 100, V = 1, A=20 B=50 C=80, D added at 35.
# Buildings A, B, C, D are node ids 1, 2, 3, 4.
EXAMPLE_POS = {"node:1:0": 20, "node:2:0": 50, "node:3:0": 80, "node:4:0": 35}
EXAMPLE_GUESTS = [10, 20, 25, 35, 50, 70, 90]


def example_ring() -> HashRing:
    ring = HashRing(1, hash_fn=EXAMPLE_POS.__getitem__)
    ring.build([1, 2, 3])
    return ring


def real_ring(n: int = 10, v: int = 32, salt: str = "") -> HashRing:
    ring = HashRing(v, salt)
    ring.build(range(1, n + 1))
    return ring


def guest_positions(k: int = 2000) -> list[int]:
    return [hash64(guest_key(c, s)) for c in range(1, 11) for s in range(1, k // 10 + 1)]


class HashingTests(unittest.TestCase):
    def test_key_formats(self):
        self.assertEqual(guest_key(1, 2), "guest:1:2")
        self.assertEqual(node_key(3, 0), "node:3:0")
        self.assertEqual(guest_key(1, 2, "0"), "0|guest:1:2")
        self.assertEqual(node_key(3, 0, "1"), "1|node:3:0")

    def test_known_values(self):
        # First 8 bytes of SHA-256, big-endian. If these change, every saved result is invalid.
        self.assertEqual(hash64("guest:1:1"), 3062031282815716176)
        self.assertEqual(hash64("node:1:0"), 3505680375118999729)
        self.assertEqual(hash64("0|guest:1:1"), 3912152983899886038)

    def test_range(self):
        for text in ["", "guest:1:1", "node:99:31", "ภาษาไทย"]:
            self.assertTrue(0 <= hash64(text) < RING_SIZE)

    def test_same_value_in_a_new_python_process(self):
        # Python's hash() would differ here because PYTHONHASHSEED changes it per process.
        code = "from hotel.hashing import hash64; print(hash64('guest:7:3'))"
        env = dict(os.environ, PYTHONHASHSEED="12345")
        out = subprocess.run(
            [sys.executable, "-c", code], cwd=PROJECT_DIR, env=env,
            capture_output=True, text=True, check=True,
        )
        self.assertEqual(int(out.stdout), hash64("guest:7:3"))

    def test_salt_changes_position(self):
        self.assertNotEqual(hash64(guest_key(1, 1)), hash64(guest_key(1, 1, "1")))


class ExampleRingTests(unittest.TestCase):
    """The worked example of PDF section 9.1."""

    def test_initial(self):
        ring = example_ring()
        self.assertEqual([ring.node_for(p) for p in EXAMPLE_GUESTS], [1, 1, 2, 2, 2, 3, 1])

    def test_add_d(self):
        ring = example_ring()
        before = [ring.node_for(p) for p in EXAMPLE_GUESTS]
        ring.add_node(4)
        after = [ring.node_for(p) for p in EXAMPLE_GUESTS]
        self.assertEqual(after, [1, 1, 4, 4, 2, 3, 1])
        moved = [(b, a) for b, a in zip(before, after) if b != a]
        self.assertEqual(len(moved), 2)
        self.assertTrue(all(a == 4 for _, a in moved))

    def test_remove_b(self):
        ring = example_ring()
        before = [ring.node_for(p) for p in EXAMPLE_GUESTS]
        ring.remove_node(2)
        after = [ring.node_for(p) for p in EXAMPLE_GUESTS]
        self.assertEqual(after, [1, 1, 3, 3, 3, 3, 1])
        moved = [(b, a) for b, a in zip(before, after) if b != a]
        self.assertEqual(len(moved), 3)
        self.assertTrue(all(b == 2 for b, _ in moved))


class LookupTests(unittest.TestCase):
    def test_exactly_on_a_point(self):
        self.assertEqual(example_ring().lookup(50), RingPoint(50, 2, 0))

    def test_between_points(self):
        self.assertEqual(example_ring().lookup(51), RingPoint(80, 3, 0))

    def test_before_first_point(self):
        self.assertEqual(example_ring().lookup(0), RingPoint(20, 1, 0))

    def test_after_last_point_wraps(self):
        ring = example_ring()
        self.assertEqual(ring.lookup(81), RingPoint(20, 1, 0))
        self.assertEqual(ring.lookup(RING_SIZE - 1), RingPoint(20, 1, 0))

    def test_collision_between_buildings(self):
        pos = {"node:2:0": 50, "node:1:0": 50, "node:3:0": 80}
        ring = HashRing(1, hash_fn=pos.__getitem__)
        ring.build([3, 2, 1])
        self.assertEqual(ring.points(), [RingPoint(50, 1, 0), RingPoint(50, 2, 0), RingPoint(80, 3, 0)])
        self.assertEqual(ring.lookup(50), RingPoint(50, 1, 0))
        self.assertEqual(ring.lookup(30), RingPoint(50, 1, 0))
        self.assertEqual(ring.successor(RingPoint(50, 1, 0)), RingPoint(50, 2, 0))

    def test_collision_within_a_building(self):
        pos = {"node:1:0": 50, "node:1:1": 50, "node:2:0": 10, "node:2:1": 90}
        ring = HashRing(2, hash_fn=pos.__getitem__)
        ring.build([1, 2])
        self.assertEqual(ring.lookup(50), RingPoint(50, 1, 0))
        self.assertEqual(len(ring), 4)

    def test_collision_added_later(self):
        pos = {"node:5:0": 50, "node:2:0": 50, "node:3:0": 80}
        ring = HashRing(1, hash_fn=pos.__getitem__)
        ring.build([5, 3])
        ring.add_node(2)
        self.assertEqual(ring.lookup(50), RingPoint(50, 2, 0))

    def test_empty_ring(self):
        ring = HashRing(4)
        with self.assertRaises(EmptyRingError):
            ring.lookup(10)
        with self.assertRaises(EmptyRingError):
            ring.node_for(10)

    def test_lookup_matches_linear_scan(self):
        ring = real_ring()
        points = ring.points()
        for pos in guest_positions(500):
            expected = next((p for p in points if p.pos >= pos), points[0])
            self.assertEqual(ring.lookup(pos), expected)


class SuccessorTests(unittest.TestCase):
    def test_next_and_wrap(self):
        ring = example_ring()
        self.assertEqual(ring.successor(RingPoint(20, 1, 0)), RingPoint(50, 2, 0))
        self.assertEqual(ring.successor(RingPoint(80, 3, 0)), RingPoint(20, 1, 0))

    def test_single_point(self):
        ring = HashRing(1, hash_fn={"node:1:0": 5}.__getitem__)
        ring.build([1])
        self.assertEqual(ring.successor(RingPoint(5, 1, 0)), RingPoint(5, 1, 0))

    def test_point_not_on_ring(self):
        with self.assertRaises(ValueError):
            example_ring().successor(RingPoint(21, 1, 0))


class BuildAndChangeTests(unittest.TestCase):
    def test_build_sizes_and_order(self):
        ring = real_ring(10, 32)
        self.assertEqual(len(ring), 320)
        self.assertEqual(ring.node_count, 10)
        self.assertEqual(ring.node_ids(), list(range(1, 11)))
        points = ring.points()
        self.assertEqual(points, sorted(points))

    def test_build_twice_rejected(self):
        ring = real_ring(3, 4)
        with self.assertRaises(InvalidInputError):
            ring.build([7])

    def test_add_keeps_existing_points(self):
        ring = real_ring(10, 32)
        before = ring.points()
        new = ring.add_node(11)
        after = ring.points()
        self.assertEqual(len(new), 32)
        self.assertTrue(all(p.node_id == 11 for p in new))
        self.assertEqual(after, sorted(before + new))
        self.assertEqual(len(ring), 352)

    def test_remove_keeps_other_points(self):
        ring = real_ring(10, 32)
        before = ring.points()
        removed = ring.remove_node(4)
        self.assertEqual(len(removed), 32)
        self.assertTrue(all(p.node_id == 4 for p in removed))
        self.assertEqual(ring.points(), [p for p in before if p.node_id != 4])
        self.assertFalse(ring.has_node(4))

    def test_add_then_remove_restores_ring(self):
        ring = real_ring(5, 8)
        before = ring.points()
        ring.add_node(6)
        ring.remove_node(6)
        self.assertEqual(ring.points(), before)

    def test_add_moves_guests_only_to_new_building(self):
        ring = real_ring(10, 32)
        positions = guest_positions()
        before = [ring.node_for(p) for p in positions]
        ring.add_node(11)
        after = [ring.node_for(p) for p in positions]
        moved = [(b, a) for b, a in zip(before, after) if b != a]
        self.assertTrue(moved)
        self.assertTrue(all(a == 11 for _, a in moved))

    def test_remove_moves_only_guests_of_removed_building(self):
        ring = real_ring(10, 32)
        positions = guest_positions()
        before = [ring.node_for(p) for p in positions]
        ring.remove_node(4)
        after = [ring.node_for(p) for p in positions]
        for b, a in zip(before, after):
            if b == 4:
                self.assertNotEqual(a, 4)
            else:
                self.assertEqual(a, b)

    def test_salt_gives_different_ring(self):
        self.assertNotEqual(real_ring(3, 4).points(), real_ring(3, 4, salt="1").points())

    def test_same_salt_gives_same_ring(self):
        self.assertEqual(real_ring(3, 4, salt="2").points(), real_ring(3, 4, salt="2").points())


class RingErrorTests(unittest.TestCase):
    def test_invalid_v(self):
        for v in [0, -1, 1.5, "3", True, None]:
            with self.assertRaises(InvalidInputError):
                HashRing(v)

    def test_invalid_node_id(self):
        ring = real_ring(2, 2)
        for node_id in [0, -3, 2.0, "3", True, None]:
            with self.assertRaises(InvalidInputError):
                ring.add_node(node_id)
        with self.assertRaises(InvalidInputError):
            HashRing(2).build([1, 0])

    def test_duplicate_node_changes_nothing(self):
        ring = real_ring(3, 4)
        before = ring.points()
        with self.assertRaises(DuplicateNodeError):
            ring.add_node(2)
        self.assertEqual(ring.points(), before)
        with self.assertRaises(DuplicateNodeError):
            HashRing(2).build([1, 2, 1])

    def test_remove_missing_changes_nothing(self):
        ring = real_ring(3, 4)
        before = ring.points()
        with self.assertRaises(NodeNotFoundError):
            ring.remove_node(9)
        self.assertEqual(ring.points(), before)

    def test_remove_last_changes_nothing(self):
        ring = real_ring(1, 4)
        before = ring.points()
        with self.assertRaises(LastNodeError):
            ring.remove_node(1)
        self.assertEqual(ring.points(), before)
        self.assertEqual(ring.node_count, 1)


if __name__ == "__main__":
    unittest.main()
