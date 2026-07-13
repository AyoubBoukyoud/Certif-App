"""Document-property checkers (read from docProps/*.xml in the ZIP)."""
from __future__ import annotations

from lxml import etree

from .base import CheckResult, checker, fail, ok

_APP = "{http://schemas.openxmlformats.org/officeDocument/2006/extended-properties}"


@checker("doc_property")
def check_doc_property(ctx, params) -> CheckResult:
    prop = params["property"]          # e.g. Company, Manager, Title, Creator
    expected = params["value"]

    # Company/Manager live in app.xml; core props (Title, Creator...) in core.xml.
    if prop in ("Company", "Manager", "Application"):
        data = ctx.read_xml("docProps/app.xml")
        if data is None:
            return fail("docProps/app.xml absent")
        root = etree.fromstring(data)
        el = root.find(f"{_APP}{prop}")
        actual = el.text if el is not None else None
    else:
        data = ctx.read_xml("docProps/core.xml")
        if data is None:
            return fail("docProps/core.xml absent")
        root = etree.fromstring(data)
        actual = None
        for el in root.iter():
            if etree.QName(el).localname.lower() == prop.lower():
                actual = el.text
                break

    if (actual or "").strip() == expected.strip():
        return ok(f"propriété {prop} = «{actual}»")
    return fail(f"propriété {prop} = «{actual}» ≠ «{expected}»")
