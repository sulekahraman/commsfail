"""The ten communication-failure modes, and helpers for annotators that report them.

Optional. Use it when your annotator speaks this taxonomy, so its output lines up with regex_v1 column for
column, and copy regex_v1/schema.json as your schema. An annotator that reports something else writes its
own schema and does not need this module.
"""
from __future__ import annotations
from ..trace import Trace

ANALYSIS_SCHEMA = "comms-failure/analysis.v1"

# id -> (name, group, the layer of a structured board that removes it)
MODES = {
    "R1":  ("Open-set decay",            "not_read",    "view"),
    "R2":  ("Replacement re-does work",  "not_read",    "view"),
    "B1":  ("Belief without commitment", "not_binding", "naming"),
    "B2":  ("Identity drift",            "not_binding", "check"),
    "D1":  ("Unattested action",         "never_done",  "check"),
    "D2":  ("Review of nothing",         "never_done",  "check"),
    "D3":  ("Closure before budget",     "never_done",  "none"),
    "D4":  ("Capability not routed",     "never_done",  "none"),
    "REP": ("Step repetition",           "not_read",    "view"),
    "HB":  ("Heartbeat cost",            "never_done",  "none"),
}
SEVERITIES = ("none", "low", "medium", "high", "unknown")
LAYERS = ("naming", "view", "check", "none")

def empty_annotation() -> dict:
    """The slots a human annotation pass fills: labels, facts, what was uncertain, who annotated."""
    return {"labels": {"accept": {}, "result": {}, "review_pass": {}},
            "facts": {"delivered": {}, "acted": {}, "passed": {}},
            "uncertain": [], "annotators": [], "adjudicated": False}

def base_analysis(trace: Trace, annotator) -> dict:
    """An analysis.v1 output with every mode absent. Fill metrics, items and the modes you have evidence for."""
    return {
        "schema": ANALYSIS_SCHEMA,
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
    """Fill one mode. Evidence rows are {seq, who, excerpt, why}; at most 25 are kept."""
    for x in analysis["modes"]:
        if x["id"] == mid:
            x.update({"present": bool(evidence) or (count or 0) > 0, "severity": severity, "confidence": confidence,
                      "count": len(evidence) if count is None else count, "evidence": evidence[:25]})
            return
    raise KeyError(mid)

def severity_for(rate: float, high: float, medium: float, low: float) -> str:
    return "high" if rate >= high else "medium" if rate >= medium else "low" if rate >= low else "none"
