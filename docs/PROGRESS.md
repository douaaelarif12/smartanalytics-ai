# SmartAnalytics AI — Progression

Date : 12 novembre 2026

## Périmètre réalisé

Landing page uniquement, créée dans `frontend/` avec React, TypeScript, Vite, Tailwind CSS v4, Lucide React et Recharts. Aucun backend, authentification, stockage de données utilisateur ou appel OpenAI.

Le workspace était vide : aucun code, README, fichier de configuration, screenshot Sociora ou AGENTS local n’était présent. Node et Google Chrome sont disponibles. npm est exécuté avec `npm.cmd` pour respecter la politique PowerShell existante.

## Interface

- Navigation desktop et menu mobile accessible.
- Hero éditorial, palette ivoire / forêt / sauge, accents serif italiques.
- Aperçu analytics original : métriques, courbe de revenus et répartition par canal.
- Fonctionnalités, parcours en trois étapes, assistant, CTA final et footer.
- Liens internes fonctionnels ; aucune fausse inscription ni formulaire de collecte.
- Filtre 3 / 6 mois et export CSV des revenus de la période sélectionnée.
- Trois questions prédéfinies avec réponses scriptées et sources fictives explicites.
- Navigation clavier, focus visibles, lien d’évitement, annonces des réponses et respect de prefers-reduced-motion.
- Layouts adaptatifs à 1000, 760 et 520 px.

## Organisation

- `frontend/src/Landing.tsx` : sections et composants réutilisables Brand, LinkButton, SectionHeading, Dashboard et Assistant.
- `frontend/src/RevenueChart.tsx` : graphique chargé séparément pour réduire le bundle initial.
- `frontend/src/data/demo.ts` : données fictives et scénarios de conversation.
- `frontend/src/index.css` : tokens Tailwind/CSS et styles responsives.
- `frontend/public/favicon.svg` : identité graphique originale.
- `frontend/index.html` : titre, description et couleur de thème.
- `frontend/vite.config.ts` : plugins React et Tailwind.

Référence visuelle consultée : https://dribbble.com/shots/27027030-SaaS-Landing-Page . Aucun asset Sociora copié. Les illustrations sont réalisées en CSS et avec les icônes Lucide.

## Vérifications

- `npm.cmd run build` : réussi (TypeScript et build de production).
- `npm install` : audit npm sans vulnérabilité signalée au moment de l’installation.
- Serveur Vite démarré sur http://127.0.0.1:5173/ ; réponse HTTP 200 confirmée.
- Graphique séparé en chunk dynamique ; bundle initial ~246 kB, chunk graphique ~362 kB avant gzip.
- Contrôle des ancres internes et cohérence des totaux de revenus : voir résultat du contrôle exécuté pendant l’implémentation.
- Tentative d’ouverture dans Google Chrome via le contrôle navigateur : échec, hôte navigateur indisponible. Aucun contrôle visuel desktop/mobile ni test de clic en navigateur ne peut donc être revendiqué.
- Pas de suite de tests préexistante. Aucun test end-to-end exécuté.

## Frontière entre démo et produit

Les données sont fictives ; les variations de KPI sont illustratives. L’assistant n’est pas une IA active. Connexions de sources, analyse de fichiers, reporting complet et collaboration sont des intentions de produit, pas des intégrations opérationnelles. Le menu latéral du dashboard est une illustration, pas une navigation applicative.

## Vérification manuelle recommandée

Ouvrir http://127.0.0.1:5173/ dans Chrome, vérifier les largeurs 390 / 768 / 1440 px, le menu mobile, les ancres, les deux périodes, le CSV téléchargé, les trois réponses de l’assistant et le parcours clavier. Aucun déploiement externe effectué.

# Phase 2 — Application Overview Dashboard

Date : 12 novembre 2026. Cette phase complète la landing page historique ci-dessus.

## Fonctionnalités implémentées

- React Router : landing `/`, Overview `/app`, routes futures explicitement marquées « Planned » pour Datasets, Data Explorer, Dashboards, AI Assistant et Settings ; états page inconnue pour les chemins non reconnus.
- Un seul changement dans la landing : le bouton principal du hero est devenu « Start Analyzing » avec destination `/app`. Aucun autre contenu, style, layout, animation ou interaction de landing modifié. Vérification SHA-256 : les fichiers `src/index.css`, `src/data/demo.ts` et `src/RevenueChart.tsx` sont identiques à leur version de départ ; le hash de `Landing.tsx` est identique après rétablissement virtuel de ces deux lignes de CTA.
- AppLayout réutilisable : sidebar, états actifs, titre de page, sélecteur de dataset, profil explicitement démo, navigation mobile via dialogue natif avec gestion du focus et fermeture Escape.
- Welcome section, CTA Upload Dataset et Explore Data. Upload ouvre une information claire sur la fonctionnalité future et permet de choisir le sample ; aucun faux upload. Explore Data mène à une page clairement signalée comme prévue.
- Quatre KPI : revenu net, commandes, panier moyen, croissance des revenus. Comparaisons calculées pour revenu, nombre de commandes et panier moyen ; absence de baseline gérée sans division par zéro.
- Trois graphiques Recharts : tendance du revenu, ventes par catégorie et distribution des revenus par catégorie. Tooltips, navigation d’accessibilité Recharts et tables de valeurs dépliables.
- Filtre 1 / 3 / 6 mois : il recalcule les KPI, graphiques et l’insight. Les résultats précédents sont remplacés par un état de chargement pendant une nouvelle requête pour éviter des chiffres décalés.
- Résumé de dataset : nom, lignes, colonnes, date d’import fictive ou absente, complétude, cellules manquantes et IDs de commande dupliqués. Le résumé concerne le dataset entier, indépendamment du filtre analytique.
- Insight de démonstration dérivé de la catégorie dominante et suggestions de questions. Les liens vers l’assistant affichent la question comme non soumise, sans réponse IA inventée.
- Dataset vide sélectionnable, récupération vers le sample, chargements, erreur avec réessai, liens retour à la landing.
- Styles isolés `sa-*` dans `src/app/dashboard.css`, réutilisant les tokens existants, responsive desktop/tablette/mobile, sidebar scrollable sur écran court et respect des préférences de mouvement réduit.

## Architecture et conventions de calcul

- `src/app/types.ts` : types SalesOrder, SalesDataset, AnalyticsSnapshot, DatasetQuality, AnalyticsService.
- `src/app/data/salesDemo.ts` : jeu centralisé de 600 commandes fictives, 8 colonnes, 4 catégories, juillet 2025–juin 2026, plus un dataset vide. Génération déterministe, aucune donnée personnelle.
- Une ligne représente une commande. Revenu net = quantité × prix unitaire × (1 − remise), arrondi une fois au centime par commande. Les centimes sont additionnés avant conversion USD.
- Panier moyen = revenu net / nombre de commandes. Croissance = variation de revenu face à la période précédente de même nombre de mois calendaires. Une baseline nulle produit une valeur indisponible.
- Les périodes sont ancrées au 30 juin 2026 dans les métadonnées du sample, sans dépendance à la date système. Un mois affiche chaque jour, y compris les jours sans vente ; 3 et 6 mois affichent les totaux mensuels.
- `src/app/services/analytics.ts` : fonctions pures de calcul et de qualité.
- `src/app/services/demoAnalyticsService.ts` : adaptateur asynchrone conforme au contrat AnalyticsService, sans HTTP ni délai artificiel. Ce contrat prépare un remplacement futur par un client FastAPI ; FastAPI n’est pas implémenté.
- `src/app/components/` : AppLayout, KpiCard, DatasetSummary, InsightsPreview, AnalyticsCharts, états réutilisables.
- `src/app/pages/` : Overview et écran explicite de fonctionnalité prévue.
- `src/App.tsx` : routes et chargement différé des écrans ; les graphiques sont également chargés séparément.
- La démo historique de la landing reste indépendante pour respecter sa préservation stricte. Toutes les analytics internes partagent la nouvelle source de commandes.

## Vérifications réellement effectuées

- Ajout ciblé de `react-router-dom`, seule dépendance nouvelle requise. Pas de réinitialisation du projet ni de réinstallation générale. Audit npm : aucune vulnérabilité signalée à l’installation.
- `npm.cmd test` : 9 tests passent, avec le runner natif de Node 24, sans dépendance de test supplémentaire.
- Tests : fixture de KPI avec résultats attendus, bornes de dates inclusives, remises et arrondis, baseline nulle, dataset vide, cohérence commandes/graphiques/KPI, changement de période, qualité, adaptateur et erreur de dataset inconnu.
- Test des vraies définitions de routes via Vite SSR et React Router matchRoutes : `/`, `/app`, `/app/`, les cinq placeholders et les chemins inconnus. Destination du CTA contrôlée.
- `npm.cmd run build` : TypeScript et build Vite réussis.
- `/app` servi avec HTTP 200 par le serveur local existant, réutilisé sans lancer un deuxième serveur.
- Contrôle manuel dans Google Chrome avec Computer Use : landing visible avec le nouveau CTA ; Overview visible à `/app` ; passage de 6 à 3 mois et recalcul des KPI/catégories confirmés ; dataset vide affiché avec son message et son résumé.
- Exemple de rapprochement vérifié dans Chrome : 6 mois = 118 663,10 USD / 372 commandes ; 3 mois = 66 091,20 USD / 204 commandes. Ce sont des données de démonstration, pas des performances produit.

## Limites de validation et périmètre futur

L’hôte de contrôle navigateur dédié est indisponible ; le contrôle a été réalisé dans la fenêtre native Google Chrome. Les vérifications visuelles à des largeurs mobile/tablette précises, le parcours complet clavier, l’ouverture des dialogues, les liens de placeholders et la lecture de console ne sont pas validés de bout en bout. Les règles responsive et ces interactions sont implémentées mais ne sont pas présentées comme entièrement testées en navigateur. Aucun test E2E automatisé ajouté.

Pas de recherche inactive dans le header. Aucun backend, upload réel, exploration de lignes, dashboard personnalisé, authentification, réglage persistant ou appel OpenAI. Les routes futures sont informatives, pas des fonctionnalités simulées. Pour un hébergement statique futur, configurer un fallback des routes SPA vers `index.html`, notamment lors d’un accès direct à `/app`.

