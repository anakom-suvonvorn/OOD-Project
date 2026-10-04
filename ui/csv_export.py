"""CSV export, UTF-8 (owner: P5). Open files with encoding="utf-8", newline="".

Each function returns the number of data rows written (header not counted).
"""
from __future__ import annotations

from hotel import HotelSystem, MoveReport

GUEST_COLUMNS = ["channel_id", "sequence_id", "node_id", "room_no"]
MOVE_COLUMNS = ["channel_id", "sequence_id", "old_node_id", "new_node_id", "room_no"]


def export_guests(system: HotelSystem, path: str) -> int:
    """One row per guest, in list_rooms() order. Row count must equal system.guest_count."""
    raise NotImplementedError("P5")


def export_moves(report: MoveReport, path: str) -> int:
    """One row per Move. Row count must equal report.moved_count."""
    raise NotImplementedError("P5")


def export_rows(rows: list[dict], path: str) -> int:
    """Generic writer for experiment results (columns = keys of the first row)."""
    raise NotImplementedError("P5")
