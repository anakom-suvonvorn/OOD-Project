"""Experiments A, B, C (owner: P4). Run: python -m experiments.run_experiments

Writes results/experiment_*.csv in the long format of PLAN.md section 11.3.
"""
from __future__ import annotations

import csv
import time
from pathlib import Path
from typing import Any

from .measure import time_call, measure_memory, get_system_env
from hotel.hotel_system import HotelSystem

SALTS = ("0", "1", "2")
CHANNELS = 10
SEARCH_BATCH_SIZE = 1000

def append_metric(rows: list[dict], exp: str, method: str, salt: str, k: int, n: int, v: int, metric: str, val: float | int, unit: str):
    """Helper for formatted Long-Format CSV writing."""
    rows.append({
        "experiment": exp,
        "method": method,
        "salt": salt,
        "K": k,
        "N": n,
        "V": v,
        "metric": metric,
        "value": val,
        "unit": unit
    })
    
def _get_moves_count(report: Any) -> int:
    """Extract number of moves from MoveReport object or integer count."""
    if hasattr(report, "moves"):
        return len(report.moves)
    elif hasattr(report, "total_moves"):
        return report.total_moves
    elif isinstance(report, (int, float)):
        return int(report)
    return 0

def _mod_n_moves(system: HotelSystem, action: str, target_node: int) -> int:
    """Calculate exact guest moves under Hash Mod N when adding or removing target_node."""
    nodes = system.node_ids()
    n = len(nodes)
    if n == 0:
        return 0

    guests = list(system.guests())
    moves = 0

    if action == "add":
        new_n = n + 1
        for g in guests:
            old_node = (g.pos % n) + 1
            new_node = (g.pos % new_n) + 1
            if old_node != new_node:
                moves += 1
    elif action == "remove":
        new_n = max(1, n - 1)
        for g in guests:
            old_node = (g.pos % n) + 1
            new_node = (g.pos % new_n) + 1
            if old_node != new_node:
                moves += 1

    return moves

def channel_sizes(k: int, channels: int = CHANNELS) -> list[int]:
    """Split k guests over `channels` channels as evenly as possible (sizes differ by at most 1)."""
    base = k // channels
    remainders = k % channels
    
    return [base + 1 if i < remainders else base for i in range(channels)]

def run_experiment_a(salts=SALTS) -> list[dict]:
    """K = 1,000 / 10,000 / 100,000 with N = 10, V = 32: time to place, search, sort; memory."""
    rows = []
    n = 10
    v = 32
    
    for k in (1000, 10000, 100000):
        cs = channel_sizes(k)
        for salt in salts:
            try:
                system, t_place = time_call(HotelSystem.initialize, n, v, cs, salt = salt)
                _, current_mib, peak_mib = measure_memory(HotelSystem.initialize, n, v, cs, salt = salt)
                
                guest_sample = list(system.guests())
                search_target = [(guest_sample[i % len(guest_sample)].c, guest_sample[i % len(guest_sample)].s) for i in range(SEARCH_BATCH_SIZE)]
                
                def search_batch():
                    for c, s in search_target:
                        system.find_guest(c, s)
                        
                _, total_search_guest_time = time_call(search_batch)
                t_search_guest = total_search_guest_time / SEARCH_BATCH_SIZE
                
                def search_room_batch():
                    for i in range(SEARCH_BATCH_SIZE):
                        g = guest_sample[i % len(guest_sample)]
                        system.find_by_room(g.node_id, g.room_no)
                        
                _, total_search_room_time = time_call(search_room_batch)
                t_search_room = total_search_room_time / SEARCH_BATCH_SIZE
                
                _, t_sorted_room = time_call(system.list_rooms)
                
                append_metric(rows, "A", "consistent", salt, k, n, v, "time_place", t_place, "seconds")
                append_metric(rows, "A", "consistent", salt, k, n, v, "time_search_guest", t_search_guest, "seconds")
                append_metric(rows, "A", "consistent", salt, k, n, v, "time_search_room", t_search_room, "seconds")
                append_metric(rows, "A", "consistent", salt, k, n, v, "time_sort", t_sorted_room, "seconds")
                append_metric(rows, "A", "consistent", salt, k, n, v, "memory_current", current_mib, "MiB")
                append_metric(rows, "A", "consistent", salt, k, n, v, "memory_peak", peak_mib, "MiB")
            except MemoryError:
                print(f"[WARN] Memory limit exceeded at K={k}, salt={salt}")
                break
    save_to_csv(rows, "experiment_a.csv")

def run_experiment_b(salts=SALTS) -> list[dict]:
    """N = 5 / 10 / 20 with K = 10,000, V = 32: add 1 and remove 1 building, both methods."""
    result = []
    k = 10000
    v = 32
    for n in (5, 10, 20):
        middle = n // 2 + 1
        cs = channel_sizes(k)
        for salt in salts:
            base_system = HotelSystem.initialize(n, v, cs, salt)
            for action, target_node in [("add", n + 1), ("remove", middle)]:
                comp_result = compare_with_mod_n(base_system, action, target_node)
                for res in comp_result:
                    res.update({"experiment": "B", "K": k, "N": n, "V": v, "salt": salt})
                    result.append(res)
    
    save_to_csv(result, "experiment_b.csv")
    return result

