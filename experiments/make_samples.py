"""Write the sample CSV files for submission (PDF 10.1 item 3): python -m experiments.make_samples

Builds one hotel (N = 10, V = 32, 10 channels x 100 guests, salt "0"), exports its guests, then adds
building 11 and removes building 6 on separate copies and exports each move list.
results/sample_info.csv records the parameters and row count of every file.
"""
from __future__ import annotations

import os

from hotel import HotelSystem
from ui.csv_export import export_guests, export_moves, export_rows

RESULTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
N, V, CHANNELS, PER_CHANNEL, SALT = 10, 32, 10, 100, "0"


def main() -> None:
    os.makedirs(RESULTS_DIR, exist_ok=True)
    system = HotelSystem.initialize(N, V, [PER_CHANNEL] * CHANNELS, SALT)
    params = {"N": N, "V": V, "K": system.guest_count, "salt": SALT}
    info = []

    path = os.path.join(RESULTS_DIR, "sample_guests.csv")
    rows = export_guests(system, path)
    info.append({"file": "sample_guests.csv", **params, "action": "", "node_id": "", "rows": rows})

    for action, node_id in (("add", N + 1), ("remove", N // 2 + 1)):
        copy = system.clone()
        report = copy.add_building(node_id) if action == "add" else copy.remove_building(node_id)
        copy.verify_integrity()
        name = f"sample_moves_{action}.csv"
        rows = export_moves(report, os.path.join(RESULTS_DIR, name))
        info.append({"file": name, **params, "action": action, "node_id": node_id, "rows": rows})

    export_rows(info, os.path.join(RESULTS_DIR, "sample_info.csv"))
    for row in info:
        print(f"{row['file']}: {row['rows']:,} rows")


if __name__ == "__main__":
    main()
