"""Page-setup / margins / print-titles / header-footer checkers."""
from __future__ import annotations

from .base import CheckResult, as_float, checker, fail, ok

CM_PER_INCH = 2.54


@checker("page_margins")
def check_page_margins(ctx, params) -> CheckResult:
    sheet = params["sheet"]
    ws = ctx.sheet_f(sheet)
    if ws is None:
        return fail(f"feuille «{sheet}» introuvable")
    m = ws.page_margins
    tol = as_float(params.get("tolerance_cm"), 0.05) / CM_PER_INCH
    checks = {
        "top": params.get("top_cm"),
        "bottom": params.get("bottom_cm"),
        "left": params.get("left_cm"),
        "right": params.get("right_cm"),
        "header": params.get("header_cm"),
        "footer": params.get("footer_cm"),
    }
    for attr, cm in checks.items():
        if cm is None:
            continue
        want_in = float(cm) / CM_PER_INCH
        got = getattr(m, attr)
        if got is None or abs(got - want_in) > tol:
            got_cm = None if got is None else round(got * CM_PER_INCH, 2)
            return fail(f"{sheet}: marge {attr}={got_cm}cm ≠ {cm}cm")
    return ok(f"{sheet}: marges conformes")


@checker("print_titles")
def check_print_titles(ctx, params) -> CheckResult:
    sheet = params["sheet"]
    ws = ctx.sheet_f(sheet)
    if ws is None:
        return fail(f"feuille «{sheet}» introuvable")
    rows = params.get("rows")     # e.g. "9:9"
    cols = params.get("cols")
    if rows:
        actual = (ws.print_title_rows or "").replace("$", "")
        if actual != rows.replace("$", ""):
            return fail(f"{sheet}: lignes à répéter «{actual}» ≠ «{rows}»")
    if cols:
        actual = (ws.print_title_cols or "").replace("$", "")
        if actual != cols.replace("$", ""):
            return fail(f"{sheet}: colonnes à répéter «{actual}» ≠ «{cols}»")
    return ok(f"{sheet}: titres d'impression conformes")


@checker("page_setup")
def check_page_setup(ctx, params) -> CheckResult:
    sheet = params["sheet"]
    ws = ctx.sheet_f(sheet)
    if ws is None:
        return fail(f"feuille «{sheet}» introuvable")
    ps = ws.page_setup
    if params.get("orientation"):
        if (ps.orientation or "portrait") != params["orientation"]:
            return fail(f"{sheet}: orientation {ps.orientation} ≠ {params['orientation']}")
    if params.get("fit_to_width"):
        want = int(params["fit_to_width"])
        if (ps.fitToWidth or 0) != want or not ws.sheet_properties.pageSetUpPr.fitToPage:
            return fail(f"{sheet}: ajuster largeur={ps.fitToWidth} (attendu {want} + fitToPage)")
    if params.get("fit_to_height"):
        want = int(params["fit_to_height"])
        if (ps.fitToHeight or 0) != want:
            return fail(f"{sheet}: ajuster hauteur={ps.fitToHeight} ≠ {want}")
    return ok(f"{sheet}: mise en page conforme")


@checker("header_footer")
def check_header_footer(ctx, params) -> CheckResult:
    sheet = params["sheet"]
    ws = ctx.sheet_f(sheet)
    if ws is None:
        return fail(f"feuille «{sheet}» introuvable")
    hf = ws.oddHeader if params.get("part", "footer") == "header" else ws.oddFooter
    position = params.get("position", "center")   # left/center/right
    section = getattr(hf, position)
    text = section.text or ""

    contains = params.get("contains")
    if contains and contains not in text:
        return fail(f"{sheet}: {params.get('part','footer')} {position}=«{text}» "
                    f"ne contient pas «{contains}»")
    # Page-number codes: &P (page), &N (total).
    if params.get("page_number") and "&P" not in text and "&[Page]" not in text:
        return fail(f"{sheet}: pas de numéro de page (texte=«{text}»)")
    if params.get("page_of_total") and not ("&P" in text and "&N" in text):
        return fail(f"{sheet}: format «Page X de Y» absent (texte=«{text}»)")
    return ok(f"{sheet}: en-tête/pied conforme")
