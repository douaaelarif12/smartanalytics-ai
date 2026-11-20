# Migration sûre de SQLite vers PostgreSQL

## Complément infrastructure — phase 3

Le [guide Docker local](DEPLOYMENT.md) ajoute un profil `app` avec migration Alembic one-shot,
backend et frontend sur 8001/5174, sans remplacer les serveurs existants 8000/5173.
Les volumes Compose sont distincts du stockage local actuel : démarrer Compose ne transfère
ni comptes, ni sessions, ni datasets existants. L'absence de ces données dans un nouvel
environnement ne justifie pas une réinitialisation ou une attribution automatique.

Pour vérifier les migrations sans toucher aux données, lancer
`backend\.venv\Scripts\python.exe backend/scripts/test_infrastructure.py` depuis la racine.
Ce lanceur utilise des bases jetables PostgreSQL et Redis et ne lance aucun import historique.
Sans Docker opérationnel, le script `backend/scripts/test_postgres.py` teste un cluster Windows
isolé réel, y compris la révision, la parité des modèles, le roundtrip vide et le refus du
downgrade d'une base peuplée. Les sources historiques restent intactes.

La bascule effective reste une opération administrateur distincte : sauvegarde/restauration,
inventaire, revue des propriétaires, dry-run puis import explicite selon les sections suivantes.
Le transfert complet d'une base SaaS SQLite déjà peuplée n'est toujours pas fourni par l'importeur
historique ; il constitue un préalable si cet environnement doit migrer ses comptes vers PostgreSQL.

Le fichier historique `backend/data/metadata.sqlite3` et son répertoire `files/` sont conservés.
Le runtime ne les importe pas et ne les attribue pas automatiquement. Sans `DATABASE_URL`, le
développement utilise une base SaaS distincte `backend/data/saas.sqlite3`.

## 1. Préparer et sauvegarder

Arrêter les anciens writers avant l’inventaire. Faire une sauvegarde cohérente de la base
historique et des fichiers, et vérifier qu’elle peut être restaurée. Ne pas remplacer ou supprimer
les sources pendant la migration. Conserver les sauvegardes hors Git et sous accès restreint.

Cette migration initiale vise le format historique `metadata.sqlite3`. Elle n’est pas un outil
de synchronisation d’une base SaaS SQLite déjà peuplée de comptes/sessions : si des comptes et
des uploads ont déjà été créés dans `saas.sqlite3`, leur transfert complet doit être planifié
explicitement avant une bascule de runtime. Ne pas changer simplement l’URL en supposant les retrouver.

## 2. Préparer PostgreSQL et Redis localement

Depuis la racine, créer `.env.compose` à partir de `.env.compose.example` **seulement si absent**,
puis définir deux mots de passe aléatoires distincts. Le fichier est ignoré par Git.

```powershell
if (-not (Test-Path .env.compose)) { Copy-Item .env.compose.example .env.compose }
docker compose --env-file .env.compose up -d postgres redis
```

Les services sont liés uniquement à `127.0.0.1` : PostgreSQL **5433** (pour éviter le serveur local
5432 existant), Redis **6380**. Les volumes nommés conservent leurs données.
Ne pas utiliser `down -v`, ne pas effacer les volumes et ne pas réinitialiser un cluster existant.
Un changement de mot de passe dans le fichier ne reconfigure pas une base PostgreSQL déjà initialisée.

Dans `backend/.env`, conserver la clé OpenAI existante et ajouter/adapter :

```dotenv
APP_ENV=development
COOKIE_SECURE=false
AUTO_MIGRATE=false
DATABASE_URL=postgresql+psycopg://smartanalytics:YOUR_URL_ENCODED_PASSWORD@127.0.0.1:5433/smartanalytics
REDIS_URL=redis://:YOUR_URL_ENCODED_REDIS_PASSWORD@127.0.0.1:6380/0
SMARTANALYTICS_CORS_ORIGINS=http://127.0.0.1:5173
```

Utiliser des secrets URL-safe ou encoder les caractères réservés. Ne jamais recopier ces URL
dans le frontend, une PR, une capture ou un journal public. Ne pas remplacer un `.env` existant
par l’exemple, ce qui ferait perdre sa configuration.

