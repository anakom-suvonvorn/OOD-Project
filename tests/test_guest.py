import unittest
from hotel.errors import GuestNotFoundError, InvalidInputError, RoomNotFoundError
from hotel.guest import Guest, guest_id_from_room, room_number, validate_guest_id
from hotel.guest_store import GuestStore
from hotel.models import RingPoint


class TestGuestMath(unittest.TestCase):
    def test_known_table(self):
        expected = {
            (1, 1): 1,
            (2, 1): 2,
            (1, 2): 3,
            (3, 1): 4,
            (2, 2): 5,
        }
        for (c, s), room in expected.items():
            self.assertEqual(room_number(c, s), room)
            self.assertEqual(guest_id_from_room(room), (c, s))

    def test_bijection_no_duplicates_and_inverse(self):
        seen_rooms = set()
        for c in range(1, 35):
            for s in range(1, 35):
                r = room_number(c, s)
                self.assertNotIn(r, seen_rooms)
                seen_rooms.add(r)
                self.assertEqual(guest_id_from_room(r), (c, s))

    def test_invalid_inputs(self):
        for bad in [0, -1, -10, True, False, 1.5, "1", None]:
            with self.assertRaises(InvalidInputError):
                validate_guest_id(bad, 1)
            with self.assertRaises(InvalidInputError):
                validate_guest_id(1, bad)
            with self.assertRaises(InvalidInputError):
                room_number(bad, 1)
            with self.assertRaises(InvalidInputError):
                guest_id_from_room(bad)


class TestGuestStore(unittest.TestCase):
    def test_place_move_unplace_consistency(self):
        store = GuestStore()
        p1 = RingPoint(100, 1, 0)
        p2 = RingPoint(200, 2, 0)

        g = Guest(1, 2, pos=50)
        store.place(g, p1)

        self.assertEqual(len(store), 1)
        self.assertIn((1, 2), store)
        self.assertEqual(store.get(1, 2), g)
        self.assertEqual(store.get_by_room(1, g.room_no), g)
        self.assertEqual(store.node_counts[1], 1)
        self.assertEqual(store.guests_at(p1), [(1, 2)])

        # Move to p2
        old_node = store.move(g, p2)
        self.assertEqual(old_node, 1)
        self.assertEqual(g.node_id, 2)
        self.assertNotIn(p1, store.buckets)
        self.assertEqual(store.guests_at(p2), [(1, 2)])
        self.assertEqual(store.get_by_room(2, g.room_no), g)
        with self.assertRaises(RoomNotFoundError):
            store.get_by_room(1, g.room_no)

        # Unplace
        removed = store.unplace(1, 2)
        self.assertEqual(removed, g)
        self.assertEqual(len(store), 0)
        self.assertEqual(store.buckets, {})
        self.assertEqual(store.room_index, {})
        self.assertEqual(store.node_counts, {})

        with self.assertRaises(GuestNotFoundError):
            store.get(1, 2)


if __name__ == "__main__":
    unittest.main()
