"""Graphs from results/*.csv (owner: P4). Run: python -m experiments.plot_results

Saves PNGs to results/graphs/. Every graph: axis titles with units, parameters in the
title or a note, and the spread over the 3 salts (median line + min-max band or error bars).
  (a) time vs K            (b) move rate vs N, both methods            (c) V vs CV and memory
"""
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

RESULTS_DIR = Path("results")
GRAPHS_DIR = RESULTS_DIR / "graphs"
GRAPHS_DIR.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({'font.size': 10, 'figure.autolayout': True})

def get_stat(df: pd.DataFrame, group_cols: list[str], value_cols: str = "value"):
    grouped = df.groupby(group_cols)[value_cols].agg(["median", "min", "max"]).reset_index()
    grouped["err_lower"] = grouped["median"] - grouped["min"]
    grouped["err_upper"] = grouped["max"] - grouped["median"]
    return grouped
  
def plot_a():
    filepath = RESULTS_DIR / "experiment_a.csv"
    if not filepath.exists():
      print(f"[skip] File not found: {filepath}")
      return
      
    df = pd.read_csv(filepath)
    time_metric = {
      "time_place" : ("Place Guests (Ring Build)", "Blue", "o", "-"),
      "time_sort" : ("Sort Rooms (list_rooms)", "green", "s", "--"),
      "time_search_guest" : ("Search Guest (per op)", "red", "^", "-."),
      "time_search_room" : ("Search Room (per op)", "orange", "d", ":")
    }
    
    fig, ax = plt.subplots(figsize = (8, 5))
    
    for metric, (label, color, marker, ls) in time_metric.items():
      sub_df = df[df["metric"] == metric]
      stats = get_stat(sub_df, ["K"])
      
      yerr = [stats["err_lower"], stats["err_upper"]]
      ax.errorbar(stats["K"], stats["median"], yerr = yerr, label = label, color = color, marker = marker, linestyle = ls, capsize= 4, linewidth= 1.5)
      
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Number of Guests (K) [Fixed: N=10, V=32]")
    ax.set_ylabel("Time (seconds, log-scale)")
    ax.set_title("Graph (a): Execution Time vs Number of Guests (K)\n(Median with Min-Max Error Bars)")
    ax.grid(True, which="both", linestyle="--", alpha=0.5)
    ax.legend()
    
    fig.savefig(GRAPHS_DIR / "graph_a_time_vs_k.png", dpi=300)
    plt.close(fig)
    print("Saved: results/graphs/graph_a_time_vs_k.png")
      
def plot_b():
    filepath = RESULTS_DIR / "experiment_b.csv"
    if not filepath.exists():
      print(f"[skip] File not found: {filepath}")
      return
            
    df = pd.read_csv(filepath)
    config = [
      ("move_rate_add", "consistent", "CH (add n + 1)", "blue", "o", "-"),
      ("move_rate_add", "mod_n", "Mod N (add n + 1)", "red", "o", "--"),
      ("move_rate_remove", "consistent", "CH (remove middle)", "cyan", "s", "-"),
      ("move_rate_remove", "mod_n", "Mod N (remove middle)", "orange", "s", "--")
    ]
      
    fig, ax = plt.subplots(figsize = (8, 5))
          
    for metric, method,  label, color, marker, ls in config:
      sub_df = df[(df["metric"] == metric) & (df["method"] == method)]
      stats = get_stat(sub_df, ["N"])
        
      yerr = [stats["err_lower"], stats["err_upper"]]
      ax.errorbar(stats["N"], stats["median"], yerr = yerr, label = label, color = color, marker = marker, linestyle = ls, capsize= 4, linewidth= 1.5)
        
    ax.set_xlabel("Number of Buildings (N) [Fixed: K=10,000, V=32]")
    ax.set_ylabel("Move Rate (Moved Guests / Total K)")
    ax.set_title("Graph (b): Guest Move Rate vs N (Consistent Hashing vs Mod N)\n(Median with Min–Max Error Bars)")
    ax.set_xticks([5, 10, 20])
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend()

    fig.savefig(GRAPHS_DIR / "graph_b_move_rate_vs_n.png", dpi=300)
    plt.close(fig)
    print("Saved: results/graphs/graph_b_move_rate_vs_n.png")
    
def plot_c():
    filepath = RESULTS_DIR / "experiment_c.csv"
    if not filepath.exists():
      print(f"[skip] File not found: {filepath}")
      return
                
    df = pd.read_csv(filepath)
    fig, ax1 = plt.subplots(figsize=(8, 5))
    
    df_cv = df[df["metric"] == "guests_cv"]
    stats_cv = get_stat(df_cv, "V")
    yerr_cv = [stats_cv["err_lower"], stats_cv["err_upper"]]
    line1 = ax1.errorbar(stats_cv["V"], stats_cv["median"], yerr = yerr_cv, color = "purple", marker = "o", linestyle = "-", capsize= 4, linewidth= 1.5, label="Load Imbalance (CV)")
    
    ax1.set_xlabel("Virtual Nodes per Building (V) [Fixed: N=10, K=10,000]")
    ax1.set_ylabel("Coefficient of Variation (CV)", color="purple")
    ax1.tick_params(axis="y", labelcolor="purple")
    ax1.set_xticks([1, 8, 32])
    
    ax2 = ax1.twinx()
    df_mem = df[df["metric"] == "memory_peak"]
    stats_mem = get_stat(df_mem, "V")
    yerr_mem = [stats_mem["err_lower"], stats_mem["err_upper"]]
    line2 = ax2.errorbar(stats_mem["V"], stats_mem["median"], yerr = yerr_mem, color = "darkorange", marker = "s", linestyle = "-", capsize= 4, linewidth= 1.5, label="Peak Memory (MiB)")
    
    ax2.set_ylabel("Peak Memory (MiB)", color="darkorange")
    ax2.tick_params(axis="y", labelcolor="darkorange")
    
    lines = [line1, line2]
    labels = [l.get_label() for l in lines]
    ax1.legend(lines, labels, loc = "upper center")
    
    ax1.set_title("Graph (c): Effect of Virtual Nodes (V) on CV & Peak Memory\n(Median with Min-Max Error Bars)")
    ax1.grid(True, linestyle="--", alpha=0.5)

    fig.savefig(GRAPHS_DIR / "graph_c_cv_memory_vs_v.png", dpi=300)
    plt.close(fig)
    print("Saved: results/graphs/graph_c_cv_memory_vs_v.png")

def main() -> None:
    plot_a()
    plot_b()
    plot_c()
    print("Finished Plotting")

if __name__ == "__main__":
    main()
