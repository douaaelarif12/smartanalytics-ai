# Infrastructure de développement SaaS

Cette configuration est locale, pas une configuration de production validée. Les ports publiés
sont liés à `127.0.0.1`. Aucun dataset historique n'est importé automatiquement.

## Démarrage

Prérequis : Docker Desktop avec moteur Linux opérationnel, Compose récent, espace disque,
`backend/.env` existant pour le backend IA. Ne jamais écraser ce fichier ni afficher son contenu.
Depuis la racine, copier `.env.compose.example` vers `.env.compose` seulement si absent, puis
renseigner deux mots de passe indépendants et aléatoires **URL-safe** (lettres/chiffres/`_`/`-`).
Les fichiers `.env*` privés sont exclus des contextes de build et ignorés par Git.

```powershell
if (-not (Test-Path .env.compose)) { Copy-Item .env.compose.example .env.compose }
# Renseigner les mots de passe en privé avant les commandes suivantes.
docker compose --env-file .env.compose --profile app config --quiet
docker compose --env-file .env.compose --profile app up -d --build --wait
docker compose --env-file .env.compose --profile app ps
```

Ouvrir `http://127.0.0.1:5174/app`. Le frontend statique Nginx utilise `/api` sur la même origine ;
il relaie cookies et Origin vers FastAPI. Backend direct : `http://127.0.0.1:8001/api/ready`.
Les serveurs Vite/FastAPI existants sur 5173/8000 restent indépendants et ne sont pas remplacés.
Pour lancer seulement les dépendances : `docker compose --env-file .env.compose up -d --wait postgres redis`.

## Configuration et persistance

| Paramètre | Utilisation |
| --- | --- |
| POSTGRES_PASSWORD / REDIS_PASSWORD | Secrets locaux distincts, obligatoires, URL-safe |
| POSTGRES_PORT / REDIS_PORT | Ports loopback facultatifs ; défauts 5433 / 6380 |
| BACKEND_PORT / FRONTEND_PORT | Ports loopback facultatifs ; défauts 8001 / 5174 |
| DATABASE_URL / REDIS_URL | Construits dans Compose pour le réseau interne ; jamais fournis au frontend |
| SMARTANALYTICS_CORS_ORIGINS | Origine exacte correspondant au port frontend |
| OPENAI_API_KEY / OPENAI_MODEL | Lus uniquement depuis `backend/.env`, monté read-only dans le backend |
| RATE_LIMIT_NAMESPACE | Préfixe Redis commun à toutes les instances d'un environnement ; défaut `smartanalytics` |
| APP_ENV / COOKIE_SECURE | Compose local : development / false ; HTTPS et true requis en production |
| AUTO_MIGRATE | false ; migration effectuée par le service one-shot `migrate` |

Trois volumes nommés conservent PostgreSQL, Redis AOF et les fichiers de datasets.
Changer un mot de passe dans `.env.compose` ne change pas le mot de passe d'un cluster PostgreSQL
déjà initialisé. Ne pas utiliser `down -v` sur l'environnement de développement/utilisateur.
Arrêt conservant les données : `docker compose --env-file .env.compose --profile app down`.
Ne pas monter `backend/data` existant dans un nouvel environnement sans plan de migration.

PostgreSQL est attendu via `pg_isready`, Redis via un PING authentifié. Alembic doit réussir
avant le démarrage du backend. `/api/health` mesure la vie du processus ; `/api/ready` vérifie
SQL et Redis configuré. Le frontend a `/healthz` ; sa disponibilité seule ne prouve pas celle de l'API.
Le schéma applicatif cible `0002_dashboard_studio` ; voir [la procédure de migration](SQLITE_TO_POSTGRES.md).
La migration `0001 → 0002` est additive, mais son application à un environnement existant reste une
action opérateur distincte après sauvegarde et inventaire. Ne pas reconstruire le backend avec le
nouveau code tant que sa base associée est encore à `0001_multi_user`.

## Tests réels isolés

```powershell
backend\.venv\Scripts\python.exe backend/scripts/test_infrastructure.py
```

Le script crée un projet Compose aléatoire, des ports libres et des secrets éphémères, attend
PostgreSQL/Redis sains puis lance les tests de sécurité, HTTP et Redis. Chaque fixture SQL crée
sa propre base. Les clés Redis sont isolées par préfixe aléatoire ; aucun `FLUSHDB` n'est effectué.
En fin de test, seuls les conteneurs/réseau du projet généré sont arrêtés ; **tous les volumes sont
conservés**, y compris ceux de QA. Le nom du projet est affiché pour permettre leur inventaire.
Les URL ne sont pas affichées. Sans moteur Docker, le script échoue explicitement et ne simule rien.
Les appels OpenAI restent simulés dans ces suites ; DuckDB, HTTP, PostgreSQL et Redis sont réels
lorsque le lanceur réussit. Ce lanceur ne construit pas les images applicatives : celles-ci nécessitent
en plus le démarrage complet et la checklist ci-dessous.

