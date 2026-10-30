# Briefing du matin — Pat

Workflow Mistral planifié tous les jours à **6h20** (Europe/Paris) :

1. Lit les événements du jour dans les agendas Google (Perso, Famille, Pat et Aurélie, SEGPA, Mairie).
2. Compile le déroulé de la journée (HTML).
3. Envoie le programme par email sur Gmail perso → notification sur le téléphone, relayée sur la montre Garmin Venu 3.

## Structure
- `src/workflows/briefing.py` — le workflow (`briefing-matin`).
- `src/entrypoints/worker.py` — démarre le worker.
- `Dockerfile` — image du déploiement géré Mistral Cloud.