## Commandes

Depuis `frontend/` :

```powershell
npm.cmd run dev -- --host 127.0.0.1
npm.cmd test
npm.cmd run build
```

Dashboard : http://127.0.0.1:5173/app . Landing : http://127.0.0.1:5173/ . Aucun déploiement externe effectué.

# Phase 3 — Ingestion CSV / Excel et profilage

Date : 12 novembre 2026.

## Fonctionnalités livrées

- Backend FastAPI modulaire dans `backend/app/` avec configuration, service métier, persistance SQLite, stockage de fichiers par UUID, schémas Pydantic et erreurs API structurées.
- Endpoints `GET /api/health`, création/liste/détail/suppression de datasets, aperçu paginé et profil statistique.
- Import `.csv` et `.xlsx`, limite configurable de 20 Mio, nom d’affichage assaini, rejet des extensions et fichiers corrompus, métadonnées persistantes entre redémarrages.
- Détection des colonnes et types, lignes/colonnes/cellules manquantes, complétude, doublons, statistiques numériques et fréquences catégorielles.
- Page `/app/datasets` : glisser-déposer, sélecteur de fichier, progression/traitement, erreurs, succès, liste, sélection, badges de types, qualité, table paginée et suppression confirmée.
- Client API TypeScript typé et URL `VITE_API_BASE_URL`. Le jeu de démonstration et les imports réels restent séparés.
- Le sélecteur global regroupe « Demo datasets » et « Uploaded datasets ». L’Overview conserve ses calculs démo ; pour un import sans mapping métier, il affiche un état explicite et aucun KPI synthétique.
- Landing et présentation du dashboard Overview préservées. Aucun backend d’authentification et aucune intégration OpenAI ajoutés.

## Vérifications

- Backend : 11 tests Pytest réussis (CSV, XLSX, extension invalide, corruption, valeurs manquantes, fichier sans lignes, pagination/validation, limite de taille, suppression et persistance).
- Frontend : 12 tests Node réussis, dont validation de fichiers, transitions loading/error/list/delete, rendu de liste/état vide et routage réel.
- `npm.cmd run build` réussi avec TypeScript et Vite.
- Les données locales sont exclues via `.gitignore`; la suppression est définitive et demande confirmation dans l’interface.
- Smoke test HTTP réel réussi : santé 200, création 201, aperçu 200 et suppression 204. Le contrôle visuel Chrome n’a pas pu être exécuté car l’hôte de contrôle navigateur était indisponible ; aucune validation visuelle manuelle n’est donc revendiquée pour cette phase.

## Limites actuelles

Le profilage relit le fichier à la demande et vise un MVP local de taille modérée. Il n’existe pas encore de mapping sémantique des colonnes, d’authentification, de stockage cloud, d’analyse multi-feuilles, de traitement asynchrone ou d’appel IA. Le serveur doit rester lié à `127.0.0.1` dans cet état.

## Commandes

