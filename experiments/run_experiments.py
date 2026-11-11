"""Experiments A, B, C (owner: P4). Run: python -m experiments.run_experiments

Writes results/experiment_*.csv in the long format of PLAN.md section 11.3.
"""
from __future__ import annotations

from measure import time_call, measure_memory

from hotel import HotelSystem

SALTS = ("0", "1", "2")
CHANNELS = 10


def channel_sizes(k: int, channels: int = CHANNELS) -> list[int]:
    """Split k guests over `channels` channels as evenly as possible (sizes differ by at most 1)."""
    base = k / channels
    remainders = k % channels
    
    return [base + 1 if i < remainders else base for i in range(channels)]

def run_experiment_a(salts=SALTS) -> list[dict]:
    """K = 1,000 / 10,000 / 100,000 with N = 10, V = 32: time to place, search, sort; memory."""
    result = []
    n = 10
    v = 32
    
    for k in (1000, 10000, 100000):
        cs = channel_sizes(k)
        for salt in salts:
            system, t_place = time_call(HotelSystem.initialize, n, v, cs, salt = salt)
            current_mib, peak_mib = measure_memory(HotelSystem.initialize, n, v, cs, salt = salt)
            
            def search_all():
                for g in system.guests():
                    system.find_guest(g.c, g.s)
                    
            _, t_search = time_call(search_all())
            
            _, t_sort = time_call(system.list_rooms())
            
            result.append({
                "experiment": "A",
                "K": k,
                "N": n,
                "V": v,
                "salt": salt,
                "time_place_sec": t_place,
                "time_search_sec": t_search,
                "time_sort_sec": t_sort,
                "memory_current_mib": current_mib,
                "memory_peak_mib": peak_mib,
            })
    raise NotImplementedError("P4")


def run_experiment_b(salts=SALTS) -> list[dict]:
    """N = 5 / 10 / 20 with K = 10,000, V = 32: add 1 and remove 1 building, both methods."""
    raise NotImplementedError("P4")


def run_experiment_c(salts=SALTS) -> list[dict]:
    """V = 1 / 8 / 32 with N = 10, K = 10,000: guests per building, CV, memory, moves."""
    raise NotImplementedError("P4")


def benchmark_system(system: HotelSystem) -> list[dict]:
    """For the menu: time the main operations on (a clone of) the current system. Must not change `system`."""
    raise NotImplementedError("P4")


def compare_with_mod_n(system: HotelSystem, action: str, node_id: int) -> list[dict]:
    """For the menu: moves / rate / time of `action` ("add" or "remove") for consistent hashing vs
    hash mod N on the current guests. Works on clones - must not change `system`."""
    raise NotImplementedError("P4")


def main() -> None:
    raise NotImplementedError("P4")


if __name__ == "__main__":
    main()
