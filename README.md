# Distributed Hilbert's Hotel (OODS 1/2569)

A Python program that assigns guests `(c, s)` to buildings in a hotel chain with **consistent hashing**.
Each guest's room number comes from the Cantor pairing of `(c, s)`, so it never changes; the building
comes from a SHA-256 hash ring with virtual nodes, so adding or removing a building moves only about
K/N guests. The project also compares this with `hash mod N`.

Team plan, design decisions and API contract: [PLAN.md](PLAN.md).

## Requirements

- **Python 3.12** (developed and tested on 3.12.0; the code also runs on 3.11).
- Program and tests: standard library only, nothing to install.
- Graphs only: `pandas` and `matplotlib`.

```
pip install -r requirements.txt
```

Run every command below from this folder (the one containing `main.py`).

## Run the program

```
python main.py
```

Text menu: create a hotel, add guests (one or a batch), remove a guest, add or remove a building
(with the move report), search by guest id or by building and room, list rooms, load report,
benchmark, compare with hash mod N, and export CSV.

## Run the tests

```
python -m unittest discover -s tests -v
```

| File | What it checks |
|---|---|
| `tests/test_ring.py` | SHA-256 positions are stable across runs, ring lookup (exact point, between points, wrap-around, ties), the PDF section 9.1 example, add/remove building |
| `tests/test_mod_n.py` | hash mod N baseline: index rule, append on add, order kept on remove |
| `tests/test_guest.py` | room-number formula, its inverse, no duplicate rooms, `GuestStore` consistency |
| `tests/test_hotel_guests.py` | adding guests never moves existing guests, all-or-nothing batches, searches, K = 0 |
| `tests/test_building.py` | guests move only into a new building / only out of a removed one, bucket method equals rechecking every guest, all building edge cases |
| `tests/test_csv_export.py` | CSV row counts equal the number of guests / moves, UTF-8 |
| `tests/test_experiments.py` | hash mod N comparison uses real building ids, benchmark and comparison never change the hotel |

## Run the experiments and draw the graphs

```
python -m experiments.run_experiments
python -m experiments.plot_results
```

The first command runs experiments A, B and C (PDF section 7) with salts `"0"`, `"1"`, `"2"` and writes
`results/experiment_a.csv`, `experiment_b.csv`, `experiment_c.csv` and `specs_when_experiment.csv`
(Python version and machine). It takes about 10–20 seconds. The second draws
`results/graphs/graph_a_time_vs_k.png`, `graph_b_move_rate_vs_n.png` and `graph_c_cv_memory_vs_v.png`.

| Experiment | Varies | Fixed | Measures |
|---|---|---|---|
| A | K = 1,000 / 10,000 / 100,000 | N = 10, V = 32 | time to build the ring, place guests, search (per search, batch of 1,000), sort; memory |
| B | N = 5 / 10 / 20 | K = 10,000, V = 32 | add building N + 1 and remove building N // 2 + 1: moves, move rate, time, consistent hashing vs hash mod N |
| C | V = 1 / 8 / 32 | N = 10, K = 10,000 | guests per building (max, min, mean, std, CV), memory (whole system and ring only), moves |

Result CSVs use one row per measurement: `experiment, method, salt, K, N, V, metric, value, unit`.
Times use `time.perf_counter()`; memory uses `tracemalloc` in a separate run from timing and is the
memory Python traces, not the whole process.

## Project structure

```
main.py                 entry point (text menu)
hotel/                  core logic, no printing or input
  hashing.py            SHA-256 -> 64-bit ring position, hash text formats guest:c:s / node:id:j
  ring.py               HashRing: sorted virtual-node points, bisect lookup, add/remove building
  mod_n.py              ModNRouter: hash mod N baseline for comparison
  guest.py              Guest, room number (Cantor pairing) and its inverse
  guest_store.py        GuestStore: guests, room index, per-point buckets, counts per building
  hotel_system.py       HotelSystem: the public API used by the menu and experiments
  models.py, errors.py  shared data types and error classes
ui/                     text menu and CSV export
experiments/            experiment runner, timing/memory helpers, graph plotting
tests/                  unittest test suite
results/                experiment CSVs and graphs
```
