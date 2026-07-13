# Excel Certification App — Detailed Project Plan

Offline desktop exam simulator for MOS Excel 2016 certification, built with **PyQt6 + SQLite**, cloning the workflow of the original "Simulateur MOS 2016" app (see `resources/`).

**Core principle (confirmed): the candidate works in the REAL Microsoft Excel.** Our app never renders a spreadsheet. It is three things:

1. A **fullscreen kiosk shell** that locks the machine to the exam.
2. A **task panel** docked at the bottom of the screen (timer, task text, navigation), with real Excel filling the rest of the screen above it.
3. An **offline grading engine** that inspects the saved `.xlsx` files (which are ZIP archives of XML) after submission.

Target OS: **Windows** with Microsoft Office installed (Excel 2016+). Grading and most UI are OS-independent and developable on Linux; the Excel-control and kiosk layers need a Windows machine.

---

## 1. Resource inventory (what we clone)

| Resource | Role in the new app |
|---|---|
| `MOS_Excel2016_Projet1..13.xlsx` | The 13 pristine starting workbooks → `content/projects/` |
| `reponse-mos-excel2016-partie1.pdf` | Task statements + official solutions, projects **1–7** |
| `reponse-mos-excel2016-partie2.pdf` | Task statements + official solutions, projects **8–13** |
| `login.png` | Launcher/branding to imitate (MOS blue theme, product tiles) |
| `the Test board.png` | The exam UI to clone: Excel on top; bottom green bar with "Projet 1 sur 13", timer `49:50`, buttons *Réponse* / *Soumettre le projet*; below it task tabs *Tâche 1..7*, the task statement, and buttons *Tâche précédente* / *marquer pour réviser* / *marquer achevée* / *Tâche suivante* |

## 2. Exam rules

- **Variant A** = projects 1–7. **Variant B** = project 1 + projects 8–13. Both = **7 projects** per exam; project 1 is always included. Variant chosen at session start (alternating or random; configurable).
- Each project has **4–7 tasks** (see §5). Total ≈ 34 tasks (A) / ≈ 33 tasks (B).
- **One global 50:00 countdown** for the whole exam (persisted — survives app restart).
- **Score = passed tasks / total tasks**, all tasks weighted 1 point (configurable per task in the XML). **PASS ≥ 85%**, FAIL < 85%.
- If the candidate submits all 7 projects before 50:00, the **review board** lets him reopen any project and continue until time runs out or he clicks "Terminer le test".
- Multi-candidate: after results, the app loops back to registration; every session is appended to `results.xlsx` and stored in SQLite.

## 3. High-level architecture

```
┌───────────────────────────────────────────────────────────────┐
│  Windows session (kiosk-locked by our app)                    │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │   REAL MICROSOFT EXCEL  (launched & managed via COM)    │  │
│  │   opens work\P{n}_{session}.xlsx (copy of pristine)     │  │
│  │   window moved/sized by us to fill this region          │  │
│  └─────────────────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  PyQt6 TASK PANEL (frameless, always-on-top, ~180 px)   │  │
│  │  Projet 3 sur 7   ⏱ 41:07   [Logout] [Soumettre projet] │  │
│  │  [Tâche 1][Tâche 2][Tâche 3][Tâche 4][Tâche 5][Tâche 6] │  │
│  │  «Dans la feuille "Étudiants", modifiez la mise en...»  │  │
│  │  [Précédente] [Marquer pour réviser] [Achevée] [Suiv.]  │  │
│  └─────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────┘

Modules:
  app/ui        PyQt6 screens & task panel
  app/kiosk     fullscreen lock, keyboard hook, focus watchdog
  app/excel     ExcelController — pywin32 COM wrapper
  app/exam      SessionManager — state machine, timer, work-dir mgmt
  app/grading   GradingEngine + checker classes (openpyxl + lxml)
  app/db        SQLite DAO + results.xlsx exporter
  content/      pristine workbooks, solution workbooks, task XML
```

**Data flow on submit:** panel → `ExcelController.save_and_close()` (COM `Workbook.Save()`) → workbook file on disk → *(at exam end)* `GradingEngine.grade(session)` reads each saved file with openpyxl/lxml → `task_results` rows → score → SQLite + `results.xlsx`.

## 4. Screen-by-screen UI specification

All UI text in **French** (like the original). Theme: MOS blue/green from `login.png` / `the Test board.png`.

### 4.1 S0 — Admin first-run setup (only when DB is empty)
- Set the **secret logout/admin code** (entered twice, stored as salted SHA-256/scrypt hash in `settings`).
- Set `results.xlsx` output path, exam duration (default 50 min), pass threshold (default 85), Excel executable autodetect check.