Backend depuis `backend/` :

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
.\.venv\Scripts\python.exe -m pytest -q
```

Frontend depuis `frontend/` :

```powershell
Copy-Item .env.example .env.local
npm.cmd run dev -- --host 127.0.0.1
npm.cmd test
npm.cmd run build
```

# Phase 4 — Data Explorer et moteur analytique sécurisé

Date : 12 novembre 2026.

## Fonctionnalités implémentées

- Nouveau endpoint `POST /api/datasets/{dataset_id}/query` fondé sur un contrat Pydantic strict ; les champs inconnus et tout SQL libre sont rejetés.
- Moteur `AnalyticsEngine` utilisant DuckDB en mémoire sur les DataFrames CSV/XLSX existants. Les noms de colonnes sont validés contre le schéma puis échappés côté serveur ; toutes les valeurs de filtres utilisent des paramètres.
- Sélection de colonnes, filtres typés, tris, pagination, groupes catégoriels, groupes de dates jour/mois/année et agrégations `COUNT`, `SUM`, `AVG`, `MIN`, `MAX`.
- Limites : 10 filtres, 3 tris, 2 dimensions, 5 agrégations, 30 colonnes et 200 lignes par réponse. DuckDB est limité à deux threads et 256 Mio par connexion.
- Détection prudente des dates ISO lors de l’ingestion afin d’autoriser les regroupements temporels uniquement quand la colonne est réellement reconnue comme date.
- Résultat chart-ready partageant exactement les mêmes lignes que la table analytique.
- Page réelle `/app/explorer` : sélecteur de dataset importé, choix de colonnes, filtres, mode lignes/agrégats, groupement, agrégations, tri en cliquant sur les en-têtes, pagination, graphiques barres/ligne/camembert et export CSV du résultat courant.
- Les datasets de démonstration restent sur Overview. L’Explorer demande explicitement un dataset importé et ne fabrique aucune donnée.
- États de chargement, erreur backend, résultat vide et absence de dataset implémentés.

## Fichiers principaux modifiés ou ajoutés

- Backend : `app/models.py`, `app/analytics.py`, `app/service.py`, `app/api.py`, `app/profiling.py`, `requirements.txt`, `tests/test_analytics.py`.
- Frontend : `src/app/pages/DataExplorer.tsx`, `src/app/components/ExplorerChart.tsx`, `src/app/explorerState.ts`, client/types API, routage, navigation et styles isolés du dashboard.
- Tests : `tests/explorer.test.ts` et `tests/explorer-render.test.mjs`.

## Vérifications effectuées

- Backend : **18 tests Pytest réussis**. Les 11 tests d’ingestion existants restent verts et 7 tests analytiques couvrent filtres/tris, pagination, exactitude des agrégats, groupes catégoriels et temporels, valeurs manquantes, dataset vide, colonnes/opérateurs invalides, payload SQL et limites.
- Frontend : **16 tests Node réussis**. Les 12 tests existants restent verts ; les nouveaux tests couvrent sélection de dataset, interaction/normalisation des filtres, configuration d’agrégation et rendu des états erreur/vide.
- `npm.cmd run build` : TypeScript et build Vite réussis.
- Smoke test réel : CSV importé avec une colonne date détectée, filtre `amount >= 7`, somme groupée par mois renvoyant exactement `30` puis `7`, payload chart-ready identique, puis suppression 204. Aucune donnée de smoke test n’a été conservée.
- Google Chrome est bien installé au chemin attendu, mais l’hôte de contrôle navigateur était indisponible. Aucun contrôle visuel manuel ou E2E navigateur n’est donc revendiqué pour cette phase.

## Limites connues

- Le moteur relit le fichier pour chaque requête et cible des datasets locaux de taille MVP ; il n’existe pas encore de cache de table DuckDB, de jobs asynchrones ni de quotas par utilisateur.
- L’export CSV porte sur la page de résultat courante, limitée à 200 lignes. Le camembert représente la première mesure lorsqu’une requête contient plusieurs agrégations.
- La détection de date automatique vise les formats ISO majoritaires. Les formats ambigus restent volontairement du texte.
- Les fichiers importés avant cette phase conservent leurs métadonnées historiques ; les réimporter permet d’appliquer la nouvelle détection temporelle.
- Aucun OpenAI, SQL libre, authentification ou partage cloud n’est implémenté.

## Prochaine phase recommandée

Ajouter un mapping sémantique explicite (date, mesure, dimension), des requêtes enregistrées et un cache DuckDB persistant. Ces contrats validés pourront ensuite devenir les outils strictement autorisés d’un futur assistant IA, sans jamais lui fournir une capacité SQL arbitraire.


# Phase 5 — Assistant AI Data Analyst

Date : 12 novembre 2026. Cette phase complète les états historiques précédents.

## Implémenté

- Endpoint `POST /api/datasets/{dataset_id}/ai/ask`, service dédié `backend/app/ai.py`, modèles
  dans `ai_models.py`, SDK officiel OpenAI Python 2.54.0 et Responses API `responses.parse`.
- Modèle `gpt-4.1-mini` par défaut ; configuration exclusivement depuis `backend/.env`, avec
  python-dotenv 1.2.4 et interpolation désactivée. Aucune clé envoyée au frontend ou au modèle.
- Planification structurée stricte depuis le schéma minimal : noms/types, valeurs manquantes,
  nombre de lignes et question. Aucun fichier ou enregistrement brut envoyé.
- Double validation par Pydantic et le moteur existant avant calcul DuckDB. Aucun SQL, code,
  outil externe ou écriture généré par le modèle exécuté.
- Explication fondée sur les résultats agrégés réellement calculés, avec second appel borné.
  Sélections brutes présentées localement sans appel explicatif. `store=False` pour chaque appel.
- Clarification pour les ambiguïtés et refus des opérations hors contrat ; états vides explicites.
- Erreurs structurées pour fournisseur indisponible, timeout, refus/sortie invalide, plan invalide,
  quota local/fournisseur et concurrence. Détails sensibles du fournisseur non répercutés.
- Limites : question de 2 000 caractères, 100 colonnes et 24 000 caractères de schéma JSON,
  50 résultats et 24 000 caractères de contexte explicatif agrégé, 2 500 tokens de sortie/appel,
  timeout SDK 20 secondes et un retry, deux requêtes simultanées et dix demandes/minute/processus.
- Client SDK fermé au shutdown FastAPI.
- Page réelle `/app/assistant` : sélection des imports, chat local, suggestions issues des colonnes,
  saisie bornée, chargement, erreurs avec reprise, explications, tableaux, graphiques interactifs
  existants et panneau du plan validé. Badge Planned retiré pour cette route.
- Réponses obsolètes ignorées après changement de dataset ; attente frontend de 100 secondes.
  Les suggestions remplissent la saisie sans déclencher un appel payant automatiquement.
- Styles `sa-assistant-*` isolés. Landing, Overview, Data Explorer et ingestion conservés.
  Aucun reset du projet, changement de dataset original ou migration de données.
- `.gitignore` exclut `.env` et ses variantes ; `.env.example` est autorisé et sans secret.
  README complété avec architecture, configuration, exemples, sécurité et limites.

## Vérifications réellement effectuées

- **40 tests backend réussis** : 18 préexistants et 22 cas IA simulés. Couverture des résultats
  réels attendus, contexte minimal, colonnes invalides, ambiguïtés, opérations interdites,
  données/résultats vides, réseau, timeout, quotas, concurrence, taille/forme des requêtes,
  plans SQL/injections interdits, non-envoi des lignes brutes et configuration de clé/client.
- Avertissement existant de dépréciation Starlette/AnyIO BlockingPortal ; aucun échec.
- **18 tests frontend réussis** : 16 préexistants et deux nouveaux pour rendu réel/clarification,
  échappement HTML et contrat HTTP d’erreur de l’assistant.
- `npm.cmd run build` réussi : TypeScript et Vite. Assistant et graphiques chargés séparément.
- `/app/assistant` servi avec HTTP 200 par le serveur Vite existant.
- **Smoke test réel OpenAI via l’endpoint FastAPI** avec stockage temporaire : HTTP 200,
  CSV synthétique de trois lignes, sommes exactes A = 15 et B = 20, explication présente,
  lignes du graphique identiques au résultat. Aucune clé affichée.
- Les premiers essais réels ont été rejetés en 422 car le modèle mélangeait sélection brute
  et agrégation. Les consignes de forme ont été précisées ; le nouvel essai a réussi.
  La validation du moteur est restée active pendant tous les essais.
- Chrome est présent au chemin attendu. Contrôle navigateur bloqué par « browser access host
  is unavailable » : aucun contrôle visuel manuel ou E2E navigateur revendiqué.
- Aucun motif de clé secrète détecté dans les sources et le build frontend (contrôle sans
  affichage des correspondances). Règle `.env` présente dans `.gitignore`.
- `git status` ne reconnaît pas de dépôt dans ce workspace. Les exclusions sont configurées,
  mais le suivi effectif dans un index Git n’a pas pu être vérifié.

## Limites connues

- MVP local sans authentification ni autorisation multi-utilisateur ; écoute sur `127.0.0.1`.
  Déploiement partagé conditionné à ces protections et à des quotas distribués.
- Limites globales par processus, réinitialisées au redémarrage ; aucun quota par utilisateur.
- Timeouts SDK réseau, sans deadline stricte couvrant lecture, DuckDB et appels IA.
  L’abandon frontend ne stoppe pas automatiquement un travail serveur déjà commencé.
- Questions indépendantes, historique local de 20 échanges ; reformuler une question complète
  après clarification. Pas de jointure, prévision, formule libre ou mémoire persistante.
- Graphiques limités aux agrégations avec une seule dimension ; troncature signalée.
- Explication probabiliste susceptible d’erreurs malgré le contexte calculé. Plan et tableau
  constituent les preuves consultables. Les tests d’injection simulés ne garantissent pas
  une résistance exhaustive aux manipulations sémantiques du modèle.
- Les groupes agrégés peuvent contenir des informations sensibles. L’interface informe de
  l’envoi à OpenAI ; `store=False` ne garantit pas la rétention zéro chez le fournisseur.
- Les connexions SQLite existantes peuvent retarder sous Windows le nettoyage des répertoires
  temporaires jusqu’au garbage collection. Les datasets du dernier smoke ont été supprimés.


# Phase 6 — QA complète et stabilisation

Date : 12 novembre 2026. Cette section est l’état le plus récent ; les phases précédentes
restent un historique des résultats et limites à leur date.

## Anomalies corrigées

- SQLite : le contexte transactionnel ne fermait pas les connexions. Ajout d’un contexte explicite
  avec commit/rollback et fermeture garantie. Une régression vérifie la fermeture immédiate,
  le rollback et la libération du fichier sous Windows, sans garbage collection nécessaire.
- Ingestion : les en-têtes normalisés pouvaient se dupliquer (`x`, ` x`, `x_2`) ou entrer en
  collision de casse avec les identifiants DuckDB. Allocation de noms uniques qui préserve
  les noms source réservés. Les fichiers originaux ne sont pas modifiés ; les anciens imports
  ne sont pas migrés automatiquement. Une réimportation applique la nouvelle normalisation.
- Analytics : rejet des alias qui masquent une dimension ou un autre alias, y compris avec
  une casse différente ; rejet des valeurs de filtre imbriquées/non finies ou trop longues.
- Graphiques : pas de payload numérique trompeur pour plusieurs dimensions ou une mesure de date.
  Les mesures numériques compatibles restent disponibles, et le tableau conserve tous les résultats.
- Camembert : message accessible lorsque les valeurs sont négatives ou sans total positif ;
  les graphiques barres/ligne et le tableau restent utilisables.
- Explorer : montage distinct par dataset et initialisation du plan dès le montage. Un ancien
  plan n’est plus soumis au dataset suivant, et les réponses tardives sont ignorées.
  Les anciens tableaux/graphiques et l’export sont masqués ou désactivés pendant le recalcul.
- Explorer : sélection initiale limitée à 30 colonnes et alias générés bornés pour respecter l’API.
- Datasets : ancien aperçu masqué pendant le chargement suivant, pagination réinitialisée après
  suppression et verrou contre les uploads simultanés par double action/glisser-déposer.
- Workspace : les erreurs réseau de rafraîchissement ne sont plus présentées comme une bibliothèque
  vide. Erreur avec reprise, conservation de la dernière liste connue et récupération vers le
  dataset démo si un import sélectionné a disparu après un rafraîchissement réussi.
- Assistant : échec de la seconde étape explicative traité comme un résultat calculé disponible
  avec avertissement, plutôt qu’une perte du tableau et du plan. Les erreurs de planification
  continuent à utiliser les statuts API structurés.
- Cohérence UI : usage de la classe typographique existante `sa-overline` pour l’assistant et
  correction du bandeau qui affirmait encore qu’aucune IA n’était connectée.
- Sécurité XLSX : limite de 2 000 membres / 100 Mio décompressés avant lecture, ajout de
  `defusedxml==0.7.1`, erreurs XML corrompues ou entités interdites converties en erreurs structurées.
- Export CSV : neutralisation des chaînes pouvant devenir des formules dans un tableur, avec
  conservation des valeurs numériques et échappement des guillemets. Aucun changement des sources.

## Fichiers concernés

Backend : `app/storage.py`, `app/profiling.py`, `app/analytics.py`, `app/ai.py`,
`requirements.txt`, `tests/test_qa.py` et `tests/test_ai.py`.
Frontend : pages `Datasets.tsx`, `DataExplorer.tsx`, `Assistant.tsx`, composants `AppLayout.tsx`
et `ExplorerChart.tsx`, `explorerState.ts`, nouveau `csv.ts`, tests `qa-ui.test.mjs`,
`csv.test.ts`, `explorer.test.ts`, dépendances de développement jsdom et lockfile.
README et présent journal mis à jour. Identité ivoire/forêt/sauge et landing conservées.

## Résultats de tests effectivement obtenus

| Contrôle | Résultat |
| --- | --- |
| `python -m pytest backend/tests -q` | **54 réussis, 0 échec** |
| `npm.cmd test` | **24 réussis, 0 échec** |
| `npm.cmd run build` | **TypeScript et production Vite réussis** |
| `npm.cmd run lint` | Exit 0 ; dix avertissements React, aucune erreur |
| `npm.cmd audit` | Zéro vulnérabilité signalée à cet instant, dev inclus |
| `python -m pip check` | Aucune dépendance incompatible |
| Santé backend local, liste des datasets | HTTP 200 |
| Landing et routes app/datasets/explorer/assistant | HTTP 200 |
| CORS origine locale autorisée | Vérifié |
| Motif de secret dans sources/build frontend | Aucun détecté, sans affichage des correspondances |
| Présence de clé et modèle GPT-4.1 mini | Vérifiée par booléens seulement |

Les routes inconnues retournent aussi HTTP 200 côté serveur Vite, conformément au fallback SPA ;
le rendu de page inconnue est vérifié par la suite de routage React, pas par ce statut HTTP seul.
Trois avertissements Python : dépréciations Starlette/AnyIO et backend WebSocket Uvicorn.
Les avertissements React concernent Fast Refresh, mises à jour d’état dans les effets et Date
pendant le rendu de la landing. Aucun remaniement gratuit de la landing pour les faire disparaître.

## Parcours intégrés et limites de preuve

- Test HTTP sur un vrai serveur Uvicorn avec socket locale temporaire et stockage de test isolé :
  upload CSV puis XLSX, détection des dates, profil complet, aperçu, filtre/tri, agrégation et
  chart-ready, assistant, clarification/refus simulés, entrée SQL interdite, suppression des seuls
  datasets synthétiques et vérification 404/retour à une liste vide.
- Résultats rapprochés de sommes calculées indépendamment avec pandas : A = 15, B = 20.
- Persistance contrôlée avec une nouvelle instance du repository ; les tests existants vérifient
  également la recréation de l’application sans perte de métadonnées.
- CORS testé avec origine locale acceptée et origine non autorisée refusée.
- Tests DOM jsdom : clic sur une suggestion et soumission de l’assistant ; changement de dataset,
  signal d’abandon et réponse tardive ignorée ; Explorer sans plan croisé ; aperçu précédent
  absent pendant le chargement suivant ; camembert incompatible expliqué de façon accessible.
- Tests de sécurité ajoutés : collisions de noms/alias, filtres imbriqués, XML corrompu, archive
  avec trop de membres, entités XML interdites et formules d’export CSV.
- IA majoritairement simulée. Aucun nouvel appel OpenAI payant dans cette phase ; le smoke réel
  HTTP 200 de la phase 5 reste la dernière preuve d’appel fournisseur réel. Les tests simulés
  vérifient les frontières de validation, pas une résistance sémantique exhaustive du modèle.
- Aucun dataset utilisateur supprimé, aucune réinitialisation de base et aucun déploiement externe.
  Backend démarré sur 127.0.0.1:8000 ; Vite existant réutilisé sur 127.0.0.1:5173.
- **Vérification visuelle non accomplie** : hôte navigateur dédié indisponible. Le contrôle natif
  Chrome a ensuite été arrêté par l’outil car l’URL courante ne pouvait pas être déterminée
  avec assez de certitude. Les interactions navigateur ont cessé. Aucun screenshot validé,
  contrôle responsive à dimensions précises ou parcours clavier complet revendiqué.

## Blocages de déploiement et points restants

- Authentification, autorisation par dataset et isolation multi-utilisateur absentes : bloquants
  pour un déploiement partagé. Garder les serveurs sur l’interface locale.
- Quotas IA par processus uniquement ; pas de quotas distribués, de budget par utilisateur
  ou de deadline stricte couvrant lecture du fichier, DuckDB et les appels IA.
- L’explication reste probabiliste : tableaux et plans calculés sont les preuves vérifiables.
- Données agrégées potentiellement sensibles envoyées au fournisseur, sans garantie de rétention zéro.
- Aucun audit de vulnérabilités Python dédié exécuté : `pip check` vérifie la compatibilité uniquement.
- Aucun dépôt Git reconnu dans ce workspace : règles d’exclusion vérifiées, suivi dans un index
  non vérifiable. Aucun commit ou publication effectué.
- Les limites XLSX protègent le parsing sans garantir une consommation mémoire/CPU maximale stricte
  pour tous les fichiers. Le moteur relit encore les fichiers pour chaque requête.

## Commandes de lancement

Depuis `backend/` (dépendances déjà installées) :

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Depuis `frontend/` :

```powershell
npm.cmd run dev -- --host 127.0.0.1 --port 5173
```

Vérifier les ports avant lancement et réutiliser un serveur existant. Les commandes d’installation
et de test figurent dans README ; les fichiers `.env` existants sont préservés.


# Phase 7 — Utilisabilité, avertissements React et contrôle visuel restant

Date : 12 novembre 2026.

## Disponibilité et limite navigateur

- README et journal consultés avant modification ; serveurs existants réutilisés, sans reset.
- FastAPI écoute sur `127.0.0.1:8000`, santé HTTP 200. Vite écoute sur `127.0.0.1:5173`.
- **URL exacte `http://127.0.0.1:5173/app` vérifiée avec HTTP 200**.
- Tentative d’ouverture avec automatisation Google Chrome à cette URL exacte : échec immédiat,
  « The browser access host is unavailable ». Aucun contrôle de pixels, screenshot desktop/mobile,
  tooltip natif, disposition ou typographie visuellement validé pendant cette phase.
