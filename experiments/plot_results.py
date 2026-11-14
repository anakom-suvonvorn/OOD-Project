"""Graphs from results/*.csv (owner: P4). Run: python -m experiments.plot_results

Needs pandas and matplotlib (see requirements.txt). Saves PNGs to results/graphs/.
Every graph: axis titles with units, parameters in the title or a note, and the spread
over the 3 salts (median line + min-max error bars).
  (a) time vs K            (b) move rate vs N, both methods            (c) V vs CV and memory
"""
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"
GRAPHS_DIR = RESULTS_DIR / "graphs"

plt.rcParams.update({"font.size": 10, "figure.autolayout": True})


def get_stat(df: pd.DataFrame, group_cols, value_cols: str = "value") -> pd.DataFrame:
    """Median, min and max over the salts, plus the error-bar lengths."""
    grouped = df.groupby(group_cols)[value_cols].agg(["median", "min", "max"]).reset_index()
    grouped["err_lower"] = grouped["median"] - grouped["min"]
    grouped["err_upper"] = grouped["max"] - grouped["median"]
    return grouped


def plot_a() -> None:
    filepath = RESULTS_DIR / "experiment_a.csv"
    if not filepath.exists():
        print(f"[skip] File not found: {filepath}")
        return

    df = pd.read_csv(filepath)
    time_metric = {
        "time_ring_build": ("Build ring (N*V points)", "purple", "x", "-"),
        "time_place": ("Place all K guests", "blue", "o", "-"),
        "time_sort": ("Sort room list (list_rooms)", "green", "s", "--"),
        "time_search_guest": ("Search by guest id (per search)", "red", "^", "-."),
        "time_search_room": ("Search by room (per search)", "orange", "d", ":"),
    }

    fig, ax = plt.subplots(figsize=(8, 5))
    for metric, (label, color, marker, ls) in time_metric.items():
        stats = get_stat(df[df["metric"] == metric], ["K"])
        if stats.empty:
            continue
        yerr = [stats["err_lower"], stats["err_upper"]]
        ax.errorbar(stats["K"], stats["median"], yerr=yerr, label=label, color=color,
                    marker=marker, linestyle=ls, capsize=4, linewidth=1.5)

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Number of guests K (log scale)  [fixed: N = 10, V = 32]")
    ax.set_ylabel("Time (seconds, log scale)")
    ax.set_title("Graph (a): Execution time vs number of guests K\n"
                 "(median of salts 0, 1, 2 with min-max error bars)")
    ax.grid(True, which="both", linestyle="--", alpha=0.5)
    ax.legend()

    fig.savefig(GRAPHS_DIR / "graph_a_time_vs_k.png", dpi=300)
    plt.close(fig)
    print("Saved: results/graphs/graph_a_time_vs_k.png")


