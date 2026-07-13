"""Import every checker module so the registry is fully populated."""
from . import (  # noqa: F401
    cells,
    data_ops,
    docprops,
    formatting,
    pagelayout,
    rawxml,
    structure,
)
from .base import REGISTRY, CheckResult  # noqa: F401
