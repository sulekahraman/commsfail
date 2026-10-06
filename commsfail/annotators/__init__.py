"""The annotator registry: the built-in annotators plus any installed package that declares one.

    [project.entry-points."commsfail.annotators"]
    my_v1 = "my_package.annotators:MyV1"

A class is keyed by its own ``name`` attribute; the entry-point name is only the fallback. ``REGISTRY`` is
resolved on first access; ``discover()`` is the uncached form. To add an annotator to this package, add it
to ``BUILTIN`` after it passes the contract tests.
"""
from __future__ import annotations
from functools import lru_cache
from .base import Annotator, base_analysis, set_mode, severity_for
from .regex_v1 import RegexV1
from .._plugins import load_group

ENTRY_POINT_GROUP = "commsfail.annotators"
BUILTIN: dict[str, type] = {
    RegexV1.name: RegexV1,
}

def discover() -> dict[str, type]:
    """Built-in annotators plus installed plugins, freshly resolved."""
    return load_group(ENTRY_POINT_GROUP, BUILTIN, key=lambda cls, ep: getattr(cls, "name", ep.name))

@lru_cache(maxsize=None)
def registry() -> dict[str, type]:
    return discover()

def get_annotator(name: str) -> Annotator:
    reg = registry()
    try:
        return reg[name]()
    except KeyError:
        raise SystemExit(f"unknown annotator '{name}'; available: {', '.join(sorted(reg))}") from None

def origin(cls: type) -> str:
    """'builtin' for annotators shipped here, otherwise the module the plugin class lives in."""
    return "builtin" if cls.__module__.startswith("commsfail.") else cls.__module__

def __getattr__(name: str):
    if name == "REGISTRY":
        return registry()
    raise AttributeError(f"module 'commsfail.annotators' has no attribute {name!r}")

__all__ = ["Annotator", "base_analysis", "set_mode", "severity_for", "RegexV1", "ENTRY_POINT_GROUP", "BUILTIN",
           "discover", "registry", "get_annotator", "origin", "REGISTRY"]
