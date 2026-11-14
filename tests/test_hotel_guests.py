import unittest
from hotel.errors import (
    DuplicateGuestError,
    EmptyRingError,
    GuestNotFoundError,
    InvalidInputError,
    RoomNotFoundError,
)
from hotel.hotel_system import HotelSystem


class TestHotelGuests(unittest.TestCase):
    def test_add_guest_does_not_move_existing_guests(self):
        sys = HotelSystem.initialize(num_nodes=4, vnodes_per_node=8, channel_sizes=[10, 10])
        before = {(g.c, g.s): (g.node_id, g.room_no) for g in sys.guests()}

        # Add to existing channel & new channel
        sys.add_guest(1, 11)
        sys.add_guest(3, 1)
        sys.add_guests(4, 1, 5)

        for gid, addr in before.items():
            g = sys.find_guest(*gid)
            self.assertEqual((g.node_id, g.room_no), addr)

    def test_duplicate_guest_and_atomic_batch(self):
        sys = HotelSystem.initialize(num_nodes=3, vnodes_per_node=4, channel_sizes=[5])
        with self.assertRaises(DuplicateGuestError):
            sys.add_guest(1, 3)

        # Batch (1, 4..7) overlaps with existing (1, 4) and (1, 5) -> nothing added
        before_count = sys.guest_count
        with self.assertRaises(DuplicateGuestError):
            sys.add_guests(1, 4, 4)
        self.assertEqual(sys.guest_count, before_count)
        with self.assertRaises(GuestNotFoundError):
            sys.find_guest(1, 6)

    def test_find_remove_and_list_rooms(self):
        sys = HotelSystem.initialize(num_nodes=3, vnodes_per_node=4, channel_sizes=[5, 5])
        g = sys.find_guest(2, 3)
        self.assertEqual(sys.find_by_room(g.node_id, g.room_no), g)

        rooms = sys.list_rooms()
        self.assertEqual(len(rooms), 10)
        self.assertEqual(rooms, sorted(rooms, key=lambda x: (x.node_id, x.room_no)))

        sys.remove_guest(2, 3)
        self.assertEqual(sys.guest_count, 9)
        with self.assertRaises(GuestNotFoundError):
            sys.find_guest(2, 3)
        with self.assertRaises(RoomNotFoundError):
            sys.find_by_room(g.node_id, g.room_no)

    def test_empty_hotel_k_zero_stats(self):
        sys = HotelSystem.initialize(num_nodes=3, vnodes_per_node=4, channel_sizes=[0, 0])
        self.assertEqual(sys.guest_count, 0)
        stats = sys.load_stats()
        self.assertEqual(stats.total, 0)
        self.assertEqual(stats.maximum, 0)
        self.assertEqual(stats.minimum, 0)
        self.assertEqual(stats.mean, 0.0)
        self.assertEqual(stats.std, 0.0)
        self.assertIsNone(stats.cv)
        self.assertEqual(stats.counts, {1: 0, 2: 0, 3: 0})

    def test_clone_independence(self):
        sys = HotelSystem.initialize(num_nodes=3, vnodes_per_node=4, channel_sizes=[5])
        cloned = sys.clone()
        cloned.add_guest(2, 1)
        self.assertEqual(sys.guest_count, 5)
        self.assertEqual(cloned.guest_count, 6)

    def test_empty_ring_raises(self):
        sys = HotelSystem(vnodes_per_node=4)
        with self.assertRaises(EmptyRingError):
            sys.add_guest(1, 1)
        with self.assertRaises(EmptyRingError):
            sys.add_guests(1, 1, 3)

    def test_batch_of_zero_changes_nothing_even_without_buildings(self):
        sys = HotelSystem(vnodes_per_node=4)
        self.assertEqual(sys.add_guests(1, 1, 0), [])
        self.assertEqual(sys.guest_count, 0)


if __name__ == "__main__":
    unittest.main()
