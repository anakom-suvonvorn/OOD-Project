"""Exceptions raised by the core logic (SHARED CONTRACT - change only via PLAN.md).

The core (hotel/) never prints. It raises one of these; the UI catches HotelError
and shows the message. Every edge case in PDF section 4.5 maps to one of them.
"""


class HotelError(Exception):
    """Base class for every expected, user-facing error."""


class InvalidInputError(HotelError):
    """A value has the wrong type or range (e.g. c < 1, V < 1, negative count)."""


class DuplicateGuestError(HotelError):
    """Adding a guest id (c, s) that is already in the system (also for batches)."""


class GuestNotFoundError(HotelError):
    """Removing or searching a guest id that is not in the system."""


class RoomNotFoundError(HotelError):
    """Searching (node_id, room_no) where nobody is staying."""


class DuplicateNodeError(HotelError):
    """Adding a building id that already exists."""


class NodeNotFoundError(HotelError):
    """Removing a building id that does not exist."""


class LastNodeError(HotelError):
    """Removing the only remaining building (N must stay >= 1)."""


class EmptyRingError(HotelError):
    """Looking up a position while the ring has no buildings yet."""
