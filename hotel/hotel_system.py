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
from .models import LoadStats, Move, MoveReport, RingPoint
from .ring import HashRing , validate_node_id

import math

def _move_order(move: Move) -> tuple[int, int]:
    """Sort key for MoveReport.moves: guest id (c, s)."""
    return (move.c, move.s)

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
        if not isinstance(num_nodes, int) or isinstance(num_nodes, bool) or num_nodes < 1:
            raise InvalidInputError(f"num_nodes must be an integer >= 1, got {num_nodes!r}")
        if not isinstance(channel_sizes, list):
            raise InvalidInputError("channel_sizes must be a list of integers >= 0")
        for size in channel_sizes:
            if not isinstance(size, int) or isinstance(size, bool) or size < 0:
                raise InvalidInputError(f"each channel size must be an integer >= 0, got {size!r}")

        system = cls(vnodes_per_node, salt=salt, hash_fn=hash_fn)
        system.ring.build(range(1, num_nodes + 1))

        for i, count in enumerate(channel_sizes):
            c = i + 1
            for s in range(1, count + 1):
                pos = system._hash(guest_key(c, s, system.salt))
                guest = Guest(c, s, pos)
                point = system.ring.lookup(pos)
                system.store.place(guest, point)

        return system

    def clone(self) -> HotelSystem:
        """Independent copy (same V, salt, hash_fn, buildings, guests) for experiments."""
        copy_sys = HotelSystem(self.V, salt=self.salt, hash_fn=self._hash_fn)
        # Copy ring state directly without re-hashing
        copy_sys.ring._points = list(self.ring._points)
        copy_sys.ring._points_by_node = {
            nid: list(pts) for nid, pts in self.ring._points_by_node.items()
        }
        # Copy all guests with their existing pos and point
        for g in self.store:
            new_g = Guest(g.c, g.s, g.pos)
            copy_sys.store.place(new_g, g.point)
        return copy_sys

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
        validate_guest_id(c, s)
        if self.ring.node_count == 0:
            raise EmptyRingError("there are no buildings yet")
        if (c, s) in self.store:
            raise DuplicateGuestError(f"guest {(c, s)} is already in the hotel")

        pos = self._hash(guest_key(c, s, self.salt))
        guest = Guest(c, s, pos)
        point = self.ring.lookup(pos)
        self.store.place(guest, point)
        return guest

    def add_guests(self, c: int, s_start: int, count: int) -> list[Guest]:
        """Batch (c, s_start .. s_start+count-1). count must be an int >= 0; 0 changes nothing.

        If ANY id already exists -> DuplicateGuestError and NOTHING is added (check all first)."""
        validate_guest_id(c, s_start)
        if not isinstance(count, int) or isinstance(count, bool) or count < 0:
            raise InvalidInputError(f"count must be an integer >= 0, got {count!r}")
        if self.ring.node_count == 0:
            raise EmptyRingError("there are no buildings yet")
        if count == 0:
            return []

        # All-or-nothing check: verify none of the IDs exist first
        for s in range(s_start, s_start + count):
            if (c, s) in self.store:
                raise DuplicateGuestError(f"guest {(c, s)} is already in the hotel")

        added: list[Guest] = []
        for s in range(s_start, s_start + count):
            pos = self._hash(guest_key(c, s, self.salt))
            guest = Guest(c, s, pos)
            point = self.ring.lookup(pos)
            self.store.place(guest, point)
            added.append(guest)
        return added

    def remove_guest(self, c: int, s: int) -> Guest:
        """Raises InvalidInputError, GuestNotFoundError. O(1)."""
        validate_guest_id(c, s)
        return self.store.unplace(c, s)

    def find_guest(self, c: int, s: int) -> Guest:
        """Raises InvalidInputError, GuestNotFoundError. O(1)."""
        validate_guest_id(c, s)
        return self.store.get(c, s)

    def find_by_room(self, node_id: int, room_no: int) -> Guest:
        """Raises InvalidInputError, RoomNotFoundError. O(1)."""
        validate_node_id(node_id)
        if not isinstance(room_no, int) or isinstance(room_no, bool) or room_no < 1:
            raise InvalidInputError(f"room_no must be an integer >= 1, got {room_no!r}")
        return self.store.get_by_room(node_id, room_no)

    def list_rooms(self) -> list[Guest]:
        """All guests sorted by (node_id, room_no) ascending. O(K log K)."""
        return sorted(self.store, key=lambda g: (g.node_id, g.room_no))

    def load_stats(self) -> LoadStats:
        """Counts for EVERY building (0 included). K == 0 -> all stats 0 and cv None."""
        nids = self.ring.node_ids()
        counts = {nid: self.store.node_counts.get(nid, 0) for nid in nids}
        total = len(self.store)
        n = len(nids)

        if total == 0 or n == 0:
            return LoadStats(
                counts=counts,
                total=0,
                maximum=0,
                minimum=0,
                mean=0.0,
                std=0.0,
                cv=None,
            )

        vals = list(counts.values())
        maximum = max(vals)
        minimum = min(vals)
        mean = total / n
        variance = sum((v - mean) ** 2 for v in vals) / n
        std = math.sqrt(variance)
        cv = std / mean

        return LoadStats(
            counts=counts,
            total=total,
            maximum=maximum,
            minimum=minimum,
            mean=mean,
            std=std,
            cv=cv,
        )

    # ---------------------------------------------------------------- buildings (P3)

    def add_building(self, node_id: int) -> MoveReport:
        """Add a building; move only guests whose owner is now one of its points.

        Raises InvalidInputError, DuplicateNodeError (system unchanged). See PLAN.md 9.1.

        Only the old point right after each new point (clockwise) can lose guests, so
        only the guests in those buckets are checked - not all K guests (PDF 4.7 "แบบ ข").
        Expected O(M + V log M + (K/N) log M + m log m); worst O(M + K log M + K log K).
        """
        total = self.guest_count

        # (a) ring update. Validates first and raises before changing anything.
        new_points = self.ring.add_node(node_id)

        # (b) find affected guests. A new point p takes part of the range of the first OLD
        # point after it. When several new points sit next to each other, only the last one
        # of the run has an old successor, and that old point's bucket already holds every
        # guest of the whole run, so new successors are simply skipped. V calls, O(V log M).
        # (Ring was empty before -> every successor is new -> no candidates, no guests.)
        candidates: set[RingPoint] = set()
        for p in new_points:
            q = self.ring.successor(p)
            if q.node_id != node_id:
                candidates.add(q)

        # (c) re-own guests whose owner changed. guests_at returns a copy, so moving is safe.
        moves: list[Move] = []
        for q in candidates:
            for gid in self.store.guests_at(q):
                guest = self.store.guests[gid]
                new_owner = self.ring.lookup(guest.pos)  # recomputed: also correct for ties
                if new_owner != q:
                    old_node = self.store.move(guest, new_owner)
                    moves.append(Move(guest.c, guest.s, old_node, new_owner.node_id, guest.room_no))
        moves.sort(key=_move_order)  # report in guest-id order, O(m log m)
        return MoveReport("add", node_id, total, moves)

    def remove_building(self, node_id: int) -> MoveReport:
        """Remove a building; its guests go to the next point clockwise.

        Raises InvalidInputError, NodeNotFoundError, LastNodeError (system unchanged).
        See PLAN.md 9.2.

        The guests to move are exactly the buckets of the removed points - no search is
        needed. O(M + V + m log M + m log m), m = guests of this building (expected K/N).
        """
        validate_node_id(node_id)
        total = self.guest_count

        # (a) ring update. Raises NodeNotFound / LastNode before changing anything.
        removed_points = self.ring.remove_node(node_id)

        # (b) affected guests = buckets of the removed points; (c) re-own each one.
        moves: list[Move] = []
        for p in removed_points:
            for gid in self.store.guests_at(p):
                guest = self.store.guests[gid]
                new_owner = self.ring.lookup(guest.pos)  # node_id has no points any more
                old_node = self.store.move(guest, new_owner)
                moves.append(Move(guest.c, guest.s, old_node, new_owner.node_id, guest.room_no))
        moves.sort(key=_move_order)  # report in guest-id order, O(m log m)
        return MoveReport("remove", node_id, total, moves)

    def compute_node(self, c: int, s: int) -> int:
        """Building for (c, s) computed fresh from the ring, ignoring stored data. O(log M).

        Works for any valid id, staying or not. Raises InvalidInputError, EmptyRingError."""
        validate_guest_id(c, s)
        pos = self._hash(guest_key(c, s, self.salt))
        return self.ring.node_for(pos)

    def assignments(self) -> dict[tuple[int, int], int]:
        """Snapshot {(c, s): node_id} of all guests. Used by tests as the "recheck everyone" oracle.

        O(K). The returned dict is a copy - later changes to the hotel do not affect it."""
        return {guest.id: guest.node_id for guest in self.store}

    def verify_integrity(self) -> None:
        """Raise AssertionError if guests / room_index / buckets / node_counts disagree, or if any
        stored node differs from compute_node. O(K log M). For tests only."""

        def check(condition: bool, message: str) -> None:
            # Explicit raise instead of `assert`, so the check still runs under python -O.
            if not condition:
                raise AssertionError(message)

        store = self.store
        ring_points = set(self.ring.points())
        ring_nodes = set(self.ring.node_ids())

        # 1. sizes agree everywhere
        k = len(store.guests)
        check(len(store.room_index) == k, f"room_index has {len(store.room_index)} entries, K = {k}")
        check(sum(len(b) for b in store.buckets.values()) == k, "bucket sizes do not add up to K")
        check(sum(store.node_counts.values()) == k, "node_counts do not add up to K")

        # 2. every guest agrees with every index and with a fresh computation
        expected_counts: dict[int, int] = {}
        for gid, guest in store.guests.items():
            check(gid == guest.id, f"guests key {gid} != guest.id {guest.id}")
            point = guest.point
            check(point is not None, f"guest {gid} has no ring point")
            check(point in ring_points, f"guest {gid} is owned by {point}, which is not on the ring")
            check(point == self.ring.lookup(guest.pos), f"guest {gid} is owned by the wrong point")
            check(gid in store.buckets.get(point, ()), f"guest {gid} is missing from its bucket")
            check(store.room_index.get((point.node_id, guest.room_no)) == gid,
                  f"room_index does not point to guest {gid}")
            check(guest.pos == self._hash(guest_key(guest.c, guest.s, self.salt)),
                  f"guest {gid} has a stale hash position")
            check(guest.node_id == self.compute_node(guest.c, guest.s),
                  f"guest {gid} stored in building {guest.node_id}, ring says otherwise")
            expected_counts[point.node_id] = expected_counts.get(point.node_id, 0) + 1

        # 3. no leftover entries (empty buckets / zero counts are deleted by GuestStore)
        for (node, room), gid in store.room_index.items():
            check(gid in store.guests and store.guests[gid].node_id == node,
                  f"room_index entry {(node, room)} is stale")
        for point, bucket in store.buckets.items():
            check(len(bucket) > 0, f"empty bucket left for {point}")
            for gid in bucket:
                check(gid in store.guests and store.guests[gid].point == point,
                      f"bucket of {point} holds stale guest {gid}")
        check(store.node_counts == expected_counts, "node_counts disagree with the guests")
        check(set(store.node_counts) <= ring_nodes, "node_counts mentions a removed building")
