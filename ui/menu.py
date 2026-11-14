"""Terminal menu for the Distributed Hilbert's Hotel simulation."""
from __future__ import annotations

from itertools import islice

from experiments.run_experiments import benchmark_system, compare_with_mod_n
from hotel import HotelError, HotelSystem, MoveReport
from hotel.guest import Guest

from .csv_export import export_guests, export_moves, export_rows

DISPLAY_LIMIT = 50
MENU_GROUPS = (
    ("HOTEL", ("1", "5", "6", "10")),
    ("GUESTS & ROOMS", ("2", "3", "4", "7", "8", "9")),
    ("EXPERIMENTS & FILES", ("11", "12", "13")),
)


def read_int(label: str, minimum: int = 1) -> int:
    try:
        value = int(input(f"{label}: "))
    except ValueError:
        raise ValueError(f"{label} must be an integer.") from None
    if value < minimum:
        raise ValueError(f"{label} must be at least {minimum}.")
    return value


def format_ratio(value: float | None) -> str:
    return "N/A (no guests)" if value is None else f"{value:.2%}"


def plural(count: int, word: str) -> str:
    return f"{count:,} {word}{'' if count == 1 else 's'}"


def show_guest(guest: Guest) -> None:
    print(f"Guest ({guest.c}, {guest.s}) | Building {guest.node_id} | Room {guest.room_no}")


def show_count(shown: int, total: int) -> None:
    if shown < total:
        print(f"Showing {shown:,} of {total:,} rows.")


def show_table(headers: tuple[str, ...], rows: list[tuple[int, ...]]) -> None:
    cells = [headers, *(tuple(map(str, row)) for row in rows)]
    widths = [max(map(len, column)) for column in zip(*cells)]
    for row in cells:
        print("  ".join(cell.ljust(width) for cell, width in zip(row, widths)).rstrip())


