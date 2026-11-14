
LOOKUP_COUNT = 1000
MENU_GROUPS = (
    ("HOTEL", ("1", "5", "6", "10")),
    ("GUESTS & ROOMS", ("2", "3", "4", "7", "8", "9")),
    ("EXPERIMENTS & FILES", ("11", "12", "13")),
)

def show_count(shown: int, total: int) -> None:
    if shown < total:
    print(f"Showing {shown} of {total} rows.")
        print(f"Showing {shown:,} of {total:,} rows.")


def show_table(headers: tuple[str, ...], rows: list[tuple[int, ...]]) -> None:
    cells = [headers, *(tuple(map(str, row)) for row in rows)]
    widths = [max(map(len, column)) for column in zip(*cells)]
    for row in cells:
        print("  ".join(cell.ljust(width) for cell, width in zip(row, widths)).rstrip())


class Menu:
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
            "2": ("Add a guest", self._add_guest),
            "3": ("Add a group of guests", self._add_guests),
            "4": ("Remove a guest", self._remove_guest),
            "5": ("Add a building", self._add_building),
            "6": ("Remove a building", self._remove_building),
            "7": ("Find by guest ID", self._find_guest),
            "8": ("Find by room", self._find_room),
            "9": ("List occupied rooms", self._list_rooms),
            "10": ("Show load statistics", self._show_load),
            "11": ("Measure time and memory", self._benchmark),
            "12": ("Compare with Hash mod N", self._compare),
            "13": ("Export CSV", self._export),
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
        print("Distributed Hilbert's Hotel")
        choice = "?"
        print("\nDistributed Hilbert's Hotel")
        print("=" * 43)
        self._show_menu(labels)
        try:
            while choice != "0":
            while True:
                choice = input("\nSelect an option [Enter for menu, 0 to exit]: ").strip()
                if choice == "0":
                    break
                try:
                    if choice == "?":
                        print("\n1. Create a new hotel")
                        for number, (label, _) in actions.items():
                            print(f"{number}. {label}")
                        print("0. Exit")
                    if choice in {"", "?"}:
                        self._show_menu(labels)
                    elif choice == "1":
                    elif choice not in actions:
                        print("Unknown option. Enter ? to view the menu.")
                        print("Unknown option. Choose a number from the menu.")
                    elif self.system is None:
                        print("Create a hotel with option 1 first.")
                        print("Choose 1 to set up a hotel first.")
                    else:
                        print(f"\n{labels[choice]}")
                        actions[choice][1](self.system)
                        actions[choice](self.system)
                except (HotelError, ValueError, OSError) as error:
                    print(f"Error: {error}")
                choice = input("\nChoice (? for menu): ").strip()
