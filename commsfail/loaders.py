"""The loader registry. A loader is any ``callable(source: str) -> Trace``.

Built in, as ``auto``: the SharedNet formats behind ``commsfail.trace.load_trace`` (a share link or token, a
saved share JSON, a ``sharednet room export`` NDJSON, a bench episode directory). Any other transcript format
is a plugin: a function in your package plus one entry point.

    [project.entry-points."commsfail.loaders"]
    chat_jsonl = "my_package.loaders:load_chat_jsonl"

``LOADERS`` is resolved on first access; ``discover()`` is the uncached form.
"""
from __future__ import annotations
from functools import lru_cache
from typing import Callable
from ._plugins import load_group
from .trace import Trace, load_trace

ENTRY_POINT_GROUP = "commsfail.loaders"
Loader = Callable[[str], Trace]
BUILTIN: dict[str, Loader] = {"auto": load_trace}

def discover() -> dict[str, Loader]:
    """Built-in loaders plus installed plugins, freshly resolved."""
    return load_group(ENTRY_POINT_GROUP, BUILTIN)

@lru_cache(maxsize=None)
def loaders() -> dict[str, Loader]:
    return discover()

def get_loader(name: str) -> Loader:
    reg = loaders()
    try:
        return reg[name]
    except KeyError:
        raise SystemExit(f"unknown loader '{name}'; available: {', '.join(sorted(reg))}") from None

def __getattr__(name: str):
    if name == "LOADERS":
        return loaders()
    raise AttributeError(f"module 'commsfail.loaders' has no attribute {name!r}")

__all__ = ["ENTRY_POINT_GROUP", "BUILTIN", "Loader", "discover", "loaders", "get_loader", "LOADERS"]
