# Simulation MAC — Exponential Backoff

## Structure du projet

```
simulation/
├── models.py          # Structures de données (EventType, Event, Station, SimResult)
├── simulator.py       # Moteur de simulation + fonctions d'analyse
├── generate_data.py   # Lance toutes les simulations, exporte results.json
├── results.json       # Données générées (produit par generate_data.py)
└── README.md
```

## Utilisation

```bash
# Générer toutes les données (parties A, B, C, D)
python generate_data.py

# Utiliser le simulateur directement dans un script
from simulator import run_simulation
result = run_simulation(N=5, K=10, lam=0.3, tau=1.0, sim_time=600, seed=42)
print(result.summary())
```

## Paramètres

| Paramètre | Valeur par défaut | Description |
|-----------|:-----------------:|-------------|
| N | 5 | Nombre de stations |
| K | 10 | Capacité de la file d'attente par station |
| λ (lam) | 0.3 | Taux d'arrivée des paquets — inter-arrivées ~ Exp(λ) |
| τ (tau) | 1.0 | Paramètre de base du backoff |
| sim_time | 600 s | Durée totale de la simulation |
| sample_dt | 5 s | Intervalle d'échantillonnage pour les courbes |

## Événements du simulateur

| Événement | Déclencheur | Action |
|-----------|-------------|--------|
| `ARRIVAL` | Inter-arrivée ~ Exp(λ) après la précédente | Ajoute un paquet à la file si K non atteint, sinon paquet perdu |
| `TX_START` | File non vide et station libre, ou fin de backoff | Démarre l'émission sur le canal pendant 1 unité de temps |
| `TX_END` | 1 unité de temps après TX_START | Succès si aucun chevauchement, sinon backoff exponentiel |

## Hypothèses

- **Détection de collision** : deux émissions qui se chevauchent dans le temps sont une collision. Le flag est levé dès le TX_START si une autre station émet déjà, et lu au TX_END.
- **Collision mutuelle** : si 3 stations (ou plus) émettent simultanément, toutes subissent la collision.
- **État i non borné** : state_i peut croître indéfiniment, il n'y a pas de plafond.
- **Durée d'émission** : fixée à 1 unité de temps pour tous les paquets.
- **État initial** : toutes les stations démarrent à state_i = 1, file vide.

## Formule de backoff

Quand une station est à l'état i après une collision, elle attend un temps tiré selon :

```
durée ~ Exp(λ)   avec   λ = 1 / (2^i × τ)   →   E[durée] = 2^i × τ
```

À chaque collision supplémentaire, state_i augmente de 1 et la moyenne double. Après un succès, state_i revient à 1.