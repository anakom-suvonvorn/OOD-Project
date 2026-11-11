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
    raise NotImplementedError("P4")


def measure_memory(fn: Callable[..., Any], *args: Any) -> tuple[Any, float, float]:
    """Run fn(*args) under tracemalloc from a clean start; return (result, current_mib, peak_mib)."""
    raise NotImplementedError("P4")
