"""Timing and memory helpers (owner: P4).

Time:   time.perf_counter(), never includes input / printing / file writing.
Memory: tracemalloc, in a SEPARATE run from timing; report MiB (bytes / 2**20).
"""
from __future__ import annotations

import time
import tracemalloc
from typing import Any, Callable


def time_call(fn: Callable[..., Any], *args: Any) -> tuple[Any, float]:
    """Run fn(*args) once; return (result, seconds)."""
    start_t = time.perf_counter()
    result = fn(*args)
    end_t = time.perf_counter()
    
    worked_time = end_t - start_t
    return result, worked_time


def measure_memory(fn: Callable[..., Any], *args: Any) -> tuple[Any, float, float]:
    """Run fn(*args) under tracemalloc from a clean start; return (result, current_mib, peak_mib)."""
    tracemalloc.start()
    tracemalloc.reset_peak()
    
    try:
        result = fn(*args)
        current_bytes, peak_bytes = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
        
    mib = 2 ** 20
    current_mib = current_bytes / mib
    peak_mib = peak_bytes / mib
    
    return result, current_mib, peak_mib
