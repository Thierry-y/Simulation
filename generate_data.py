"""
generate_data.py - Lance toutes les simulations et affiche les courbes du projet.
Usage : python generate_data.py
"""

import os
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

sys.path.insert(0, os.path.dirname(__file__))
from simulator import run_simulation, sweep_lambda, sweep_N, find_optimal_N

# Paramètres
N_BASE   = 5
K_BASE   = 10
LAM_BASE = 0.3
TAU_BASE = 1.0
SIM_TIME = 600.0

print("=== Simulation MAC — Exponential Backoff ===\n")

# Partie A
print(f"[A] Simulation temporelle  N={N_BASE}, K={K_BASE}, λ={LAM_BASE}, τ={TAU_BASE}")
res_a = run_simulation(N_BASE, K_BASE, LAM_BASE, TAU_BASE, sim_time=SIM_TIME, sample_dt=5.0, seed=42)
print(f"    Débit final   : {res_a.final_throughput:.4f} paquets/s")
print(f"    Succès        : {res_a.total_success}")
print(f"    Pertes (file) : {res_a.total_lost}")
print(f"    Collisions    : {res_a.total_collisions}")

# Partie B
lam_values = [round(0.05 * i, 3) for i in range(1, 21)]
print(f"\n[B] Sweep λ  (N={N_BASE}, K={K_BASE}, τ={TAU_BASE})")
lams_b, thr_b = sweep_lambda(N_BASE, K_BASE, TAU_BASE, lam_values, sim_time=SIM_TIME, seed=42)

# Partie C
N_values = list(range(1, 16))
print(f"\n[C] Sweep N  (K={K_BASE}, λ={LAM_BASE}, τ={TAU_BASE})")
Ns_c, thr_c = sweep_N(K_BASE, LAM_BASE, TAU_BASE, N_values, sim_time=SIM_TIME, seed=42)

# Partie D
print(f"\n[D] N optimal avec IC 95%  (20 réplications par N)")
opt = find_optimal_N(K_BASE, LAM_BASE, TAU_BASE,
                     N_values=list(range(1, 12)),
                     n_replicas=20, sim_time=SIM_TIME)
print(f"    N optimal = {opt['best_N']}")
for n, v in opt["results"].items():
    print(f"    N={n:2d}  mean={v['mean']:.4f}  ±{v['ci']:.4f} (IC 95%)")

# ── Génération des courbes ──────────────────────────────────────────────────

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "courbes_MAC.pdf")

with PdfPages(OUTPUT_PATH) as pdf:

    # Partie A — Débit n(t)/t
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(res_a.time_points, res_a.throughput_series, color="#2563EB", lw=1.5, label="n(t)/t")
    ax.axhline(res_a.final_throughput, color="#16A34A", lw=1.2, ls="--",
               label=f"d = {res_a.final_throughput:.4f} paquets/s")
    ax.set_xlabel("Temps (s)")
    ax.set_ylabel("Débit (paquets/s)")
    ax.set_title(f"Partie A — Débit n(t)/t  (N={N_BASE}, K={K_BASE}, λ={LAM_BASE}, τ={TAU_BASE})")
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    pdf.savefig(fig); plt.close()

    # Partie A — File moyenne
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(res_a.time_points, res_a.avg_queue_series, color="#EA580C", lw=1.5)
    ax.set_xlabel("Temps (s)")
    ax.set_ylabel("Taille moyenne de la file")
    ax.set_title(f"Partie A — File d'attente moyenne  (N={N_BASE}, K={K_BASE}, λ={LAM_BASE}, τ={TAU_BASE})")
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    pdf.savefig(fig); plt.close()

    # Partie A — Taux de perte
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(res_a.time_points, res_a.loss_rate_series, color="#DC2626", lw=1.5)
    ax.set_ylim(0, 1)
    ax.set_xlabel("Temps (s)")
    ax.set_ylabel("Taux de perte")
    ax.set_title(f"Partie A — Taux de paquets perdus  (N={N_BASE}, K={K_BASE}, λ={LAM_BASE}, τ={TAU_BASE})")
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    pdf.savefig(fig); plt.close()

    # Partie B — Débit vs lambda
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(lams_b, thr_b, color="#2563EB", lw=2,
            marker="o", markersize=5, markerfacecolor="white", markeredgewidth=1.5)
    ax.set_xlabel("λ (taux d'arrivée)")
    ax.set_ylabel("Débit d(N,K,λ,τ)")
    ax.set_title(f"Partie B — Débit en fonction de λ  (N={N_BASE}, K={K_BASE}, τ={TAU_BASE})")
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    pdf.savefig(fig); plt.close()

    # Partie C — Débit vs N
    best_n = opt["best_N"]
    bar_colors = ["#16A34A" if n == best_n else "#2563EB" for n in Ns_c]
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.bar(Ns_c, thr_c, color=bar_colors, edgecolor="white", width=0.7)
    ax.set_xlabel("N (nombre de stations)")
    ax.set_ylabel("Débit d(N,K,λ,τ)")
    ax.set_title(f"Partie C — Débit en fonction de N  (K={K_BASE}, λ={LAM_BASE}, τ={TAU_BASE})")
    ax.set_xticks(Ns_c)
    ax.grid(True, alpha=0.3, axis="y")
    plt.tight_layout()
    pdf.savefig(fig); plt.close()

    # Partie D — IC 95%
    ns    = sorted(opt["results"].keys())
    means = [opt["results"][n]["mean"] for n in ns]
    cis   = [opt["results"][n]["ci"]   for n in ns]
    ns_int = [int(n) for n in ns]
    bar_colors_d = ["#16A34A" if int(n) == best_n else "#2563EB" for n in ns]
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.bar(ns_int, means, color=bar_colors_d, edgecolor="white", width=0.6)
    ax.errorbar(ns_int, means, yerr=cis, fmt="none", color="#374151",
                capsize=5, capthick=1.5, elinewidth=1.5)
    ax.set_xlabel("N (nombre de stations)")
    ax.set_ylabel("Débit moyen")
    ax.set_title(f"Partie D — N optimal avec IC 95%  (20 réplications, t={opt['t_val']})")
    ax.set_xticks(ns_int)
    ax.grid(True, alpha=0.3, axis="y")
    plt.tight_layout()
    pdf.savefig(fig); plt.close()

print(f"\n✓ Courbes exportées → {OUTPUT_PATH}")