- La [checklist manuelle](VISUAL_QA_CHECKLIST.md) fournit les étapes, valeurs attendues, formats
  de captures et viewports précis (1440 × 900, 768 × 1024, 390 × 844, 320 × 740). Elle couvre
  les cinq pages demandées, navigation, tableaux, graphiques, chargement, erreurs, focus,
  clavier, zoom 200 % et mouvement réduit. Son statut reste **à exécuter**.

## Dix avertissements React traités sans désactivation de règle

| Avertissement initial | Correction |
| --- | --- |
| Fast Refresh : export de configuration dans App | Configuration dans `routes.tsx`, écrans dans `RouteScreens.tsx`, App limité aux composants. Test de routes mis à jour. |
| Fast Refresh : constante exportée depuis InsightsPreview | Questions transférées vers `app/data/suggestedQuestions.ts`. |
| Fast Refresh : hook exporté depuis AppLayout | Contrat et hook dans `app/workspace.ts`, imports des pages mis à jour. |
| Date appelée pendant le rendu de Landing | Année initialisée une fois au montage avec l’initialiseur de useState ; présentation conservée. |
| Assistant : réinitialisation synchrone dans un effet | Composant de conversation monté par dataset ; effet réservé à l’abandon des requêtes au démontage. |
| AppLayout : effacement d’erreur dans l’effet du sample | Effacement dans l’événement de réessai ; chargement asynchrone conservé. |
| AppLayout : rafraîchissement déclenchant des setters depuis l’effet | Mises à jour uniquement dans les callbacks de résolution/rejet de la requête. |
| AppLayout : fermeture du menu avec setter dans l’effet de navigation | État d’ouverture associé à la route et mises à jour dans les événements du dialogue ; fermeture et retour du focus conservés. |
| Datasets : réinitialisation synchrone des détails dans l’effet | Chargement dérivé de la clé dataset/pagination et de la dernière réponse terminée ; anciens aperçus masqués immédiatement. |
| Explorer : état de chargement modifié dans l’effet | Initialisation au montage et transitions dans `applyQuery`, appelée par les actions Run, Reset, tri, pagination et Retry. |

La configuration `.oxlintrc.json` n’a pas été affaiblie. Aucun changement CSS ni refonte visuelle.
Le footer Overview a aussi été corrigé : l’insight démo est calculé localement, tandis que
l’assistant applicatif est désormais connecté ; le lien ne le présente plus comme un simple preview.

## Assistant réel sur dataset synthétique

- Fixture ajoutée : `docs/fixtures/usability-sales.csv`, trois lignes (A/10, B/20, A/5), avec dates ISO.
- Dataset local créé : `8b47aec9-1610-4a0b-89e0-0eda76feebe7`, nom `usability-sales`.
  Il est conservé pour la checklist manuelle. Aucun dataset utilisateur supprimé.
- **Un seul nouvel appel réel** à l’endpoint de l’assistant : HTTP 200, statut `answer`.
- Sommes attendues calculées indépendamment avec le module Python `csv` et addition d’entiers :
  A = 15 et B = 20. Résultats réels identiques, lignes du graphique identiques au tableau,
  explication générée sans avertissement de secours.
- Preuve non sensible enregistrée dans `docs/usability-ai-smoke.json` ; aucune clé ou contenu
  de `.env` affiché ni enregistré dans cet artefact.
- Cet appel valide le parcours backend/fournisseur, pas l’affichage dans le navigateur.

## Tests après les modifications

| Commande | Résultat |
| --- | --- |
| `backend/.venv/Scripts/python.exe -m pytest backend/tests -q` | **54 réussis, zéro échec** |
| `npm.cmd test` depuis frontend | **26 réussis, zéro échec** |
| `npm.cmd run lint` | **Exit 0, zéro erreur, zéro avertissement** |
| `node_modules/.bin/tsc.cmd -b --pretty false` | **Exit 0** |
| `npm.cmd run build` | **TypeScript et production Vite réussis** |

Les trois avertissements de dépréciation Python Starlette/AnyIO/WebSocket restent présents,
sans échec. Les 24 tests frontend existants restent verts et deux régressions DOM ont été ajoutées :

1. Explorer : résultat visible, lancement suivant, indicateur de chargement sans ancien résultat,
   erreur réseau lisible, puis reprise réussie sans erreur persistante.
2. Sidebar : ouverture du dialogue, navigation vers l’assistant, fermeture, `aria-expanded=false`
   et focus rendu au bouton menu. Les méthodes natives du dialogue sont simulées dans jsdom ;
   ce test n’est pas une preuve de comportement visuel ou tactile dans Chrome mobile.

Les régressions existantes continuent à vérifier l’abandon des réponses IA après changement de
dataset, l’absence de plans croisés et le masquage des aperçus périmés.

## Travail restant et frontières

La validation visuelle demandée reste bloquée par l’outil navigateur. La checklist manuelle
constitue le livrable pour lever ce blocage ; ses cases ne sont pas déclarées réussies.
Authentification, autorisation par dataset, isolation multi-utilisateur, quotas distribués et
deadline globale restent des blocages de déploiement partagé. Aucun contournement, exposition
réseau publique, modification de clé, suppression utilisateur ou réinitialisation n’a été effectué.


# Phase 8 — Phase 2 SaaS : authentification et isolation multi-utilisateur

Date : 12 novembre 2026. Cette section décrit l’état actuel et complète les phases historiques.

## Architecture examinée et évolution retenue

L’ancienne persistance était un repository SQLite direct avec table `datasets`, JSON de métadonnées
et fichiers `files/{uuid}.{csv|xlsx}`, sans utilisateur ni session. Les contrôles Pydantic/DuckDB,
l’ingestion et le frontend existants ont été examinés et conservés. Pas de reset ni suppression
ou attribution automatique des données historiques.

- Ajout d’une couche SQLAlchemy 2 compatible PostgreSQL et d’Alembic, révision `0001_multi_user`.
  Tables : users, sessions, métadonnées propriétaires, décisions d’attribution, compteurs et usage IA.
- En développement sans URL DB, nouveau fichier `backend/data/saas.sqlite3` distinct de l’ancien.
  Les comptes et sessions ne sont jamais écrits par le format legacy. Une URL PostgreSQL invalide
  ne provoque pas de fallback ; la production refuse SQLite et impose Redis/cookies Secure/HTTPS.
- Le point d’entrée `app.main:app` est conservé avec initialisation ASGI différée : importer les
  outils/tests ne connecte pas implicitement la base configurée par l’opérateur.
- Import legacy séparé, read-only côté source, simulation par défaut, inventaire UUID/noms,
  attribution par fichier privé UUID→email existant et identité opérateur obligatoire.
  Sans attribution, import en quarantaine inaccessible aux comptes. Conflits refusés, UUID/JSON
  conservés, copies de fichiers vérifiées SHA-256, sources jamais supprimées.
- Le downgrade d’une base SaaS peuplée est refusé. Le roundtrip d’une base neuve et la parité
  modèles/migration sont testés. Le template de génération de migrations produit du Python valide.
- PostgreSQL 17 répond sur la machine, mais ses credentials applicatifs n’ont pas été présumés.
  Les tests PG ont donc utilisé un cluster temporaire SCRAM séparé, sur port aléatoire, avec mots
  de passe éphémères non affichés. Le serveur PostgreSQL local existant n’a pas été modifié.
- Compose de développement PostgreSQL 17/Redis 7 livré, ports loopback 5433/6380 et volumes persistants.
  `docker compose config --quiet` réussi avec placeholders de validation. Le daemon Docker est arrêté :
  aucun lancement de conteneur ni test Redis réel revendiqué.

## Authentification et frontières de sécurité implémentées

- Inscription, connexion, déconnexion, session restaurable et current-user réels en base.
- Email validé/normalisé, unicité SQL ; mots de passe 15–128 caractères avec quatre classes,
  Argon2id 64 Mio/trois itérations/parallélisme deux et limite de quatre calculs crypto simultanés.
- SID aléatoire 256 bits, hashé en base, renouvelé à l’authentification, expirations absolue/inactive,
  révocation effective à la déconnexion et partagée entre instances.
