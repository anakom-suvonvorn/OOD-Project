"""All guest data and indexes, kept consistent in one place (owner: P2).

RULE: the four structures below are changed ONLY through place / unplace / move.
Nobody else edits them directly. That is how they can never disagree.
"""
from __future__ import annotations

from typing import Iterator

from .errors import GuestNotFoundError, RoomNotFoundError
from .guest import Guest
from .models import GuestId, RingPoint


class GuestStore:
    """
    guests       dict[GuestId, Guest]                 search by (c, s)          O(1)
    room_index   dict[(node_id, room_no), GuestId]    search by address         O(1)
    buckets      dict[RingPoint, set[GuestId]]        guests owned by a point   (empty sets are deleted)
    node_counts  dict[node_id, int]                   guests per building       (missing key = 0)
    """

    def __init__(self) -> None:
        self.guests: dict[GuestId, Guest] = {}
        self.room_index: dict[tuple[int, int], GuestId] = {}
        self.buckets: dict[RingPoint, set[GuestId]] = {}
        self.node_counts: dict[int, int] = {}

    def __len__(self) -> int:
        """K."""
        return len(self.guests)

    def __contains__(self, gid: GuestId) -> bool:
        return gid in self.guests

    def __iter__(self) -> Iterator[Guest]:
        return iter(self.guests.values())

    def get(self, c: int, s: int) -> Guest:
        """Raises GuestNotFoundError."""
        gid = (c, s)
        if gid not in self.guests:
            raise GuestNotFoundError(f"guest {(c, s)} is not in the hotel")
        return self.guests[gid]

    def get_by_room(self, node_id: int, room_no: int) -> Guest:
        """Raises RoomNotFoundError."""
        key = (node_id, room_no)
        if key not in self.room_index:
            raise RoomNotFoundError(f"room {room_no} in building {node_id} is unoccupied")
        gid = self.room_index[key]
        return self.guests[gid]

    def place(self, guest: Guest, point: RingPoint) -> None:
        """Insert a NEW guest owned by `point` into all four structures. O(1)."""
        gid = guest.id
        node_id = point.node_id

        guest.point = point
        self.guests[gid] = guest
        self.room_index[(node_id, guest.room_no)] = gid

        if point not in self.buckets:
            self.buckets[point] = set()
        self.buckets[point].add(gid)

        self.node_counts[node_id] = self.node_counts.get(node_id, 0) + 1

    def unplace(self, c: int, s: int) -> Guest:
        """Remove a guest from all four structures and return it. O(1). Raises GuestNotFoundError."""
        guest = self.get(c, s)
        gid = guest.id
        point = guest.point
        node_id = point.node_id

        del self.guests[gid]
        del self.room_index[(node_id, guest.room_no)]

        bucket = self.buckets[point]
        bucket.remove(gid)
        if not bucket:
            del self.buckets[point]

        self.node_counts[node_id] -= 1
        if self.node_counts[node_id] == 0:
            del self.node_counts[node_id]

        return guest

    def move(self, guest: Guest, new_point: RingPoint) -> int:
        """Re-own an existing guest by new_point; update bucket, room_index, node_counts
        and guest.point. Returns the old node_id. O(1)."""
        gid = guest.id
        old_point = guest.point
        old_node = old_point.node_id
        new_node = new_point.node_id

        # 1. Update buckets
        old_bucket = self.buckets[old_point]
        old_bucket.remove(gid)
        if not old_bucket:
            del self.buckets[old_point]

        if new_point not in self.buckets:
            self.buckets[new_point] = set()
        self.buckets[new_point].add(gid)

        # 2. Update room_index & node_counts (if building changed)
        if old_node != new_node:
            del self.room_index[(old_node, guest.room_no)]
            self.room_index[(new_node, guest.room_no)] = gid

            self.node_counts[old_node] -= 1
            if self.node_counts[old_node] == 0:
                del self.node_counts[old_node]
            self.node_counts[new_node] = self.node_counts.get(new_node, 0) + 1

        # 3. Update guest.point
        guest.point = new_point
        return old_node

    def guests_at(self, point: RingPoint) -> list[GuestId]:
        """Copy of the bucket of `point` ([] if none) - a copy so callers may move guests while looping."""
        if point not in self.buckets:
            return []
        return list(self.buckets[point])
