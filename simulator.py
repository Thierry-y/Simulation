"""
simulator.py - Moteur de simulation MAC avec Exponential Backoff.
Simulateur à événements discrets. Les structures de données sont dans models.py.
"""

import heapq
import math
import random
from typing import List, Tuple

from models import Event, EventType, SimResult, Station


def run_simulation(
    N:         int,
    K:         int,
    lam:       float,
    tau:       float,
    sim_time:  float = 500.0,
    sample_dt: float = 5.0,
    seed:      int   = None,
) -> SimResult:
    """
    Lance une simulation MAC avec Exponential Backoff.

    N         : nombre de stations
    K         : capacité de la file de chaque station
    lam       : taux d'arrivée des paquets, inter-arrivées ~ Exp(lam)
    tau       : paramètre de base du backoff
    sim_time  : durée totale de la simulation
    sample_dt : intervalle entre deux points d'échantillonnage
    seed      : graine aléatoire (None = non fixée)
    """
    if seed is not None:
        random.seed(seed)

    # Une station par identifiant, toutes initialisées à l'état 1, file vide
    stations = [Station(i, K) for i in range(N)]

    # Tas min ordonné par temps : on en extrait toujours l'événement le plus proche
    heap: List[Event] = []

    current_time    = 0.0
    success_count   = 0   # paquets transmis avec succès
    lost_count      = 0   # paquets arrivés sur une file pleine
    collision_count = 0   # nombre de collisions détectées

    # Stations en train d'émettre à cet instant : liste de (station_id, heure_fin)
    # Plusieurs entrées simultanées signifient une collision en cours
    transmitting_now: List[Tuple[int, float]] = []

    # Listes pour les courbes (remplies à chaque point d'échantillonnage)
    time_points       = []
    throughput_series = []
    avg_queue_series  = []
    loss_rate_series  = []
    next_sample       = sample_dt

    # Planifie la prochaine arrivée de paquet sur une station donnée.
    # L'inter-arrivée suit une loi exponentielle de paramètre lam.
    def schedule_arrival(station_id: int, after: float = 0.0) -> None:
        t = after + random.expovariate(lam)
        heapq.heappush(heap, Event(t, EventType.ARRIVAL, station_id))

    # Déclenche un TX_START immédiat pour la station s (à current_time).
    def start_tx(s: Station) -> None:
        s.in_backoff = False
        heapq.heappush(heap, Event(current_time, EventType.TX_START, s.id))

    # Enregistre les métriques au temps t dans les séries temporelles.
    def record_sample(t: float) -> None:
        throughput = success_count / t if t > 0 else 0.0
        avg_q      = sum(st.queue for st in stations) / N
        total_arr  = success_count + lost_count
        loss_rate  = lost_count / total_arr if total_arr > 0 else 0.0
        time_points.append(t)
        throughput_series.append(throughput)
        avg_queue_series.append(avg_q)
        loss_rate_series.append(loss_rate)

    # Première arrivée planifiée pour chaque station
    for i in range(N):
        schedule_arrival(i)

    # Boucle principale : on traite les événements dans l'ordre chronologique
    while heap and current_time < sim_time:
        event        = heapq.heappop(heap)
        current_time = event.time

        # Rattraper tous les points d'échantillonnage dépassés par ce saut de temps
        while next_sample <= current_time and next_sample <= sim_time:
            record_sample(next_sample)
            next_sample += sample_dt

        s = stations[event.station_id]

        if event.event_type == EventType.ARRIVAL:
            # Planifier l'arrivée suivante sur cette station
            schedule_arrival(s.id, after=current_time)

            if not s.queue_full:
                s.queue += 1
                # Si la station est libre, elle peut émettre tout de suite
                if not s.is_busy:
                    start_tx(s)
            else:
                # File pleine : le paquet est perdu
                lost_count += 1

        elif event.event_type == EventType.TX_START:
            s.is_transmitting = True
            s.in_backoff      = False
            end_time          = current_time + 1.0  # durée d'émission fixée à 1

            transmitting_now.append((s.id, end_time))

            # Si une autre station émettait déjà, c'est une collision.
            # On lève le flag sur toutes les stations concernées.
            if len(transmitting_now) > 1:
                collision_count += 1
                for (sid, _) in transmitting_now:
                    stations[sid].collision_flag = True

            heapq.heappush(heap, Event(end_time, EventType.TX_END, s.id))

        elif event.event_type == EventType.TX_END:
            # Retirer cette station de la liste des émetteurs actifs
            transmitting_now = [(sid, et) for sid, et in transmitting_now if sid != s.id]

            if s.collision_flag:
                # Collision : incrémenter l'état, tirer un backoff, replanifier
                s.increment_state()
                backoff           = s.backoff_duration(tau)
                s.is_transmitting = False
                s.in_backoff      = True
                s.collision_flag  = False
                heapq.heappush(heap, Event(current_time + backoff, EventType.TX_START, s.id))
            else:
                # Succès : comptabiliser, vider une place dans la file, réinitialiser
                success_count += 1
                s.queue -= 1
                s.reset_state()

                # S'il reste des paquets en attente, enchaîner directement
                if s.queue > 0:
                    start_tx(s)

    # Dernier point d'échantillonnage à la fin effective de la simulation
    if current_time > 0:
        record_sample(current_time)

    return SimResult(
        time_points=time_points, throughput_series=throughput_series,
        avg_queue_series=avg_queue_series, loss_rate_series=loss_rate_series,
        final_throughput=success_count / sim_time if sim_time > 0 else 0.0,
        total_success=success_count, total_lost=lost_count,
        total_collisions=collision_count, sim_time=sim_time,
        N=N, K=K, lam=lam, tau=tau,
    )


