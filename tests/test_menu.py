"""Drive the terminal menu with scripted input."""
import csv
import io
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from experiments.run_experiments import compare_with_mod_n
from ui.menu import Menu


class MenuTests(unittest.TestCase):
    def setUp(self) -> None:
        self.menu = Menu()

    def run_menu(self, answers: list[str]) -> str:
        output = io.StringIO()
        with patch("builtins.input", side_effect=[*answers, "0"]), redirect_stdout(output):
            self.menu.run()
        return output.getvalue()

    def test_option_before_setup(self) -> None:
        output = self.run_menu(["2"])
        self.assertIn("Choose 1 to set up a hotel first.", output)

    def test_full_session(self) -> None:
        with TemporaryDirectory() as directory:
            guest_csv = Path(directory) / "guests.csv"
            unavailable_csv = Path(directory) / "missing" / "moves.csv"
            output = self.run_menu([
                "1", "3", "4", "2", "5", "5", "",
                "2", "1", "6",       # Check in one guest.
                "2", "1", "6",       # Duplicate guest.
                "2", "abc",          # Invalid channel.
                "3", "1", "4", "4",  # Overlap includes an existing and a new guest.
                "4", "9", "1",       # Missing guest.
                "5", "2",            # Existing building.
                "6", "9",            # Missing building.
                "7", "9", "1",       # Missing guest.
                "8", "1", "999",     # Unoccupied room.
                "5", "7", str(unavailable_csv),
                "6", "7", "",
                "9", "10", "11",
                "12", "add", "8",
                "12", "remove", "3",
                "13", "1", str(guest_csv),
            ])
            with guest_csv.open(encoding="utf-8", newline="") as stream:
                guest_rows = list(csv.DictReader(stream))

        for message in (
            "guest (1, 6) is already in the hotel",
            "Channel ID must be an integer.",
            "guest (1, 4) is already in the hotel",
            "guest (9, 1) is not in the hotel",
            "building 2 already exists",
            "building 9 does not exist",
            "room 999 in building 1 is unoccupied",
            "The building change was done, but the CSV could not be saved:",
            "Removed building 7.",
            "Occupied rooms: 11",
            "time_search_guest:",
            "Consistent hashing:",
            "Goodbye.",
        ):
            with self.subTest(message=message):
                self.assertIn(message, output)
        self.assertEqual(output.count("guest (9, 1) is not in the hotel"), 2)
        self.assertEqual(self.menu.system.guest_count, 11)
        self.assertEqual(len(guest_rows), self.menu.system.guest_count)
        self.assertEqual(self.menu.system.node_ids(), [1, 2, 3])
        self.assertRegex(output, r"CV \d+\.\d{3}\n")
        self.menu.system.verify_integrity()

    def test_compare_does_not_change_hotel(self) -> None:
        self.run_menu(["1", "3", "4", "1", "20", ""])
        assignments = self.menu.system.assignments()
        nodes = self.menu.system.node_ids()
        output = self.run_menu([
            "12", "add", "7", "12", "remove", "2",
            "12", "add", "2", "12", "remove", "99",
        ])
        self.assertEqual(output.count("Consistent hashing:"), 2)
        self.assertIn("Could not complete the action. building 2 already exists", output)
        self.assertIn("Could not complete the action. building 99 does not exist", output)
        self.assertEqual(self.menu.system.assignments(), assignments)
        self.assertEqual(self.menu.system.node_ids(), nodes)
        self.assertEqual(self.menu.building_order, nodes)

    def test_compare_uses_building_order(self) -> None:
        self.run_menu(["1", "3", "4", "1", "5", "", "5", "7", "", "5", "5", ""])
        with patch("ui.menu.compare_with_mod_n", wraps=compare_with_mod_n) as compare:
            self.run_menu(["12", "remove", "2"])
        compare.assert_called_once_with(self.menu.system, "remove", 2, building_order=[1, 2, 3, 7, 5])

    def test_remove_last_building_is_refused(self) -> None:
        output = self.run_menu(["1", "1", "4", "0", "", "6", "1", "12", "remove", "1"])
        self.assertEqual(output.count("last building"), 2)
        self.assertEqual(self.menu.system.node_ids(), [1])

    def test_end_of_input(self) -> None:
        output = io.StringIO()
        with patch("builtins.input", side_effect=EOFError), redirect_stdout(output):
            self.menu.run()
        self.assertIn("Goodbye.", output.getvalue())

    def test_export_results_after_benchmark(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "results.csv"
            output = self.run_menu([
                "1", "2", "4", "1", "0", "0", "3", "1", "1", "1",
                "10", "11", "13", "3", str(path),
            ])
            with path.open(encoding="utf-8", newline="") as stream:
                rows = list(csv.DictReader(stream))

        self.assertEqual(len(rows), len(self.menu.last_results))
        self.assertIn("memory_peak", {row["metric"] for row in rows})
        self.assertIn("Added 1 guest.\n", output)
        self.assertRegex(output, r"Building [12]: 1 guest\n")
        self.assertIn("CV 1.000", output)
        self.assertIn("N=2 | V=4 | K=1 | salt='0'", output)
        self.assertIn("tracemalloc traces for a full copy", output)


if __name__ == "__main__":
    unittest.main()
