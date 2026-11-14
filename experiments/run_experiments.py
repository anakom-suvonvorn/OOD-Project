"""Experiments A, B, C (owner: P4). Run: python -m experiments.run_experiments

Writes results/experiment_*.csv in the long format of PLAN.md section 11.3:
experiment, method, salt, K, N, V, metric, value, unit
"""
from __future__ import annotations

import csv
import time
from pathlib import Path

from .measure import get_system_env, measure_memory, time_call
from hotel.hotel_system import HotelSystem
from hotel.mod_n import ModNRouter
from hotel.ring import HashRing

SALTS = ("0", "1", "2")
CHANNELS = 10
SEARCH_BATCH_SIZE = 1000
RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"
CSV_COLUMNS = ["experiment", "method", "salt", "K", "N", "V", "metric", "value", "unit"]


def append_metric(rows: list[dict], exp: str, method: str, salt: str, k: int, n: int, v: int,
                  metric: str, val: float | int | None, unit: str) -> None:
    """Append one row in the long CSV format."""
    rows.append({
        "experiment": exp,
        "method": method,
        "salt": salt,
        "K": k,
        "N": n,
        "V": v,
        "metric": metric,
        "value": val,
        "unit": unit,
    })


def channel_sizes(k: int, channels: int = CHANNELS) -> list[int]:
    """Split k guests over `channels` channels as evenly as possible (sizes differ by at most 1)."""
    base = k // channels
    remainders = k % channels
    return [base + 1 if i < remainders else base for i in range(channels)]


def _search_targets(system: HotelSystem) -> list:
    """SEARCH_BATCH_SIZE guests to search for, cycling through the guests if K < batch size."""
    guests = list(system.guests())
    if not guests:
        return []
    return [guests[i % len(guests)] for i in range(SEARCH_BATCH_SIZE)]


def _time_searches(system: HotelSystem) -> tuple[float, float]:
    """Seconds per search (guest id, then room address), timed over one batch of 1,000."""
    targets = _search_targets(system)
    if not targets:
        return 0.0, 0.0
    ids = [(g.c, g.s) for g in targets]
    rooms = [(g.node_id, g.room_no) for g in targets]

    def by_guest():
        for c, s in ids:
            system.find_guest(c, s)

    def by_room():
        for node_id, room_no in rooms:
            system.find_by_room(node_id, room_no)

    _, t_guest = time_call(by_guest)
    _, t_room = time_call(by_room)
    return t_guest / len(ids), t_room / len(rooms)


def _place_all(system: HotelSystem, sizes: list[int]) -> None:
    """Place every channel's guests into a system whose ring is already built."""
    for c, size in enumerate(sizes, start=1):
        system.add_guests(c, 1, size)


def _mod_n_change(system: HotelSystem, action: str, node_id: int) -> tuple[int, float]:
    """hash mod N on the same guest positions and the same building change (PDF 7.1).

    Building ids are kept in the order they were added (ascending ids, which is the order
    initialize adds them); "add" appends, "remove" deletes the target and keeps the order
    of the rest, and moves are counted by comparing real building ids, not indexes.
    The timed part is the router update plus recomputing every guest, because mod N has no
    way to find who moved without checking all K guests. Returns (moved, seconds).
    """
    router = ModNRouter()
    router.build(system.node_ids())
    guests = list(system.guests())
    before = [router.node_for(g.pos) for g in guests]

    start = time.perf_counter()
    if action == "add":
        router.add_node(node_id)
    elif action == "remove":
        router.remove_node(node_id)
    else:
        raise ValueError(f"unknown action: {action}")
    moved = sum(1 for g, old in zip(guests, before) if router.node_for(g.pos) != old)
    seconds = time.perf_counter() - start
    return moved, seconds


