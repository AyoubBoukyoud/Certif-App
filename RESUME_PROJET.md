# Certif-App — Résumé du projet

## 1. Qu'est-ce que Certif-App ?

Certif-App fait passer une épreuve de certification **Microsoft Office
Specialist (MOS) Excel 2016** à un candidat, sur un poste kiosque Windows,
dans le **vrai Microsoft Excel** (l'app ne simule jamais une feuille de
calcul : elle pilote Excel via COM et corrige ensuite le fichier
`.xlsx` enregistré).

Le projet a deux grandes parties, développées en plusieurs itérations :

| Partie | Rôle | Répertoire |
|---|---|---|
| **App desktop (kiosque)** | Fait passer l'examen sur le poste candidat | `excel_cert_app/` |
| **Plateforme en ligne** | Coordination Direction Nationale → Régionale → Établissement → Surveillant → Candidat, dashboard web | `supabase/` + `web/dashboard/` |

## 2. App desktop — le moteur d'examen (itération 1)

Documenté en détail dans [`PLAN.md`](PLAN.md) et [`excel_cert_app/README.md`](excel_cert_app/README.md).

- **PyQt6** : shell kiosque plein écran, panneau de tâches ancré en bas
  pendant qu'Excel occupe le reste de l'écran.
- **pywin32 (COM)** pilote une instance Excel dédiée : ouverture des
  classeurs de projet, positionnement de la fenêtre, sauvegarde/fermeture,
  détection de crash et relance automatique.
- **Moteur de correction hors-ligne** (`app/grading/`) : après l'examen, les
  fichiers `.xlsx` enregistrés (des archives ZIP de XML) sont inspectés par
  ~37 vérificateurs (openpyxl + lxml) — aucune connexion ni Excel requis
  pour corriger.
- **Règles de l'épreuve** : 7 projets, 50 minutes au total, variante A
  (projets 1-7) ou B (projet 1 + 8-13), score = tâches réussies / total,
  réussite ≥ 85 %.
- **Verrouillage kiosque** (`app/kiosk/`) : hook clavier bas niveau, watchdog
  de focus, déconnexion par code administrateur haché (PBKDF2).
- **SQLite locale** (`app/db/`) : candidats, sessions, résultats, journal
  d'audit local — c'est toujours la source de vérité locale, même
  aujourd'hui avec Supabase en plus.

Ce moteur (`app/exam/`, `app/grading/`, `app/excel/`, `app/kiosk/`) est
stable et fonctionne en conditions réelles — les itérations suivantes ne
l'ont jamais touché, seulement l'écran d'accueil/inscription qui l'alimente.

## 3. Plateforme en ligne (itération 2 — plan à 5 rôles)

Besoin exprimé : coordonner plusieurs parties prenantes de la certification
au lieu d'un poste isolé avec saisie libre. Plan détaillé dans
`~/.claude/plans/jiggly-hopping-cascade.md`.

**5 rôles, hiérarchie par Row Level Security Postgres** (pas de hiérarchie
applicative complexe) :

| Rôle | Portée | Accès |
|---|---|---|
| Direction Nationale | toutes les régions | Dashboard web |
| Direction Régionale | 1 région | Dashboard web — gère les établissements, planifie les sessions |
| Administration d'établissement | 1 établissement | Dashboard web — importe les candidats, gère les surveillants |
| Surveillant | 1 établissement | **Poste kiosque uniquement** — valide un candidat avant l'examen |
| Candidat | — | Pas de compte, identifié par CIN au poste |

**Stack** : Supabase (Postgres + Auth + RLS), projet réel
`pummdlglelbsviokubxw`. Dashboard web séparé (`web/dashboard/`, React +
Vite + `@supabase/supabase-js`).

**Décision produit constante depuis cette itération** : le poste kiosque
est **toujours en ligne** — pas de mode dégradé/file d'attente hors-ligne.

Réalisé à ce stade : schéma initial (`supabase/migrations/0001_init_schema.sql`),
4 comptes de test réels validés bout en bout, dashboard React scaffoldé
(pages nationale/régionale/établissement, encore simples).

## 4. Refonte du parcours desktop (itération 3 — cahier des charges détaillé)