### 4.2 S1 — Candidate registration
- Fullscreen, branded like `login.png`. Fields: **Prénom, Nom, CIN, N° de téléphone**.
- Validation: all required; CIN uppercased/trimmed, regex `^[A-Z]{1,2}[0-9]{4,8}$` (warning only, overridable); phone regex `^0[5-7][0-9]{8}$` (warning only).
- Variant selector hidden behind admin code (default: automatic alternation).
- Button **«Commencer»** → S2. The kiosk lock is already active from launch.

### 4.3 S2 — Instructions
- Static page: rules (50 min, 7 projects, ~34 tasks, no external help, how the panel buttons work), replicating the original's intro.
- **«Démarrer le test»** → creates session row, copies the 7 pristine workbooks to the session work dir, starts the timer, opens project 1 → S3.

### 4.4 S3 — Exam (the task panel)
Bottom-docked frameless window, full screen width, ~180–200 px tall, always-on-top. Excel occupies everything above it.

| Zone | Widgets & behavior |
|---|---|
| Top strip | `Projet {i} sur 7` • live countdown `MM:SS` (turns red < 5:00) • **Logout** (admin-code dialog) • **«Soumettre le projet»** |
| Task tabs | One tab per task (`QTabBar`). Tab decorations: ✔ green when *marquée achevée*, ★ orange when *marquée pour réviser*. |
| Statement | Read-only rich-text of the current task (from XML), 2–4 lines, scrollable. |
| Bottom buttons | **«Tâche précédente»** / **«Marquer pour réviser»** (toggle) / **«Marquer achevée»** (toggle) / **«Tâche suivante»** |

