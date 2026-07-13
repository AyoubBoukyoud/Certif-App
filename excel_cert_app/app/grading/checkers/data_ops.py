"""Sorting and de-duplication checkers (value-level data operations)."""
from __future__ import annotations

from .base import CheckResult, checker, fail, ok


def _data_rows(ws, header_row: int):
    """Yield lists of cell values for rows below the header."""
    for r in range(header_row + 1, ws.max_row + 1):
        yield r, [c.value for c in ws[r]]


@checker("sort_order")
def check_sort_order(ctx, params) -> CheckResult:
    """Verify rows are ordered by one or more columns.

    ``by`` is a comma list like "Pays:asc,Code:asc,Matricule:asc". An optional
    ``custom_order`` (pipe list) fixes the ordering of the first key's values
    (e.g. "États-Unis|Canada").
    """
    sheet = params["sheet"]
    ws = ctx.sheet_v(sheet)
    if ws is None:
        return fail(f"feuille «{sheet}» introuvable")
    header_row = int(params.get("header_row", 1))

    keys = []
    for spec in params["by"].split(","):
        name, _, direction = spec.partition(":")
        col = ctx.header_column(ws, name.strip(), header_row)
        if not col:
            return fail(f"{sheet}: colonne «{name}» introuvable")
        from openpyxl.utils import column_index_from_string
        keys.append((column_index_from_string(col) - 1,
                     (direction or "asc").lower().startswith("d")))

    custom = None
    if params.get("custom_order"):
        custom = {v.strip(): i for i, v in enumerate(params["custom_order"].split("|"))}

    def sort_key(values):
        out = []
        for i, (ci, desc) in enumerate(keys):
            v = values[ci] if ci < len(values) else None
            if i == 0 and custom is not None:
                rank = custom.get(str(v), len(custom))
                out.append(rank)
            else:
                out.append(_Comparable(v, desc))
        return out

    rows = [vals for _, vals in _data_rows(ws, header_row)
            if any(x is not None for x in vals)]
    prev = None
    for vals in rows:
        k = sort_key(vals)
        if prev is not None and _key_gt(prev, k):
            return fail(f"{sheet}: ordre de tri incorrect")
        prev = k
    return ok(f"{sheet}: {len(rows)} lignes triées correctement")


class _Comparable:
    """Wraps a value so None sorts last and desc inverts comparison."""
    __slots__ = ("v", "desc")

    def __init__(self, v, desc):
        self.v = v
        self.desc = desc

    def _cmp_val(self):
        v = self.v
        return (v is None, str(v) if not isinstance(v, (int, float)) else v)


def _key_gt(a, b) -> bool:
    """True if key ``a`` should come strictly after ``b`` (i.e. mis-ordered)."""
    for x, y in zip(a, b):
        xv = x._cmp_val() if isinstance(x, _Comparable) else (False, x)
        yv = y._cmp_val() if isinstance(y, _Comparable) else (False, y)
        desc = isinstance(x, _Comparable) and x.desc
        try:
            if xv == yv:
                continue
            gt = xv > yv
        except TypeError:
            gt = str(xv) > str(yv)
        return (not gt) if desc else gt
    return False


@checker("dedup_rows")
def check_dedup_rows(ctx, params) -> CheckResult:
    """No duplicate values remain in the key column(s)."""
    sheet = params["sheet"]
    ws = ctx.sheet_v(sheet)
    if ws is None:
        return fail(f"feuille «{sheet}» introuvable")
    header_row = int(params.get("header_row", 1))
    from openpyxl.utils import column_index_from_string

    cols = []
    for name in params["key"].split(","):
        col = ctx.header_column(ws, name.strip(), header_row)
        if not col:
            return fail(f"{sheet}: colonne clé «{name}» introuvable")
        cols.append(column_index_from_string(col) - 1)

    seen = set()
    for _, vals in _data_rows(ws, header_row):
        if all(vals[c] is None for c in cols if c < len(vals)):
            continue
        key = tuple(vals[c] if c < len(vals) else None for c in cols)
        if key in seen:
            return fail(f"{sheet}: doublon restant {key}")
        seen.add(key)

    if params.get("expected_rows"):
        want = int(params["expected_rows"])
        if len(seen) != want:
            return fail(f"{sheet}: {len(seen)} lignes uniques (attendu {want})")
    return ok(f"{sheet}: aucun doublon ({len(seen)} enregistrements)")