def run_experiment_c(salts=SALTS) -> list[dict]:
    """V = 1 / 8 / 32 with N = 10, K = 10,000: guests per building, CV, memory, moves."""
    result = []
    k = 10000
    n = 10
    cs = channel_sizes(k)
    middle = n // 2 + 1
    for v in (1, 8, 32):
        for salt in salts:
            system, current_mib, peak_mib = measure_memory(HotelSystem.initialize, n, v, cs, salt)
            
            stats = system.load_stats()
            
            sys_add = system.clone()
            report_add = sys_add.add_building(n + 1)
            move_add = _get_moves_count(report_add)
            
            sys_rem = system.clone()
            report_rem = sys_rem.remove_building(middle)
            move_rem = _get_moves_count(report_rem)
            
            append_metric(result, "C", "consistent", salt, k, n, v, "guests_max", stats.maximum, "guests")
            append_metric(result, "C", "consistent", salt, k, n, v, "guests_min", stats.minimum, "guests")
            append_metric(result, "C", "consistent", salt, k, n, v, "guests_mean", stats.mean, "guests")
            append_metric(result, "C", "consistent", salt, k, n, v, "guests_std", stats.std, "guests")
            append_metric(result, "C", "consistent", salt, k, n, v, "guests_cv", stats.cv if stats.cv is not None else 0.0, "ratio")
            append_metric(result, "C", "consistent", salt, k, n, v, "memory_current", current_mib, "MiB")
            append_metric(result, "C", "consistent", salt, k, n, v, "memory_peak", peak_mib, "MiB")
            append_metric(result, "C", "consistent", salt, k, n, v, "moves_add", move_add, "guests")
            append_metric(result, "C", "consistent", salt, k, n, v, "moves_remove", move_rem, "guests")
            
    save_to_csv(result, "experiment_c.csv")
    return result

def benchmark_system(system: HotelSystem) -> list[dict]:
    """For the menu: time the main operations on (a clone of) the current system. Must not change `system`."""
    sys = system.clone()
    result = []
    
    guest_sample = list(sys.guests())
    if guest_sample:
        search_target = [(guest_sample[i % len(guest_sample)].c, [i % len(guest_sample)].s) for i in range(min(SEARCH_BATCH_SIZE, len(guest_sample)))]

        def search_batch():
            for c, s in search_target:
                sys.find_guest(c, s)
                
        _,t_search = time_call(search_batch)
        t_search_per_op = t_search / len(search_target)
    else:
        t_search_per_op = 0.0
    
    _, t_sort = time_call(sys.list_rooms)
    _, t_stats = time_call(sys.load_stats)
    
    result.append({"operation": "search_guest", "time_sec": t_search_per_op})
    result.append({"operation": "list_rooms", "time_sec": t_sort})
    result.append({"operation": "load_stats", "time_sec": t_stats})

    return result

def compare_with_mod_n(system: HotelSystem, action: str, node_id: int) -> list[dict]:
    """For the menu: moves / rate / time of `action` ("add" or "remove") for consistent hashing vs
    hash mod N on the current guests. Works on clones - must not change `system`."""
    results = []
    k = system.guest_count
    metric_prefix = "_add" if action == "add" else "_remove"
    
    sys_ch = system.clone()
    if action == "add":
        report_ch, t_ch = time_call(sys_ch.add_building, node_id)
    elif action == "remove":
        report_ch, t_ch = time_call(sys_ch.remove_building, node_id)
    else:
        raise ValueError(f"Unknown action:  {action}")
    
    move_ch = _get_moves_count(report_ch)
    rate_ch = move_ch / k if k > 0 else 0.0
    
    results.append({"method": "consistent", "metric": f"moves{metric_prefix}", "value": move_ch, "unit": "guests"})
    results.append({"method": "consistent", "metric": f"move_rate{metric_prefix}", "value": rate_ch, "unit": "ratio"})
    results.append({"method": "consistent", "metric": f"time{metric_prefix}", "value": t_ch, "unit": "seconds"})
    
    t0 = time.perf_counter()
    move_mod = _mod_n_moves(system, action, node_id)
    time_mod = time.perf_counter() - t0
    rate_mod = move_mod / k if k > 0 else 0.0
    
    results.append({"method": "mod_n", "metric": f"moves{metric_prefix}", "value": move_mod, "unit": "guests"})
    results.append({"method": "mod_n", "metric": f"move_rate{metric_prefix}", "value": rate_mod, "unit": "ratio"})
    results.append({"method": "mod_n", "metric": f"time{metric_prefix}", "value": time_mod, "unit": "seconds"})
    
    return results

def save_to_csv(data: list[dict], filename: str) -> None:
    """Write rows list directly into results/*.csv in long format."""
    if not data:
        return
    filepath = Path("results") / filename
    filepath.parent.mkdir(parents=True, exist_ok=True)
    keys = ["experiment", "method", "salt", "K", "N", "V", "metric", "value", "unit"]
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(data)
        
def record_system_environment() -> None:
    env = get_system_env()

    filepath = Path("results") / "specs_when_experiment.csv"
    filepath.parent.mkdir(parents=True, exist_ok=True)
    keys = ["python_version", "platform", "processor", "cpu_count"]
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerow(env)
    return

def main() -> None:
    print("Executiing System Environment")
    record_system_environment()    
    print("Executing Experiment A...")
    run_experiment_a()
    print("Executing Experiment B...")
    run_experiment_b()
    print("Executing Experiment C...")
    run_experiment_c()


if __name__ == "__main__":
    main()
