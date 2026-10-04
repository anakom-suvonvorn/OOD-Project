"""Public API of the hotel. The UI and experiments talk only to this class.

Owners: guest methods = P2, building methods = P3 (marked on each method).
"""
from __future__ import annotations

from typing import Callable, Iterator

from .errors import (
    DuplicateGuestError,
    EmptyRingError,
    GuestNotFoundError,
    InvalidInputError,
    RoomNotFoundError,
)
from .guest import Guest, validate_guest_id
from .guest_store import GuestStore
from .hashing import guest_key, hash64
from .models import LoadStats, Move, MoveReport
from .ring import HashRing


class HotelSystem:
    def __init__(
        self,
        vnodes_per_node: int,
        salt: str = "",
        hash_fn: Callable[[str], int] | None = None,
    ) -> None:
        """An empty hotel with no buildings. Usually created via initialize()."""
        self.salt = salt
        self._hash_fn = hash_fn
        self._hash = hash_fn or hash64
        self.ring = HashRing(vnodes_per_node, salt, hash_fn)
        self.store = GuestStore()

    # ---------------------------------------------------------------- setup (P2)

    @classmethod
    def initialize(
        cls,
        num_nodes: int,
        vnodes_per_node: int,
        channel_sizes: list[int],
        salt: str = "",
        hash_fn: Callable[[str], int] | None = None,
    ) -> HotelSystem:
        """Buildings 1..num_nodes; channel c = i + 1 gets guests s = 1 .. channel_sizes[i].

        Ring built once (ring.build), then guests placed. Raises InvalidInputError."""
        raise NotImplementedError("P2")

    def clone(self) -> HotelSystem:
        """Independent copy (same V, salt, hash_fn, buildings, guests) for experiments."""
        raise NotImplementedError("P2")

    @property
    def V(self) -> int:
        return self.ring.V

    @property
    def guest_count(self) -> int:
        """K."""
        return len(self.store)

    def node_ids(self) -> list[int]:
        return self.ring.node_ids()

    def guests(self) -> Iterator[Guest]:
        return iter(self.store)

    # ---------------------------------------------------------------- guests (P2)

    def add_guest(self, c: int, s: int) -> Guest:
        """Raises InvalidInputError, DuplicateGuestError, EmptyRingError. O(log M)."""
        raise NotImplementedError("P2")

    def add_guests(self, c: int, s_start: int, count: int) -> list[Guest]:
        """Batch (c, s_start .. s_start+count-1). count must be an int >= 0; 0 changes nothing.

        If ANY id already exists -> DuplicateGuestError and NOTHING is added (check all first)."""
        raise NotImplementedError("P2")

    def remove_guest(self, c: int, s: int) -> Guest:
        """Raises InvalidInputError, GuestNotFoundError. O(1)."""
        raise NotImplementedError("P2")

    def find_guest(self, c: int, s: int) -> Guest:
        """Raises InvalidInputError, GuestNotFoundError. O(1)."""
        raise NotImplementedError("P2")

    def find_by_room(self, node_id: int, room_no: int) -> Guest:
        """Raises InvalidInputError, RoomNotFoundError. O(1)."""
        raise NotImplementedError("P2")

    def list_rooms(self) -> list[Guest]:
        """All guests sorted by (node_id, room_no) ascending. O(K log K)."""
        raise NotImplementedError("P2")

    def load_stats(self) -> LoadStats:
        """Counts for EVERY building (0 included). K == 0 -> all stats 0 and cv None."""
        raise NotImplementedError("P2")

    # ---------------------------------------------------------------- buildings (P3)

    def add_building(self, node_id: int) -> MoveReport:
        """Add a building; move only guests whose owner is now one of its points.

        Raises InvalidInputError, DuplicateNodeError (system unchanged). See PLAN.md 9.1."""
        raise NotImplementedError("P3")

    def remove_building(self, node_id: int) -> MoveReport:
        """Remove a building; its guests go to the next point clockwise.

        Raises NodeNotFoundError, LastNodeError (system unchanged). See PLAN.md 9.2."""
        raise NotImplementedError("P3")

    def compute_node(self, c: int, s: int) -> int:
        """Building for (c, s) computed fresh from the ring, ignoring stored data. O(log M)."""
        raise NotImplementedError("P3")

    def assignments(self) -> dict[tuple[int, int], int]:
        """Snapshot {(c, s): node_id} of all guests. Used by tests as the "recheck everyone" oracle."""
        raise NotImplementedError("P3")

    def verify_integrity(self) -> None:
        """Raise AssertionError if guests / room_index / buckets / node_counts disagree, or if any
        stored node differs from compute_node. O(K log M). For tests only."""
        raise NotImplementedError("P3")