- Cookies HttpOnly/SameSite=Lax ; Secure et préfixe __Host- quand activé, obligatoires en production.
  L’exception `COOKIE_SECURE=false` reste réservée au HTTP local de développement.
- CSRF synchronisé en mémoire frontend avec session serveur ; origine exacte et header requis,
  y compris pour login/register/logout. Origines wildcard et headers CSRF non ASCII refusés.
- Middleware d’accès privé avant parsing des uploads, limites des corps HTTP y compris chunked,
  headers no-store/nosniff/DENY et erreurs publiques sans données fournisseur ou credential.
- Quotas auth IP/email et plafonds d’inscription/bootstrap ; erreurs de connexion génériques.
- Propriété vérifiée pour liste, upload, détail, aperçu, profil, query, IA, export et delete.
  Aucun owner frontend accepté ; accès croisé = 404, session absente = 401.
- Chemins privés UUID validés ; une collision d’allocation ne supprime plus un fichier préexistant.
- Quotas IA par utilisateur/minute/jour via Redis atomique ou SQL atomique en développement.
  Redis configuré indisponible = 503, aucun fallback local silencieux. Retry-After sur 429.
- Ledger de tokens par utilisateur et modèle, endpoint privé d’usage, estimation USD facultative.
  Aucun prompt/résultat ni clé n’est enregistré dans ce ledger. L’estimation n’est pas une facture.
- SDK Responses/Pydantic/DuckDB préservés, autorisation avant quota/fichier/fournisseur.
  Attente serveur 90 secondes, checks d’annulation avant étapes, SDK 20 secondes/un retry,
  interruption DuckDB après dix secondes. Une étape réseau déjà engagée peut terminer et être facturée.
- `/api/ready` vérifie DB/Redis configuré et échoue en 503 sans détails sensibles.

## Frontend implémenté

- Pages `/register` et `/login` dans l’identité visuelle existante, formulaires accessibles avec
  autocomplete, consignes, pending et erreurs. `/app` attend la session puis redirige si anonyme.
- Menu du compte avec vraie adresse et déconnexion, restauration et reprise après erreur réseau.
- Cookies avec credentials, CSRF en mémoire seulement ; aucun token auth dans localStorage/sessionStorage.
- Bootstrap de session mutualisé pour éviter les courses entre montages React ; signalisation entre
  onglets compatibles via BroadcastChannel, sans secret transporté.
- Workspace monté par identité utilisateur : caches/résultats privés réinitialisés au changement de compte.
  Bibliothèque vide pour un nouveau compte, sample Overview conservé et explicitement démo.
- Export Explorer relié au backend protégé avec le plan appliqué, CSRF et cookie ; erreur et annulation
  gérées sans déclencher un téléchargement provenant d’un composant démonté.
- Landing, typographie/palette existantes, ingestion, Explorer, graphiques et AI Analyst préservés.

## Vérifications finales obtenues

| Contrôle | Résultat réel |
| --- | --- |
| Suite backend complète | **107 tests réussis, 0 échec** |
| Suite sécurité avec PostgreSQL réel | **52 tests réussis, 0 échec** — sous-ensemble réexécuté, pas 52 tests uniques supplémentaires |
| Suite frontend complète | **32 tests réussis, 0 échec** |
| Lint React/TypeScript | **0 erreur, 0 avertissement** |
| TypeScript `tsc -b --pretty false` | **Réussi** |
| Production Vite | **Réussie** |
| `pip check` | Aucune dépendance incompatible |
| `npm audit` | Zéro vulnérabilité signalée à cet instant, dev inclus |
| Configuration Compose | Validée syntaxiquement, daemon non démarré |
| Template Alembic | Génération et compilation Python validées dans un répertoire temporaire isolé |

Les 54 anciens tests backend ont été adaptés pour créer une vraie session avec Argon2id/CSRF ;
aucun bypass d’authentification ou override de sécurité n’a été utilisé pour les faire passer.
Les 26 anciens tests frontend restent verts ; six tests auth/HTTP privés ont été ajoutés.
Les avertissements de dépréciation Python Starlette/AnyIO/WebSocket subsistent sans échec.

### Couverture de sécurité et migration

Deux utilisateurs indépendants vérifient chaque opération privée, dont refus de query/IA/export/
suppression croisés et maintien du fichier du propriétaire. Tests de mot de passe incorrect, email
inconnu/dupliqué/normalisé, politique forte, cookie Secure/HttpOnly/SameSite, rotation, replay,
expiration, CSRF/origine, rate limiting durable, concurrence crypto/SQL, usage privé, Redis fail-closed,
annulation IA, upload malveillant/collision et corps HTTP surdimensionné.

Sessions et révocation sont vérifiées avec deux instances d’application partageant la DB.
Un test HTTP réel Uvicorn utilise deux cookie jars séparés, inscrit/connecte les comptes, importe
un CSV synthétique, refuse les accès croisés, calcule A=15/B=20, exporte, puis révoque la session.
Les appels OpenAI sont simulés, avec calcul DuckDB réel ; aucun nouvel appel fournisseur payant.

L’import historique est testé en dry-run, en quarantaine, puis avec attribution explicite à un
compte existant ; le second compte reste exclu, la répétition ne duplique pas les décisions et
les SHA-256 de la base et du fichier sources restent inchangés. Ces cas passent aussi sur PostgreSQL.

### Smoke test sur les serveurs du workspace

- Backend redémarré sur `127.0.0.1:8000`, Vite réutilisé sur 5173.
- Vie/disponibilité : HTTP 200 ; liste de datasets, me et usage sans session : HTTP 401.
- Bootstrap anonyme réel : HTTP 200, user=null, cookie HttpOnly, CORS credentials=true,
  sans affichage du cookie ou du CSRF.
- Landing, `/login`, `/register`, `/app`, `/app/assistant` servis HTTP 200 par Vite.
  Ce statut est le fallback SPA, pas une preuve de rendu ni d’accès authentifié.
- Runtime local actuel : **SQLite de développement distinct, Redis non configuré**.
  La cible PostgreSQL/Redis est implémentée et PostgreSQL validé en tests isolés ; le runtime
  n’a pas été basculé vers le serveur PostgreSQL existant sans credentials/décisions opérateur.
- Somme SHA-256 du legacy SQLite inchangée avant/après ce smoke ; aucune migration réelle des
  données historiques exécutée et aucun propriétaire inventé. Aucun dataset utilisateur supprimé.
- Aucun motif de clé dans les sources/build frontend ; aucun usage de stockage navigateur pour l’auth.
- Tentative Chrome à l’URL exacte `/app` : « browser access host is unavailable ».
  Les nouveaux écrans ne sont pas déclarés visuellement validés ; checklist manuelle mise à jour.

## Documentation et fichiers principaux

`README.md` et `backend/README.md` reflètent désormais l’authentification réelle. Nouveaux documents :
[architecture SaaS](SAAS_ARCHITECTURE.md) et [migration SQLite/PostgreSQL](SQLITE_TO_POSTGRES.md).
Exemples d’environnement mis à jour sans toucher à `backend/.env` ni à sa clé.

Backend : database/db_models/repository/auth/limits/security/legacy_migration, migrations Alembic,
service/API/main/AI, tests de sécurité et HTTP multi-utilisateur, script de tests PG isolés.
Frontend : auth provider/context/API/formulaires/guard/menu, transport HTTP central, export protégé,
routes/Layout et tests. Compose et exclusions de fichiers privés ajoutés.

## Limites et prérequis de déploiement non masqués

- Aucune attribution effective des datasets historiques : décisions d’un administrateur nécessaires.
- Les comptes déjà créés dans le nouveau fallback SaaS SQLite nécessiteraient un transfert complet
  explicite avant un changement d’URL ; l’importeur livré traite le format historique des datasets.
- Redis réel, conteneurs Compose, reverse proxy/TLS, rôles DB minimaux, stockage partagé protégé,
  backups/restaurations et maintenance opérationnelle restent à vérifier avant exposition publique.
- Pas de vérification email, reset de mot de passe, MFA, screening de mots de passe compromis,
  quotas de stockage, audit immuable ou interface web d’administration.
- Parsing de fichiers sans deadline CPU globale ; fichiers/DB sans transaction atomique commune.
  Annuler le client n’annule pas instantanément une requête fournisseur déjà engagée.
- Les coûts estimés ne remplacent pas les factures OpenAI ni un budget fournisseur ; une erreur
  réseau/retry peut laisser une consommation facturable inconnue du ledger.
- Les tests DOM ne remplacent pas la revue visuelle desktop/mobile ; l’audit Python de vulnérabilités
  dédié n’a pas été exécuté (`pip check` vérifie la compatibilité seulement).
- Pas de dépôt Git reconnu dans ce workspace ; règles d’exclusion présentes, index non vérifiable.
  Aucune publication, déploiement public, réinitialisation ou modification d’associations navigateur.

Les commandes de lancement/test actuelles figurent dans README. La configuration production est
volontairement refusée si ses dépendances et protections minimales ne sont pas renseignées.

## Phase 3 — Infrastructure SaaS, 12 novembre 2026

Travail poursuivi depuis le baseline existant, sans reset de base, modification des datasets
utilisateur, attribution historique ou déploiement public. Profil privé et architecture existante
consultés ; aucun contenu du profil n'est copié dans le projet.

### Implémentation et revue

- Compose étendu : PostgreSQL 17, Redis 7 avec AOF et PING authentifié, migration Alembic one-shot,
  FastAPI et frontend statique Nginx facultatifs via profil `app`. Dépendances saines puis migration
  réussie avant démarrage backend ; healthchecks backend SQL/Redis et frontend.
- Ports loopback : PostgreSQL 5433, Redis 6380, backend 8001, frontend 5174 ; configurables sans
  remplacer les serveurs existants 8000/5173. Volumes distincts DB/Redis/fichiers persistants.
- Images applicatives non root ; contextes de build excluant secrets, stockage et environnements
  locaux. `backend/.env` monté seulement en lecture dans le backend, jamais dans le frontend ni
  le service de migration. Aucun secret n'est inclus dans les arguments du build frontend.
