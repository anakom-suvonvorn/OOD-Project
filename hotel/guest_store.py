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
        raise NotImplementedError("P2")

    def get_by_room(self, node_id: int, room_no: int) -> Guest:
        """Raises RoomNotFoundError."""
        raise NotImplementedError("P2")

    def place(self, guest: Guest, point: RingPoint) -> None:
        """Insert a NEW guest owned by `point` into all four structures. O(1)."""
        raise NotImplementedError("P2")

    def unplace(self, c: int, s: int) -> Guest:
        """Remove a guest from all four structures and return it. O(1). Raises GuestNotFoundError."""
        raise NotImplementedError("P2")

    def move(self, guest: Guest, new_point: RingPoint) -> int:
        """Re-own an existing guest by new_point; update bucket, room_index, node_counts
        and guest.point. Returns the old node_id. O(1)."""
        raise NotImplementedError("P2")

    def guests_at(self, point: RingPoint) -> list[GuestId]:
        """Copy of the bucket of `point` ([] if none) - a copy so callers may move guests while looping."""
        raise NotImplementedError("P2")