def plot_b() -> None:
    filepath = RESULTS_DIR / "experiment_b.csv"
    if not filepath.exists():
        print(f"[skip] File not found: {filepath}")
        return

    df = pd.read_csv(filepath)
    config = [
        ("move_rate_add", "consistent", "Consistent hashing: add building N+1", "blue", "o", "-"),
        ("move_rate_add", "mod_n", "Hash mod N: add building N+1", "red", "o", "--"),
        ("move_rate_remove", "consistent", "Consistent hashing: remove middle building", "cyan", "s", "-"),
        ("move_rate_remove", "mod_n", "Hash mod N: remove middle building", "orange", "s", "--"),
    ]

    fig, ax = plt.subplots(figsize=(8, 5))
    for metric, method, label, color, marker, ls in config:
        sub_df = df[(df["metric"] == metric) & (df["method"] == method)]
        stats = get_stat(sub_df, ["N"])
        yerr = [stats["err_lower"], stats["err_upper"]]
        ax.errorbar(stats["N"], stats["median"], yerr=yerr, label=label, color=color,
                    marker=marker, linestyle=ls, capsize=4, linewidth=1.5)

    # Expected values with uniform hashing (PDF 4.4), thin dotted in the matching colour.
    ns = sorted(df["N"].unique())
    expected = [
        ("Expected 1/(N+1)", [1 / (n + 1) for n in ns], "blue"),
        ("Expected N/(N+1)", [n / (n + 1) for n in ns], "red"),
        ("Expected 1/N", [1 / n for n in ns], "cyan"),
        ("Expected (N-1)/N", [(n - 1) / n for n in ns], "orange"),
    ]
    for label, values, color in expected:
        ax.plot(ns, values, color=color, linestyle=":", marker="x", linewidth=1, alpha=0.8,
                label=label)

    ax.set_xlabel("Number of buildings N before the change  [fixed: K = 10,000, V = 32]")
    ax.set_ylabel("Move rate (moved guests / K)")
    ax.set_title("Graph (b): Guest move rate vs N, consistent hashing vs hash mod N\n"
                 "(median of salts 0, 1, 2 with min-max error bars; dotted = expected)")
    ax.set_xticks(ns)
    ax.set_ylim(0, 1.05)
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend(loc="center right", fontsize=8, ncol=2)

    fig.savefig(GRAPHS_DIR / "graph_b_move_rate_vs_n.png", dpi=300)
    plt.close(fig)
    print("Saved: results/graphs/graph_b_move_rate_vs_n.png")


def plot_c() -> None:
    filepath = RESULTS_DIR / "experiment_c.csv"
    if not filepath.exists():
        print(f"[skip] File not found: {filepath}")
        return

    df = pd.read_csv(filepath)
    vs = sorted(df["V"].unique())
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.8))

    stats_cv = get_stat(df[df["metric"] == "guests_cv"], "V")
    ax1.errorbar(stats_cv["V"], stats_cv["median"], yerr=[stats_cv["err_lower"], stats_cv["err_upper"]],
                 color="purple", marker="o", linestyle="-", capsize=4, linewidth=1.5,
                 label="CV = std / mean of guests per building")
    ax1.set_xlabel("Virtual nodes per building V")
    ax1.set_ylabel("Coefficient of variation (CV, no unit)")
    ax1.set_title("Load imbalance (lower = more balanced)")
    ax1.set_xticks(vs)
    ax1.set_ylim(bottom=0)
    ax1.grid(True, linestyle="--", alpha=0.5)
    ax1.legend()

    memory_lines = [
        ("memory_peak", "Whole system: ring + K guests + indexes", "darkorange", "s"),
        ("memory_ring_peak", "Ring only (N*V points)", "teal", "^"),
    ]
    for metric, label, color, marker in memory_lines:
        stats = get_stat(df[df["metric"] == metric], "V")
        if stats.empty:
            continue
        ax2.errorbar(stats["V"], stats["median"], yerr=[stats["err_lower"], stats["err_upper"]],
                     color=color, marker=marker, linestyle="-", capsize=4, linewidth=1.5, label=label)
    ax2.set_yscale("log")
    ax2.set_xlabel("Virtual nodes per building V")
    ax2.set_ylabel("Peak memory (MiB, tracemalloc, log scale)")
    ax2.set_title("Peak memory traced by Python")
    ax2.set_xticks(vs)
    ax2.grid(True, which="both", linestyle="--", alpha=0.5)
    ax2.legend()

    fig.suptitle("Graph (c): Effect of virtual nodes V on load balance and memory  "
                 "[fixed: N = 10, K = 10,000]\n(median of salts 0, 1, 2 with min-max error bars)")

    fig.savefig(GRAPHS_DIR / "graph_c_cv_memory_vs_v.png", dpi=300)
    plt.close(fig)
    print("Saved: results/graphs/graph_c_cv_memory_vs_v.png")


def main() -> None:
    GRAPHS_DIR.mkdir(parents=True, exist_ok=True)
    plot_a()
    plot_b()
    plot_c()
    print("Finished plotting")


if __name__ == "__main__":
    main()