- Nginx sert la SPA et relaie `/api` sur la même origine ; build `VITE_API_BASE_URL=/` vérifié.
- Préfixe Redis configurable et validé (`RATE_LIMIT_NAMESPACE`) pour isoler environnements/tests ;
  même préfixe requis entre instances d'une application. Algorithme Lua atomique conservé, pas de
  repli SQL silencieux quand Redis configuré échoue.
- Six tests Redis réels ajoutés : concurrence entre clients, séparation utilisateurs/préfixes,
  reconnexion, TTL/fenêtre, refus AUTH et échec fermé. Aucun mock substitué si Redis absent.
- Nouveau lanceur Compose de QA : projet/ports/secrets jetables, bases SQL par fixture, namespaces
  Redis aléatoires, aucune commande FLUSHDB ; nettoyage limité au projet généré.
- Lanceur PostgreSQL Windows étendu aux parcours HTTP, avec bases et fichiers temporaires.
  Migrations/revue : révision figée, FKs, parité modèles, upgrade/roundtrip vide et refus du
  downgrade peuplé ; import historique explicite et source read-only inchangés.

### Résultats effectivement observés

| Vérification | Résultat et limite de preuve |
| --- | --- |
| Backend complet | **107 réussis, 6 ignorés**, 3 avertissements de dépréciation de dépendances |
| PostgreSQL réel isolé | **66 réussis** dans le lanceur étendu ; 52 cas sécurité + 2 HTTP utilisent PG réel, 12 autres cas conservent SQLite/unitaires |
| Redis réel | **Non exécuté** : aucun serveur local trouvé, moteur Docker et WSL non répondants |
| Compose | `config --quiet` **réussi**, avec valeurs factices ; builds/démarrage des conteneurs non exécutés |
| Lanceur Compose QA | Échec explicite avant démarrage : Docker info dépasse 15 secondes ; aucun succès simulé |
| Frontend | **32 tests réussis**, aucun ignoré |
| Lint | Oxlint configuré : **zéro erreur/avertissement** ; ESLint absent, pas prétendu exécuté |
| TypeScript | `tsc -b --pretty false` réussi |
| Builds frontend | Build habituel et build même origine `/` réussis |
| Compatibilité Python | `pip check` : aucune dépendance cassée |
| Serveurs existants | 8000 health/ready **200**, datasets sans session **401**, URL exacte 5173/app **200** |
| Secrets frontend | Comparaison en mémoire avec la clé backend : absente du build ; aucune valeur affichée |
| Navigateur | Chrome détecté ; `The browser access host is unavailable`. **Aucune validation visuelle** |

Le premier passage backend a révélé une fixture manquante dans le module HTTP après son extension
aux services réels ; import corrigé, puis suite backend complète repassée avec succès.
Les appels OpenAI sont simulés dans les tests : HTTP, Argon2id, SQL et DuckDB sont réels.
Les deux parcours HTTP utilisent un serveur Uvicorn réel et des comptes/datasets synthétiques.
Résultat analytique indépendant : A=15, B=20, total=35 ; les exports et autorisations sont testés.
Les cookies Secure/HttpOnly/SameSite, CSRF, expiration/révocation, sessions partagées, erreurs génériques,
limites SQL atomiques, accès croisées dataset/IA/export/suppression et uploads malveillants sont couverts
par les cas de sécurité passés sur PostgreSQL. Cela ne prouve pas un déploiement HTTPS réel.

### Blocages restant à lever

- Docker Desktop est lancé mais son moteur Linux ne répond pas ; WSL dépasse également son délai.
  Aucun reset Docker, changement BIOS/virtualisation, effacement de volume ou de sécurité Windows.
  Les journaux indiquent que le backend VM n'est pas en cours d'exécution ; cause racine non établie.
- Redis réel et pile Compose complète doivent être exécutés sur un moteur opérationnel ; persistance
  après recréation de conteneurs, AOF après redémarrage et proxy frontend/backend restent non validés.
- Revue visuelle desktop/mobile toujours à faire : checklist mise à jour, sans cases validées fictivement.
- TLS et cookies Secure en situation réelle, rôles DB minimaux séparés, Redis privé ACL/TLS,
  backups/restaurations, stockage partagé, audit des images/dépendances et supervision restent requis.
- Le proxy local ne fait pas confiance aux IP Forwarded ; les limites par IP peuvent être communes
  derrière Nginx. Configurer et vérifier un proxy de confiance avant déploiement public.
- Migration complète des comptes/sessions d'une base SaaS SQLite peuplée non fournie ; l'importeur
  historique ne couvre que les datasets avec décisions administrateur explicites.
- Les limites produit/sécurité de phase 2 restent applicables ; aucune revendication de production readiness.
- Pas de répertoire `.git` reconnu : exclusions présentes, index Git non vérifiable.

Documentation mise à jour : README, SQLITE_TO_POSTGRES, checklist visuelle ; guide DEPLOYMENT ajouté
avec commandes, environnement, santé, tests réels, sécurité et blocages de production.

## Reprise infrastructure — diagnostic après activation Windows, 12 novembre 2026

### Diagnostic confirmé, sans retries infinis

- Docker Desktop est ouvert ; `docker info --format '{{.ServerVersion}}'` expire à **15 secondes**.
- `docker compose version` fonctionne : **v5.6.0**. `wsl --status` et `wsl --list --verbose`
  expirent également à 15 secondes ; version WSL 2 et distributions non confirmables.
- Windows indique **CBSRebootPending=True**. DISM journalise une demande d'activation de
  VirtualMachinePlatform après le dernier démarrage, avec `CbsInstallStateInstallRequested`.
  Le redémarrage nécessaire n'est donc pas encore finalisé dans cette session.
- L'hyperviseur est détecté ; les indicateurs CPU WMI contradictoires ne prouvent pas un BIOS
  désactivé. Le service privilégié Docker est arrêté, sans en déduire que cela explique seul
  la panne du backend WSL. La lecture Get-WindowsOptionalFeature exige une élévation.
- Action utilisateur minimale : enregistrer ses documents, **Redémarrer Windows**, ouvrir Docker
  Desktop puis vérifier WSL et docker info. Procédure et contrôles admin éventuels dans DEPLOYMENT.
  Aucun redémarrage, changement BIOS, reset Docker ou suppression de volumes lancé par l'agent.

### Corrections et tests exécutés

- Le lanceur QA arrête désormais seulement ses conteneurs/réseau ; **tous les volumes sont conservés**.
  Aucun `down` avec option de suppression de volumes n'a été exécuté. Documentation alignée.
- Ajout d'un test réel de pool PostgreSQL : connexion rendue au pool, terminaison via un second
  moteur dans sa base `sa_qa_*`, puis nouvelle requête réussie grâce à pre-ping et nouveau PID.
  La vérification du nom de base précède la terminaison ; aucune connexion utilisateur ciblée.

| Commande exécutée depuis la racine, sauf indication | Résultat réel |
| --- | --- |
| `backend\.venv\Scripts\python.exe -m pytest backend/tests -q --tb=short` | **107 réussis, 7 ignorés**, 3 dépréciations ; six Redis absents + un PG sans URL dans ce passage |
| `backend\.venv\Scripts\python.exe backend/scripts/test_postgres.py` | **67 réussis**, 3 dépréciations ; **55 sur PG réel** (53 sécurité/pooling + 2 HTTP), 12 SQLite/unitaires |
| `npm.cmd test` dans frontend | **32 réussis**, aucun ignoré |
| `npm.cmd run lint` dans frontend | Oxlint réussi, zéro erreur/avertissement |
| `node_modules\.bin\tsc.cmd -b --pretty false` dans frontend | Réussi |
| `npm.cmd run build` dans frontend | Réussi |
| `docker compose --env-file .env.compose.example --profile app config --quiet` avec secrets factices dans l'environnement | Réussi, aucun secret réel affiché |

Six tests Redis : concurrence/compteur partagé, séparation utilisateurs, reconnexion, expiration,
séparation des namespaces et refus AUTH/échec fermé sont **tous non exécutés**, pas réussis.
Le lanceur Compose n'a pas été relancé après le timeout moteur confirmé : cela aurait seulement
répété le même blocage. Aucun build d'image, démarrage Compose, service discovery, healthcheck
conteneur ou persistance de volume n'est déclaré validé.

Les parcours HTTP réels sur PostgreSQL couvrent uploads CSV/XLSX, profilage, requêtes DuckDB,
assistant avec OpenAI simulé, résultats A=15/B=20, configuration de graphique, export protégé,
déconnexion et restrictions entre comptes. Connexion, CSRF, restauration/révocation/expiration
de session et ownership restent vérifiés par la suite sécurité PG. Il ne s'agit pas d'un E2E
navigateur à travers Nginx : accès navigateur retenté, toujours `browser access host unavailable`.
Le rendu des graphiques et la revue desktop/mobile restent non vérifiés.

Les serveurs locaux restent accessibles : 8000 health/ready 200, datasets anonymes 401,
`http://127.0.0.1:5173/app` 200. Le build frontend ne contient pas la clé backend (comparaison
en mémoire, aucune valeur affichée). Contextes Docker revus : secrets exclus ; absence dans
les couches d'image et logs conteneurs **non vérifiable sans moteur**, pas revendiquée.

Restent requis : redémarrage utilisateur puis validation Docker/Redis/proxy/volumes, HTTPS et
cookies Secure en déploiement, rôles DB minimaux, Redis privé, sauvegardes/restaurations et
limites opérationnelles déjà listées. Aucun appel OpenAI réel, changement du design premium,
attribution historique, modification de dataset utilisateur ou déploiement public.

## Reprise après redémarrage Windows — 12 novembre 2026

Le redémarrage Windows a été observé à 15 h 20, après la demande d'activation de
`VirtualMachinePlatform` enregistrée à 15 h 00. L'hyperviseur est actif, mais l'installation
reste incomplète : état CBS `InstallRequested` (`CurrentState=96`), `CBSRebootPending` présent,
aucun service `vmcompute`/WSL et commandes WSL bloquées. Docker Desktop 4.95.0 s'ouvre, mais son
journal indique continuellement `backend is not running`; `docker info` expire à 15 secondes.
Le lanceur `scripts/test_infrastructure.py` s'arrête explicitement avec « Docker engine unavailable
or timed out » avant de créer le moindre conteneur.

Résultats réellement obtenus pendant cette reprise :

