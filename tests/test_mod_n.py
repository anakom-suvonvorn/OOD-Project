"""Tests for mod_n.py (owner: P1)."""
import unittest

from hotel.errors import (
    DuplicateNodeError,
    EmptyRingError,
    InvalidInputError,
    LastNodeError,
    NodeNotFoundError,
)
from hotel.hashing import guest_key, hash64
from hotel.mod_n import ModNRouter
from hotel.ring import HashRing


def router(ids) -> ModNRouter:
    r = ModNRouter()
    r.build(ids)
    return r


class ModNTests(unittest.TestCase):
    def test_node_for_uses_index_in_added_order(self):
        r = router([7, 3, 5])
        self.assertEqual([r.node_for(p) for p in range(6)], [7, 3, 5, 7, 3, 5])

    def test_add_appends(self):
        r = router([1, 2])
        r.add_node(9)
        self.assertEqual(r.node_ids(), [1, 2, 9])
        self.assertEqual(r.node_for(2), 9)

    def test_remove_keeps_order_of_the_rest(self):
        r = router([1, 2, 3, 4])
        r.remove_node(2)
        self.assertEqual(r.node_ids(), [1, 3, 4])
        self.assertEqual(r.node_for(1), 3)

    def test_errors_change_nothing(self):
        r = router([1, 2])
        with self.assertRaises(DuplicateNodeError):
            r.add_node(2)
        with self.assertRaises(NodeNotFoundError):
            r.remove_node(5)
        with self.assertRaises(InvalidInputError):
            r.add_node(0)
        self.assertEqual(r.node_ids(), [1, 2])
        single = router([1])
        with self.assertRaises(LastNodeError):
            single.remove_node(1)
        self.assertEqual(single.node_ids(), [1])
        with self.assertRaises(DuplicateNodeError):
            router([1, 1])
        with self.assertRaises(InvalidInputError):
            r.build([3])

    def test_empty(self):
        with self.assertRaises(EmptyRingError):
            ModNRouter().node_for(3)

    def test_adding_a_building_moves_far_more_than_consistent_hashing(self):
        positions = [hash64(guest_key(c, s)) for c in range(1, 11) for s in range(1, 101)]
        mod = router(range(1, 11))
        ring = HashRing(32)
        ring.build(range(1, 11))
        mod_before = [mod.node_for(p) for p in positions]
        ring_before = [ring.node_for(p) for p in positions]
        mod.add_node(11)
        ring.add_node(11)
        mod_moved = sum(b != mod.node_for(p) for b, p in zip(mod_before, positions))
        ring_moved = sum(b != ring.node_for(p) for b, p in zip(ring_before, positions))
        # Expected: mod N moves about N/(N+1) = 91%, consistent hashing about 1/(N+1) = 9%.
        self.assertGreater(mod_moved, 0.8 * len(positions))
        self.assertLess(ring_moved, 0.2 * len(positions))


if __name__ == "__main__":
    unittest.main()
