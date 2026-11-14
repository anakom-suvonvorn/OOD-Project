"""Tests for the hotel project's UTF-8 CSV exports."""

import csv
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from hotel import HotelSystem
from ui.csv_export import export_guests, export_moves, export_rows


class TestCsvExport(unittest.TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "export.csv"

    def read_csv(self):
        with self.path.open(encoding="utf-8", newline="") as stream:
            return list(csv.reader(stream, strict=True))

    def test_exports_all_current_guests_in_room_order(self):
        system = HotelSystem.initialize(3, 4, [35, 30])
        system.remove_guest(1, 2)

        written = export_guests(system, str(self.path))
        header, *rows = self.read_csv()

        self.assertEqual(header, ["channel_id", "sequence_id", "node_id", "room_no"])
        self.assertEqual(written, system.guest_count)
        self.assertEqual(len(rows), system.guest_count)
        expected = sorted(
            ((g.c, g.s, g.node_id, g.room_no) for g in system.guests()),
            key=lambda row: (row[2], row[3]),
        )
        self.assertEqual([tuple(map(int, row)) for row in rows], expected)

    def test_exports_all_moves_with_guest_and_room_details(self):
        positions = {"node:1:0": 20, "node:2:0": 50, "node:3:0": 80}

        def fixed_hash(key):
            return positions.get(key, 30)

        system = HotelSystem.initialize(3, 1, [27, 28], hash_fn=fixed_hash)
        report = system.remove_building(2)
        self.assertEqual(report.moved_count, 55)

        written = export_moves(report, str(self.path))
        header, *rows = self.read_csv()

        self.assertEqual(
            header, ["channel_id", "sequence_id", "old_node_id", "new_node_id", "room_no"]
        )
        self.assertEqual(written, report.moved_count)
        self.assertEqual(len(rows), report.moved_count)
        self.assertCountEqual(
            [tuple(map(int, row)) for row in rows],
            [(m.c, m.s, m.old_node, m.new_node, m.room_no) for m in report.moves],
        )

    def test_empty_guest_and_move_exports_keep_the_header(self):
        system = HotelSystem.initialize(2, 1, [0])
        report = system.remove_building(2)

        with self.subTest(export="guests"):
            self.assertEqual(export_guests(system, str(self.path)), 0)
            self.assertEqual(self.read_csv(), [["channel_id", "sequence_id", "node_id", "room_no"]])

        with self.subTest(export="moves"):
            self.assertEqual(export_moves(report, str(self.path)), 0)
            self.assertEqual(
                self.read_csv(),
                [["channel_id", "sequence_id", "old_node_id", "new_node_id", "room_no"]],
            )

    def test_export_rows_round_trips_utf8_and_csv_special_characters(self):
        note = 'ทดสอบ, "สองบรรทัด"\nบรรทัดที่สอง'
        results = [
            {"experiment": "A", "salt": "0", "K": 1000, "note": note},
            {"note": "ปกติ", "K": 1000, "salt": "1", "experiment": "A"},
        ]

        self.assertEqual(export_rows(results, str(self.path)), len(results))
        self.assertEqual(
            self.read_csv(),
            [
                ["experiment", "salt", "K", "note"],
                ["A", "0", "1000", note],
                ["A", "1", "1000", "ปกติ"],
            ],
        )


if __name__ == "__main__":
    unittest.main()
