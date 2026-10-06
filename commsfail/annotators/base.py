"""The annotator contract.

An annotator is a class with ``name``, ``version`` and ``annotate(trace) -> dict``; the dict must pass
``commsfail.schema.validate``. Anything that reads a Trace and emits analysis.v1 qualifies: a regex pass,
a model-as-judge, an importer of human labels, an ensemble. ``base_analysis`` builds the skeleton so an
annotator only has to fill metrics, items and the mode entries it has evidence for.
"""
from __future__ import annotations
from typing import Protocol, runtime_checkable
from ..schema import SCHEMA, MODES, empty_annotation
from ..trace import Trace

@runtime_checkable
class Annotator(Protocol):
    name: str
    version: str
    def annotate(self, trace: Trace) -> dict: ...

def base_analysis(trace: Trace, annotator: "Annotator") -> dict:
    """A conforming analysis with every mode absent; annotators fill it in."""
    return {
        "schema": SCHEMA,
        "source": {**trace.source, "annotator": f"{annotator.name}@{annotator.version}"},
        "room": {"name": trace.room.get("name"), "created_at": trace.room.get("created_at"),
                 "latest_sequence": trace.room.get("latest_sequence"), "seats": trace.seats},
        "metrics": {"posts": len(trace.posts), "seats": len(trace.seats), "asks": 0, "asks_unanswered": 0, "claims": 0,
                    "re_claims": 0, "heartbeat_posts": 0, "heartbeat_share": 0.0, "open_items_at_end": 0, "last_post_kind": "other"},
        "items": {},
        "modes": [{"id": mid, "name": name, "group": group, "present": False, "severity": "none", "count": 0,
                   "confidence": 0.0, "removed_by": layer, "evidence": []} for mid, (name, group, layer) in MODES.items()],
        "annotation": empty_annotation(),
        "caveats": [],
    }

def set_mode(analysis: dict, mid: str, *, evidence: list, severity: str, confidence: float, count: int | None = None) -> None:
    for x in analysis["modes"]:
        if x["id"] == mid:
            x.update({"present": bool(evidence) or (count or 0) > 0, "severity": severity, "confidence": confidence,
                      "count": len(evidence) if count is None else count, "evidence": evidence[:25]})
            return
    raise KeyError(mid)

def severity_for(rate: float, high: float, medium: float, low: float) -> str:
    return "high" if rate >= high else "medium" if rate >= medium else "low" if rate >= low else "none"