Un cahier des charges plus précis a ensuite formalisé le **parcours du
poste kiosque** en 5 écrans, avec un vocabulaire de tables différent
(`candidates`, `exam_sessions` par candidat, `audit_logs`). Plan détaillé
dans `~/.claude/plans/harmonic-cuddling-flask.md`.

### Le scénario, écran par écran

1. **Vérification du système** (`app/ui/system_check.py`) — au lancement :
   Windows/Office installés et activés, version Excel compatible MOS,
   connexion Internet, connexion à la plateforme Supabase, heure système,
   espace disque. Le bouton **Continuer** reste désactivé tant qu'une
   vérification critique échoue. Le résultat est journalisé dans
   `audit_logs`.
2. **Identification du candidat** (`app/ui/candidate_lookup.py`) — un champ
   CIN, bouton **Rechercher** : le poste (authentifié comme établissement)
   cherche le candidat dans Supabase, scopé à l'établissement du poste et à
   la session du jour. Trouvé → fiche identité (nom, établissement,
   filière, version MOS, session programmée…) + bouton **Commencer
   l'examen**. Sinon → « Candidat introuvable. ».
3. **Validation du surveillant** (`app/ui/supervisor_validation.py`) — une
   fenêtre modale (login + mot de passe), le surveillant s'authentifie via
   Supabase Auth ; le poste vérifie que c'est bien un compte surveillant de
   cet établissement. Succès → crée la ligne distante `exam_sessions`
   (candidat, surveillant, poste, heure de début, statut `started`).
4. **Préparation** (`app/ui/preparation.py`) — écran de chargement, UI
   verrouillée, création de la session locale, puis lancement automatique
   des instructions/du moteur d'examen existant.
5. **Fin de l'examen** — pas de nouvel écran : à la fin de l'examen
   existant (`_on_finish`), la ligne `exam_sessions` distante est mise à
   jour (heure de fin, score, réussite, statut `terminated`) en plus de
   l'export local `resultats.xlsx` habituel.

### Ce qui a été construit pour ça

- `app/supabase_service/` (renommé depuis `app/online/`) : `client.py`
  (wrapper `supabase-py`, clé publique uniquement), `auth.py` (session
  établissement du poste + connexion surveillant ponctuelle),
  `pairing.py` (identifiants établissement du poste, chiffrés DPAPI),
  `candidates.py`, `exam_sessions.py`, `audit.py`, `connectivity.py`.
- `app/ui/admin_dialog.py` étendu avec les champs d'appairage établissement
  (login/mot de passe) du poste.
- `supabase/migrations/0003_rename_to_candidate_workflow.sql` — renomme le
  schéma initial vers le vocabulaire du cahier des charges (`stagiaires`→
  `candidates`, l'ancien `exam_sessions`→`exam_schedules`, `exam_attempts`→
  `exam_sessions`, `audit_log`→`audit_logs`) et ajoute les colonnes
  nécessaires (poste de travail, statut, incidents, etc.).
- `web/dashboard/` mis à jour pour suivre ce renommage.

## 5. État réel au 17/07/2026 — points d'attention

- **Le moteur d'examen local (Excel, correction, kiosque) n'a pas changé**
  et continue de fonctionner tel quel.
- **La migration `0003` n'a pas encore été appliquée à la base Supabase
  réelle** — elle doit être exécutée à la main dans le SQL Editor, comme
  `0001` avant elle. Tant que ce n'est pas fait, le poste ne pourra pas
  encore chercher de vrais candidats en ligne.
- **Conflit non résolu** : un fichier `supabase/migrations/0002_extend_schema.sql`
  existe aussi, écrit en parallèle avec l'**ancien** vocabulaire
  (`stagiaires`/`exam_attempts`) — il est incompatible avec `0003` et **les
  deux ne doivent jamais être appliqués ensemble**. Ce point est documenté
  dans l'en-tête de `0003` et dans la mémoire du projet ; à trancher avant
  toute exécution de migration.
- Le mode « Test rapide » (bypass complet de l'identification, données
  factices) reste disponible pour dérouler l'examen sans plateforme.
- La calibration du moteur de correction (classeurs solutions de référence,
  voir §7.4 du `PLAN.md`) reste, comme avant cette itération, à finaliser
  avant mise en production.