class Menu:
    def __init__(self) -> None:
        self.system: HotelSystem | None = None
        self.building_order: list[int] = []
        self.last_moves: MoveReport | None = None
        self.last_results: list[dict] = []

    def run(self) -> None:
        labels = {
            "1": "Set up a hotel",
            "2": "Check in one guest",
            "3": "Check in a group",
            "4": "Check out a guest",
            "5": "Add a building",
            "6": "Remove a building",
            "7": "Find a guest by ID",
            "8": "Find a guest by room",
            "9": "List occupied rooms",
            "10": "Show guests per building",
            "11": "Measure time and memory",
            "12": "Compare with Hash mod N",
            "13": "Export CSV",
        }
        actions = {
            "2": self._add_guest,
            "3": self._add_guests,
            "4": self._remove_guest,
            "5": self._add_building,
            "6": self._remove_building,
            "7": self._find_guest,
            "8": self._find_room,
            "9": self._list_rooms,
            "10": self._show_load,
            "11": self._benchmark,
            "12": self._compare,
            "13": self._export,
        }
        print("\nDistributed Hilbert's Hotel")
        print("=" * 43)
        self._show_menu(labels)
        try:
            while True:
                choice = input("\nSelect an option [Enter for menu, 0 to exit]: ").strip()
                if choice == "0":
                    break
                try:
                    if choice in {"", "?"}:
                        self._show_menu(labels)
                    elif choice == "1":
                        self._initialize()
                    elif choice not in actions:
                        print("Unknown option. Choose a number from the menu.")
                    elif self.system is None:
                        print("Choose 1 to set up a hotel first.")
                    else:
                        print(f"\n{labels[choice]}")
                        actions[choice](self.system)
                except (HotelError, ValueError, OSError) as error:
                    print(f"Could not complete the action. {error}")
        except (EOFError, KeyboardInterrupt):
            print()
        print("Goodbye.")

    def _show_menu(self, labels: dict[str, str]) -> None:
        if self.system is None:
            print("Choose 1 to set up your hotel.")
        else:
            print(f"Buildings: {len(self.building_order):,} | Guests: {self.system.guest_count:,}"
                  f" | Virtual nodes per building: {self.system.V:,}")
        for title, options in MENU_GROUPS:
            print(f"\n{title}")
            for option in options:
                print(f"  {option:>2}  {labels[option]}")

    def _initialize(self) -> None:
        print("\nSet up a hotel" if self.system is None else "\nSet up a replacement hotel")
        if self.system is not None:
            answer = input("Start over and discard the current hotel? [y/N]: ").strip().lower()
            if answer not in {"y", "yes"}:
                return
        n = read_int("Number of buildings (N)")
        v = read_int("Virtual nodes per building (V)")
        channels = read_int("Number of channels", minimum=0)
        sizes = [read_int(f"Guests in channel {c}", minimum=0) for c in range(1, channels + 1)]
        salt = input("Salt (Enter for the default): ")
        self.system = HotelSystem.initialize(n, v, sizes, salt)
        self.building_order = self.system.node_ids()
        self.last_moves = None
        self.last_results = []
        print(f"Hotel ready | Buildings: {n:,} | Guests: {self.system.guest_count:,}")

    def _add_guest(self, system: HotelSystem) -> None:
        guest = system.add_guest(read_int("Channel ID"), read_int("Sequence ID"))
        show_guest(guest)

    def _add_guests(self, system: HotelSystem) -> None:
        guests = system.add_guests(
            read_int("Channel ID"), read_int("First sequence ID"), read_int("Guest count", minimum=0)
        )
        print(f"Added {plural(len(guests), 'guest')}.")

    def _remove_guest(self, system: HotelSystem) -> None:
        guest = system.remove_guest(read_int("Channel ID"), read_int("Sequence ID"))
        print(f"Removed guest ({guest.c}, {guest.s}).")

    def _add_building(self, system: HotelSystem) -> None:
        node = read_int("Building ID")
        report = system.add_building(node)
        self.building_order.append(node)
        print(f"Added building {node}.")
        self._show_moves(report)

    def _remove_building(self, system: HotelSystem) -> None:
        node = read_int("Building ID")
        report = system.remove_building(node)
        self.building_order.remove(node)
        print(f"Removed building {node}.")
        self._show_moves(report)

    def _show_moves(self, report: MoveReport) -> None:
        self.last_moves = report
        print(f"Moved {report.moved_count:,} of {plural(report.total_guests, 'guest')}.")
        print(f"Move rate: {format_ratio(report.move_rate)}")
        preview = report.moves[:DISPLAY_LIMIT]
        if preview:
            show_table(
                ("Channel", "Sequence", "From building", "To building", "Room"),
                [(m.c, m.s, m.old_node, m.new_node, m.room_no) for m in preview],
            )
            show_count(len(preview), report.moved_count)
        path = input("Save the move report? Enter a CSV filename or press Enter to skip: ").strip()
        if path:
            try:
                count = export_moves(report, path)
            except OSError as error:
                print(f"The building change was done, but the CSV could not be saved: {error}")
            else:
                print(f"Saved {plural(count, 'row')} to {path}.")

    def _find_guest(self, system: HotelSystem) -> None:
        show_guest(system.find_guest(read_int("Channel ID"), read_int("Sequence ID")))

    def _find_room(self, system: HotelSystem) -> None:
        show_guest(system.find_by_room(read_int("Building ID"), read_int("Room number")))

    def _list_rooms(self, system: HotelSystem) -> None:
        rooms = system.list_rooms()
        if not rooms:
            print("There are no occupied rooms.")
            return
        preview = rooms[:DISPLAY_LIMIT]
        print(f"Occupied rooms: {len(rooms):,}")
        show_table(
            ("Building", "Room", "Channel", "Sequence"),
            [(g.node_id, g.room_no, g.c, g.s) for g in preview],
        )
        show_count(len(preview), len(rooms))

    def _show_load(self, system: HotelSystem) -> None:
        stats = system.load_stats()
        for node, count in islice(stats.counts.items(), DISPLAY_LIMIT):
            print(f"Building {node}: {plural(count, 'guest')}")
        show_count(min(len(stats.counts), DISPLAY_LIMIT), len(stats.counts))
        print(f"Total {stats.total} | Min {stats.minimum} | Max {stats.maximum}")
        cv = "N/A (no guests)" if stats.cv is None else f"{stats.cv:.3f}"
        print(f"Mean {stats.mean:.2f} | Std dev {stats.std:.2f} | CV {cv}")

    def _benchmark(self, system: HotelSystem) -> None:
        rows = benchmark_system(system)
        params = rows[0]
        print(f"N={params['N']} | V={params['V']} | K={params['K']} | salt={params['salt']!r}")
        for row in rows:
            print(f"{row['metric']}: {row['value']:.9g} {row['unit']}")
        print("Memory is what Python's tracemalloc traces for a full copy of the hotel, not the whole process.")
        self.last_results = rows

    def _compare(self, system: HotelSystem) -> None:
        action = input("Compare add or remove? ").strip().lower()
        if action not in {"add", "remove"}:
            raise ValueError("Enter add or remove.")
        node = read_int("Building ID")
        rows = compare_with_mod_n(system, action, node, building_order=self.building_order)
        guest_count = system.guest_count
        print("Timing: consistent hashing = the real add/remove on a copy of the hotel; "
              "hash mod N = update the building list + recompute every guest.")
        for method, label in (("consistent", "Consistent hashing"), ("mod_n", "Hash mod N")):
            values = {row["metric"]: row["value"] for row in rows if row["method"] == method}
            moved = values[f"moves_{action}"]
            rate = format_ratio(values[f"move_rate_{action}"])
            seconds = values[f"time_{action}"]
            print(f"{label}: {moved:,} of {guest_count:,} moved ({rate}) | {seconds:.6f} seconds")
        self.last_results = [
            {
                **row, "action": action, "node_id": node, "N": len(self.building_order),
                "V": system.V, "K": guest_count, "salt": system.salt,
            }
            for row in rows
        ]

    def _export(self, system: HotelSystem) -> None:
        print("  1  Current guests\n  2  Latest building move report\n  3  Latest experiment results")
        selection = input("Select what to export [Enter to go back]: ").strip().lower()
        if not selection:
            return
        kind = {"1": "guests", "2": "moves", "3": "results"}.get(selection, selection)
        if kind not in {"guests", "moves", "results"}:
            raise ValueError("Choose 1 for guests, 2 for moves, or 3 for results.")
        if kind == "moves" and self.last_moves is None:
            print("Add or remove a building first to create a move report.")
            return
        if kind == "results" and not self.last_results:
            print("Run option 11 or 12 first to create results.")
            return
        path = input(f"CSV filename [e.g. {kind}.csv, Enter to go back]: ").strip()
        if not path:
            return
        if kind == "guests":
            count = export_guests(system, path)
        elif kind == "moves":
            count = export_moves(self.last_moves, path)
        else:
            count = export_rows(self.last_results, path)
        print(f"Saved {plural(count, 'row')} to {path}.")