## 3. Appliquer les migrations de schéma

Depuis `backend/` :

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m alembic current
```

La révision applicative attendue est `0002_dashboard_studio`. Les tables SaaS sont distinctes du format historique.
Sur une base existante à `0001_multi_user`, inventorier et sauvegarder avant d'exécuter l'upgrade ;
la migration ajoute uniquement `dashboards` et `dashboard_widgets` et ne réécrit aucune ligne existante.
En production, employer un rôle de migration pour cette étape puis un rôle runtime limité aux
opérations nécessaires. `APP_ENV=production` n’exécute jamais de DDL automatiquement au démarrage.

## 4. Inventorier sans connecter la cible

```powershell
.\.venv\Scripts\python.exe -m app.legacy_migration --source .\data\metadata.sqlite3 --inventory
```

Cette commande lit seulement les UUID et noms de la source SQLite, en mode read-only.
Son affichage peut être sensible : le garder dans l’espace administrateur, pas dans Git.

## 5. Créer les comptes et décider explicitement des propriétaires

Démarrer le backend avec la configuration cible, puis créer les comptes réels via `/register`.
La bibliothèque de chaque compte reste vide jusqu’à attribution ou upload.
Créer un fichier privé `backend/legacy-owners.json`, ignoré par Git, selon ce format fictif :

```json
{
  "11111111-1111-4111-8111-111111111111": "existing-owner@example.com"
}
```

Les UUID doivent provenir de l’inventaire et les emails doivent appartenir à des comptes existants.
Un opérateur disposant de l’accès DB/FS choisit les attributions. Il n’existe pas d’endpoint public
permettant de définir `owner_id`, ni d’auto-attribution au premier inscrit.

## 6. Simuler, puis appliquer

```powershell
# Sans --apply : validation des fichiers, des conflits et des décisions ; aucun import de données.
.\.venv\Scripts\python.exe -m app.legacy_migration --source .\data\metadata.sqlite3 --owners .\legacy-owners.json --administrator "YOUR_OPERATOR_ID"
# Après revue explicite des décisions :
.\.venv\Scripts\python.exe -m app.legacy_migration --source .\data\metadata.sqlite3 --owners .\legacy-owners.json --administrator "YOUR_OPERATOR_ID" --apply
```

Une alternative consiste à importer sans fichier `--owners` : toutes les métadonnées sont alors
en quarantaine (`owner_id=NULL`) et invisibles aux comptes. Relancer avec les décisions explicites
permet d’attribuer ces enregistrements. Aucun ancien propriétaire n’est inventé.

L’import est répétable : UUID et JSON sont conservés, les entrées déjà identiques ne sont pas
dupliquées, les décisions déjà appliquées ne sont pas réinsérées. Un conflit de métadonnées,
de contenu fichier ou de propriétaire provoque un refus, pas un overwrite.

Si les répertoires de stockage diffèrent, les fichiers sont copiés et vérifiés par SHA-256 ;
les sources ne sont jamais supprimées. En cas d’échec DB après copie, des fichiers cibles orphelins
peuvent subsister : les examiner avant tout nettoyage manuel. Il n’y a pas de suppression automatique.

## 7. Vérifier avant bascule

- Comparer nombres de datasets, UUID, schémas et sommes SHA-256 avec la sauvegarde.
- Se connecter avec deux comptes : chacun doit voir uniquement ses fichiers.
- Tester détails, aperçu, profil, query, assistant, exports et suppression sur des **fixtures de test**.
  Un UUID d’un autre propriétaire doit renvoyer 404, une requête anonyme 401.
- Vérifier `/api/ready`, les sauvegardes PostgreSQL et le partage du répertoire privé entre instances.
- Conserver l’ancienne base et les fichiers tant que la migration n’est pas validée.

La procédure n’a pas été appliquée aux données historiques de ce workspace, faute de décisions
administrateur explicites. Elle a été testée sur des fixtures avec contrôle d’intégrité et sur
PostgreSQL temporaire protégé par SCRAM. Le cluster PostgreSQL local existant n’a pas été modifié.