| Contrôle | Résultat |
| --- | --- |
| Backend complet | **107 réussis, 7 ignorés**, 3 avertissements ; six Redis réels + un PG séparé ignorés |
| PostgreSQL isolé réel | **67 réussis**, 3 avertissements ; migrations, pooling, sessions et isolation inter-comptes |
| Frontend | **32 réussis**, aucun ignoré |
| Oxlint / TypeScript / build Vite | Réussis |
| `pip check` | Aucune incompatibilité |
| `npm audit --audit-level=high` | Aucune vulnérabilité signalée |
| Redis réel | **6 tests non exécutés** : moteur indisponible |
| Compose / healthchecks / Nginx | **Non exécutés** : moteur indisponible |
| Volumes Docker | **Non testés et non modifiés** |
| Chrome automatisé | **Non exécuté** : `browser access host is unavailable` |

Un smoke HTTP réel a été exécuté avec FastAPI/Uvicorn et un répertoire temporaire distinct des
données du projet : deux inscriptions 201, upload 201, accès propriétaire 200, accès croisés
détail et aperçu 404, restauration de session 200, logout 204 puis ancienne session 401. Après
arrêt et redémarrage d'Uvicorn sur le même répertoire temporaire, la reconnexion, le dataset et
`/api/ready` répondent 200. Cette preuve couvre la persistance applicative locale ; elle ne prouve
ni les volumes Compose, ni PostgreSQL/Redis en conteneurs, ni le proxy Nginx.

Le prochain prérequis est une vérification dans PowerShell administrateur de l'état des deux
fonctionnalités Windows, puis l'activation effective de `VirtualMachinePlatform` si elle n'est pas
`Enabled` et le redémarrage demandé par Windows. Aucun reset Docker/WSL, `down -v`, `FLUSHDB`,
changement de données existantes, suppression de volume ou déploiement public n'a été effectué.

## Validation Docker Compose après résolution WSL — 13 novembre 2026

Cette section est l'état le plus récent et remplace les anciens blocages Docker/WSL ci-dessus,
conservés comme historique. `VirtualMachinePlatform`, WSL 3.0.5 et la distribution WSL 2
`docker-desktop` sont opérationnels. Docker Engine 29.8.2 et Compose v5.6.0 répondent.

### Démarrage et santé

- Inventaire préalable : aucun projet Compose, conteneur ou volume utilisateur existant ; seul
  PostgreSQL Windows 17 sur 5432 était actif et n'a pas été utilisé.
- Empreintes des deux SQLite historiques vérifiées avant démarrage, puis `.env.compose` créé avec
  deux secrets indépendants générés localement et jamais affichés.
- `docker compose --env-file .env.compose --profile app config --quiet` réussi.
- Images PostgreSQL, Redis, Python, Node et Nginx téléchargées ou construites ; build React réussi.
- Trois volumes créés : PostgreSQL, Redis AOF et fichiers. Aucun volume supprimé.
- PostgreSQL, Redis, FastAPI et Nginx sains ; aucun redémarrage inattendu. Le service `migrate`
  s'est terminé avec le code zéro et la révision `0001_multi_user` est présente.
- PostgreSQL Docker répond uniquement sur 5433, Redis sur 6380, FastAPI sur 8001 et Nginx sur 5174.
  PostgreSQL Windows sur 5432 est resté indépendant.
- `/api/health`, `/api/ready`, `/healthz`, le proxy Nginx `/api` et le fallback SPA `/app`
  répondent HTTP 200. Les en-têtes `no-store`, `nosniff`, `DENY` et `no-referrer` sont présents.

### Résultats réellement exécutés

| Contrôle | Résultat réel |
| --- | --- |
| Backend standard | **107 réussis, 7 ignorés**, 3 avertissements de dépréciation |
| Intégration PostgreSQL/Redis Docker | **73 réussis**, aucun ignoré, 3 avertissements de dépréciation |
| Frontend | **32 réussis**, aucun ignoré |
| Oxlint / TypeScript / build Vite | Réussis |
| `pip check` | Aucune incompatibilité |
| `npm audit --audit-level=high` | Aucune vulnérabilité signalée |
| Alembic | `0001_multi_user`, migration one-shot code 0 |
| OpenAI | Simulé dans les tests ; aucun appel réel pendant cette validation |

Les 7 ignorés du passage standard correspondent aux 6 tests Redis réels et au test PostgreSQL
conditionnel, tous exécutés dans le passage d'infrastructure réel. Les avertissements concernent
les API dépréciées Starlette/AnyIO et WebSocket Uvicorn ; aucun échec ne leur est associé.

Le passage réel crée des bases aléatoires `sa_qa_*`, les utilise, puis les supprime. Une lecture du
catalogue après les tests confirme qu'aucune base `sa_qa_*` ne subsiste. Les tests Redis utilisent
des namespaces aléatoires et ne lancent jamais `FLUSHDB`.

### Parcours Compose et persistance

- Deux comptes synthétiques par parcours, bibliothèques privées et refus croisés détail/aperçu/
  requête/suppression en 404 ; accès anonyme en 401.
- Upload CSV synthétique et analytics réelles A = 15, B = 20.
- Session PostgreSQL et dataset du volume fichiers disponibles après redémarrage contrôlé de FastAPI.
- Clé synthétique disponible après redémarrage contrôlé de Redis ; AOF actif et états de persistance OK.
- Les quatre comptes, quatre sessions, deux datasets et deux fichiers synthétiques issus de deux
  passages QA ont été inventoriés puis supprimés après autorisation explicite. La suppression SQL
  était ciblée et transactionnelle ; les fichiers ont été renommés atomiquement avant la transaction
  avec restauration prévue en cas d'échec. Les contrôles finaux confirment zéro utilisateur, dataset
  ou session QA, tandis que l'unique session anonyme est conservée. Aucun usage IA, décision de
  propriété, compteur SQL ou clé Redis applicative n'était lié à ces éléments.

Deux erreurs de script QA sans défaut applicatif ont été observées : les adresses en `.test` ont été
refusées par le validateur email, puis une assertion utilisait `total` au lieu de `total_rows`.
Le passage corrigé a réussi sans modification du code métier.

### Intégrité historique et limite visuelle

- `metadata.sqlite3` : SHA-256 final identique au baseline
  `253E235C97AC672C1478BBFBD26D94FA7D9E6707BBF7CEB2E163E9FD0E86A002`.
- `saas.sqlite3` : SHA-256 final identique au baseline
  `6F9D53D7A7C5F175C59387A1A008E6EDE6EA8F6F842FB4DB0FF182ACB94A3918`.
- Fichier historique `8b47aec9-1610-4a0b-89e0-0eda76feebe7.csv` : taille et horodatage
  inchangés ; SHA-256 `481F6D8114D9544C36EC197D2F9A61BADF0D2928F1A5E0889E4809F44450F74F`,
  identique à la fixture source. Aucune empreinte initiale distincte n'avait été enregistrée pour
  ce CSV, cette comparaison ne remplace donc pas un baseline antérieur.

La revue visuelle Chrome reste non exécutée. Computer Use a ouvert une fenêtre Chrome mais a arrêté
le contrôle, car il ne pouvait pas confirmer l'URL active avec assez de certitude. Aucun contournement
n'a été tenté. URL manuelle vérifiée par Compose et HTTP 200 : `http://127.0.0.1:5174/app`.

## Phase 1 « Verdant Intelligence » — 13 novembre 2026

Cette section remplace l’état frontend de 32 tests et la mention d’absence totale de contrôle visuel
ci-dessus, conservés comme historique.

### Changements livrés

- correction de l’héritage Nginx sur `index.html` : `no-store`, `nosniff`, `DENY` et `no-referrer` ;
- design system React unifié (forêt profonde, ivoire, sauge, focus visible, cartes, formulaires,
  tableaux, graphiques, navigation et états) ;
- Overview réel connecté à `/api/datasets/{id}/profile`, sans KPI métier inventé ;
- affichage des statistiques numériques existantes et des fréquences catégorielles existantes ;
- profil séparé de la pagination de l’aperçu afin d’éviter son rechargement à chaque page ;
- textes de landing, états et README actualisés.

### Validation exécutée

| Contrôle | Résultat réel |
| --- | --- |
| Frontend | **34 réussis**, aucun ignoré |
| Oxlint / TypeScript / build Vite | Réussis |
| Test Nginx statique | Réussi |
| `nginx -t` sur le réseau Compose | Réussi |
| Nginx déployé `/app` et `/index.html` | HTTP 200 avec les quatre en-têtes attendus |
| API via Nginx `/api/ready` | `ready` |
| Chrome headless | Landing et connexion inspectées à 1440 px et 500 px |
| OpenAI | Aucun appel réel |

Seul le conteneur frontend a été reconstruit et recréé. Backend, PostgreSQL et Redis sont restés
actifs ; aucun volume, dataset, compte, secret ou état Alembic n’a été modifié. Le contrôle Chrome
interactif reste indisponible (`browser access host is unavailable`) et Chrome headless Windows
recadre les captures demandées à 390 px depuis sa largeur minimale : le parcours manuel à 390 px,
le clavier et les pages privées restent donc dans la checklist visuelle.

## Phase 2A — Advanced Data Insights, lot 1 — 13 novembre 2026

### Contrat et calculs

- contrat `/profile` additif `2.0`, sans suppression de champ existant ;
- Q1 et Q3 par interpolation linéaire Pandas, IQR, bornes de Tukey à 1,5 IQR et whiskers ;
- écart-type d’échantillon explicite avec `ddof=1` ;
- nulls et valeurs numériques non finies comptés séparément ;
- booléens exclus des statistiques numériques ;
- qualité par colonne : complétude, cardinalité et détection de constante ;
- avertissements explicites pour zéro valeur finie, moins de 20 valeurs finies et IQR nul ;
- aucune valeur brute atypique renvoyée et aucun atypique automatiquement qualifié d’erreur.

### Cache borné

Le cache local au processus conserve uniquement le JSON Pydantic sérialisé. La clé contient le
propriétaire, le dataset, la version du profil, la taille et le `mtime_ns` du fichier. Le dépôt
contrôle le propriétaire avant toute lecture du cache. LRU : 8 entrées, 8 Mio et TTL 600 secondes
par défaut ; invalidation après suppression réussie. Aucun DataFrame, fichier de cache, schéma SQL
ou migration Alembic n’est ajouté.

