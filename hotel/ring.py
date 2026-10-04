"""Consistent-hashing ring (owner: P1)."""
from __future__ import annotations

import bisect
from typing import Callable, Iterable

from .errors import (
    DuplicateNodeError,
    EmptyRingError,
    InvalidInputError,
    LastNodeError,
    NodeNotFoundError,
)
from .hashing import hash64, node_key
from .models import RingPoint


class HashRing:
    """Sorted list of virtual-node points on the ring 0 .. 2^64 - 1.

    _points          list[RingPoint], always sorted by (pos, node_id, j)  -> M items
    _points_by_node  dict[node_id, list[RingPoint]]                       -> for removal
    """

    def __init__(
        self,
        vnodes_per_node: int,
        salt: str = "",
        hash_fn: Callable[[str], int] | None = None,
    ) -> None:
        """V must be an int >= 1. hash_fn defaults to hash64; tests pass a fake one
        (e.g. a dict lookup) to put points at hand-picked positions."""
        if not isinstance(vnodes_per_node, int) or isinstance(vnodes_per_node, bool) or vnodes_per_node < 1:
            raise InvalidInputError("V must be an integer >= 1")
        self.V = vnodes_per_node
        self.salt = salt
        self._hash = hash_fn or hash64
        self._points: list[RingPoint] = []
        self._points_by_node: dict[int, list[RingPoint]] = {}

    def build(self, node_ids: Iterable[int]) -> None:
        """Initial build on an empty ring: create all N*V points, sort once. O(M log M).

        Raises InvalidInputError (bad id), DuplicateNodeError (id repeated)."""
        raise NotImplementedError("P1")

    def add_node(self, node_id: int) -> list[RingPoint]:
        """Add the V points of a new building and return them.

        Sort the V new points, then merge with _points by hand: O(V log V + M).
        Existing points are never changed. Raises InvalidInputError, DuplicateNodeError."""
        raise NotImplementedError("P1")

    def remove_node(self, node_id: int) -> list[RingPoint]:
        """Remove all V points of a building and return them. O(M).

        Raises NodeNotFoundError, LastNodeError (would leave the ring empty)."""
        raise NotImplementedError("P1")

    def lookup(self, pos: int) -> RingPoint:
        """First point with point.pos >= pos; wrap to _points[0] if none. O(log M).

        Hint: bisect.bisect_left(self._points, (pos,)). Raises EmptyRingError."""
        raise NotImplementedError("P1")

    def node_for(self, pos: int) -> int:
        """node_id of lookup(pos)."""
        raise NotImplementedError("P1")

    def successor(self, point: RingPoint) -> RingPoint:
        """The next point clockwise after `point` (wraps around). point must be on the ring."""
        raise NotImplementedError("P1")

    def has_node(self, node_id: int) -> bool:
        raise NotImplementedError("P1")

    def node_ids(self) -> list[int]:
        """All building ids, ascending."""
        raise NotImplementedError("P1")

    def points(self) -> list[RingPoint]:
        """Copy of the sorted point list (for tests / drawing). O(M)."""
        raise NotImplementedError("P1")

    @property
    def node_count(self) -> int:
        """N."""
        return len(self._points_by_node)

    def __len__(self) -> int:
        """M = N * V."""
        return len(self._points)
