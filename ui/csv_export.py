"""Write guest, move, and experiment CSV files in UTF-8."""
from __future__ import annotations

import csv

from hotel import HotelSystem, MoveReport

GUEST_COLUMNS = ["channel_id", "sequence_id", "node_id", "room_no"]
MOVE_COLUMNS = ["channel_id", "sequence_id", "old_node_id", "new_node_id", "room_no"]


def export_guests(system: HotelSystem, path: str) -> int:
    """Write all current guests in room order and return the data row count."""
    guests = system.list_rooms()
    with open(path, "w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(GUEST_COLUMNS)
        writer.writerows((g.c, g.s, g.node_id, g.room_no) for g in guests)
    return len(guests)


def export_moves(report: MoveReport, path: str) -> int:
    """Write one row per move in the report and return the data row count."""
    with open(path, "w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(MOVE_COLUMNS)
        writer.writerows((m.c, m.s, m.old_node, m.new_node, m.room_no) for m in report.moves)
    return report.moved_count


def export_rows(rows: list[dict], path: str) -> int:
    """Use the first row's keys as columns, or write an empty file for no rows."""
    with open(path, "w", encoding="utf-8", newline="") as stream:
        if rows:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    return len(rows)