def run_experiment_a(salts=SALTS) -> list[dict]:
    """K = 1,000 / 10,000 / 100,000 with N = 10, V = 32: time to build the ring, place guests,
    search, sort; memory (separate run)."""
    rows: list[dict] = []
    n, v = 10, 32

    for k in (1000, 10000, 100000):
        sizes = channel_sizes(k)
        for salt in salts:
            # Ring build and guest placement timed separately (PDF 7.2).
            _, t_ring = time_call(HashRing(v, salt).build, range(1, n + 1))
            system = HotelSystem(v, salt)
            system.ring.build(range(1, n + 1))
            _, t_place = time_call(_place_all, system, sizes)

            t_search_guest, t_search_room = _time_searches(system)
            _, t_sort = time_call(system.list_rooms)

            # Memory in its own run, never mixed with timing.
            _, current_mib, peak_mib = measure_memory(HotelSystem.initialize, n, v, sizes, salt)

            append_metric(rows, "A", "consistent", salt, k, n, v, "time_ring_build", t_ring, "seconds")
            append_metric(rows, "A", "consistent", salt, k, n, v, "time_place", t_place, "seconds")
            append_metric(rows, "A", "consistent", salt, k, n, v, "time_search_guest", t_search_guest, "seconds")
            append_metric(rows, "A", "consistent", salt, k, n, v, "time_search_room", t_search_room, "seconds")
            append_metric(rows, "A", "consistent", salt, k, n, v, "time_sort", t_sort, "seconds")
            append_metric(rows, "A", "consistent", salt, k, n, v, "memory_current", current_mib, "MiB")
            append_metric(rows, "A", "consistent", salt, k, n, v, "memory_peak", peak_mib, "MiB")

    save_to_csv(rows, "experiment_a.csv")
    return rows


def run_experiment_b(salts=SALTS) -> list[dict]:
    """N = 5 / 10 / 20 with K = 10,000, V = 32: add building N + 1 and remove building
    N // 2 + 1, each from the same starting state, for both methods."""
    rows: list[dict] = []
    k, v = 10000, 32
    sizes = channel_sizes(k)
    for n in (5, 10, 20):
        middle = n // 2 + 1
        for salt in salts:
            base_system = HotelSystem.initialize(n, v, sizes, salt)
            for action, target_node in (("add", n + 1), ("remove", middle)):
                for res in compare_with_mod_n(base_system, action, target_node):
                    append_metric(rows, "B", res["method"], salt, k, n, v,
                                  res["metric"], res["value"], res["unit"])

    save_to_csv(rows, "experiment_b.csv")
    return rows


def run_experiment_c(salts=SALTS) -> list[dict]:
    """V = 1 / 8 / 32 with N = 10, K = 10,000: guests per building, CV, memory, moves."""
    rows: list[dict] = []
    k, n = 10000, 10
    sizes = channel_sizes(k)
    middle = n // 2 + 1
    for v in (1, 8, 32):
        for salt in salts:
            system, current_mib, peak_mib = measure_memory(HotelSystem.initialize, n, v, sizes, salt)
            # The ring alone, so the effect of V is not hidden by the K guests' data.
            _, ring_current_mib, ring_peak_mib = measure_memory(HashRing(v, salt).build, range(1, n + 1))
            stats = system.load_stats()
            report_add = system.clone().add_building(n + 1)
            report_rem = system.clone().remove_building(middle)

            append_metric(rows, "C", "consistent", salt, k, n, v, "guests_max", stats.maximum, "guests")
            append_metric(rows, "C", "consistent", salt, k, n, v, "guests_min", stats.minimum, "guests")
            append_metric(rows, "C", "consistent", salt, k, n, v, "guests_mean", stats.mean, "guests")
            append_metric(rows, "C", "consistent", salt, k, n, v, "guests_std", stats.std, "guests")
            append_metric(rows, "C", "consistent", salt, k, n, v, "guests_cv", stats.cv, "ratio")
            append_metric(rows, "C", "consistent", salt, k, n, v, "ring_points", len(system.ring), "points")
            append_metric(rows, "C", "consistent", salt, k, n, v, "memory_current", current_mib, "MiB")
            append_metric(rows, "C", "consistent", salt, k, n, v, "memory_peak", peak_mib, "MiB")
            append_metric(rows, "C", "consistent", salt, k, n, v, "memory_ring_current", ring_current_mib, "MiB")
            append_metric(rows, "C", "consistent", salt, k, n, v, "memory_ring_peak", ring_peak_mib, "MiB")
            append_metric(rows, "C", "consistent", salt, k, n, v, "moves_add", report_add.moved_count, "guests")
            append_metric(rows, "C", "consistent", salt, k, n, v, "move_rate_add", report_add.move_rate, "ratio")
            append_metric(rows, "C", "consistent", salt, k, n, v, "moves_remove", report_rem.moved_count, "guests")
            append_metric(rows, "C", "consistent", salt, k, n, v, "move_rate_remove", report_rem.move_rate, "ratio")

    save_to_csv(rows, "experiment_c.csv")
    return rows