def sweep_lambda(N, K, tau, lam_values, sim_time=500.0, seed=42):
    """Partie B : calcule le débit pour chaque valeur de lambda, N/K/tau fixes."""
    throughputs = [
        run_simulation(N, K, lam, tau, sim_time=sim_time, seed=seed).final_throughput
        for lam in lam_values
    ]
    return lam_values, throughputs


def sweep_N(K, lam, tau, N_values, sim_time=500.0, seed=42):
    """Partie C : calcule le débit pour chaque valeur de N, K/lam/tau fixes."""
    throughputs = [
        run_simulation(N, K, lam, tau, sim_time=sim_time, seed=seed).final_throughput
        for N in N_values
    ]
    return N_values, throughputs


def find_optimal_N(K, lam, tau, N_values, n_replicas=20, sim_time=500.0):
    """
    Partie D : trouve le N qui maximise le débit avec un IC à 95%.

    Pour chaque N, on lance n_replicas simulations indépendantes avec des
    graines différentes, puis on calcule moyenne, écart-type et intervalle
    de confiance via la loi de Student (ddl = n_replicas - 1).
    """
    # Valeurs de t de Student pour IC 95% selon le nombre de degrés de liberté
    t_table = {5: 2.776, 10: 2.228, 15: 2.131, 20: 2.093, 25: 2.060, 30: 2.042, 40: 2.021, 50: 2.009}
    closest = min(t_table.keys(), key=lambda k: abs(k - n_replicas))
    t_val   = t_table[closest]

    results = {}
    for N in N_values:
        samples = [
            run_simulation(N, K, lam, tau, sim_time=sim_time, seed=rep * 1000 + N).final_throughput
            for rep in range(n_replicas)
        ]
        mean = sum(samples) / n_replicas
        std  = math.sqrt(sum((x - mean) ** 2 for x in samples) / (n_replicas - 1))
        ci   = t_val * std / math.sqrt(n_replicas)
        results[N] = {"mean": mean, "std": std, "ci": ci, "samples": samples}

    best_N = max(results, key=lambda n: results[n]["mean"])
    return {"best_N": best_N, "t_val": t_val, "n_replicas": n_replicas, "results": results}