"""Taxonomies: each annotator owns one, in ``taxonomy.json`` next to its code.

There is no global taxonomy. Different methods cut failures differently, and each annotator states its own
cut as data:

    {"id": "...", "version": "1", "description": "...",
     "groups": [{"id", "name", "definition"}],                      optional
     "modes":  [{"id", "name", "definition",
                 "group": "<a group id>",                           optional
                 "maps_to": ["<annotator>:<mode id>", ...],         optional: the same failure in another taxonomy
                 ...}]}                                             any other field is the annotator's own

``maps_to`` is what keeps different taxonomies comparable: regex_v1's ten modes are the shared reference
that most taxonomies here map onto. The contract tests check that every ``maps_to`` names a real mode.

An annotator with a taxonomy also implements ``modes_in(output)``: the mode ids an output reports. The
contract tests check that they are all in its taxonomy.

The second half of this module helps annotators whose output is ``comms-failure/analysis.v1`` (regex_v1's
format): the output lists every mode of the annotator's taxonomy, present or not.
"""
from __future__ import annotations
import inspect, json
from functools import lru_cache
from pathlib import Path
from ..trace import Trace

def taxonomy_path(annotator) -> Path | None:
    """Where the annotator's taxonomy file would be, or None when it is given inline as a dict."""
    cls = annotator if isinstance(annotator, type) else type(annotator)
    t = getattr(cls, "taxonomy", "taxonomy.json")
    return None if isinstance(t, dict) else Path(inspect.getfile(cls)).resolve().parent / t

@lru_cache(maxsize=None)
def load_taxonomy(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))

def taxonomy_of(annotator) -> dict | None:
    """The annotator's taxonomy, or None when it has none."""
    cls = annotator if isinstance(annotator, type) else type(annotator)
    t = getattr(cls, "taxonomy", "taxonomy.json")
    if isinstance(t, dict):
        return t
    p = taxonomy_path(cls)
    return load_taxonomy(str(p)) if p.is_file() else None

def mode_ids(taxonomy: dict) -> list[str]:
    return [m["id"] for m in taxonomy["modes"]]

def check_taxonomy(tax, registry: dict | None = None) -> list[str]:
    """Problems with a taxonomy. With a registry, also check that every maps_to names a real mode."""
    if not isinstance(tax, dict):
        return ["a taxonomy must be a JSON object"]
    errs = [f"the taxonomy needs a non-empty string '{k}'" for k in ("id", "version", "description")
            if not isinstance(tax.get(k), str) or not tax[k]]
    groups = tax.get("groups", [])
    if not isinstance(groups, list) or not all(isinstance(g, dict) for g in groups):
        return errs + ["'groups' must be a list of objects"]
    gids = [g.get("id") for g in groups]
    for g in groups:
        errs += [f"group {g.get('id')!r} needs a non-empty string '{k}'" for k in ("id", "name", "definition")
                 if not isinstance(g.get(k), str) or not g[k]]
    if len(set(gids)) != len(gids):
        errs.append("group ids must be unique")
    modes = tax.get("modes")
    if not isinstance(modes, list) or not modes or not all(isinstance(m, dict) for m in modes):
        return errs + ["'modes' must be a non-empty list of objects"]
    ids = [m.get("id") for m in modes]
    if len(set(ids)) != len(ids):
        errs.append("mode ids must be unique")
    for m in modes:
        mid = m.get("id")
        errs += [f"mode {mid!r} needs a non-empty string '{k}'" for k in ("id", "name", "definition")
                 if not isinstance(m.get(k), str) or not m[k]]
        if "group" in m and m["group"] not in gids:
            errs.append(f"mode {mid!r} is in group {m['group']!r}, which 'groups' does not define")
        targets = m.get("maps_to", [])
        if not isinstance(targets, list) or not all(isinstance(t, str) and t.count(":") == 1 for t in targets):
            errs.append(f"mode {mid!r}: 'maps_to' must be a list of '<annotator>:<mode id>'")
            continue
        if registry is not None:
            for t in targets:
                name, target = t.split(":")
                other = taxonomy_of(registry[name]) if name in registry else None
                if other is None:
                    errs.append(f"mode {mid!r} maps to {t}, but no installed annotator {name!r} has a taxonomy")
                elif target not in mode_ids(other):
                    errs.append(f"mode {mid!r} maps to {t}, but {name}'s taxonomy has no mode {target!r}")
    return errs

# ---- helpers for annotators whose output is analysis.v1

ANALYSIS_SCHEMA = "comms-failure/analysis.v1"
SEVERITIES = ("none", "low", "medium", "high", "unknown")
LAYERS = ("naming", "view", "check", "none")

def empty_annotation() -> dict:
    """The slots a human annotation pass fills: labels, facts, what was uncertain, who annotated."""
    return {"labels": {"accept": {}, "result": {}, "review_pass": {}},
            "facts": {"delivered": {}, "acted": {}, "passed": {}},
            "uncertain": [], "annotators": [], "adjudicated": False}

def base_analysis(trace: Trace, annotator) -> dict:
    """An analysis.v1 output with every mode of the annotator's taxonomy absent. Fill metrics, items and the
    modes you have evidence for."""
    return {
        "schema": ANALYSIS_SCHEMA,
        "source": {**trace.source, "annotator": f"{annotator.name}@{annotator.version}"},
        "room": {"name": trace.room.get("name"), "created_at": trace.room.get("created_at"),
                 "latest_sequence": trace.room.get("latest_sequence"), "seats": trace.seats},
        "metrics": {"posts": len(trace.posts), "seats": len(trace.seats), "asks": 0, "asks_unanswered": 0, "claims": 0,
                    "re_claims": 0, "heartbeat_posts": 0, "heartbeat_share": 0.0, "open_items_at_end": 0, "last_post_kind": "other"},
        "items": {},
        "modes": [{"id": m["id"], "name": m["name"], "group": m.get("group"), "present": False, "severity": "none",
                   "count": 0, "confidence": 0.0, "removed_by": m.get("removed_by", "none"), "evidence": []}
                  for m in taxonomy_of(annotator)["modes"]],
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
