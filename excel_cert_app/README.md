# Simulateur de Certification Excel (MOS 2016)

Application de bureau **hors-ligne** qui fait passer une épreuve de certification
Excel dans le **vrai Microsoft Excel**, en s'inspirant du simulateur MOS 2016.
L'app est un shell kiosque plein écran + un panneau de tâches ancré en bas + un
moteur de correction hors-ligne. Elle n'imite jamais Excel : elle le pilote.

- **PyQt6** pour l'interface.
- **SQLite** pour les candidats, sessions, résultats et journal d'audit.
- **openpyxl + lxml** pour corriger le classeur enregistré (un `.xlsx` est une
  archive ZIP de XML) — aucune connexion, aucun Excel requis pour corriger.
- **pywin32 (COM)** pour piloter Excel sous Windows ; sur Linux/Mac un
  contrôleur de développement ouvre le classeur avec l'éditeur par défaut.

## Règles de l'épreuve

- **7 projets**, **50 minutes** au total (chronomètre global).
- Épreuve **A** = projets 1→7 ; épreuve **B** = projet 1 + projets 8→13.
- Score = tâches réussies / total. **Réussite ≥ 85 %**.
- Terminé avant la fin → tableau de bord pour revenir sur chaque projet.
- Verrouillage kiosque ; déconnexion par **code administrateur**.
- Multi-candidats : chaque résultat est ajouté à un `resultats.xlsx`.

## Installation

```bash
python -m venv .venv
. .venv/bin/activate            # Windows : .venv\Scripts\activate
pip install -r requirements.txt
```

Python 3.11+ recommandé. Sous Windows, `pywin32` est installé automatiquement.

## Lancer

```bash
python main.py                  # exécution normale (kiosque)
python main.py --no-resume      # ignorer une session interrompue
python main.py --unlock         # libérer un verrou kiosque résiduel (dépannage)
```

Au premier lancement, une boîte de dialogue demande de définir le **code
administrateur** et les paramètres (chemin des résultats, durée, seuil).

## Architecture

```
main.py                 point d'entrée + arguments CLI
app/config.py           chemins et constantes
app/content.py          chargement des tâches XML (énoncés + vérifications)
app/security.py         hachage PBKDF2 du code administrateur
app/db/                 schéma SQLite, DAO, export resultats.xlsx
app/exam/               machine à états, chronomètre mural, variantes, dossiers
app/excel/              contrôleur Excel (COM Windows / stub de dev)
app/grading/            moteur de correction + ~37 vérificateurs
app/kiosk/              verrouillage clavier + surveillance du focus (Windows)
app/ui/                 écrans PyQt6 + thème + contrôleur applicatif
content/projects/       classeurs vierges MOS_Excel2016_Projet1..13.xlsx
content/solutions/      classeurs corrigés (à produire — voir Calibration)
content/tasks/          projet1..13.xml (énoncés + vérifications)
tests/                  pytest : unités, base, correction, flux
```

## Correction (vérification hors-ligne)

Chaque tâche est décrite dans `content/tasks/projet{n}.xml` par un ou plusieurs
`<check>` reliés à une classe de vérificateur (`app/grading/checkers/`). Un
`<check>` compare l'état du classeur du candidat à l'attendu. Les vérificateurs
lisent openpyxl pour la plupart des cas et le XML brut (lxml) pour les
graphiques, sparklines, textes de remplacement, rotation d'image et propriétés
du document. Les noms de fonctions FR/EN sont normalisés (`MOYENNE`↔`AVERAGE`…).

### Calibration (étape indispensable avant la mise en production)

Le moteur et les vérificateurs sont testés (`tests/test_grading.py` : chaque
tâche échoue sur le fichier vierge et réussit sur un fichier modifié). Il reste
à **produire les classeurs corrigés de référence** pour verrouiller les
vérifications basées sur les valeurs et les styles de graphiques :

1. Ouvrir chaque `content/projects/Projet{n}.xlsx` dans Excel, réaliser les
   tâches, enregistrer sous `content/solutions/projet{n}.xlsx`.
2. Les `<check ... expected_value="from_solution">` compareront alors les
   valeurs calculées à la référence.
3. Points à confirmer en calibration (voir aussi le PLAN) :
   - Projet 4, tâche 3 : l'énoncé dit **95 %**, le corrigé officiel **×90 %**.
   - Styles/dispositions de graphiques (Projet 7, 13) : vérification actuelle
     approximative (présence du bon type de graphique).
   - Rotation d'image (Projet 9) : passe si aucune rotation (0°).

## Déploiement Windows

- Machine d'examen : **Windows + Microsoft Office (Excel 2016/2019/365)**.
- Empaqueter avec PyInstaller (`packaging/`), inclure le dossier `content/`.
- Durcissement recommandé : voir `packaging/hardening.md`.

`Ctrl+Alt+Suppr` ne peut pas être bloqué par une application en mode
utilisateur ; la surveillance du focus ramène l'épreuve au premier plan et
chaque tentative est journalisée dans `audit_log`.
