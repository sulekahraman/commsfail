"""commsfail: communication-failure analysis of multi-agent message boards.

A board is any place where several agents post to one ordered log and read each other: a SharedNet Room,
a group chat, a shared forum. commsfail reads one board into a ``Trace``, runs an ``Annotator`` over it and
writes one ``analysis.v1`` record: room-level metrics, the work items that were claimed, done and reviewed,
and one entry per failure mode with severity, confidence and evidence rows a human can check.

    from commsfail import load_trace, get_annotator, validate
    trace = load_trace("room.ndjson")                     # or a share link, a saved share JSON, an episode dir
    record = get_annotator("regex_v1").annotate(trace)    # a dict; validate(record) == []

Modules:

- ``commsfail.trace``       the Trace shape and the SharedNet loaders (share link, share JSON, room export, episode dir)
- ``commsfail.loaders``     the loader registry; plugins add formats through the ``commsfail.loaders`` entry point
- ``commsfail.annotators``  the annotator contract, ``regex_v1`` and the registry; plugins use ``commsfail.annotators``
- ``commsfail.schema``      the analysis.v1 contract and ``validate()``
- ``commsfail.cli``         ``commsfail analyse | annotators | loaders | schema | validate``

``REGISTRY`` and ``LOADERS`` are resolved on first access, not on import, so a plugin module may import
commsfail freely.
"""
from __future__ import annotations
from .trace import Trace, load_trace, parse_ts
from .schema import SCHEMA, MODES, validate
from .annotators import Annotator, base_analysis, set_mode, severity_for, get_annotator
from .loaders import get_loader

__version__ = "0.1.0"
__all__ = ["Trace", "load_trace", "parse_ts", "SCHEMA", "MODES", "validate", "Annotator", "base_analysis",
           "set_mode", "severity_for", "get_annotator", "get_loader", "REGISTRY", "LOADERS", "__version__"]

def __getattr__(name: str):
    if name == "REGISTRY":
        from .annotators import registry
        return registry()
    if name == "LOADERS":
        from .loaders import loaders
        return loaders()
    raise AttributeError(f"module 'commsfail' has no attribute {name!r}")
