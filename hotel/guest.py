"""Guest record and room-number math (owner: P2)."""
from __future__ import annotations

from .errors import InvalidInputError
from .models import GuestId, RingPoint

def _isqrt(n: int) -> int:
    """Integer square root using Newton's method (no floats)."""
    if n < 0:
        raise ValueError("isqrt() argument must be nonnegative")
    if n == 0:
        return 0
    x = n
    y = (x + 1) // 2
    while y < x:
        x = y
        y = (x + n // x) // 2
    return x

def validate_guest_id(c: int, s: int) -> None:
    """Raise InvalidInputError unless c and s are ints >= 1 (bool is not accepted)."""
    if not isinstance(c, int) or isinstance(c, bool) or c < 1:
        raise InvalidInputError(f"channel c must be an integer >= 1, got {c!r}")
    if not isinstance(s, int) or isinstance(s, bool) or s < 1:
        raise InvalidInputError(f"sequence s must be an integer >= 1, got {s!r}")


def room_number(c: int, s: int) -> int:
    """Cantor pairing with a = c - 1, b = s - 1:

        room_no = ((a + b) * (a + b + 1)) // 2 + b + 1     (integers only, no floats)

    (1,1)->1  (2,1)->2  (1,2)->3  (3,1)->4  (2,2)->5
    """
    validate_guest_id(c, s)
    a = c - 1
    b = s - 1
    return ((a + b) * (a + b + 1)) // 2 + b + 1


def guest_id_from_room(room_no: int) -> GuestId:
    """Inverse of room_number: room_no -> (c, s). Raise InvalidInputError if room_no < 1.

    Write your own integer square root (binary search or Newton) - no floats."""
    if not isinstance(room_no, int) or isinstance(room_no, bool) or room_no < 1:
        raise InvalidInputError(f"room_no must be an integer >= 1, got {room_no!r}")
    z = room_no - 1
    w = (_isqrt(8 * z + 1) - 1) // 2
    t = (w * (w + 1)) // 2
    b = z - t
    a = w - b
    return (a + 1, b + 1)


class Guest:
    """One staying guest. pos is hashed once at creation and never recomputed.

    point is the ring point that currently owns the guest; it is set only by
    GuestStore.place / GuestStore.move, so node_id always matches the bucket.
    """

    __slots__ = ("c", "s", "pos", "room_no", "point")

    def __init__(self, c: int, s: int, pos: int) -> None:
        self.c = c
        self.s = s
        self.pos = pos
        self.room_no = room_number(c, s)
        self.point: RingPoint | None = None

    @property
    def id(self) -> GuestId:
        return (self.c, self.s)

    @property
    def node_id(self) -> int:
        return self.point.node_id

    def __repr__(self) -> str:
        node = self.point.node_id if self.point else None
        return f"Guest(c={self.c}, s={self.s}, node={node}, room={self.room_no})"
