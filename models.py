"""
models.py — Structures de données du simulateur MAC
====================================================
Ce fichier contient UNIQUEMENT les modèles de données :
  - EventType  : énumération des types d'événements
  - Event      : un événement horodaté dans la file de priorité
  - Station    : état complet d'une station émettrice
  - SimResult  : résultat complet d'une simulation

Aucune logique de simulation ici — tout ça est dans simulator.py.
"""

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import List


# EventType

class EventType(Enum):
    """
    Les trois événements possibles dans la simulation.

    ARRIVAL  : un nouveau paquet arrive dans la file d'une station.
               Déclenché périodiquement selon une loi Exp(λ).

    TX_START : une station commence à émettre son paquet de tête sur le canal.
               Déclenché soit juste après une ARRIVAL (si la station est libre),
               soit à la fin d'un backoff.

    TX_END   : l'émission d'un paquet se termine (après 1 unité de temps).
               → Succès si aucun chevauchement avec une autre émission.
               → Collision sinon : backoff exponentiel et re-planification.
    """
    ARRIVAL  = "ARRIVAL"
    TX_START = "TX_START"
    TX_END   = "TX_END"

# Event

@dataclass(order=True)
class Event:
    """
    Représente un événement unique dans la file de priorité (tas min).

    Attributs
    ---------
    time       : instant auquel l'événement doit être traité.
                 Utilisé pour le tri dans le heapq (order=True → compare sur time).
    event_type : type de l'événement (ARRIVAL, TX_START ou TX_END).
    station_id : identifiant de la station concernée (indice dans la liste).

    Note sur order=True
    -------------------
    Le décorateur @dataclass(order=True) génère automatiquement __lt__, __le__,
    __gt__, __ge__ en comparant les champs dans l'ordre de déclaration.
    Comme `time` est déclaré en premier et les deux autres ont compare=False,
    seul `time` est utilisé pour le tri → heapq extrait toujours l'événement
    le plus proche dans le temps.
    """
    time:       float
    event_type: EventType = field(compare=False)
    station_id: int       = field(compare=False)

    def __repr__(self) -> str:
        return (
            f"Event(t={self.time:.4f}, "
            f"type={self.event_type.name}, "
            f"station={self.station_id})"
        )


# Station
class Station:
    """
    Représente une station émettrice dans le réseau.

    Une station peut être dans l'un de ces états exclusifs :
      - Idle        : is_transmitting=False, in_backoff=False, queue=0
      - En attente  : is_transmitting=False, in_backoff=False, queue>0
                      (attend de démarrer TX_START)
      - Émission    : is_transmitting=True
      - Backoff     : in_backoff=True  (attend après une collision)

    Attributs
    ---------
    id               : identifiant unique (0..N-1)
    K                : capacité maximale de la file d'attente
    queue            : nombre de paquets actuellement en file
                       (le paquet en cours d'émission est compté dedans
                        jusqu'au TX_END succès)
    state_i          : état de backoff courant, commence à 1.
                       Augmente de 1 à chaque collision.
                       Remis à 1 après un succès.
    is_transmitting  : True si un TX_START a eu lieu sans TX_END encore traité
    in_backoff       : True si la station attend la fin d'un backoff
    collision_flag   : True si l'émission courante a subi une collision
                       (mis à True dans TX_START quand chevauchement détecté,
                        lu et remis à False dans TX_END)
    """

    def __init__(self, station_id: int, K: int) -> None:
        self.id              = station_id
        self.K               = K
        self.queue           = 0
        self.state_i         = 1
        self.is_transmitting = False
        self.in_backoff      = False
        self.collision_flag  = False

    # Transitions d'état 

    def reset_state(self) -> None:
        """
        Remet la station à son état initial après un succès.
        state_i revient à 1, tous les flags sont effacés.
        """
        self.state_i         = 1
        self.collision_flag  = False
        self.is_transmitting = False
        self.in_backoff      = False

    def increment_state(self) -> None:
        """
        Augmente l'état de backoff d'un cran après une collision.
        state_i += 1  →  la prochaine attente sera deux fois plus longue.
        """
        self.state_i += 1

    # Calcul du backoff 

    def backoff_duration(self, tau: float) -> float:
        """
        Tire la durée du prochain backoff selon une loi exponentielle.

        Formule
        -------
        λ    = 1 / (2^i × τ)
        durée ~ Exp(λ)  →  E[durée] = 1/λ = 2^i × τ

        Paramètres
        ----------
        tau : paramètre de base du backoff (unité de temps de référence)

        Retour
        ------
        Durée d'attente en secondes (valeur positive, loi sans mémoire).

        Exemples (τ=1)
        --------------
        état 1 → moyenne = 2^1 × 1 = 2 s
        état 2 → moyenne = 2^2 × 1 = 4 s
        état 3 → moyenne = 2^3 × 1 = 8 s
        """
        mean  = (2 ** self.state_i) * tau
        lambd = 1.0 / mean
        return random.expovariate(lambd)

    # ── Propriétés dérivées ──────────────────────────────────────────────────

    @property
    def is_idle(self) -> bool:
        """True si la station ne fait rien et n'a rien à envoyer."""
        return not self.is_transmitting and not self.in_backoff and self.queue == 0

    @property
    def is_busy(self) -> bool:
        """True si la station est occupée (émission ou backoff)."""
        return self.is_transmitting or self.in_backoff

    @property
    def queue_full(self) -> bool:
        """True si la file est pleine (prochain paquet arrivant sera perdu)."""
        return self.queue >= self.K

    def __repr__(self) -> str:
        status = "TX" if self.is_transmitting else ("BACKOFF" if self.in_backoff else "IDLE")
        return (
            f"Station(id={self.id}, "
            f"file={self.queue}/{self.K}, "
            f"état_i={self.state_i}, "
            f"status={status})"
        )