Behaviors:
- Marks are candidate bookkeeping only — **they never affect grading**.
- «Soumettre le projet» → confirm dialog («Vous ne pourrez plus revenir… avant la fin des 7 projets») → COM save+close → open next project. Submitting the 7th project → S4 if time remains, else S5.
- The panel never shows solutions. (The original's *Réponse* button is training-mode only — see §12 "later options".)
- Timer at 00:00 at any moment → modal «Temps écoulé», force save/close, → S5.

### 4.5 S4 — Review board (only when all 7 submitted and time > 0)
- Grid of 7 project cards: project number, sheet-name hint, submitted time, counts of tasks *achevées* / *à réviser*.
- Click a card → reopens that project's **work file** (state preserved) in Excel, back to S3 for that project.
- **«Terminer le test»** (confirm) → S5.

### 4.6 S5 — Grading & results
- «Correction en cours…» progress (grading ~34 tasks takes a few seconds).
- Result page: big **score %**, verdict **RÉUSSI** (≥85, green) / **ÉCHOUÉ** (<85, red), per-project bar (x/y tasks), duration used.
- Per-task detail is NOT shown to the candidate (admin can query SQLite); this mirrors real MOS.
- **«Candidat suivant»** → wipe/archive work dir → S1.

### 4.7 Admin dialog (from Logout button, any screen)
- Enter secret code (3 attempts, then 30 s lockout; attempts audit-logged).
- On success: menu — *Quitter l'application* (unlock kiosk & exit), *Abandonner la session* (mark `aborted`, back to S1), *Paramètres* (S0 settings), *Exporter les résultats*.

## 5. Complete task → verification matrix (all 13 projects)

Extracted from the two answer PDFs. Each row becomes one `<task>` in `content/tasks/projet{n}.xml`. "Checker" names refer to §7 classes. *(Statements below are abbreviated; the XML will carry the full French text.)*

### Projet 1 — workbook `MOS_Excel2016_Projet1.xlsx` (7 tasks)
| # | Task (abbrev.) | Checker(s) | How it verifies (offline, on saved XML) |
|---|---|---|---|
| 1 | Table banded rows in "Étudiants" | `table_style_option` | `worksheet.tables[*].tableStyleInfo.showRowStripes == True` |
| 2 | Multi-level sort: Pays (US then Canada), Code A→Z, Matricule ↑ | `sort_order` | Read data rows; assert the full expected ordering (compare against sorted solution values) |
| 3 | N2 = average of Âge (D2:D501) | `formula` | Formula in N2 matches `MOYENNE/AVERAGE` over D2:D501 **and** cached value ≈ expected (±0.01) |
| 4 | 3-decimal number format on "Quantité" col ("Articles") | `number_format` | `cell.number_format` contains `0.000` on the column range |
| 5 | Conditional formatting: above-average, green fill + dark-green text on TotalCommande (I2:I501) | `conditional_formatting` | CF rule of type `aboveAverage` on the range with dxf fill/font ≈ green preset |
| 6 | J2 = MAX of TotalCommande | `formula` | `MAX` over I2:I501 + value check |
| 7 | Remove duplicates by N.Nationale in "DateEmploi" | `dedup_rows` | Row count + remaining values equal the solution workbook (no extra deletions) |

### Projet 2 — `Projet2.xlsx` (5 tasks)
| # | Task | Checker(s) | Verification |
|---|---|---|---|
| 1 | Import `Donateurs.txt` (tab-separated) at A5 of "Contributeurs -100" | `range_values` | Region starting A5 equals the parsed txt / solution values |
| 2 | Clear content of named range "Génie" | `named_range_empty` | `wb.defined_names['Génie']` cells are all empty |
| 3 | Add new sheet "Contributeurs -10" | `sheet_exists` | Name in `wb.sheetnames` |
| 4 | Hyperlink in C3 → mailto:ouaftechno@gmail.com | `hyperlink` | `cell.hyperlink.target == 'mailto:…'` |
| 5 | Sheet "Contributeurs -10" positioned first | `sheet_order` | `wb.sheetnames[0]` |

*Note: ships with a data file `Donateurs.txt` in the project folder (recreate it from the solution workbook during calibration).*

### Projet 3 — `Projet3.xlsx` (4 tasks)
| # | Task | Checker(s) | Verification |
|---|---|---|---|
| 1 | Margins: top/bottom 3.25 cm, left/right 1.90 cm, header/footer 2.31 cm | `page_margins` | `page_margins` values in inches ≈ cm/2.54 (±0.01) |
| 2 | Hide rows 29–30 | `hidden_rows` | `row_dimensions[29].hidden and [30].hidden` |
| 3 | Freeze so row 9 + WordArt stay visible (freeze at A10) | `freeze_panes` | `worksheet.freeze_panes == 'A10'` |
| 4 | Accessibility: alt-text title "Fourniture scolaire" on the text box | `shape_alt_text` | lxml on `xl/drawings/drawing*.xml`: `//xdr:sp//a:...  title="Fourniture scolaire"` |

### Projet 4 — `Projet4.xlsx` (4–5 tasks)
| # | Task | Checker(s) | Verification |
|---|---|---|---|
| 1 | Print titles: repeat row 9 on every page ("Achat de moteurs") | `print_titles` | `worksheet.print_title_rows == '$9:$9'` |
| 2 | Replace all "Pick-up" → "Caravane" | `text_absent_present` | No cell contains "Pick-up"; count of "Caravane" == solution |
| 3 | Column J = discounted price formula (⚠ PDF states 95% but its answer uses `G10*90%` — **resolve during calibration**, accept both formula patterns if the exam text says 95%) | `formula_column` | Every J-cell formula matches pattern `G{r}\*(0\.9(5)?|9(0|5)%)` + value check |
| 4 | Table style "Brun tanné, Style clair 17" on table "Achat" | `table_style_name` | `tableStyleInfo.name == 'TableStyleLight17'` (verify exact id in calibration) |
| 5 | *(PDF page break suggests a 5th task: create table with headers — confirm against the PDF during content transcription)* | `table_exists` | Table object with expected ref & headerRowCount=1 |

### Projet 5 — `Projet5.xlsx` (4 tasks)
| # | Task | Checker(s) | Verification |
|---|---|---|---|
| 1 | Column sparklines (Histogramme) in H10↓, data B10:F10 per row ("Éducation physique") | `sparkline` | lxml `x14:sparklineGroups` in sheet XML: type=`column`(default histogram), locations & ranges match |
| 2 | Create table A9:G19 with row 9 as header ("Programme Annuel") | `table_exists` | Table ref == `A9:G19`, headerRowCount == 1 |
| 3 | Unhide sheet "Conclusion" | `sheet_visible` | `wb['Conclusion'].sheet_state == 'visible'` |
| 4 | Alt-text title "Inscriptions des athlètes" on table "Educationphysique" | `table_alt_text` | Table XML attr `title`/`altText…` (raw `xl/tables/table*.xml`) |

### Projet 6 — `Projet6.xlsx` (5 tasks)
| # | Task | Checker(s) | Verification |
|---|---|---|---|
| 1 | K10 = count of groups ≥ 12 (order-independent → NB.SI/COUNTIF) | `formula` | Pattern `NB.SI|COUNTIF` with `">=12"` + value check |
| 2 | K11 = SUM of Total for groups ≥ 12 (SOMME.SI/SUMIF) | `formula` | Pattern `SOMME.SI|SUMIF` + value |
| 3 | C8 = concatenate Nom + ", " + Prénom | `formula` | Pattern `CONCATENER|CONCAT|&` containing `", "` + value `"Campbell, David"`-style |
| 4 | Convert table to range (keep formatting) | `table_absent` | Sheet has no table object; cell values/styles unchanged vs solution |
| 5 | Centered footer with "Page 1 de ?" format ("Les Forums") | `header_footer` | `worksheet.oddFooter.center.text` contains `&P` and `&N` (Page X de Y codes) |

### Projet 7 — `Projet7.xlsx` (5 tasks) — chart-heavy
| # | Task | Checker(s) | Verification |
|---|---|---|---|
| 1 | Create 3D pie chart from "Produits"+"Total" cols, placed right of histograms | `chart_exists` | lxml `xl/charts/chart*.xml`: a `pie3DChart` whose series ref the Produits/Total ranges; anchor col > histogram anchor |
| 2 | Add series "Total" to chart "Graphique trimestriel" | `chart_series` | Named chart contains an extra `c:ser` whose `c:val` refs the Total column |
| 3 | Chart title "Nouveaux repas", axis titles "Aliments" (V) / "Consommation" (H) | `chart_titles` | `c:title` texts match (whitespace-insensitive) |
| 4 | Style 3 + monochrome color 2 on the 3D pie | `chart_style` | `xl/charts/style*.xml` / `c14:style val="203"`-family + colorStyle XML (**calibrate exact ids**) |
| 5 | Switch rows/columns of the histogram | `chart_plot_by` | Series count/cat-val orientation equals solution chart XML |

### Projet 8 — `Projet8.xlsx` (5 tasks)
| # | Task | Checker(s) | Verification |
|---|---|---|---|
| 1 | Merge A1:N1 **without changing alignment** ("Ingrédients") | `merged_range` + `alignment_unchanged` | `'A1:N1' in merged_cells`; A1 alignment == pristine (i.e. plain Merge, not Merge & Center) |
| 2 | Auto-fit widths of columns A:N | `column_widths_changed` | Widths differ from pristine and ≈ content-fit widths of solution (±0.5) |
| 3 | Right header "Séquentiel" on every page | `header_footer` | `oddHeader.right.text == 'Séquentiel'` |
| 4 | Hyperlink A6 → cell A18 of sheet "Description" | `hyperlink` | `cell.hyperlink.location == 'Description!A18'` |
| 5 | Print all columns on one page, landscape | `page_setup` | `orientation=='landscape'`, `fitToWidth==1` (scale mode on) |

### Projet 9 — `Projet9.xlsx` (5 tasks)
| # | Task | Checker(s) | Verification |
|---|---|---|---|
| 1 | Doc property: Company = "Salon International" | `doc_property` | `docProps/app.xml` `<Company>` (raw XML; openpyxl exposes core props only) |
| 2 | "Différence" column = Prix de vente − Coût (formatting untouched) | `formula_column` + `styles_unchanged` | Formula pattern per row + values; column style == pristine |
| 3 | F37 = MOYENNE.SI Editeur="Fabrikam, Inc." over Prix de vente | `formula` | Pattern `MOYENNE.SI|AVERAGEIF` + value |
| 4 | Move sheet "Achats annuels" between "Œuvres" and "titres" | `sheet_order` | Index("Œuvres") < Index("Achats annuels") < Index("titres") |
| 5 | Image rotation set to 0° ("Œuvres") | `image_rotation` | drawing XML `a:xfrm` has no `rot` attr (or rot=0) |

### Projet 10 — `Projet10.xlsx` (5 tasks)
| # | Task | Checker(s) | Verification |
|---|---|---|---|
| 1 | New sheet "Trimestre 3" at far right | `sheet_exists` + `sheet_order` | Name present; index == last |
| 2 | IF formula in "STATUT ACHATS": ≥800 → "Excellent" else "Passable" | `formula_column` | Pattern `SI|IF` with `>=800`, `"Excellent"`, `"Passable"` + values (at least first cell; full column optional per statement) |
| 3 | Line sparklines in "EVOLUTION" (Janvier→Mars, T1) | `sparkline` | `x14:sparklineGroup type="line"` locations/ranges |
| 4 | Extend chart in "Trimestre 2" to include "Juin" | `chart_series_range` | Series `c:val` refs now include the Juin column |
| 5 | Show formulas view on "Trimestre 2" | `sheet_view_flag` | sheet XML `<sheetView showFormulas="1">` |

### Projet 11 — `Projet11.xlsx` (4 tasks)
| # | Task | Checker(s) | Verification |
|---|---|---|---|
| 1 | Delete the authors column from table "Achats" | `column_absent` | No header cell "Auteur(s)"; table columnCount == solution |
| 2 | Convert table to range in "Meilleurs Achats" (keep formatting) | `table_absent` + `styles_unchanged` | No table part for that sheet; fonts/fills intact |
| 3 | Copy A9:A12 ("Meilleurs Achats") → A3:A6 ("Nouveau Plan") | `range_values` | Target range values equal source values |
| 4 | 3D stacked column chart of Q1 purchases; titles on H axis, months as legend, title "Achats du trimestre 1" | `chart_exists` + `chart_titles` + `chart_plot_by` | `bar3DChart` grouping="stacked"; cat refs = book titles; title text match |

### Projet 12 — `Projet12.xlsx` (4 tasks)
| # | Task | Checker(s) | Verification |
|---|---|---|---|
| 1 | Hide column D ("CODE ouvrier") | `hidden_cols` | `column_dimensions['D'].hidden` |
| 2 | Column L: first names in lowercase via function | `formula_column` | Pattern `MINUSCULE|LOWER` + values |
| 3 | Clear content of named range "Aka_Regional" | `named_range_empty` | All cells of the defined name empty |
| 4 | Print titles: repeat row 7 ("Academy") | `print_titles` | `print_title_rows == '$7:$7'` |

### Projet 13 — `Projet13.xlsx` (5 tasks per PDF header; 4 transcribed)
| # | Task | Checker(s) | Verification |
|---|---|---|---|
| 1 | Import `Boissons.txt` at A7 of "Orange" (Get & Transform, defaults) | `range_values` | Region at A7 equals parsed txt / solution values (query metadata ignored) |
| 2 | Table style "Vert, Style de tableau moyen 9" ("Graphique") | `table_style_name` | `tableStyleInfo.name == 'TableStyleMedium9'` (calibrate) |
| 3 | Chart Layout 9; V-axis title "Prix"; remove H-axis title | `chart_titles` + `chart_layout` | V `c:title` == "Prix"; no H-axis title element; layout ≈ solution |
| 4 | Move chart from "Ventes" to chart sheet "Ventes de thé" | `chartsheet_exists` | `wb.chartsheets` contains "Ventes de thé"; chart part attached |
| 5 | *(verify 5th task against PDF during transcription — header says 5 tâches)* | — | — |

**Transcription step (M2)** re-reads both PDFs task-by-task and captures the exact French statements verbatim into the XML files; the two ⚠ ambiguities above (P4.3 percentage, P4.5/P13.5 existence) are resolved there.

## 6. Excel integration — `app/excel/controller.py` (pywin32)

```python
class ExcelController:
    def start(self) -> None                 # EnsureDispatch('Excel.Application'), our own instance
    def open_project(self, path) -> None    # Workbooks.Open(path); position window
    def position_window(self, rect) -> None # win32gui.MoveWindow(hwnd of "XLMAIN", above panel)
    def force_save(self) -> Path            # Workbook.Save(); wait until saved
    def close_workbook(self) -> None        # Close(SaveChanges=True)
    def shutdown(self) -> None              # Quit + kill orphan EXCEL.EXE of our PID tree
    def is_alive(self) -> bool              # ping COM; detect crash
    def active_workbook_path(self) -> str   # for the watchdog (detect File>Open of foreign files)
```

Details & hardening:
- **Own instance**: create a dedicated Excel process (`DispatchEx`) so we never touch a user's open Excel; track its PID; kill tree on exit.
- **Positioning**: find `XLMAIN` hwnd of our PID; `MoveWindow` to `(0, 0, screen_w, screen_h − panel_h)`; re-assert in the watchdog tick (Excel restores geometry on some actions).
- **Excel settings on open** (via COM, restored on exit): `DisplayFullScreen=False`, disable `AutoSave` (365), `Application.AskToUpdateLinks=False`, `DisplayAlerts=False` around open/save only.
- **Events**: advise sink on `WorkbookBeforeClose` (veto → panel message "Utilisez Soumettre le projet"), `WindowDeactivate` (watchdog refocus assist).
- **Crash recovery**: `is_alive()` polled every tick; if Excel died → relaunch and reopen the current **work file** (last saved state); log to `audit_log`. Additionally auto-`Save` every 60 s via COM so a crash loses ≤ 1 min of work.
- **Foreign file guard**: if `ActiveWorkbook.FullName` ≠ current work file → close the foreign workbook, refocus ours, audit-log.
- **Save-format guard**: work files are `.xlsx`; `Workbook.Save()` keeps format, no dialogs.

## 7. Grading engine — `app/grading/`

### 7.1 Inputs
- Candidate's saved work file (`.xlsx` = ZIP of XML).
- Pristine workbook (to check "unchanged" assertions and compute diffs).
- Solution workbook (frozen reference produced in calibration).
- Task XML (`content/tasks/projet{n}.xml`).

### 7.2 Task XML schema

```xml
<project id="6" workbook="MOS_Excel2016_Projet6.xlsx" title="Les Forums">
  <task id="1" points="1">
    <statement lang="fr"><![CDATA[Dans la cellule K10 de la feuille de calcul
      "Les Forums", insérez une fonction pour calculer le nombre de groupes de
      12 personnes ou plus, même si l'ordre des lignes est modifié.]]></statement>
    <check type="formula" sheet="Les Forums" cell="K10"
           pattern="(NB\.SI|COUNTIF)" must_contain="&quot;&gt;=12&quot;"
           expected_value="from_solution" tolerance="0"/>
  </task>
  <task id="4" points="1">
    <statement lang="fr"><![CDATA[…retirez la fonctionnalité de tableau…]]></statement>
    <check type="table_absent"      sheet="Les Forums"/>
    <check type="styles_unchanged"  sheet="Les Forums" range="B9:J40" against="solution"/>
  </task>
</project>
```

Rules:
- A task passes iff **all** its `<check>` elements pass. `<any>` wrapper allows alternative solutions (e.g. `CONCATENER` **or** `&` operator).
- `expected_value="from_solution"` = read the value from the solution workbook at load time → no hand-typed constants to drift.
- Formula matching is **locale-aware**: openpyxl stores formulas in English internally; the engine normalizes (`MOYENNE→AVERAGE`, `NB.SI→COUNTIF`, `;`→`,`) before matching, so both French and English patterns work.

### 7.3 Checker framework

```python
class BaseChecker(ABC):
    def __init__(self, params: dict, ctx: GradingContext): ...
    @abstractmethod
    def run(self) -> CheckResult   # (passed: bool, reason: str)

class GradingContext:
    wb_user: openpyxl.Workbook        # candidate file (values + formulas via two loads)
    wb_pristine / wb_solution
    zip_user: zipfile.ZipFile         # raw XML access (lxml) for drawings/charts/
                                      # sparklines/docProps/tables/sheetViews
```

Checker registry (one module each, ~25 checkers — full list in §5 tables):
`formula, formula_column, range_values, number_format, conditional_formatting, table_exists, table_absent, table_style_name, table_style_option, table_alt_text, column_absent, sort_order, dedup_rows, named_range_empty, sheet_exists, sheet_order, sheet_visible, sheet_view_flag, merged_range, alignment_unchanged, styles_unchanged, column_widths_changed, hidden_rows, hidden_cols, freeze_panes, page_margins, page_setup, print_titles, header_footer, hyperlink, doc_property, shape_alt_text, image_rotation, sparkline, chart_exists, chart_series, chart_series_range, chart_titles, chart_style, chart_layout, chart_plot_by, chartsheet_exists, text_absent_present`.

Implementation notes:
- openpyxl covers ~70% (cells, formulas, formats, tables, CF, page setup, defined names, merged cells, dimensions, freeze panes, headers/footers, hyperlinks).
- Raw **lxml over the ZIP** covers the rest: sparklines (`x14` extLst), chart XML (`xl/charts/*.xml` + rels for placement), drawing alt-text & rotation, `docProps/app.xml`, `showFormulas` sheet view, table alt-text.
- Load candidate file **twice**: `data_only=False` (formulas) and `data_only=True` (cached values Excel wrote at save — reliable because Excel always recalculates before save).

### 7.4 Calibration & test harness (critical)
For each of the ~65 tasks across the 13 projects:
1. Perform the task by hand in Excel on the pristine file → save as `content/solutions/projet{n}_t{k}.xlsx` (or one cumulative solution per project + per-task snapshots for tricky ones).
2. pytest matrix: **pristine must FAIL** every check; **solution must PASS**; where the statement allows several techniques (e.g. banded rows via style option vs. any striped style; CONCAT vs `&`), produce one solution file per accepted technique — all must pass.
3. CI runs the matrix on every checker change. This is the single biggest quality lever of the project.

## 8. Session state machine & timing — `app/exam/`

```
IDLE → REGISTERED → INSTRUCTIONS → RUNNING(project i, task j)
     → (all submitted & t>0) REVIEWING ⇄ RUNNING(reopened project)
     → (t==0 anywhere | «Terminer») GRADING → RESULTS → IDLE
     → (admin abort) ABORTED → IDLE
```

- **Timer**: `deadline = started_at + 50min` persisted in `sessions`; the panel clock derives from wall time, not a decrementing counter → app crash/restart recomputes remaining time correctly.
- **Crash resume**: on launch, if a `RUNNING` session exists in DB → dialog (admin code NOT required) «Reprendre la session de {prénom} {nom} ?» → reopen current project work file, timer continues from wall clock. Work dir + `session_projects.workfile_path` make this deterministic.
- **Work dir**: `%LOCALAPPDATA%/ExcelCert/work/{session_id}/P{n}.xlsx` + data files (`Donateurs.txt`, `Boissons.txt`) copied beside them; archived (zipped) after grading for audit, then originals removed.

## 9. Kiosk lock-down — `app/kiosk/` (Windows)

| Layer | Mechanism |
|---|---|
| Fullscreen shell | Frameless `Qt.WindowStaysOnTopHint` windows; a black background window covers the full desktop on all monitors; secondary monitors get an opaque cover window |
| Keyboard hook | `SetWindowsHookEx(WH_KEYBOARD_LL)` via ctypes in a dedicated thread: swallow `Alt+Tab`, `Alt+Esc`, `Ctrl+Esc`, `Win`, `Alt+F4`, `F11`; pass everything else (Excel needs full typing incl. Alt-ribbon shortcuts — only the exact combos above are filtered) |
| Focus watchdog | QTimer 500 ms: foreground hwnd must be our panel, our dialogs, or our Excel PID's windows; else `SetForegroundWindow` back + audit log |
| Excel guards | §6: veto workbook close, foreign-file guard, geometry re-assert |
| Escape hatch | Logout → admin code (hashed); 3 fails = 30 s lockout |
| Not blockable | `Ctrl+Alt+Del`/Task Manager (OS-level). Mitigation: watchdog re-fronts on return, event audit-logged with timestamp; optional deployment doc: local group policy `DisableTaskMgr` + assigned-access notes for exam PCs |
| Clean unlock | Every lock is reversed on admin exit **and** by a `--unlock` CLI flag (recovery if the app dies while hooked) |

## 10. Data layer — `app/db/`

```sql
CREATE TABLE candidates (
  id INTEGER PRIMARY KEY, first_name TEXT NOT NULL, last_name TEXT NOT NULL,
  cin TEXT NOT NULL, phone TEXT NOT NULL, created_at TEXT NOT NULL);

CREATE TABLE sessions (
  id INTEGER PRIMARY KEY, candidate_id INTEGER NOT NULL REFERENCES candidates(id),
  variant TEXT CHECK(variant IN ('A','B')), started_at TEXT, deadline TEXT,
  ended_at TEXT, duration_s INTEGER, score_pct REAL, passed INTEGER,
  status TEXT CHECK(status IN ('running','finished','aborted')) DEFAULT 'running');

CREATE TABLE session_projects (
  id INTEGER PRIMARY KEY, session_id INTEGER NOT NULL REFERENCES sessions(id),
  project_no INTEGER NOT NULL, order_idx INTEGER NOT NULL,
  workfile_path TEXT, submitted_at TEXT, reopened_count INTEGER DEFAULT 0);

CREATE TABLE task_results (
  id INTEGER PRIMARY KEY, session_project_id INTEGER REFERENCES session_projects(id),
  task_no INTEGER NOT NULL, marked_complete INTEGER DEFAULT 0,
  marked_review INTEGER DEFAULT 0, passed INTEGER, checker_details TEXT);  -- JSON

CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT);
-- admin_code_hash, admin_code_salt, results_xlsx_path, exam_minutes=50,
-- pass_threshold=85, variant_mode=alternate

CREATE TABLE audit_log (
  id INTEGER PRIMARY KEY, session_id INTEGER, ts TEXT NOT NULL, event TEXT NOT NULL);
-- events: focus_escape, excel_closed_by_user, excel_crash, foreign_workbook,
-- admin_code_fail, admin_unlock, resume_after_crash
```

**`results.xlsx` export** (openpyxl, append one row per finished session; file created with header if missing; retry-with-copy if the file is open/locked):

| Date | Prénom | Nom | CIN | Téléphone | Variante | Durée | Score % | Résultat |

## 11. Repository layout

```
excel_cert_app/
├── main.py                     # arg parsing (--unlock, --admin), boots App
├── app/
│   ├── config.py
│   ├── ui/         (registration.py, instructions.py, task_panel.py,
│   │                review_board.py, results.py, admin_dialog.py, theme.qss)
│   ├── kiosk/      (lock.py, keyboard_hook.py, watchdog.py)
│   ├── excel/      (controller.py, window.py, events.py)
│   ├── exam/       (session.py, timer.py, workdir.py, variants.py)
│   ├── grading/    (engine.py, context.py, checkers/*.py, formula_locale.py)
│   └── db/         (schema.sql, dao.py, results_export.py)
├── content/
│   ├── projects/   Projet1..13.xlsx  (+ Donateurs.txt, Boissons.txt)
│   ├── solutions/  projet{n}[_t{k}].xlsx      (built in M3)
│   └── tasks/      projet1..13.xml
├── tests/          test_checkers_matrix.py, test_engine.py, test_timer.py,
│                   test_export.py, fixtures/
└── packaging/      pyinstaller.spec, installer notes, exam-PC hardening.md
```

Dependencies: `PyQt6`, `openpyxl`, `lxml`, `pywin32` (Windows only), `pytest` (dev). Python 3.11+.

## 12. Milestones with acceptance criteria

| # | Milestone | Contents | Done when |
|---|---|---|---|
| **M1** | App skeleton (cross-platform) | PyQt6 screens S0–S5 with stubbed Excel; SQLite schema + DAO; wall-clock timer; variant selection; results.xlsx export | Full candidate flow runs on Linux with a fake "project" placeholder; rows land in SQLite + results.xlsx; crash-resume works |
| **M2** | Exam content | Verbatim transcription of all task statements from both PDFs into `tasks/*.xml` (resolve P4/P13 ambiguities); task panel renders tabs/marks exactly like `the Test board.png`; French UI + theme | Side-by-side visual match with the screenshot; all 13 XML files load & validate against an XSD |
| **M3** | Grading engine (cross-platform) | All ~25 checkers; formula locale normalization; solution workbooks authored for all tasks; calibration pytest matrix | `pytest` green: every task fails on pristine, passes on solution(s), incl. alternative-technique files |
| **M4** | Excel integration (Windows) | `ExcelController` complete: dedicated instance, positioning, save/close, events, crash recovery, autosave tick, foreign-file guard | Full exam runnable end-to-end on Windows with real Excel; submit → grade → correct score |
| **M5** | Kiosk lock-down (Windows) | Keyboard hook, focus watchdog, multi-monitor covers, admin-code logout, audit log, `--unlock` recovery | Red-team checklist passes: Alt+Tab/Win/Alt+F4 dead, Excel close vetoed, foreign file bounced, Ctrl+Alt+Del escape is re-fronted + logged |
| **M6** | Review board & polish | S4 board with per-project status, reopen flow, low-time warnings, results screen polish, admin settings/export UI | A tester finishes early, reopens 2 projects, edits, re-submits; grading reflects final state |
| **M7** | Packaging & field test | PyInstaller one-dir build (content bundled), first-run setup, hardening doc, dry run with 3–5 real candidates on the target exam PC | Installer-free copy runs on a clean Windows + Office machine; dry-run feedback triaged and fixed |

Suggested order: M1 → M2 → M3 can proceed on Linux in parallel with early M4 spikes on Windows; M4 → M5 → M6 → M7 sequential.

## 13. Edge cases & failure handling

- **Time expires mid-typing** → COM save is issued regardless; whatever is on disk is graded.
- **Excel crash** → auto-relaunch + reopen work file (≤ 60 s of loss thanks to autosave tick); audit-logged; timer unaffected.
- **App/PC crash or power loss** → on next launch, `running` session detected → resume with recomputed remaining time.
- **results.xlsx locked/open** → write to `results_YYYYMMDD_HHMMSS.xlsx` fallback and log a warning in admin UI.
- **Candidate opens another workbook via Excel File>Open** → foreign-file guard closes it (recent-files list is also cleared on open).
- **Two Excel versions / 365 AutoSave** → AutoSave forced off; work files are local so OneDrive never intercepts.
- **Accented sheet names** ("Étudiants", "Œuvres") → all lookups NFC-normalized.
- **Grading exception in one checker** → task marked failed with `checker_details` = traceback; never blocks the session; surfaced in admin export.

## 14. Later options (explicitly out of scope for v1)

- **Training mode** with the original's *Réponse* button revealing the step-by-step solution (all data for it already sits in the task XML — add `<solution>` element).
- Word / PowerPoint modules (the launcher screenshot shows all three exams).
- Immediate per-project grading feedback, per-task score weighting, question randomization within projects.

## 15. Open points to confirm

1. Variant split **A = 1–7, B = 1 + 8–13** (supported by the two PDFs: "7 projets" / "6 projets").
2. P4 task 3: statement says **95%**, official answer uses **×90%** — which is authoritative?
3. Confirm existence/wording of P4 task 5 and P13 task 5 during transcription.
4. Should the review board also allow reopening **before** all 7 are submitted (original MOS: no — a submitted project is locked until the review phase)? Plan assumes MOS behavior.
