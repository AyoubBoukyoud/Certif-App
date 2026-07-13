# Durcissement des postes d'examen (Windows)

L'application bloque déjà, en mode utilisateur : Alt+Tab, Alt+Échap, Ctrl+Échap,
les touches Windows, Alt+F4 et F11, et ramène l'épreuve au premier plan si le
focus s'échappe. Les points suivants relèvent du système et sont recommandés
sur les postes dédiés.

## Non blocable par l'application
- **Ctrl+Alt+Suppr / Gestionnaire des tâches** : ne peut pas être intercepté
  par une application. Atténuation : la surveillance du focus refait passer
  l'épreuve devant, et chaque évasion est journalisée (`audit_log`).

## Stratégie de groupe (gpedit.msc) — optionnel
- Désactiver le Gestionnaire des tâches :
  `Configuration utilisateur > Modèles d'administration > Système >
   Options Ctrl+Alt+Suppr > Supprimer le Gestionnaire des tâches`.
- Masquer les lecteurs, désactiver l'invite de commandes et l'accès au Registre
  pour le compte d'examen.

## Accès attribué (Assigned Access / mode kiosque Windows)
Pour un verrouillage fort, configurer un compte local en mode kiosque lançant
uniquement l'application. Comme l'app pilote Excel via COM, préférer un compte
standard durci (stratégie de groupe ci-dessus) plutôt que le kiosque UWP.

## Excel
- L'app crée sa propre instance Excel (DispatchEx) et ne touche pas aux
  classeurs de l'utilisateur.
- L'enregistrement automatique (365) est désactivé ; les fichiers de travail
  sont locaux (`%LOCALAPPDATA%\ExcelCert\work`) donc OneDrive n'intercepte pas.

## Récupération
- `python main.py --unlock` libère un éventuel verrou clavier résiduel si
  l'application s'est arrêtée pendant qu'elle était accrochée.
- Une session interrompue est proposée à la reprise au démarrage (chronomètre
  recalculé à partir de l'échéance persistée).
