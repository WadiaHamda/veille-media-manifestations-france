# Veille média : manifestations en France (octobre 2026)

Analyse automatique des articles publiés sur les manifestations en France,
avec un tableau de bord interactif.

## Installation

```bash
pip install -r requirements.txt
```

## Utilisation

```bash
# 1. créer la base + collecter + nettoyer + analyser (tout d'un coup)
python src/pipeline.py

# 2. lancer le dashboard
streamlit run app/dashboard.py
```

On peut aussi lancer les étapes une par une :

| Etape | Commande | Rôle |
|---|---|---|
| 1 | `python src/db.py` | crée la base SQLite (`data/veille.db`) |
| 2 | `python src/collect.py` | récupère les articles d'octobre (Google News + RSS) |
| 3 | `python src/dedup.py` | supprime / regroupe les doublons |
| 3 bis | `python src/enrich.py` | trouve villes, thèmes et signaux |
| 4 | `streamlit run app/dashboard.py` | affiche le tableau de bord |

## Base de données

- `articles` : titre, url, source, date, résumé, groupe de doublons
- `villes` : 42 grandes villes avec région et coordonnées GPS
- `themes` : 11 thèmes (retraites, budget, agriculture, éducation…) + mots clés
- `signal` : signaux détectés dans chaque article, avec une intensité entre 0 et 1
- `article_ville`, `article_theme` : tables de liaison

## C'est quoi un signal ?

Un indice dans un article qui peut annoncer une décision politique :

| Type | Exemples | Poids |
|---|---|---|
| Réaction politique | 49.3, ministre, motion de censure, amendement | 1.0 |
| Appel à la mobilisation | préavis de grève, journée de mobilisation | 0.9 |
| Ampleur | "15 000 manifestants", selon la préfecture | 0.8 |
| Violences | interpellations, heurts | 0.7 |
| Syndicats | intersyndicale, CGT, CFDT, FNSEA | 0.6 |

En plus, le dashboard détecte les **pics** : un jour avec plus d'articles que
la moyenne + 2 écarts-types.

## Limites

- Google News ne garde pas tout l'historique : il vaut mieux lancer la collecte
  plusieurs fois pendant le mois.
- L'analyse se fait sur le titre + le résumé, pas sur l'article complet (articles payants).
- La méthode par mots clés peut faire des erreurs (ex : "Paris" dans "PSG - Paris").
- Les sources sont surtout nationales, les petites manifestations locales sont moins visibles.

## Améliorations possibles

- spaCy pour détecter toutes les villes (pas seulement les 42 de la liste)
- analyse de sentiment avec un modèle français (CamemBERT)
- mise à jour automatique tous les jours (cron)