Alternative Windows sans Docker : `backend\.venv\Scripts\python.exe backend/scripts/test_postgres.py`.
Elle crée un cluster PostgreSQL SCRAM temporaire distinct du serveur existant, exécute sécurité et
parcours HTTP, puis retire uniquement ses propres fichiers. Elle ne remplace pas le test Redis.

## Vérification après démarrage complet

1. Vérifier `ps` : PostgreSQL/Redis/backend/frontend sains, `migrate` terminé avec code zéro.
2. Via le frontend 5174, créer deux comptes synthétiques ; importer seulement la fixture QA.
3. Vérifier les requêtes réseau `/api` même origine, cookies HttpOnly/SameSite et CSRF ; aucun token dans le stockage navigateur.
4. Vérifier somme A=15, B=20, total=35 dans Explorer ; compte B ne voit ni ne modifie le dataset A.
5. Recréer seulement le conteneur backend (`up -d --force-recreate backend`) : session/datasets conservés.
6. Redémarrer Redis : contrôler conservation AOF des quotas non expirés ; arrêter Redis : protection/ready échouent sans repli silencieux.
7. Reprendre [la checklist visuelle](VISUAL_QA_CHECKLIST.md) pour desktop/mobile et états d'erreur.

## Limites avant production

### Validation Windows/WSL/Docker — 13 novembre 2026

Le blocage Windows est résolu. `VirtualMachinePlatform` est activé, WSL 3.0.5 répond et la
distribution `docker-desktop` fonctionne sous WSL 2. Docker Engine 29.8.2 et Compose v5.6.0
sont opérationnels. Le PostgreSQL Windows existant reste sur 5432 et n'est pas utilisé par Compose.

La pile a été construite et démarrée avec `--profile app --wait` : PostgreSQL, Redis, FastAPI et
Nginx sont sains, tandis que `migrate` s'est terminé avec le code zéro. La révision Alembic active
est `0001_multi_user`. Les connexions PostgreSQL/Redis, le proxy Nginx et les endpoints de santé
ont répondu correctement.

Validation exécutée : backend **107 réussis / 7 ignorés** dans le passage standard, puis
**73 réussis** contre PostgreSQL et Redis Docker réels ; frontend **32 réussis**. Oxlint,
TypeScript, build Vite, `pip check` et `npm audit` ont réussi. Les 7 cas ignorés du premier passage
ont été exercés dans le passage réel. Trois avertissements de dépréciation Starlette/AnyIO/Uvicorn
subsistent sans échec. OpenAI est simulé et aucun appel réel n'a été effectué.

Le parcours via `http://127.0.0.1:5174` confirme l'authentification, l'isolation entre deux comptes,
l'upload CSV, les agrégats A = 15/B = 20, la persistance PostgreSQL/fichiers après redémarrage de
FastAPI et la persistance AOF après redémarrage de Redis. Aucune base `sa_qa_*` ne subsiste.
Après inventaire et autorisation explicite, les quatre comptes, quatre sessions, deux datasets et
deux fichiers synthétiques ont été supprimés de façon ciblée. La session anonyme a été conservée.
Les trois volumes restent montés ; aucun `down -v`, `FLUSHDB` ou reset Alembic n'a eu lieu.

La revue visuelle Google Chrome reste manuelle : ouvrir `http://127.0.0.1:5174/app` et suivre
[la checklist visuelle](VISUAL_QA_CHECKLIST.md). Les statuts HTTP et tests DOM ne valident pas le
rendu responsive, le focus, le clavier, les tooltips ou les états visuels. Les images de base
doivent encore être figées par digest et auditées avant un déploiement public.

Prévoir TLS, cookies Secure, secrets gérés, rôles SQL séparés migration/runtime à droits minimaux
(le rôle PostgreSQL Compose est administrateur de développement), Redis privé avec ACL/TLS,
sauvegardes/restaurations testées et stockage protégé partagé entre instances. Le proxy actuel ne
fait pas confiance aux en-têtes Forwarded : l'IP observée derrière Nginx est celle du proxy. Les limites
par IP peuvent donc être communes aux utilisateurs ; les limites par compte restent distinctes.
Configurer et tester explicitement un proxy de confiance avant tout déploiement multi-instance.
Les autres limites produit/sécurité figurent dans SAAS_ARCHITECTURE.md et PROGRESS.md.
