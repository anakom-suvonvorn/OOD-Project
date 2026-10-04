"""hash mod N baseline, used only for comparison in experiments (owner: P1).

Same interface idea as HashRing (build / add_node / remove_node / node_for) so the
experiment code can treat both the same way. Uses the SAME guest positions (hash64 of
guest_key with the same salt), so both methods see identical hash values.
"""
from __future__ import annotations

from typing import Iterable

from .errors import DuplicateNodeError, EmptyRingError, InvalidInputError, LastNodeError, NodeNotFoundError


class ModNRouter:
    """_nodes: list of building ids in the order they were added."""

    def __init__(self) -> None:
        self._nodes: list[int] = []

    def build(self, node_ids: Iterable[int]) -> None:
        raise NotImplementedError("P1")

    def add_node(self, node_id: int) -> None:
        """Append to the end of _nodes."""
        raise NotImplementedError("P1")

    def remove_node(self, node_id: int) -> None:
        """Remove node_id and keep the order of the rest. O(N)."""
        raise NotImplementedError("P1")

    def node_for(self, pos: int) -> int:
        """_nodes[pos % N]. Raises EmptyRingError when there are no buildings."""
        raise NotImplementedError("P1")

    def node_ids(self) -> list[int]:
        raise NotImplementedError("P1")
