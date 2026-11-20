# SmartAnalytics AI — Frontend

Interface React, TypeScript et Vite de SmartAnalytics AI. Elle combine une landing page de démonstration clairement fictive et un espace privé connecté à l’API FastAPI.

## Fonctionnalités actuelles

- landing responsive avec aperçu produit sans compte ;
- inscription, connexion, restauration et révocation de session serveur ;
- Overview de démonstration et Overview factuel pour le dataset importé actif ;
- import CSV/XLSX, bibliothèque privée, aperçu paginé et contrat de profil `3.0` (qualité, quartiles,
  IQR, atypiques, histogrammes, distributions, corrélations et séries temporelles structurées) ;
- visualisations avancées chargées à la demande : histogrammes, distributions catégorielles,
  heatmap Pearson, fréquences temporelles et panneaux méthodologiques accessibles ;
- Data Explorer avec filtres, tris, agrégations, graphiques et export CSV ;
- assistant analytique connecté au backend, fondé sur des plans validés ;
- états loading, empty, error et success ;
- navigation responsive et composants accessibles au clavier.

Les données de la landing et de l’Overview de démonstration sont fictives et étiquetées comme telles. Pour un dataset importé, l’Overview affiche uniquement des métriques structurelles calculées par le backend ; aucun KPI métier n’est inféré sans mapping explicite. Les datasets importés appartiennent au compte authentifié et sont chargés depuis l’API.

## Lancement local

Depuis la racine du projet :

```powershell
cd frontend
npm.cmd install
if (-not (Test-Path .env.local)) { Copy-Item .env.example .env.local }
npm.cmd run dev -- --host 127.0.0.1 --port 5173
```

Ouvrir `http://127.0.0.1:5173` dans Google Chrome. Le backend local documenté utilise `http://127.0.0.1:8000`.

## Structure principale

- `src/Landing.tsx` : présentation publique et démonstration fictive ;
- `src/app/components/AppLayout.tsx` : shell authentifié, navigation et dataset actif ;
- `src/app/pages/Overview.tsx` : synthèse de démonstration ou profil réel du dataset actif ;
- `src/app/components/DatasetProfileInsights.tsx` : qualité, statistiques numériques et fréquences catégorielles ;
- `src/app/components/ProfileVisualizations.tsx` : visualisations interactives du profil API `3.0` ;
- `src/app/pages/Datasets.tsx` : import, profilage et aperçu ;
- `src/app/pages/DataExplorer.tsx` : construction et exécution de requêtes validées ;
- `src/app/pages/Assistant.tsx` : analyses assistées par IA ;
- `src/app/api/` : contrats et client API avec cookies et CSRF en mémoire ;
- `src/index.css`, `src/app/dashboard.css`, `src/app/auth/auth.css` : design responsive.

## Vérification

```powershell
npm.cmd test
npm.cmd run lint
npm.cmd run build
npm.cmd audit --audit-level=high
```

Le build de production est servi par Nginx. Les routes SPA inconnues sont redirigées vers `index.html` et `/api` est relayé vers FastAPI sur la même origine.

La fixture locale `tests/visual-profile.html` permet une revue responsive sans compte ni donnée
utilisateur. Elle est servie uniquement par Vite en développement et n’entre pas dans le build `dist`.

Après avoir démarré Vite sur le port 4175, `node tests/capture-profile.mjs` contrôle la fixture avec
Google Chrome à 1440×900, 768×1024 et 390×844, puis génère les captures synthétiques dans
`docs/screenshots`. Le script vérifie aussi le focus clavier, les tables accessibles, la heatmap
défilable et l'absence de débordement horizontal global.

La configuration complète, les limites de sécurité et les commandes Docker figurent dans le [README principal](../README.md).
