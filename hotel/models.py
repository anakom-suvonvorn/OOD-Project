"""Shared data types used across modules (SHARED CONTRACT - change only via PLAN.md)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import NamedTuple

GuestId = tuple[int, int]
"""A guest id (c, s): channel c and sequence s, both ints >= 1."""


class RingPoint(NamedTuple):
    """One virtual node on the ring.

    Field order is the required sort key (pos, node_id, j), so a sorted list of
    RingPoint is already in the tie-break order of PDF section 4.3 rule 4.
    """

    pos: int
    node_id: int
    j: int


@dataclass(frozen=True)
class Move:
    """One guest whose building changed. room_no never changes when a guest moves."""

    c: int
    s: int
    old_node: int
    new_node: int
    room_no: int


@dataclass
class MoveReport:
    """Result of HotelSystem.add_building / remove_building."""

    action: str  # "add" or "remove"
    node_id: int
    total_guests: int  # K at the time of the command
    moves: list[Move] = field(default_factory=list)

    @property
    def moved_count(self) -> int:
        return len(self.moves)

    @property
    def move_rate(self) -> float | None:
        """moved / K, or None when K == 0 (the rate is not computed without guests)."""
        if self.total_guests == 0:
            return None
        return len(self.moves) / self.total_guests


@dataclass
class LoadStats:
    """Guests per building. std is the population standard deviation (divide by N)."""

    counts: dict[int, int]  # every building incl. those with 0 guests, node_id ascending
    total: int
    maximum: int
    minimum: int
    mean: float
    std: float
    cv: float | None  # std / mean, None when total == 0
