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


def validate_node_id(node_id: int) -> None:
    """Raise InvalidInputError unless node_id is an int >= 1 (bool is not accepted)."""
    if not isinstance(node_id, int) or isinstance(node_id, bool) or node_id < 1:
        raise InvalidInputError(f"building id must be an integer >= 1, got {node_id!r}")


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

    def _make_points(self, node_id: int) -> list[RingPoint]:
        """The V points of one building, sorted. O(V log V)."""
        return sorted(
            RingPoint(self._hash(node_key(node_id, j, self.salt)), node_id, j)
            for j in range(self.V)
        )

    def build(self, node_ids: Iterable[int]) -> None:
        """Initial build on an empty ring: create all N*V points, sort once. O(M log M).

        Raises InvalidInputError (bad id, or ring already built), DuplicateNodeError (id repeated)."""
        if self._points_by_node:
            raise InvalidInputError("ring is already built; use add_node")
        ids = list(node_ids)
        seen: set[int] = set()
        for node_id in ids:
            validate_node_id(node_id)
            if node_id in seen:
                raise DuplicateNodeError(f"building {node_id} is listed twice")
            seen.add(node_id)

        for node_id in ids:
            self._points_by_node[node_id] = self._make_points(node_id)
        self._points = sorted(p for pts in self._points_by_node.values() for p in pts)

    def add_node(self, node_id: int) -> list[RingPoint]:
        """Add the V points of a new building and return them.

        Sort the V new points, then merge with _points by hand: O(V log V + M).
        Existing points are never changed. Raises InvalidInputError, DuplicateNodeError."""
        validate_node_id(node_id)
        if node_id in self._points_by_node:
            raise DuplicateNodeError(f"building {node_id} already exists")

        new = self._make_points(node_id)
        old = self._points
        merged: list[RingPoint] = []
        i = k = 0
        while i < len(old) and k < len(new):
            if old[i] < new[k]:
                merged.append(old[i])
                i += 1
            else:
                merged.append(new[k])
                k += 1
        merged.extend(old[i:])
        merged.extend(new[k:])

        self._points = merged
        self._points_by_node[node_id] = new
        return list(new)

    def remove_node(self, node_id: int) -> list[RingPoint]:
        """Remove all V points of a building and return them. O(M).

        Raises NodeNotFoundError, LastNodeError (would leave the ring empty)."""
        if node_id not in self._points_by_node:
            raise NodeNotFoundError(f"building {node_id} does not exist")
        if len(self._points_by_node) == 1:
            raise LastNodeError(f"building {node_id} is the last building and cannot be removed")

        removed = self._points_by_node.pop(node_id)
        self._points = [p for p in self._points if p.node_id != node_id]
        return list(removed)

    def lookup(self, pos: int) -> RingPoint:
        """First point with point.pos >= pos; wrap to _points[0] if none. O(log M).

        (pos,) sorts before every (pos, node_id, j), so bisect_left lands on the first
        point at or after pos, and among equal positions on the smallest (node_id, j).
        Raises EmptyRingError."""
        if not self._points:
            raise EmptyRingError("there are no buildings yet")
        i = bisect.bisect_left(self._points, (pos,))
        if i == len(self._points):
            i = 0
        return self._points[i]

    def node_for(self, pos: int) -> int:
        """node_id of lookup(pos)."""
        return self.lookup(pos).node_id

    def successor(self, point: RingPoint) -> RingPoint:
        """The next point clockwise after `point` (wraps around). point must be on the ring. O(log M)."""
        i = bisect.bisect_left(self._points, point)
        if i == len(self._points) or self._points[i] != point:
            raise ValueError(f"{point} is not on the ring")
        return self._points[(i + 1) % len(self._points)]

    def has_node(self, node_id: int) -> bool:
        return node_id in self._points_by_node

    def node_ids(self) -> list[int]:
        """All building ids, ascending."""
        return sorted(self._points_by_node)

    def points(self) -> list[RingPoint]:
        """Copy of the sorted point list (for tests / drawing). O(M)."""
        return list(self._points)

    @property
    def node_count(self) -> int:
        """N."""
        return len(self._points_by_node)

    def __len__(self) -> int:
        """M = N * V."""
        return len(self._points)
