"""Stable 64-bit hashing for ring positions (owner: P1).

Never use Python's built-in hash() here: its value changes every time Python starts.
"""
import hashlib

RING_BITS = 64
RING_SIZE = 2**RING_BITS  # positions are 0 .. RING_SIZE - 1


def guest_key(c: int, s: int, salt: str = "") -> str:
    """Text hashed to place guest (c, s) on the ring.

    guest_key(1, 2)      == "guest:1:2"
    guest_key(1, 2, "0") == "0|guest:1:2"
    """
    key = f"guest:{c}:{s}"
    return f"{salt}|{key}" if salt else key


def node_key(node_id: int, j: int, salt: str = "") -> str:
    """Text hashed to place virtual node j (0 .. V-1) of building node_id.

    node_key(3, 0)      == "node:3:0"
    node_key(3, 0, "1") == "1|node:3:0"
    """
    key = f"node:{node_id}:{j}"
    return f"{salt}|{key}" if salt else key


def hash64(text: str) -> int:
    """SHA-256 of text encoded as UTF-8; the first 8 bytes read as a big-endian unsigned int.

    Returns an int in [0, RING_SIZE - 1]. Same text gives the same result on every run.
    """
    raise NotImplementedError("P1")  # uses hashlib