def benchmark_system(system: HotelSystem) -> list[dict]:
    """For the menu: time and memory of the main operations on a clone of the current system.

    Must not change `system`. Rows: {"K", "N", "V", "salt", "metric", "value", "unit"}.
    Searches are timed over a batch of 1,000 and reported per search (PDF 7.2)."""
    params = {"K": system.guest_count, "N": len(system.node_ids()), "V": system.V, "salt": system.salt}
    copy = system.clone()
    rows: list[dict] = []

    def add(metric: str, value: float, unit: str) -> None:
        rows.append({**params, "metric": metric, "value": value, "unit": unit})

    t_guest, t_room = _time_searches(copy)
    add("time_search_guest", t_guest, "seconds per search")
    add("time_search_room", t_room, "seconds per search")
    _, t_sort = time_call(copy.list_rooms)
    add("time_list_rooms", t_sort, "seconds")
    _, t_stats = time_call(copy.load_stats)
    add("time_load_stats", t_stats, "seconds")

    # Memory of a full copy of the hotel, measured in a run of its own.
    _, current_mib, peak_mib = measure_memory(system.clone)
    add("memory_current", current_mib, "MiB (tracemalloc)")
    add("memory_peak", peak_mib, "MiB (tracemalloc)")
    return rows


def compare_with_mod_n(system: HotelSystem, action: str, node_id: int) -> list[dict]:
    """For the menu and experiment B: moves / rate / time of `action` ("add" or "remove")
    for consistent hashing vs hash mod N on the current guests. Works on a clone - never
    changes `system`. Raises HotelError (e.g. DuplicateNodeError) for an invalid change.
    Rows: {"method", "metric", "value", "unit"}; move rate is None when K == 0."""
    if action not in ("add", "remove"):
        raise ValueError(f"unknown action: {action}")
    k = system.guest_count
    suffix = "_" + action

    ch_system = system.clone()
    change = ch_system.add_building if action == "add" else ch_system.remove_building
    report, t_ch = time_call(change, node_id)

    moved_mod, t_mod = _mod_n_change(system, action, node_id)
    rate_mod = moved_mod / k if k > 0 else None

    return [
        {"method": "consistent", "metric": "moves" + suffix, "value": report.moved_count, "unit": "guests"},
        {"method": "consistent", "metric": "move_rate" + suffix, "value": report.move_rate, "unit": "ratio"},
        {"method": "consistent", "metric": "time" + suffix, "value": t_ch, "unit": "seconds"},
        {"method": "mod_n", "metric": "moves" + suffix, "value": moved_mod, "unit": "guests"},
        {"method": "mod_n", "metric": "move_rate" + suffix, "value": rate_mod, "unit": "ratio"},
        {"method": "mod_n", "metric": "time" + suffix, "value": t_mod, "unit": "seconds"},
    ]


def save_to_csv(data: list[dict], filename: str) -> None:
    """Write rows into results/<filename> in the long format."""
    if not data:
        return
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_DIR / filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(data)


def record_system_environment() -> None:
    """Save the machine and Python version the results were produced on."""
    env = get_system_env()
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_DIR / "specs_when_experiment.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(env))
        writer.writeheader()
        writer.writerow(env)


def main() -> None:
    print("Recording system environment...")
    record_system_environment()
    print("Running experiment A...")
    run_experiment_a()
    print("Running experiment B...")
    run_experiment_b()
    print("Running experiment C...")
    run_experiment_c()
    print(f"Done. CSV files are in {RESULTS_DIR}")


if __name__ == "__main__":
    main()
