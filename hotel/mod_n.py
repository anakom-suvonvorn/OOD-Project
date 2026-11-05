"""hash mod N baseline, used only for comparison in experiments (owner: P1).

Same interface idea as HashRing (build / add_node / remove_node / node_for) so the
experiment code can treat both the same way. Uses the SAME guest positions (hash64 of
guest_key with the same salt), so both methods see identical hash values.
"""
from __future__ import annotations

from typing import Iterable

from .errors import DuplicateNodeError, EmptyRingError, InvalidInputError, LastNodeError, NodeNotFoundError
from .ring import validate_node_id


class ModNRouter:
    """_nodes: list of building ids in the order they were added."""

    def __init__(self) -> None:
        self._nodes: list[int] = []

    def build(self, node_ids: Iterable[int]) -> None:
        """Initial build on an empty router. Raises InvalidInputError, DuplicateNodeError."""
        if self._nodes:
            raise InvalidInputError("router is already built; use add_node")
        ids = list(node_ids)
        seen: set[int] = set()
        for node_id in ids:
            validate_node_id(node_id)
            if node_id in seen:
                raise DuplicateNodeError(f"building {node_id} is listed twice")
            seen.add(node_id)
        self._nodes = ids

    def add_node(self, node_id: int) -> None:
        """Append to the end of _nodes. O(N) for the duplicate check."""
        validate_node_id(node_id)
        if node_id in self._nodes:
            raise DuplicateNodeError(f"building {node_id} already exists")
        self._nodes.append(node_id)

    def remove_node(self, node_id: int) -> None:
        """Remove node_id and keep the order of the rest. O(N)."""
        if node_id not in self._nodes:
            raise NodeNotFoundError(f"building {node_id} does not exist")
        if len(self._nodes) == 1:
            raise LastNodeError(f"building {node_id} is the last building and cannot be removed")
        self._nodes.remove(node_id)

    def node_for(self, pos: int) -> int:
        """_nodes[pos % N]. Raises EmptyRingError when there are no buildings."""
        if not self._nodes:
            raise EmptyRingError("there are no buildings yet")
        return self._nodes[pos % len(self._nodes)]

    def node_ids(self) -> list[int]:
        """Building ids in the order they were added (this order decides pos % N)."""
        return list(self._nodes)
