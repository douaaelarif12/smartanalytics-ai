# Scénario de démonstration — 60 à 90 secondes

Ce scénario présente Advanced Data Insights avec un dataset strictement synthétique. Il ne nécessite aucun appel OpenAI réel.

## Préparation

1. Démarrer la pile Compose et vérifier que les quatre services sont sains.
2. Ouvrir Google Chrome sur `http://127.0.0.1:5174/app` avec un compte de démonstration déjà autorisé.
3. Sélectionner uniquement le dataset synthétique prévu pour la démonstration.
4. Fermer gestionnaires de mots de passe, notifications et onglets contenant des informations personnelles.
5. Préparer en secours les [captures QA](screenshots/advanced-insights-desktop.png).

Le parcours authentifié doit être répété manuellement avant l'enregistrement. En l'absence de cette répétition, utiliser la fixture ou les captures et ne pas prétendre montrer une session réelle validée.

## Déroulé parlé

| Temps | Action | Message suggéré |
| --- | --- | --- |
| 0–10 s | Overview du dataset | « SmartAnalytics transforme un fichier importé en profil statistique vérifiable, sans inventer de KPI métier. » |
| 10–30 s | Histogramme | Montrer moyenne, médiane, quartiles, écart-type, IQR, whiskers, atypiques potentiels et avertissement d'échantillonnage. |
| 30–45 s | Distribution catégorielle | Montrer le top 10, le reste agrégé et les valeurs manquantes séparées. |
| 45–60 s | Heatmap Pearson | Montrer coefficients positifs/négatifs, effectifs finis et rappeler que corrélation n'implique pas causalité. |
| 60–75 s | Série temporelle | Expliquer qu'il s'agit d'un comptage par période, uniquement pour une vraie colonne datetime, sans mesure métier inventée. |
| 75–90 s | Méthode et conclusion | Ouvrir les données accessibles ou la méthodologie : calculs serveur bornés, profil propriétaire, frontend sans recalcul statistique. |

## Points à ne pas affirmer

- Une valeur atypique n'est pas automatiquement une erreur.
- Une corrélation n'établit pas de causalité.
- La série temporelle ne représente pas un chiffre d'affaires si aucune mesure métier n'est définie.
- La plateforme n'est pas déclarée prête pour une exposition publique sans les mesures de déploiement documentées.
- Ne pas présenter le parcours authentifié comme validé si la répétition Chrome réelle n'a pas été réalisée.

## Plan de secours

En cas de problème de session ou de biométrie Windows, ne saisir aucun identifiant provenant d'une capture et ne contourner aucun dialogue. Présenter les captures synthétiques desktop, tablette, mobile et heatmap, puis expliquer clairement qu'elles proviennent de la fixture QA locale.
