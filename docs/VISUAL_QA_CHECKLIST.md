# Checklist QA visuelle — Advanced Data Insights

État au 13 novembre 2026 : les visualisations du profil ont été contrôlées automatiquement dans Google Chrome avec une fixture synthétique. Le parcours privé authentifié n'a pas été validé dans un navigateur interactif et reste à vérifier manuellement.

## Preuves automatisées acquises

La page locale `frontend/tests/visual-profile.html` utilise exclusivement des données synthétiques et le vrai composant React `ProfileVisualizations`. Elle n'est pas incluse dans le build de production.

| Contrôle | Résultat |
| --- | --- |
| Desktop | 1440 × 900, aucun débordement horizontal global |
| Tablette | 768 × 1024, aucun débordement horizontal global |
| Mobile | 390 × 844, aucun débordement horizontal global |
| Clavier | premier sélecteur atteint par Tab, `:focus-visible` actif, contour 3 px |
| Données accessibles | 4 tables de données et 3 panneaux détaillés présents |
| Heatmap | région défilable au clavier avec `tabindex="0"` |
| Mouvement réduit | `prefers-reduced-motion: reduce` reconnu |
| Confidentialité | fixture synthétique uniquement, aucune donnée personnelle |

Captures disponibles :

- [desktop](screenshots/advanced-insights-desktop.png) ;
- [tablette](screenshots/advanced-insights-tablet.png) ;
- [mobile](screenshots/advanced-insights-mobile.png) ;
- [heatmap et série temporelle](screenshots/advanced-insights-heatmap.png).

Pour régénérer les captures :

```powershell
cd frontend
npm.cmd run dev -- --host 127.0.0.1 --port 4175 --strictPort
# Dans un second terminal :
node tests/capture-profile.mjs http://127.0.0.1:4175/tests/visual-profile.html
```

Le script utilise l'installation locale de Google Chrome, un profil temporaire isolé et supprime uniquement ce profil après fermeture complète du navigateur.

## Checklist manuelle avant démonstration

Utiliser un compte de démonstration et un dataset synthétique appartenant à ce compte. Ne jamais capturer une valeur de cookie, un jeton CSRF, un secret, un dialogue biométrique ou un gestionnaire de mots de passe.

- [ ] Ouvrir `http://127.0.0.1:5174/app` dans Google Chrome et confirmer un parcours connexion → Datasets → Overview.
- [ ] Confirmer que le dataset synthétique actif alimente le profil sans afficher les données d'un autre compte.
- [ ] Parcourir histogramme, catégories, heatmap et série temporelle ; comparer les valeurs aux tables repliables.
- [ ] Changer rapidement de dataset et confirmer qu'aucun profil ou graphique tardif de l'ancienne sélection ne réapparaît.
- [ ] Vérifier les états vide, erreur, colonne constante, petit échantillon et données incompatibles.
- [ ] Refaire Tab/Shift+Tab, Enter/Espace, focus visible, défilement de la heatmap et zoom 200 %.
- [ ] Vérifier 1440 × 900, 768 × 1024, 390 × 844 et 320 × 740 dans DevTools.
- [ ] Vérifier la console et le panneau Réseau sans inspecter ni capturer les valeurs sensibles.
- [ ] Confirmer déconnexion, Retour/F5 et refus d'accès anonyme.

La vérification biométrique Windows ne doit jamais être contournée. Si elle apparaît, interrompre le parcours et laisser Douaa reprendre manuellement. Aucun mot de passe provenant d'une capture ne doit être utilisé.

## Limite de preuve

Les captures prouvent le rendu du composant sur une fixture contrôlée, pas le fonctionnement complet d'une session propriétaire réelle. Les tests automatisés backend valident l'isolation, les autorisations et les réponses API ; ils ne remplacent pas une répétition manuelle du parcours authentifié dans Chrome.