### Validation

| Contrôle | Résultat |
| --- | --- |
| Backend complet | **118 réussis, 7 ignorés**, 3 avertissements de dépréciation |
| Nouveaux tests profil/cache | **11 réussis** |
| Frontend | **34 réussis**, aucun ignoré |
| Oxlint / TypeScript / build Vite | Réussis |
| `pip check` | Aucune incompatibilité |
| Upload synthétique volumineux | 60 000 lignes à forte cardinalité, profil HTTP inférieur à 20 Ko |
| OpenAI | Simulé par les tests existants ; aucun appel réel |

Les 7 tests ignorés restent les scénarios conditionnels d’infrastructure déjà couverts séparément.
Les calculs de visualisation, histogrammes et corrélations ne font pas partie de ce lot.

## Phase 2A — Advanced Data Insights, lot 2 — 13 novembre 2026

### Données de visualisation

- contrat `/profile` additif `3.0`, sans suppression des données du lot 1 ;
- histogrammes numériques Sturges entre 5 et 30 classes pour les séries non constantes, une classe
  explicite pour les constantes et aucune pour les séries sans valeur finie ;
- échantillonnage déterministe borné à 50 000 valeurs, avec effectifs source/échantillon et indicateur
  `sampled` ; NaN et infinis restent exclus des données de visualisation ;
- distributions catégorielles limitées aux 10 valeurs les plus fréquentes, `other_count`, nulls
  séparés et libellés bornés à 160 caractères et 256 octets avec suffixe SHA-256 anti-collision ;
- matrice de Pearson pairwise-complete, 12 colonnes numériques maximum, minimum trois paires finies,
  booléens exclus, coefficients impossibles à `null` et avertissement causal explicite ;
- séries de comptage uniquement pour les colonnes réellement typées `datetime`, agrégées au jour,
  au mois ou par intervalles annuels adaptatifs, avec 60 points maximum et sans mesure métier inventée.

La version de cache passe de `2.0` à `3.0`. La version faisant partie de la clé, les anciens profils
ne sont pas relus. Les limites LRU du lot 1 restent inchangées : 8 entrées, 8 Mio et TTL 600 secondes
par défaut, JSON seulement et contrôle propriétaire avant lecture.

### Validation

| Contrôle | Résultat |
| --- | --- |
| Profilage ciblé | **21 réussis**, dont histogrammes, échantillonnage, cardinalité, Pearson et dates |
| Backend complet | **128 réussis, 7 ignorés**, 3 avertissements de dépréciation |
| Frontend | **34 réussis**, aucun ignoré |
| Oxlint / TypeScript / build Vite | Réussis |
| `pip check` | Aucune incompatibilité |
| Docker | Images backend/frontend construites, services recréés et healthchecks sains |
| API conteneurisée | `/api/ready` prêt, `/app` HTTP 200 et OpenAPI du profil `3.0` vérifié |
| Alembic | `0001_multi_user (head)`, sans nouvelle migration |
| OpenAI | Aucun appel réel ; les suites existantes utilisent leurs doublures |

Ce lot ne modifie aucun composant visuel, aucune migration Alembic, aucun dataset ni volume. Les
calculs restent effectués après lecture du fichier complet par Pandas : les payloads et travaux de
visualisation sont bornés, mais il n’existe pas encore de limite CPU globale ni de lecture en flux.
Les volumes PostgreSQL, Redis et fichiers sont restés attachés ; aucune commande de suppression ou
de réinitialisation n’a été exécutée.

## Phase 2A — Advanced Data Insights, lot 3 — 13 novembre 2026

### Visualisations frontend

- module React/Recharts chargé à la demande depuis le profil existant ; aucune nouvelle dépendance ;
- histogrammes numériques avec sélection de colonne, indicateurs descriptifs, whiskers, atypiques,
  nulls, non-finis, avertissements d’échantillonnage, petit échantillon et IQR nul ;
- distributions catégorielles top 10 + reste, valeurs manquantes séparées et signalement des
  libellés bornés par l’API ;
- heatmap Pearson divergente, valeurs exactes, effectifs finis, coefficients impossibles, colonnes
  exclues, échantillonnage, limite de colonnes et avertissement causal ;
- fréquence temporelle uniquement pour les colonnes datetime, avec granularité, regroupement,
  valeurs manquantes et limite de points visibles ;
- tableaux de données repliables, états sans données, méthodologie API, navigation clavier,
  focus visible et mise en page responsive Verdant Intelligence.

Le navigateur ne recalcule aucun quartile, coefficient, histogramme ou agrégat temporel. Il ne fait
que sélectionner, formater et représenter les valeurs du contrat propriétaire `/profile` `3.0`.
Une fixture locale isolée permet la revue visuelle sans compte ni donnée utilisateur et n’est pas
incluse dans le build de production.

### Validation

| Contrôle | Résultat |
| --- | --- |
| Frontend | **36 réussis**, aucun ignoré |
| Nouveaux scénarios | Valeurs API, sélection de colonne, états insuffisants et méthodologie |
| Oxlint / TypeScript / build Vite | Réussis |
| Chrome headless | Fixture réelle inspectée en desktop et petit écran ; composition desktop corrigée |
| Docker | Frontend reconstruit/recréé, Nginx et `/api/ready` vérifiés |
| Backend ciblé | Contrat/profilage `3.0` inchangé et tests ciblés réussis |
| OpenAI | Aucun appel réel |

La tentative Chrome interactive a été interrompue lorsqu’une vérification biométrique Windows liée
au gestionnaire de mots de passe est apparue ; aucune interaction avec ce dialogue ni utilisation
d’identifiants n’a été effectuée. La fixture Chrome headless fournit la preuve visuelle sans contourner
l’authentification. Aucun schéma SQL, migration, dataset, compte, secret ou volume n’a été modifié.

## Phase 2A — Advanced Data Insights, lot 4 — 13 novembre 2026

### Validation finale exécutée

| Contrôle | Résultat réel |
| --- | --- |
| Backend complet | **128 réussis, 7 ignorés**, 3 avertissements de dépréciation |
| Infrastructure PostgreSQL/Redis isolée | **73 réussis**, 3 avertissements de dépréciation |
| Frontend complet | **36 réussis**, aucun échec ni test ignoré |
| Oxlint / TypeScript / build Vite | Réussis |
| `npm audit --audit-level=high` | 0 vulnérabilité |
| `pip check` | Aucune incompatibilité |
| Chrome synthétique | 1440×900, 768×1024 et 390×844 validés sans overflow global |
| Accessibilité ciblée | Tab, focus visible, 4 tables, détails et heatmap défilable validés |
| Docker Compose | backend, frontend, PostgreSQL et Redis sains |
| Nginx `/app` | HTTP 200, `no-store`, `nosniff`, `DENY`, `no-referrer` |
| Santé API | `/api/health` OK, `/api/ready` ready, accès anonyme datasets 401 |
| Alembic | `0001_multi_user (head)` |
| OpenAI | Aucun appel réel ; doublures uniquement dans les tests |

Les tests couvrent les histogrammes et leurs effectifs, l'échantillonnage déterministe, les catégories
à forte cardinalité, Pearson positif/négatif/non calculable, dates et granularités, valeurs vides,
manquantes, non finies, constantes et petits échantillons. Les scénarios frontend couvrent également
les réponses tardives lors d'un changement de dataset. Le test d'infrastructure utilise un projet
Compose isolé et conserve ses deux volumes ; aucun `down -v` ni effacement n'a été exécuté.

### QA visuelle et corrections

Quatre captures synthétiques ont été produites dans `docs/screenshots`. Le script de capture a été
durci pour attendre la fermeture complète de Chrome sous Windows et tolérer le verrou transitoire du
fichier `DevToolsActivePort`. Cette correction concerne uniquement l'outillage QA. Aucun défaut métier
confirmé n'a nécessité de modification des composants ou du backend pendant ce lot.

La fixture n'est pas incluse dans `frontend/dist`. Le parcours authentifié interactif n'a pas été
validé : la vérification biométrique Windows antérieure n'a pas été contournée et aucun mot de passe
provenant d'une capture n'a été utilisé. La checklist et le scénario de démonstration distinguent
explicitement cette limite des preuves automatisées.

## Dashboard Studio — lot 1 backend — 13 novembre 2026

### Socle livré

- migration additive `0002_dashboard_studio` avec dashboards, widgets, contraintes et index ;
- FK dashboard `CASCADE`, FK dataset `SET NULL` et snapshots historiques conservés ;
- contrats Pydantic stricts pour table, KPI, barres, lignes et camembert ;
- persistance exclusive de `AnalyticsQuerySpec` validés, sans SQL/Python/JavaScript libre ;
- CRUD propriétaire avec 404 uniforme, sessions/CSRF/origine existants et protection anticipée ;
- verrouillage optimiste atomique par révision ;
- limites de 50 dashboards par utilisateur et 12 widgets par dashboard ;
- méthodes CORS PATCH/PUT autorisées explicitement.

### Validation isolée

| Contrôle | Résultat |
| --- | --- |
| Migration SQLite `0001 → 0002` | Réussie, lignes historiques identiques |
| Migration PostgreSQL isolée `0001 → 0002` | Réussie, FK/index/contraintes inspectés |
| Suppression dataset | Widget conservé, `dataset_id = NULL`, snapshots présents |
| Suppression dashboard | Widgets supprimés en cascade |
| Conflit de révision concurrent | Une mutation réussit, l'autre retourne 409 |
| Backend complet final | **138 réussis, 8 ignorés**, 3 avertissements |
| PostgreSQL/Redis isolés final | **84 réussis**, 3 avertissements |
| PostgreSQL SCRAM temporaire sur le code final | **78 réussis**, 3 avertissements |
| `pip check` | Aucune incompatibilité |
| OpenAI | Aucun appel réel |

La base PostgreSQL principale et ses conteneurs restent à `0001_multi_user`. Le backend principal
n'a pas été reconstruit avec le code `0002`. Aucune migration principale, suppression de volume,
réinitialisation ou downgrade n'a été exécuté ; une autorisation distincte reste nécessaire.
