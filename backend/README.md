# SmartAnalytics AI API

FastAPI, SQLAlchemy 2 / PostgreSQL, sessions serveur, propriété des datasets, DuckDB et OpenAI.
La configuration et la procédure complètes figurent dans le [README racine](../README.md).

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
.\.venv\Scripts\python.exe -m pytest -q
```

Les routes datasets nécessitent une session authentifiée et, pour les mutations, un jeton CSRF
et une origine autorisée. L’ancien SQLite n’est pas utilisé comme bibliothèque publique.
Sans URL PostgreSQL, le mode développement crée un `data/saas.sqlite3` distinct ; le format
historique est importé uniquement avec la [procédure administrateur](../docs/SQLITE_TO_POSTGRES.md).

`/api/health` vérifie la vie du processus, `/api/ready` les dépendances configurées.
La production exige PostgreSQL, Redis, cookies Secure et origines HTTPS. Le serveur reste lié
à `127.0.0.1` pendant le développement ; aucun déploiement public n’est effectué.

`GET /api/datasets/{id}/profile` expose le contrat additif `profile_version: "3.0"`. Il conserve la
qualité par colonne, les quartiles par interpolation linéaire, l’écart-type d’échantillon (`ddof=1`)
et les valeurs atypiques selon Tukey à 1,5 IQR. Il ajoute des histogrammes bornés, les dix catégories
les plus fréquentes avec `other_count`, une matrice de corrélation de Pearson et des séries de volumes
temporels uniquement pour les colonnes détectées comme dates. Une corrélation n’implique pas une
causalité et une valeur atypique n’est pas automatiquement une erreur de donnée.

Les histogrammes et corrélations utilisent un échantillon déterministe de 50 000 observations au
maximum. La corrélation est limitée à 12 colonnes et exige trois paires finies. Les séries temporelles
sont agrégées au jour, au mois ou à l’année et limitées à 60 points sans inventer de mesure métier.
Les profils JSON sont mis en cache localement sans DataFrame, après contrôle du propriétaire, avec
TTL et budgets d’entrées/octets configurables. La version `3.0` rend les entrées `2.0` inaccessibles.

## Dashboard Studio — socle backend

La migration additive `0002_dashboard_studio` ajoute les dashboards privés et leurs widgets analytiques.
Un widget conserve uniquement un `AnalyticsQuerySpec` strict, une configuration graphique bornée et
sa disposition ; aucun SQL, Python, JavaScript ou résultat brut n'est persisté. Toutes les ressources
sont résolues depuis l'utilisateur de la session. Les accès croisés retournent 404.

Routes CRUD :

- `GET`, `POST /api/dashboards` ;
- `GET`, `PATCH`, `DELETE /api/dashboards/{id}` ;
- `POST /api/dashboards/{id}/widgets` ;
- `GET`, `PATCH`, `DELETE /api/dashboards/{id}/widgets/{widget_id}`.

Les mutations utilisent `expected_revision` et un incrément atomique. Limites : 50 dashboards par
utilisateur et 12 widgets par dashboard. La suppression d'un dataset met `dataset_id` à `NULL` et
préserve les snapshots d'identité du widget. Les endpoints d'exécution et l'interface React ne font
pas partie de ce lot.