# SimResult
@dataclass
class SimResult:
    """
    Résultat complet d'une simulation.

    Séries temporelles (échantillonnées tous les sample_dt secondes)
    ----------------------------------------------------------------
    time_points       : instants d'échantillonnage [t0, t1, ..., T]
    throughput_series : n(t)/t à chaque instant  → converge vers d(N,K,λ,τ)
    avg_queue_series  : taille moyenne des files d'attente (sur toutes les stations)
    loss_rate_series  : taux cumulé de paquets perdus (file pleine) / total arrivées

    Statistiques finales
    --------------------
    final_throughput  : débit moyen d(N,K,λ,τ) = total_success / sim_time
    total_success     : nombre de paquets transmis avec succès
    total_lost        : nombre de paquets arrivés sur une file pleine (perdus)
    total_collisions  : nombre d'événements de collision (chevauchements)
    sim_time          : durée totale de la simulation

    Paramètres de la simulation
    ---------------------------
    N, K, lam, tau    : paramètres utilisés (pour traçabilité)
    """

    # Séries temporelles
    time_points:       List[float]
    throughput_series: List[float]
    avg_queue_series:  List[float]
    loss_rate_series:  List[float]

    # Statistiques finales
    final_throughput:  float
    total_success:     int
    total_lost:        int
    total_collisions:  int
    sim_time:          float

    # Paramètres
    N:   int
    K:   int
    lam: float
    tau: float

    def summary(self) -> str:
        """Affiche un résumé lisible des résultats."""
        total_arr = self.total_success + self.total_lost
        loss_pct  = 100 * self.total_lost / total_arr if total_arr > 0 else 0.0
        return (
            f"╔══ SimResult ══════════════════════════════╗\n"
            f"║  Paramètres : N={self.N}, K={self.K}, "
            f"λ={self.lam}, τ={self.tau}\n"
            f"║  Durée sim  : {self.sim_time} s\n"
            f"╠═══════════════════════════════════════════╣\n"
            f"║  Débit final       : {self.final_throughput:.4f} paquets/s\n"
            f"║  Succès            : {self.total_success}\n"
            f"║  Pertes (file)     : {self.total_lost}  ({loss_pct:.1f}%)\n"
            f"║  Collisions        : {self.total_collisions}\n"
            f"╚═══════════════════════════════════════════╝"
        )

    def __repr__(self) -> str:
        return (
            f"SimResult(N={self.N}, K={self.K}, λ={self.lam}, τ={self.tau}, "
            f"débit={self.final_throughput:.4f}, "
            f"succès={self.total_success}, pertes={self.total_lost})"
        )