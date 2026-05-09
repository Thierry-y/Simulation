import random
from enum import Enum

# Définition de l'énumération des types d'événements pour éviter l'utilisation de chaînes de caractères codées en dur
class EventType(Enum):
    ARRIVAL = "ARRIVAL"    # Arrivée d'un paquet
    TX_START = "TX_START"  # Début de transmission
    TX_END = "TX_END"      # Fin de transmission

class Event:
    """
    Classe Événement (Event)
    Représente un événement unique dans une simulation à événements discrets.
    """
    def __init__(self, time: float, event_type: EventType, station_id: int):
        self.time = time              # Horodatage de l'événement
        self.event_type = event_type  # Type d'événement
        self.station_id = station_id  # ID de la station ayant déclenché l'événement

    def __lt__(self, other: 'Event') -> bool:
        """
        Surcharge de l'opérateur "inférieur à" (<).
        Utilisé pour classer les événements par ordre chronologique dans la file de priorité.
        """
        return self.time < other.time
        
    def __repr__(self):
        return f"Event(temps={self.time:.3f}, type={self.event_type.name}, station={self.station_id})"


class Station:
    """
    Classe Station (Station)
    Représente un nœud émetteur dans le réseau.
    """
    def __init__(self, station_id: int, K: int):
        self.id = station_id          # Identifiant unique
        self.K = K                    # Capacité maximale de la file d'attente
        self.queue = 0                # Nombre actuel de paquets dans la file
        self.state_i = 1              # État de backoff actuel i (initialisé à 1)
        self.is_active = False        # Indique si la station est en backoff ou prête à envoyer
        self.collision_flag = False   # Indique si la transmission actuelle a subi une collision

    def reset_state(self):
        """
        Réinitialise l'état de la station après une transmission réussie.
        """
        self.state_i = 1
        self.collision_flag = False

    def increment_state(self):
        """
        Augmente l'état de backoff en cas de collision.
        """
        self.state_i += 1

    def calculate_backoff(self, tau: float) -> float:
        """
        Calcule le temps de backoff.
        Génère un nombre aléatoire selon une loi exponentielle avec le paramètre lambda = 1 / (2^i * tau).
        """
        lambd = 1.0 / ((2 ** self.state_i) * tau)
        return random.expovariate(lambd)
        
    def __repr__(self):
        return f"Station(id={self.id}, file={self.queue}/{self.K}, état_i={self.state_i}, active={self.is_active})"