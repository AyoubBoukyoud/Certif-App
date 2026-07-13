"""Table, conditional-formatting and column-presence checkers."""
from __future__ import annotations

import unicodedata

from .base import CheckResult, as_bool, checker, fail, ok


def _nfc(s):
    return unicodedata.normalize("NFC", str(s)).strip().casefold()


@checker("table_exists")
def check_table_exists(ctx, params) -> CheckResult:
    sheet = params["sheet"]
    ws = ctx.sheet_f(sheet)
    if ws is None:
        return fail(f"feuille «{sheet}» introuvable")
    tables = getattr(ws, "tables", {})
    if not tables:
        return fail(f"{sheet}: aucun tableau")
    ref = params.get("ref")
    name = params.get("name")
    for tname in tables:
        t = tables[tname]
        if name and tname.casefold() != name.casefold():
            continue
        if ref and str(t.ref).replace("$", "") != ref.replace("$", ""):
            continue
        return ok(f"{sheet}: tableau «{tname}» ({t.ref})")
    return fail(f"{sheet}: aucun tableau ne correspond (ref={ref}, name={name})")


@checker("table_absent")
def check_table_absent(ctx, params) -> CheckResult:
    """Table converted back to a range: sheet must have no table objects."""
    sheet = params["sheet"]
    ws = ctx.sheet_f(sheet)
    if ws is None:
        return fail(f"feuille «{sheet}» introuvable")
    tables = getattr(ws, "tables", {})
    if tables:
        return fail(f"{sheet}: tableau encore présent ({list(tables)})")
    return ok(f"{sheet}: converti en plage")


@checker("table_style_name")
def check_table_style_name(ctx, params) -> CheckResult:
    sheet, style = params["sheet"], params["style"]
    ws = ctx.sheet_f(sheet)
    if ws is None:
        return fail(f"feuille «{sheet}» introuvable")
    tables = getattr(ws, "tables", {})
    name = params.get("name")
    for tname in tables:
        if name and tname.casefold() != name.casefold():
            continue
        si = tables[tname].tableStyleInfo
        actual = si.name if si else None
        if actual == style:
            return ok(f"{sheet}: «{tname}» style {actual}")
        return fail(f"{sheet}: «{tname}» style {actual} ≠ {style}")
    return fail(f"{sheet}: tableau introuvable pour style")


@checker("table_style_option")
def check_table_style_option(ctx, params) -> CheckResult:
    """Banded rows / columns toggles on a table."""
    sheet = params["sheet"]
    ws = ctx.sheet_f(sheet)
    if ws is None:
        return fail(f"feuille «{sheet}» introuvable")
    option = params.get("option", "showRowStripes")
    expected = as_bool(params.get("expected"), True)
    name = params.get("name")
    tables = getattr(ws, "tables", {})
    for tname in tables:
        if name and tname.casefold() != name.casefold():
            continue
        si = tables[tname].tableStyleInfo
        actual = bool(getattr(si, option, False)) if si else False
        if actual == expected:
            return ok(f"{sheet}: «{tname}» {option}={actual}")
        return fail(f"{sheet}: «{tname}» {option}={actual} ≠ {expected}")
    return fail(f"{sheet}: tableau introuvable")


@checker("conditional_formatting")
def check_conditional_formatting(ctx, params) -> CheckResult:
    sheet = params["sheet"]
    ws = ctx.sheet_f(sheet)
    if ws is None:
        return fail(f"feuille «{sheet}» introuvable")
    want_type = params.get("rule_type")     # e.g. aboveAverage, cellIs, colorScale
    want_range = params.get("range")
    found = []
    for rng, rules in ws.conditional_formatting._cf_rules.items():
        rng_str = str(rng.sqref) if hasattr(rng, "sqref") else str(rng)
        for rule in rules:
            found.append((rng_str, rule.type))
            type_ok = (want_type is None) or (rule.type == want_type)
            range_ok = (want_range is None) or (want_range.replace("$", "") in rng_str.replace("$", ""))
            if type_ok and range_ok:
                # optional: aboveAverage direction
                if params.get("above_average") is not None and rule.type == "aboveAverage":
                    if bool(rule.aboveAverage) != as_bool(params.get("above_average")):
                        continue
                return ok(f"{sheet}: règle {rule.type} sur {rng_str}")
    return fail(f"{sheet}: aucune mise en forme conditionnelle correspondante "
                f"(type={want_type}, plage={want_range}; trouvé={found})")


@checker("column_absent")
def check_column_absent(ctx, params) -> CheckResult:
    """A column whose header matched has been deleted."""
    sheet, header = params["sheet"], params["header"]
    header_row = int(params.get("header_row", 1))
    ws = ctx.sheet_f(sheet)
    if ws is None:
        return fail(f"feuille «{sheet}» introuvable")
    want = _nfc(header)
    for cell in ws[header_row]:
        if cell.value is not None and _nfc(cell.value) == want:
            return fail(f"{sheet}: colonne «{header}» toujours présente ({cell.coordinate})")
    return ok(f"{sheet}: colonne «{header}» supprimée")
