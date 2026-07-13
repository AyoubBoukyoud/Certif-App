"""Checkers that inspect raw OOXML parts openpyxl does not fully surface:
charts, sparklines, drawing alt-text and rotation, chart sheets, table alt-text.

All XPath uses ``local-name()`` so we don't fight XML namespaces.
"""
from __future__ import annotations

from lxml import etree

from .base import CheckResult, as_bool, checker, fail, ok


def _ln(tag: str) -> str:
    return f"*[local-name()='{tag}']"


def _iter_parts(ctx, prefix: str):
    for name in ctx.namelist():
        if name.startswith(prefix) and name.endswith(".xml"):
            data = ctx.read_xml(name)
            if data:
                yield name, etree.fromstring(data)


def _all_text(el) -> str:
    return "".join(el.itertext())


@checker("chart_exists")
def check_chart_exists(ctx, params) -> CheckResult:
    """A chart of the given OOXML element type exists (e.g. pie3DChart, bar3DChart)."""
    want = params["chart_type"]          # local-name of the plot element
    for name, root in _iter_parts(ctx, "xl/charts/chart"):
        if root.xpath(f".//{_ln(want)}"):
            return ok(f"graphique {want} présent ({name})")
    return fail(f"aucun graphique de type «{want}»")


@checker("chartsheet_exists")
def check_chartsheet_exists(ctx, params) -> CheckResult:
    sheets = [n for n in ctx.namelist() if n.startswith("xl/chartsheets/sheet")]
    if not sheets:
        return fail("aucune feuille de graphique")
    # openpyxl exposes titles via wb.chartsheets when a name is required.
    name = params.get("name")
    if name:
        titles = [cs.title for cs in ctx.wb_formulas.chartsheets]
        if not any(t.casefold() == name.casefold() for t in titles):
            return fail(f"feuille de graphique «{name}» absente (trouvé {titles})")
    return ok("feuille de graphique présente")


@checker("chart_titles")
def check_chart_titles(ctx, params) -> CheckResult:
    """The (first matching) chart contains the requested title/axis-title texts."""
    wanted = {k: params[k] for k in ("title", "value_axis", "cat_axis") if params.get(k)}
    for name, root in _iter_parts(ctx, "xl/charts/chart"):
        text = _all_text(root)
        if all(v in text for v in wanted.values()):
            return ok(f"titres du graphique conformes ({name})")
    return fail(f"titres attendus {list(wanted.values())} introuvables")


@checker("chart_series")
def check_chart_series(ctx, params) -> CheckResult:
    """Chart has at least N series and/or references a given column name."""
    min_series = int(params.get("min_series", 1))
    refs = params.get("references")
    for name, root in _iter_parts(ctx, "xl/charts/chart"):
        sers = root.xpath(f".//{_ln('ser')}")
        text = _all_text(root)
        if len(sers) >= min_series and (refs is None or refs in text):
            return ok(f"{len(sers)} séries ({name})")
    return fail(f"aucun graphique avec ≥ {min_series} séries"
                + (f" référençant «{refs}»" if refs else ""))


@checker("sparkline")
def check_sparkline(ctx, params) -> CheckResult:
    """Sparkline group of a given type exists on a sheet.

    Sheet is resolved to its part via the workbook's sheet order.
    """
    sheet = params["sheet"]
    want_type = params.get("spark_type", "column")   # column | line | stacked
    ws = ctx.sheet_f(sheet)
    if ws is None:
        return fail(f"feuille «{sheet}» introuvable")
    idx = ctx.wb_formulas.worksheets.index(ws) + 1
    data = ctx.read_xml(f"xl/worksheets/sheet{idx}.xml")
    if data is None:
        return fail(f"partie de feuille introuvable pour «{sheet}»")
    root = etree.fromstring(data)
    groups = root.xpath(f".//{_ln('sparklineGroup')}")
    if not groups:
        return fail(f"{sheet}: aucun graphique sparkline")
    for g in groups:
        gtype = g.get("type", "column")   # attribute absent => column histogram
        if want_type == "column" and gtype in ("column", "", None):
            return ok(f"{sheet}: sparkline histogramme")
        if gtype == want_type:
            return ok(f"{sheet}: sparkline {want_type}")
    return fail(f"{sheet}: aucun sparkline de type «{want_type}»")


@checker("shape_alt_text")
def check_shape_alt_text(ctx, params) -> CheckResult:
    """Alt-text title/description on a drawing shape (cNvPr title/descr)."""
    expected = params["title"]
    field = params.get("field", "title")   # title | descr
    for name, root in _iter_parts(ctx, "xl/drawings/drawing"):
        for cnv in root.xpath(f".//{_ln('cNvPr')}"):
            if (cnv.get(field) or "").strip() == expected.strip():
                return ok(f"texte de remplacement «{expected}» présent ({name})")
    return fail(f"texte de remplacement «{expected}» introuvable")


@checker("table_alt_text")
def check_table_alt_text(ctx, params) -> CheckResult:
    """Alt-text title on a table part (table element carries the attribute)."""
    expected = params["title"]
    for name, root in _iter_parts(ctx, "xl/tables/table"):
        # Excel stores the table alt-text title on the root <table> element.
        if (root.get("title") or "").strip() == expected.strip() \
                or expected in _all_text(root):
            return ok(f"texte de remplacement de tableau «{expected}» présent ({name})")
    return fail(f"texte de remplacement de tableau «{expected}» introuvable")


@checker("image_rotation")
def check_image_rotation(ctx, params) -> CheckResult:
    """Image rotation equals the expected degrees (default 0)."""
    want_deg = float(params.get("degrees", 0))
    want_rot = int(round(want_deg * 60000))   # OOXML stores 1/60000 degree
    for name, root in _iter_parts(ctx, "xl/drawings/drawing"):
        for xfrm in root.xpath(f".//{_ln('xfrm')}"):
            rot = int(xfrm.get("rot", "0"))
            if rot == want_rot:
                return ok(f"rotation {want_deg}° ({name})")
    if want_deg == 0:
        # No rot attribute anywhere also means 0°.
        return ok("rotation 0° (aucune rotation appliquée)")
    return fail(f"rotation {want_deg}° introuvable")
